import ast
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

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


def trim_history_by_scale(history: List[dict], context_window_scale: float) -> List[dict]:
    """
    Recorta el historial de mensajes según la escala de ventana de contexto.

    Args:
        history: Lista de mensajes [{"role": "user|assistant", "content": "..."}]
        context_window_scale: Float de 0.1 a 1.0

    Returns:
        Historial recortado proporcionalmente
    """
    if not history:
        return []

    if context_window_scale >= 1.0:
        return history

    # Calcular número de mensajes a mantener (mínimo 2 para mantener al menos 1 intercambio)
    total_messages = len(history)
    keep_count = max(2, int(total_messages * context_window_scale))

    # Redondear a número par para mantener pares user/assistant
    if keep_count % 2 != 0:
        keep_count += 1
    keep_count = min(keep_count, total_messages)

    # Tomar los últimos mensajes
    return history[-keep_count:]


def _is_substantive_content(text: str) -> bool:
    """
    Verifica si un texto contiene contenido técnico sustancial (no solo saludos/trivialidades).

    Args:
        text: Texto a evaluar

    Returns:
        True si tiene contenido técnico sustancial, False si es saludo/trivial/vacío
    """
    if not text or not text.strip():
        return False

    text_lower = text.strip().lower()

    # Patrones de saludos/trivialidades comunes
    trivial_patterns = [
        r'^\s*(hola|buenos?\s*d[ií]as?|buenas?\s*tardes?|buenas?\s*noches?)\s*[!?.]*\s*$',
        r'^\s*(hey|hi|hello)\s*[!?.]*\s*$',
        r'^\s*(gracias?|thanks?|thx)\s*[!?.]*\s*$',
        r'^\s*(ok|vale|entendido|entendido\.?|de acuerdo)\s*[!?.]*\s*$',
        r'^\s*(¿qu[eé]\s+puedes?\s+hacer|qu[eé]\s+puedes?\s+hacer)\s*[!?.]*\s*$',
        r'^\s*(¿hay\s+(info|informaci[oó]n|algo))\s*[!?.]*\s*$',
        r'^\s*(c[oó]mo\s+est[aá]s?|qu[eé]\s+tal)\s*[!?.]*\s*$',
        r'^\s*(adios|hasta\s+luego|bye)\s*[!?.]*\s*$',
    ]

    for pattern in trivial_patterns:
        if re.match(pattern, text_lower):
            return False

    # Si tiene muy pocos caracteres y no parece código/técnico
    if len(text.strip()) < 50:
        # Verificar si tiene indicadores técnicos
        tech_indicators = ['def ', 'class ', 'import ', 'function', '```', '```python', '```json',
                          'configuraci[oó]n', 'c[oó]digo', 'script', 'api', 'endpoint',
                          'base de datos', 'sql', 'query', 'tabla', 'esquema',
                          'memoria', 'archivo', 'guardar', 'persistir']
        has_tech = any(re.search(ind, text_lower) for ind in tech_indicators)
        if not has_tech:
            return False

    return True


def _find_last_substantive_assistant_message(history: Optional[List[dict]]) -> Optional[str]:
    """
    Busca en el historial hacia atrás el último mensaje del asistente con contenido sustancial.

    Args:
        history: Lista de mensajes del historial

    Returns:
        Contenido del último mensaje sustancial del asistente, o None si no hay
    """
    if not history:
        return None

    # Recorrer hacia atrás
    for msg in reversed(history):
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            if _is_substantive_content(content):
                return content

    return None


