import re
import time
from typing import List, Optional


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
    ) -> str:
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

        # 2. Inferencia y medición del tiempo de respuesta
        start_time = time.perf_counter()
        respuesta = self.ollama_client.generate(
            prompt=prompt, temperature=temperature, num_ctx=num_ctx
        )
        elapsed_time = time.perf_counter() - start_time

        # 3. Mostrar métricas de rendimiento en consola
        print("\n" + "=" * 50)
        print(" [MÉTRICAS DE RENDIMIENTO]")
        print(
            f"   • Reducción de contexto: {chars_before:,} -> {chars_after:,} caracteres"
        )
        print(f"   • Tiempo de respuesta LLM: {elapsed_time:.2f} segundos")
        print("=" * 50 + "\n")

        return respuesta