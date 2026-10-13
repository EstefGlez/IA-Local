import re
import time
from typing import List, Optional

# Monitor de recursos (opcional)
try:
    from core.utils.monitor import monitor_resources
    MONITOR_AVAILABLE = True
except ImportError:
    MONITOR_AVAILABLE = False

# RagSourceManager para fuentes dinámicas
try:
    from core.rag_source_manager import RagSourceManager
    RAG_SOURCES_AVAILABLE = True
except ImportError:
    RAG_SOURCES_AVAILABLE = False


def clean_html_content(html: str) -> str:
    """Lógica de limpieza inspirada en Wabbott para reducir ruido de HTML/metadatos."""
    if not html:
        return ""

    # 1. Eliminar bloques <script> y <style>
    text = re.sub(
        r"<script[\s\S]*?<\/script>", "", html, flags=re.IGNORECASE
    )
    text = re.sub(
        r"<style[\s\S]*?<\/style>", "", text, flags=re.IGNORECASE
    )

    # 2. Eliminar comentarios HTML y URIs base64
    text = re.sub(r"<!--[\s\S]*?-->", "", text)
    text = re.sub(r"data:[^;]*;base64,[^\s]*", "", text, flags=re.IGNORECASE)

    # 3. Convertir etiquetas de bloque a saltos de línea
    text = re.sub(
        r"<(p|div|li|br|h[1-6])[^>]*>", "\n", text, flags=re.IGNORECASE
    )

    # 4. Eliminar el resto de etiquetas HTML
    text = re.sub(r"<[^>]+>", "", text)

    # 5. Decodificar entidades HTML comunes
    entities = {
        "&nbsp;": " ",
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&quot;": '"',
        "&#39;": "'",
    }
    for entity, char in entities.items():
        text = text.replace(entity, char)

    # 6. Normalizar espacios
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)

    return text.strip()