def build_memory_json_from_response(
    assistant_response: str,
    suggested_filename: str,
    tema: str,
    history: Optional[List[dict]] = None
) -> dict:
    """
    Construye el JSON de memoria de forma determinista a partir de la última respuesta
    completa del asistente, preservando TODO el Markdown (explicaciones, bloques de código, etc.)

    Si la respuesta actual está vacía o es trivial (saludo), busca en el historial
    el último mensaje sustancial del asistente.

    Args:
        assistant_response: Texto Markdown completo de la última respuesta del asistente
        suggested_filename: Nombre de archivo sugerido por el modelo
        tema: Tema/resumen breve del contenido
        history: Historial de conversación opcional para fallback

    Returns:
        Diccionario con la estructura completa de memoria lista para guardar
    """
    from datetime import datetime

    # Asegurar extensión .json
    if not suggested_filename.endswith(".json"):
        suggested_filename += ".json"

    # Validar contenido de la respuesta actual
    content_to_save = assistant_response
    used_fallback = False

    if not _is_substantive_content(assistant_response):
        # Buscar en historial si está disponible
        if history:
            fallback_content = _find_last_substantive_assistant_message(history)
            if fallback_content:
                content_to_save = fallback_content
                used_fallback = True
            else:
                # No hay contenido sustancial en historial, usar respuesta actual pero marcar
                content_to_save = assistant_response
                used_fallback = False
        else:
            # Sin historial, usar respuesta actual
            content_to_save = assistant_response
            used_fallback = False

    # Estructura fiel: empaquetar todo el Markdown en content.respuesta_completa
    memory_data = {
        "metadata": {
            "saved_at": datetime.now().isoformat(),
            "filename": suggested_filename,
            "topic": tema,
            "fallback_used": used_fallback
        },
        "content": {
            "respuesta_completa": content_to_save
        }
    }

    return memory_data


def execute_save_json_memory(session_id: str, memory_data: dict) -> dict:
    """
    Ejecuta el guardado físico del archivo de memoria ya construido.

    Args:
        session_id: ID de la sesión actual
        memory_data: Diccionario completo con metadata y content (generado por build_memory_json_from_response)

    Returns:
        Diccionario con resultado de la operación
    """
    try:
        # Asegurar directorio
        memory_dir = Path("./data/archivos_memoria") / session_id
        memory_dir.mkdir(parents=True, exist_ok=True)

        # Obtener filename de metadata
        filename = memory_data.get("metadata", {}).get("filename", "memoria.json")
        if not filename.endswith(".json"):
            filename += ".json"

        filepath = memory_dir / filename

        # Guardar archivo directamente (memory_data ya viene completo y validado)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(memory_data, f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "message": f"Archivo de memoria '{filename}' guardado correctamente en sesión {session_id}",
            "filepath": str(filepath)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error al guardar archivo de memoria: {str(e)}",
            "filepath": None
        }


def _extract_balanced_json(text: str, start_idx: int = 0) -> Optional[str]:
    """
    Extrae un objeto JSON balanceado (con llaves anidadas) desde start_idx.

    Args:
        text: Texto completo
        start_idx: Índice donde empieza el '{' inicial

    Returns:
        String con el JSON balanceado o None si no se encuentra
    """
    if start_idx >= len(text) or text[start_idx] != '{':
        return None

    depth = 0
    in_string = False
    string_char = None
    escape = False

    for i in range(start_idx, len(text)):
        ch = text[i]

        if escape:
            escape = False
            continue

        if ch == '\\':
            escape = True
            continue

        if not in_string:
            if ch in ('"', "'"):
                in_string = True
                string_char = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return text[start_idx:i+1]
        else:
            if ch == string_char:
                in_string = False
                string_char = None

    return None


