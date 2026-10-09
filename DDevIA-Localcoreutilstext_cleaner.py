"""Utilidades de limpieza de texto para optimizar chunks RAG antes de enviarlos al LLM.

Adaptado de Wabbott (src/services/businessContext.js) - funcion cleanHtmlContent.
"""

import re
from typing import List


def clean_text(text: str) -> str:
    """
    Limpia texto extrayendo solo el contenido legible.
    Elimina HTML, scripts, estilos, data URIs y normaliza espacios.

    Args:
        text: Texto a limpiar (puede contener HTML, markdown, etc.)

    Returns:
        Texto plano limpio y normalizado.
    """
    if not isinstance(text, str):
        return str(text) if text is not None else ""

    # 1. Eliminar bloques <script> y <style> completos
    text = re.sub(r'<script[\s\S]*?<\/script>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<style[\s\S]*?<\/style>', '', text, flags=re.IGNORECASE)

    # 2. Eliminar comentarios HTML
    text = re.sub(r'<!--[\s\S]*?-->', '', text)

    # 3. Eliminar data URIs (ej. data:image/png;base64,...)
    text = re.sub(r'data:[^;]*;base64,[^"\'\s]*', '', text, flags=re.IGNORECASE)

    # 4. Convertir etiquetas de bloque a saltos de linea
    text = re.sub(r'</p>|</div>|</li>|<br\s*/?>|</h[1-6]>', '\n', text, flags=re.IGNORECASE)

    # 5. Eliminar el resto de etiquetas HTML
    text = re.sub(r'<[^>]+>', '', text)

    # 6. Decodificar entidades HTML comunes
    html_entities = {
        '&nbsp;': ' ',
        '&': '&',
        '<': '<',
        '>': '>',
        '"': '"',
        ''': "'",
        '&apos;': "'",
        '&copy;': '\u00a9',
        '&reg;': '\u00ae',
        '&mdash;': '\u2014',
        '&ndash;': '\u2013',
        '&hellip;': '\u2026',
    }
    for entity, char in html_entities.items():
        text = text.replace(entity, char)

    # 7. Decodificar entidades numericas (&#123; / &#x1F;)
    text = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))) if int(m.group(1)) < 0x110000 else '', text)
    text = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)) if int(m.group(1), 16) < 0x110000 else '', text)

    # 8. Normalizar espacios en blanco (colapsar multiples espacios a uno)
    text = re.sub(r' +', ' ', text)

    # 9. Normalizar saltos de linea (maximo 2 seguidos)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 10. Trim final
    return text.strip()


def clean_chunks(chunks: List[str]) -> List[str]:
    """
    Limpia una lista de chunks de texto.

    Args:
        chunks: Lista de fragmentos de texto a limpiar.

    Returns:
        Lista de chunks limpios (se eliminan chunks vacios tras limpieza).
    """
    cleaned = []
    for chunk in chunks:
        cleaned_chunk = clean_text(chunk)
        if cleaned_chunk:  # Solo mantener chunks no vacios
            cleaned.append(cleaned_chunk)
    return cleaned


def estimate_tokens(text: str, chars_per_token: float = 3.5) -> int:
    """
    Estima el numero de tokens en un texto (aproximado para espanol/ingles).

    Args:
        text: Texto a estimar.
        chars_per_token: Ratio caracteres/token (default 3.5 para texto mixto).

    Returns:
        Estimacion de tokens.
    """
    return max(1, int(len(text) / chars_per_token))


def truncate_chunks_to_token_limit(
    chunks: List[str],
    max_tokens: int,
    chars_per_token: float = 3.5
) -> List[str]:
    """
    Trunca una lista de chunks para no exceder un limite de tokens.

    Args:
        chunks: Lista de chunks (se asume ya limpios y ordenados por relevancia).
        max_tokens: Limite maximo de tokens totales.
        chars_per_token: Ratio para estimacion.

    Returns:
        Lista truncada de chunks que cabe en el limite.
    """
    result = []
    total_tokens = 0

    for chunk in chunks:
        chunk_tokens = estimate_tokens(chunk, chars_per_token)
        if total_tokens + chunk_tokens <= max_tokens:
            result.append(chunk)
            total_tokens += chunk_tokens
        else:
            # Si el chunk individual cabe, pero no todos, lo cortamos
            remaining_chars = int((max_tokens - total_tokens) * chars_per_token)
            if remaining_chars > 100:  # Solo anadir si queda espacio significativo
                result.append(chunk[:remaining_chars] + "...")
            break

    return result


if __name__ == "__main__":
    # Test rapido
    test_html = """
    <html>
    <head><style>body { color: red; }</style></head>
    <body>
        <h1>Titulo Principal</h1>
        <p>Este es un <strong>parrafo</strong> con <a href="#">enlace</a>.</p>
        <p>Otro parrafo con &nbsp; espacios & entidades.</p>
        <script>alert('hola');</script>
        <div>Contenido en div</div>
        <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==">
    </body>
    </html>
    """

    print("=== TEXTO ORIGINAL ===")
    print(test_html[:200])
    print("...")

    cleaned = clean_text(test_html)
    print("\n=== TEXTO LIMPIO ===")
    print(cleaned)
    print(f"\nTokens estimados: {estimate_tokens(cleaned)}")

    # Test con chunks
    test_chunks = [
        "<p>Chunk 1 con <b>HTML</b></p>",
        "<div>Chunk 2</div>",
        "   ",
        "<script>malicious()</script>",
        "Chunk 3 normal",
    ]
    print("\n=== CHUNKS LIMPIOS ===")
    for i, c in enumerate(clean_chunks(test_chunks)):
        print(f"  [{i}] {c}")
