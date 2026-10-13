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


def get_save_json_memory_tool() -> Dict[str, Any]:
    """
    Retorna la definición de la herramienta save_json_memory para Ollama function calling.
    """
    return {
        "type": "function",
        "function": {
            "name": "save_json_memory",
            "description": "Guarda un archivo JSON de memoria en ./data/archivos_memoria/{session_id}/ con metadatos (fecha, session_id, tema y contenido). Úsalo cuando el usuario confirme que quiere guardar información importante (preferencias, correcciones, contexto de proyecto, etc.).",
            "parameters": {
                "type": "object",
                "required": ["filename", "content", "topic_summary"],
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Nombre descriptivo del archivo (ej: 'preferencias_usuario.json', 'correcciones_tecnicas.json', 'contexto_proyecto.json'). Debe terminar en .json"
                    },
                    "content": {
                        "type": "object",
                        "description": "Contenido JSON a guardar (diccionario con la información a persistir)"
                    },
                    "topic_summary": {
                        "type": "string",
                        "description": "Resumen breve del tema/contenido para metadatos (ej: 'Preferencias de idioma y formato del usuario', 'Correcciones sobre arquitectura del sistema')"
                    }
                }
            }
        }
    }


def execute_save_json_memory(session_id: str, filename: str, content: dict | str, topic_summary: str) -> dict:
    """
    Ejecuta la herramienta save_json_memory: guarda físicamente el archivo JSON con metadatos.

    Args:
        session_id: ID de la sesión actual
        filename: Nombre del archivo (debe terminar en .json)
        content: Diccionario con el contenido a guardar, o string JSON a parsear automáticamente
        topic_summary: Resumen del tema para metadatos

    Returns:
        Diccionario con resultado de la operación
    """
    try:
        # Asegurar directorio
        memory_dir = Path("./data/archivos_memoria") / session_id
        memory_dir.mkdir(parents=True, exist_ok=True)

        # Asegurar extensión .json
        if not filename.endswith(".json"):
            filename += ".json"

        filepath = memory_dir / filename

        # Si content es un string, intentar parsearlo como JSON
        parsed_content = content
        if isinstance(content, str):
            try:
                parsed_content = json.loads(content)
            except json.JSONDecodeError:
                # Si no es JSON válido, mantenerlo como string
                parsed_content = {"raw_content": content}

        # Preparar datos con metadatos
        memory_data = {
            "metadata": {
                "saved_at": datetime.now().isoformat(),
                "session_id": session_id,
                "topic": topic_summary,
                "filename": filename
            },
            "content": parsed_content
        }

        # Guardar archivo
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

    # Patrón para detectar save_json_memory en bloques de código o inline
    # Captura el JSON completo de la propuesta
    save_memory_pattern = r'\{\s*"name"\s*:\s*"save_json_memory"\s*,\s*"(?:arguments|parameters)"\s*:\s*(\{[\s\S]*?\})\s*\}'

    def extract_and_remove_save_memory(match):
        """Extrae la propuesta de memoria y la remueve del texto"""
        try:
            args_json = match.group(1)
            args = json.loads(args_json)
            filename = args.get("filename", "")
            content_data = args.get("content", {})
            topic_summary = args.get("topic_summary", "")

            if filename and content_data and topic_summary:
                memory_proposals.append({
                    "filename": filename,
                    "content": content_data,
                    "topic_summary": topic_summary
                })
        except (json.JSONDecodeError, KeyError):
            pass
        return ""  # Remover del texto

    # Aplicar extracción en bloques de código
    def process_code_block(match):
        lang = match.group(1) or ""
        code_content = match.group(2)

        # Buscar y extraer save_json_memory en este bloque
        extracted = re.sub(save_memory_pattern, extract_and_remove_save_memory, code_content, flags=re.DOTALL)

        # Si el bloque quedó vacío o solo tiene whitespace, eliminarlo
        if not extracted.strip():
            return ""

        # Si no era save_json_memory, verificar si es otra tool inválida
        if '"name"' in code_content and '"arguments"' in code_content:
            tool_name_match = re.search(r'"name"\s*:\s*"([^"]+)"', code_content)
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

    # También buscar y extraer JSON inline de save_json_memory
    inline_save_memory_pattern = r'\{\s*"name"\s*:\s*"save_json_memory"\s*,\s*"(?:arguments|parameters)"\s*:\s*\{[\s\S]*?\}\s*\}'

    def extract_inline_save_memory(match):
        try:
            full_json = match.group(0)
            # Extraer solo la parte de arguments/parameters
            args_match = re.search(r'"(?:arguments|parameters)"\s*:\s*(\{[\s\S]*?\})\s*\}', full_json)
            if args_match:
                args_json = args_match.group(1)
                args = json.loads(args_json)
                filename = args.get("filename", "")
                content_data = args.get("content", {})
                topic_summary = args.get("topic_summary", "")

                if filename and content_data and topic_summary:
                    memory_proposals.append({
                        "filename": filename,
                        "content": content_data,
                        "topic_summary": topic_summary
                    })
        except (json.JSONDecodeError, KeyError):
            pass
        return ""  # Remover del texto

    cleaned = re.sub(
        inline_save_memory_pattern,
        extract_inline_save_memory,
        cleaned,
        flags=re.DOTALL
    )

    # ============================================================
    # PASO 2: Limpiar otras invocaciones de herramientas inválidas
    # ============================================================
    function_call_pattern = r'\{\s*"name"\s*:\s*"([^"]+)"\s*,\s*"(?:arguments|parameters)"\s*:\s*\{[^}]*\}\s*\}'

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
        # System prompt explícito para Llama 3.2 con instrucciones estrictas de tool calling
        self.system_instruction = system_instruction or (
            "Eres un asistente conversacional útil, amable y directo. "
            "Responde a las preguntas e interacciones del usuario de forma natural, clara y precisa.\n\n"
            "=== REGLAS ESTRICTAS DE TOOL CALLING (OBLIGATORIO) ===\n"
            "1. Para guardar memorias, DEBES usar EXCLUSIVAMENTE el mecanismo nativo de function calling (tool calling).\n"
            "2. NUNCA escribas en tu respuesta de texto plano bloques JSON como:\n"
            '   {"name": "save_json_memory", "arguments": {"filename": "...", "content": {...}, "topic_summary": "..."}}\n'
            "   Esto NO funciona y será filtrado por el sistema.\n"
            "3. Cuando identifiques información técnica valiosa que merezca persistir (código, configuraciones,\n"
            "   explicaciones detalladas, correcciones, preferencias), invoca la herramienta `save_json_memory`\n"
            "   mediante el protocolo oficial de tool calling del modelo.\n"
            "4. El contenido de memoria debe ser DETALLADO y ESTRUCTURADO: incluye descripciones claras,\n"
            "   bloques de código de ejemplo completos, y contexto suficiente para ser útil en futuras sesiones.\n"
            "5. Para interacciones casuales (saludos, preguntas simples, charla trivial): NO uses herramientas,\n"
            "   simplemente responde de forma natural y conversacional.\n"
        )
        self.rag_source_manager = rag_source_manager
        self._rag_enabled = True  # Flag para fallback graceful

        # Tool definition para function calling
        self.tools = [get_save_json_memory_tool()]

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
                if msg["role"] in ("user", "assistant", "tool"):
                    # Incluir mensajes de tool para mantener el contexto de function calling
                    messages.append(msg)

        # Añadir pregunta actual
        messages.append({"role": "user", "content": pregunta})

        # 2. Inferencia con monitoreo de recursos (con soporte para tool calling)
        start_time = time.perf_counter()

        # Loop para manejar múltiples tool calls (máximo 3 iteraciones para evitar bucles infinitos)
        max_tool_iterations = 3
        final_response = ""
        tool_results = []

        for iteration in range(max_tool_iterations):
            # ==================== DEBUG LOGS ====================
            print(f"\n{'='*60}")
            print(f"[DEBUG] Iteración {iteration + 1}/{max_tool_iterations}")
            print(f"[DEBUG] Tools enviadas: {[t['function']['name'] for t in self.tools]}")
            print(f"[DEBUG] Mensajes en historial: {len(messages)}")
            if messages:
                last_user = next((m for m in reversed(messages) if m['role'] == 'user'), None)
                if last_user:
                    print(f"[DEBUG] Último mensaje user: {last_user['content'][:150]}...")
            print(f"{'='*60}")
            # ==================== FIN DEBUG LOGS ====================

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
                        tools=self.tools
                    )
                    samples = monitor.stop()
            else:
                response = self.ollama_client.chat(
                    messages=messages,
                    temperature=temperature,
                    num_ctx=num_ctx,
                    tools=self.tools
                )
                samples = []

            content = response.get("content", "")
            tool_calls = response.get("tool_calls", None)

            # ==================== DEBUG LOGS RESPUESTA ====================
            print(f"[DEBUG] Respuesta Ollama keys: {list(response.keys())}")
            print(f"[DEBUG] Content (primeros 300 chars): {content[:300] if content else '(vacío)'}")
            print(f"[DEBUG] Tool calls: {tool_calls}")
            if tool_calls:
                for i, tc in enumerate(tool_calls):
                    fn = tc.get('function', {})
                    print(f"[DEBUG]   Tool call #{i+1}: name='{fn.get('name')}', args={fn.get('arguments')}")
            print(f"{'='*60}")
            # ==================== FIN DEBUG LOGS ====================

            if tool_calls:
                # El modelo quiere ejecutar herramientas
                # Añadir la respuesta del asistente con tool_calls al historial
                messages.append({
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls
                })

                # Procesar tool calls: SOLO detectar propuestas de memoria, NO ejecutarlas automáticamente
                memory_proposals = []
                for tool_call in tool_calls:
                    function = tool_call.get("function", {})
                    func_name = function.get("name")
                    func_args = function.get("arguments", {})

                    if func_name == "save_json_memory" and session_id:
                        # Capturar la propuesta de memoria para devolverla a la UI
                        filename = func_args.get("filename", "")
                        content_data = func_args.get("content", {})
                        topic_summary = func_args.get("topic_summary", "")

                        if filename and content_data and topic_summary:
                            memory_proposals.append({
                                "filename": filename,
                                "content": content_data,
                                "topic_summary": topic_summary
                            })

                        # Añadir resultado simulado al historial para que el modelo sepa que "se guardó"
                        messages.append({
                            "role": "tool",
                            "tool_name": func_name,
                            "content": json.dumps({
                                "success": True,
                                "message": f"Propuesta de memoria capturada: {filename}",
                                "proposal_captured": True
                            }, ensure_ascii=False)
                        })
                    else:
                        # Tool desconocido o alucinado (ej. spearmanr) - no ejecutar, solo informar
                        messages.append({
                            "role": "tool",
                            "tool_name": func_name,
                            "content": json.dumps({
                                "success": False,
                                "message": f"Herramienta no disponible: {func_name}. Solo 'save_json_memory' está permitida."
                            }, ensure_ascii=False)
                        })

                # Si hubo propuestas de memoria, añadirlas a tool_results para devolver a la UI
                if memory_proposals:
                    tool_results.extend([{"type": "memory_proposal", "data": p} for p in memory_proposals])

                # Continuar el loop para que el modelo procese los resultados
                continue
            else:
                # No hay tool calls, esta es la respuesta final
                # Sanitizar y extraer propuestas de memoria escritas en texto plano
                final_response, extracted_proposals = sanitize_model_response(content)
                if extracted_proposals:
                    tool_results.extend([{"type": "memory_proposal", "data": p} for p in extracted_proposals])
                break

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