def _try_parse_json_fallback(text: str) -> Optional[dict]:
    """
    Intenta parsear JSON con varios mecanismos de respaldo tolerantes a errores.

    Estrategias (en orden):
    1. json.loads() estándar
    2. Limpieza de comillas simples -> dobles (solo donde sea seguro)
    3. ast.literal_eval() para diccionarios estilo Python
    4. Limpieza agresiva de sintaxis JSON común

    Args:
        text: String que debería contener un objeto JSON/dict

    Returns:
        Diccionario parseado o None si todas las estrategias fallan
    """
    if not text or not text.strip():
        return None

    text = text.strip()

    # Estrategia 1: JSON estándar
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Estrategia 2: Reemplazar comillas simples por dobles (cuidadosamente)
    # Solo reemplazar comillas simples que parezcan delimitadores de string, no contenido
    def fix_single_quotes(s: str) -> str:
        result = []
        in_double = False
        in_single = False
        escape = False

        for i, ch in enumerate(s):
            if escape:
                result.append(ch)
                escape = False
                continue

            if ch == '\\':
                escape = True
                result.append(ch)
                continue

            if ch == '"' and not in_single:
                in_double = not in_double
                result.append(ch)
            elif ch == "'" and not in_double:
                in_single = not in_single
                result.append('"')  # Convertir a comilla doble
            else:
                result.append(ch)

        return ''.join(result)

    try:
        fixed = fix_single_quotes(text)
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Estrategia 3: ast.literal_eval para formato Python dict
    try:
        # ast.literal_eval acepta comillas simples y dobles
        result = ast.literal_eval(text)
        if isinstance(result, dict):
            return result
    except (ValueError, SyntaxError):
        pass

    # Estrategia 4: Limpieza agresiva - eliminar trailing commas, fix True/False/None
    def aggressive_clean(s: str) -> str:
        # Eliminar comas finales antes de } o ]
        s = re.sub(r',\s*([}\]])', r'\1', s)
        # Convertir True/False/None a true/false/null
        s = re.sub(r'\bTrue\b', 'true', s)
        s = re.sub(r'\bFalse\b', 'false', s)
        s = re.sub(r'\bNone\b', 'null', s)
        # Comillas simples a dobles (versión simple)
        s = fix_single_quotes(s)
        return s

    try:
        cleaned = aggressive_clean(text)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    return None


