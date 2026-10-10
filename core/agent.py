import re
import time
from typing import List, Optional

# Monitor de recursos (opcional)
try:
    from core.utils.monitor import monitor_resources
    MONITOR_AVAILABLE = True
except ImportError:
    MONITOR_AVAILABLE = False


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
        top_k: int = 1,
        system_instruction: Optional[str] = None,
    ):
        self.retriever = retriever
        self.ollama_client = ollama_client
        self.top_k = top_k
        self.system_instruction = system_instruction or (
            "Eres un asistente virtual útil. Responde a la pregunta del usuario utilizando "
            "únicamente la información proporcionada en el contexto a continuación. Si el contexto no "
            "contiene la respuesta, indica amablemente que no dispones de esa información."
        )

    def ask(
        self,
        pregunta: str,
        source: Optional[str] = None,
        top_k: Optional[int] = None,
        temperature: float = 0.3,
    ) -> tuple[str, dict]:
        k = top_k or self.top_k

        # 1. Recuperar contexto desde el retriever
        chunks = self.retriever.search(pregunta, top_k=k, source=source)

        if chunks:
            raw_context = "\n\n---\n\n".join(chunks)

            # Limpiar contenido (estilo Wabbott)
            cleaned_context = clean_html_content(raw_context)

            chars_before = len(raw_context)
            chars_after = len(cleaned_context)

            # Estimar tokens del contexto limpio (~4 chars/token)
            estimated_tokens = chars_after // 4
            num_ctx = 2048 if estimated_tokens > 800 else 1024

            if estimated_tokens > 800:
                print(f"   [INFO] Contexto grande detectado ({estimated_tokens:,} tokens est.) -> ampliando ventana a {num_ctx}")

            prompt = (
                f"{self.system_instruction}\n\n"
                f"CONTEXTO RECUPERADO:\n{cleaned_context}\n\n"
                f"PREGUNTA: {pregunta}\n\n"
                f"RESPUESTA:"
            )
        else:
            chars_before = 0
            chars_after = 0
            num_ctx = 1024
            prompt = (
                f"{self.system_instruction}\n\n"
                f"No se encontró contexto relevante para la pregunta: '{pregunta}'.\n"
                f"Indica que no tienes suficiente información para responder."
            )

        # 2. Inferencia con monitoreo de recursos
        start_time = time.perf_counter()

        if MONITOR_AVAILABLE:
            with monitor_resources(interval=0.3) as monitor:
                respuesta = self.ollama_client.generate(
                    prompt=prompt, temperature=temperature, num_ctx=num_ctx
                )
                samples = monitor.stop()  # Obtener muestras para métricas
        else:
            respuesta = self.ollama_client.generate(
                prompt=prompt, temperature=temperature, num_ctx=num_ctx
            )
            samples = []

        elapsed_time = time.perf_counter() - start_time

        # 3. Calcular métricas de recursos
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
        }

        return respuesta, metrics