class ConversationalAgent:

    def __init__(
        self,
        retriever,
        ollama_client,
        top_k: int = 3,
        system_instruction: Optional[str] = None,
        rag_source_manager=None,
    ):
        self.retriever = retriever
        self.ollama_client = ollama_client
        self.top_k = top_k
        # System prompt conciso: sin saludos repetitivos, directo al grano
        self.system_instruction = system_instruction or (
            "Eres un asistente conciso y directo. Responde basándote en el contexto proporcionado. "
            "Si el contexto no tiene la información, dilo claramente. No repitas saludos ni frases "
            "de cortesía innecesarias en cada turno. Sé breve y útil."
        )
        self.rag_source_manager = rag_source_manager
        self._rag_enabled = True  # Flag para fallback graceful

    def ask(
        self,
        pregunta: str,
        history: Optional[List[dict]] = None,
        source: Optional[str] = None,
        top_k: Optional[int] = None,
        temperature: float = 0.3,
        session_samples: Optional[list] = None,
        session_start_time: Optional[float] = None,
    ) -> tuple[str, dict]:
        """
        Genera una respuesta usando el historial completo de la conversación.

        Args:
            pregunta: Pregunta actual del usuario
            history: Historial de mensajes [{"role": "user|assistant", "content": "..."}]
            source: Fuente RAG específica a filtrar
            top_k: Número de chunks a recuperar
            temperature: Temperatura de muestreo
            session_samples: Lista de muestras de recursos para métricas de sesión
            session_start_time: Timestamp de inicio de sesión

        Returns:
            Tupla (respuesta, metrics_dict)
        """
        k = top_k or self.top_k
        rag_fallback = False

        # 1. Recuperar contexto desde el retriever (si RAG está habilitado)
        if self._rag_enabled and self.rag_source_manager and self.rag_source_manager.has_sources():
            search_source = source
            chunks = self.retriever.search(pregunta, top_k=k, source=search_source)
        else:
            chunks = self.retriever.search(pregunta, top_k=k, source=None)
            rag_fallback = True

        if chunks:
            raw_context = "\n\n---\n\n".join(chunks)
            cleaned_context = clean_html_content(raw_context)

            chars_before = len(raw_context)
            chars_after = len(cleaned_context)

            estimated_tokens = chars_after // 4
            num_ctx = 4096 if estimated_tokens > 800 else 2048

            if estimated_tokens > 800:
                print(f"   [INFO] Contexto grande detectado ({estimated_tokens:,} tokens est.) -> ampliando ventana a {num_ctx}")

            # Construir mensajes para chat: system + context + history + current question
            messages = [
                {"role": "system", "content": self.system_instruction},
                {"role": "system", "content": f"CONTEXTO RECUPERADO:\n{cleaned_context}"},
            ]
        else:
            chars_before = 0
            chars_after = 0
            num_ctx = 2048
            # Modo fallback: sin contexto RAG
            messages = [
                {"role": "system", "content": self.system_instruction},
            ]
            if rag_fallback or not self._rag_enabled:
                messages.append({"role": "system", "content": "[MODO OFFLINE - Sin contexto RAG disponible]"})
            else:
                messages.append({"role": "system", "content": "No se encontró contexto relevante para la pregunta."})

        # Añadir historial de conversación (excluyendo el system prompt actual)
        if history:
            for msg in history:
                if msg["role"] in ("user", "assistant"):
                    messages.append({"role": msg["role"], "content": msg["content"]})

        # Añadir pregunta actual
        messages.append({"role": "user", "content": pregunta})

        # 2. Inferencia con monitoreo de recursos
        start_time = time.perf_counter()

        if MONITOR_AVAILABLE:
            with monitor_resources(
                interval=0.3,
                all_samples=session_samples,
                session_start_time=session_start_time,
            ) as monitor:
                respuesta = self.ollama_client.chat(
                    messages=messages, temperature=temperature, num_ctx=num_ctx
                )
                samples = monitor.stop()
        else:
            respuesta = self.ollama_client.chat(
                messages=messages, temperature=temperature, num_ctx=num_ctx
            )
            samples = []

        elapsed_time = time.perf_counter() - start_time

        # 3. Calcular métricas de recursos (solo de esta inferencia)
        if samples:
            cpu_vals = [s[1] for s in samples]
            ram_vals = [s[2] for s in samples]
            avg_cpu = sum(cpu_vals) / len(cpu_vals)
            cpu_peak = max(cpu_vals)
            avg_ram = sum(ram_vals) / len(ram_vals)
            ram_peak = max(ram_vals)
            num_samples = len(samples)
        else:
            avg_cpu = cpu_peak = avg_ram = ram_peak = 0.0
            num_samples = 0

        # 4. Mostrar métricas de rendimiento en consola
        print("\n" + "=" * 50)
        print(" [MÉTRICAS DE RENDIMIENTO]")
        print(
            f"   • Reducción de contexto: {chars_before:,} -> {chars_after:,} caracteres"
        )
        print(f"   • Tiempo de respuesta LLM: {elapsed_time:.2f} segundos")

        if samples:
            print(f"   • CPU promedio: {avg_cpu:.1f}% (pico: {cpu_peak:.1f}%)")
            print(f"   • RAM promedio: {avg_ram:.1f}% (pico: {ram_peak:.1f}%)")
            print(f"   • Muestras tomadas: {num_samples}")
            print(f"   • Gráfica guardada: performance_dashboard.png")

        print("=" * 50 + "\n")

        # 5. Retornar respuesta + diccionario de métricas
        metrics = {
            "elapsed_time": elapsed_time,
            "avg_cpu": avg_cpu,
            "cpu_peak": cpu_peak,
            "avg_ram": avg_ram,
            "ram_peak": ram_peak,
            "samples": num_samples,
            "dashboard_path": "performance_dashboard.png",
            "session_samples": session_samples,
            "rag_used": not rag_fallback and self._rag_enabled,
            "rag_fallback": rag_fallback,
        }

        return respuesta, metrics

    def set_rag_enabled(self, enabled: bool) -> None:
        """Activa/desactiva el uso de RAG (para fallback graceful)."""
        self._rag_enabled = enabled

    def is_rag_enabled(self) -> bool:
        """Verifica si RAG está habilitado y disponible."""
        return self._rag_enabled and self.rag_source_manager and self.rag_source_manager.has_sources()