def sanitize_model_response(content: str) -> tuple[str, list[dict]]:
    """
    Limpia la respuesta del modelo eliminando JSON crudo de herramientas alucinadas
    o invocaciones de funciones que no existen (ej. spearmanr).

    ADICIONALMENTE: Detecta y EXTRAE propuestas de memoria escritas en texto plano
    (cuando el modelo escribe el JSON de save_json_memory en lugar de usar tool calling),
    las remueve de la respuesta y las devuelve como propuestas estructuradas.

    Returns:
        Tupla (cleaned_content: str, memory_proposals: list[dict])
        - cleaned_content: Texto limpio para mostrar al usuario
        - memory_proposals: Lista de propuestas de memoria extraídas (cada una con filename, content, topic_summary)
    """
    if not content:
        return content, []

    import re

    # Lista de herramientas válidas conocidas
    valid_tools = {"save_json_memory"}

    # Detectar si la respuesta parece ser sobre programación/código
    code_indicators = [
        "python", "pandas", "matplotlib", "numpy", "plot", "gráfico", "grafico",
        "dataframe", "visualiz", "chart", "seaborn", "plotly", "codigo", "código",
        "script", "función", "function", "ejemplo", "tutorial", "cómo", "como"
    ]
    content_lower = content.lower()
    is_code_explanation = any(indicator in content_lower for indicator in code_indicators)

    # Si hay bloques de código válidos, preservarlos
    code_blocks = re.findall(r'```(\w+)?\s*([\s\S]*?)```', content)
    has_valid_code_blocks = len(code_blocks) > 0

    # ============================================================
    # PASO 1: Detectar y EXTRAER propuestas de save_json_memory en texto plano
    # ============================================================
    memory_proposals = []

    # Función para extraer propuestas de save_json_memory de un texto
    def extract_save_memory_proposals(text: str, remove: bool = True) -> str:
        """
        Busca y extrae todas las propuestas de save_json_memory en el texto.
        Si remove=True, las elimina del texto y devuelve el texto limpio.
        """
        result_parts = []
        last_end = 0
        i = 0

        while i < len(text):
            # Buscar "name": "save_json_memory" o 'name': 'save_json_memory'
            name_match = re.search(r'[\'"]name[\'"]\s*:\s*[\'"]save_json_memory[\'"]', text[i:])
            if not name_match:
                break

            abs_start = i + name_match.start()

            # Buscar hacia atrás el inicio del objeto JSON completo
            obj_start = text.rfind('{', 0, abs_start)
            if obj_start == -1:
                i = abs_start + 1
                continue

            # Extraer JSON balanceado
            full_json = _extract_balanced_json(text, obj_start)
            if not full_json:
                i = abs_start + 1
                continue

            # Verificar que tenga arguments/parameters
            args_match = re.search(r'[\'"](?:arguments|parameters)[\'"]\s*:\s*(\{)', full_json)
            if not args_match:
                i = abs_start + 1
                continue

            args_start = args_match.start(1)
            args_json = _extract_balanced_json(full_json, args_start)
            if not args_json:
                i = abs_start + 1
                continue

            # Parsear con tolerancia a errores
            args = _try_parse_json_fallback(args_json)
            if args is None:
                i = abs_start + 1
                continue

            filename = args.get("filename", "")
            content_data = args.get("content", {})
            topic_summary = args.get("topic_summary", "")

            # Asegurar que content_data sea un dict limpio
            if isinstance(content_data, str):
                parsed = _try_parse_json_fallback(content_data)
                if parsed is not None:
                    content_data = parsed
                else:
                    content_data = {"raw_content": content_data}

            if filename and content_data and topic_summary:
                memory_proposals.append({
                    "filename": filename,
                    "content": content_data,
                    "topic_summary": topic_summary
                })

            # Si remove, saltar este JSON en el resultado
            if remove:
                result_parts.append(text[last_end:obj_start])
                last_end = obj_start + len(full_json)

            i = obj_start + len(full_json)

        if remove:
            result_parts.append(text[last_end:])
            return ''.join(result_parts)
        return text

    # Aplicar extracción en bloques de código
    def process_code_block(match):
        lang = match.group(1) or ""
        code_content = match.group(2)

        # Buscar y extraer save_json_memory en este bloque
        extracted = extract_save_memory_proposals(code_content, remove=True)

        # Si el bloque quedó vacío o solo tiene whitespace, eliminarlo
        if not extracted.strip():
            return ""

        # Si no era save_json_memory, verificar si es otra tool inválida
        # Detectar tanto comillas simples como dobles
        has_name_double = '"name"' in code_content
        has_name_single = "'name'" in code_content
        has_args_double = '"arguments"' in code_content
        has_args_single = "'arguments'" in code_content
        has_tool_pattern = (has_name_double or has_name_single) and (has_args_double or has_args_single)
        if has_tool_pattern:
            tool_name_match = re.search(r'[\'"]name[\'"]\s*:\s*[\'"]([^\'"]+)[\'"]', code_content)
            if tool_name_match and tool_name_match.group(1) not in valid_tools:
                if is_code_explanation or has_valid_code_blocks:
                    return ""  # Eliminar silenciosamente
                return "[Invocación de herramienta no válida removida. Uso bloques de código Markdown estándar para ejemplos.]\n"

        # Reconstruir bloque de código válido
        return f"```{lang}\n{extracted}\n```"

    cleaned = re.sub(
        r'```(\w+)?\s*([\s\S]*?)```',
        process_code_block,
        content,
        flags=re.IGNORECASE | re.DOTALL
    )

    # También buscar y extraer JSON inline de save_json_memory (fuera de bloques de código)
    cleaned = extract_save_memory_proposals(cleaned, remove=True)

    # ============================================================
    # PASO 2: Limpiar otras invocaciones de herramientas inválidas
    # ============================================================
    function_call_pattern = r'\{\s*[\'"]name[\'"]\s*:\s*[\'"]([^\'"]+)[\'"]\s*,\s*[\'"](?:arguments|parameters)[\'"]\s*:\s*\{[^}]*\}\s*\}'

    def replace_inline_function_call(match):
        tool_name = match.group(1)
        if tool_name not in valid_tools:
            if is_code_explanation:
                return ""  # Eliminar silenciosamente en contexto de código
            return f"[Herramienta '{tool_name}' no disponible]"
        return match.group(0)

    cleaned = re.sub(
        function_call_pattern,
        replace_inline_function_call,
        cleaned
    )

    # Limpiar espacios extra
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()

    return cleaned, memory_proposals


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
        # System prompt simplificado: solo conversacional, sin tool calling
        self.system_instruction = system_instruction or (
            "Eres un asistente conversacional útil, amable y directo. "
            "Responde a las preguntas e interacciones del usuario de forma natural, clara y precisa. "
            "Proporciona explicaciones detalladas, código completo cuando sea relevante, "
            "y contexto suficiente para ser útil. No uses herramientas externas."
        )
        self.rag_source_manager = rag_source_manager
        self._rag_enabled = True  # Flag para fallback graceful

        # Sin tools: el guardado de memoria se maneja desde la UI (botón usuario)
        self.tools = []

    def ask(
        self,
        pregunta: str,
        history: Optional[List[dict]] = None,
        source: Optional[str] = None,
        top_k: Optional[int] = None,
        temperature: float = 0.3,
        session_samples: Optional[list] = None,
        session_start_time: Optional[float] = None,
        context_window_scale: float = 0.7,
        session_id: Optional[str] = None,
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
            context_window_scale: Escala de ventana de contexto (0.1 a 1.0).
                                 0.1 = últimos 2-4 mensajes, 1.0 = historial completo.
            session_id: ID de la sesión actual (necesario para tool calling de memoria)

        Returns:
            Tupla (respuesta, metrics_dict)
        """
        k = top_k or self.top_k
        rag_fallback = False

        # Recortar historial según la escala de ventana de contexto
        if history:
            history = trim_history_by_scale(history, context_window_scale)

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

        # Añadir historial de conversación recortado (excluyendo el system prompt actual)
        if history:
            for msg in history:
                if msg["role"] in ("user", "assistant"):
                    messages.append(msg)

        # Añadir pregunta actual
        messages.append({"role": "user", "content": pregunta})

        # 2. Inferencia con monitoreo de recursos (sin tool calling)
        start_time = time.perf_counter()

        if MONITOR_AVAILABLE:
            with monitor_resources(
                interval=0.3,
                all_samples=session_samples,
                session_start_time=session_start_time,
            ) as monitor:
                response = self.ollama_client.chat(
                    messages=messages,
                    temperature=temperature,
                    num_ctx=num_ctx,
                    tools=self.tools  # Lista vacía
                )
                samples = monitor.stop()
        else:
            response = self.ollama_client.chat(
                messages=messages,
                temperature=temperature,
                num_ctx=num_ctx,
                tools=self.tools  # Lista vacía
            )
            samples = []

        content = response.get("content", "")

        # Sanitizar respuesta (eliminar JSON crudo de herramientas alucinadas si las hay)
        final_response, extracted_proposals = sanitize_model_response(content)
        tool_results = []
        if extracted_proposals:
            tool_results.extend([{"type": "memory_proposal", "data": p} for p in extracted_proposals])

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

        if tool_results:
            print(f"   • Herramientas ejecutadas: {len(tool_results)}")
            for tr in tool_results:
                status = "✓" if tr.get("success") else "✗"
                print(f"     {status} {tr.get('message')}")

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
            "tool_calls_executed": len(tool_results),
            "tool_results": tool_results,
        }

        return final_response, metrics

    def set_rag_enabled(self, enabled: bool) -> None:
        """Activa/desactiva el uso de RAG (para fallback graceful)."""
        self._rag_enabled = enabled

    def is_rag_enabled(self) -> bool:
        """Verifica si RAG está habilitado y disponible."""
        return self._rag_enabled and self.rag_source_manager and self.rag_source_manager.has_sources()