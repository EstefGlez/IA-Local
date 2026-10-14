"""Interfaz Streamlit para IA-Local: Chat + Monitor de Recursos + Configuración."""

import time
import json
from pathlib import Path
import streamlit as st

# Configuración de página
st.set_page_config(
    page_title="IA-Local: Asistente + Monitor",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilo personalizado
st.markdown(
    """
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 1rem; }
        .stChatMessage { border-radius: 10px; margin-bottom: 10px; }
        .metric-card {
            background: #f0f2f6;
            padding: 0.75rem;
            border-radius: 0.5rem;
            margin: 0.25rem 0;
        }
        .rag-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.3rem 0.8rem;
            border-radius: 9999px;
            font-size: 0.85rem;
            font-weight: 600;
            white-space: nowrap;
            flex-shrink: 0;
        }
        .rag-connected { background: #d4edda; color: #155724; }
        .rag-connecting { background: #fff3cd; color: #856404; }
        .rag-disconnected { background: #f8d7da; color: #721c24; }
        .conv-item {
            padding: 0.5rem;
            border-radius: 0.5rem;
            margin: 0.25rem 0;
            cursor: pointer;
            transition: background 0.15s;
        }
        .conv-item:hover { background: #e8eaf0; }
        .conv-item.active { background: #d0e7ff; font-weight: 600; }
        /* Fix header badge container */
        .header-badge-container {
            display: flex;
            justify-content: flex-end;
            align-items: center;
            height: 100%;
            min-height: 2.5rem;
        }
    </style>
""",
    unsafe_allow_html=True,
)

# Imports core
from core.ollama_client import OllamaClient
from core.retriever import RAGRetriever
from core.document import Document
from core.agent import (
    ConversationalAgent,
    build_memory_json_from_response,
    execute_save_json_memory,
)
from core.conversation_manager import ConversationManager
from core.rag_source_manager import RagSourceManager, SourceType


# Variable global para directorio base de memoria (se inicializa en init_core_components)
memory_base_dir = Path("./data/archivos_memoria")
memory_base_dir.mkdir(parents=True, exist_ok=True)


# ==================== FUNCIONES DE MEMORIA ====================
def get_memory_dir(session_id: str) -> Path:
    """Obtiene el directorio de memoria para una sesión."""
    return memory_base_dir / session_id


def list_memory_files(session_id: str) -> List[Path]:
    """Lista archivos JSON de memoria para una sesión."""
    mem_dir = get_memory_dir(session_id)
    if not mem_dir.exists():
        return []
    return sorted(mem_dir.glob("*.json"))


def detect_json_memory_proposal(content: str) -> Optional[dict]:
    """
    Detecta si un mensaje del asistente contiene una propuesta de guardado de memoria en formato JSON.
    Busca bloques de código JSON que parezcan propuestas de memoria (con campos filename, content, topic_summary).

    Returns:
        Dict con la propuesta parseada o None si no se detecta.
    """
    import re

    # Buscar bloques de código JSON
    json_blocks = re.findall(r'```json\s*(\{[\s\S]*?\})\s*```', content)

    for block in json_blocks:
        try:
            data = json.loads(block)
            # Verificar que tiene los campos esperados de una propuesta de memoria
            if isinstance(data, dict) and "filename" in data and "content" in data and "topic_summary" in data:
                return data
        except json.JSONDecodeError:
            continue

    # También buscar JSON inline (sin bloques de código) que parezca una propuesta
    # Usar un enfoque más flexible: buscar cualquier objeto JSON con los 3 campos requeridos
    # Buscar patrones que contengan los tres campos clave
    inline_json_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*"filename"(?:[^{}]|(?:\{[^{}]*\}))*"content"(?:[^{}]|(?:\{[^{}]*\}))*"topic_summary"(?:[^{}]|(?:\{[^{}]*\}))*\}'
    matches = re.findall(inline_json_pattern, content)

    for match in matches:
        try:
            data = json.loads(match)
            if isinstance(data, dict) and "filename" in data and "content" in data and "topic_summary" in data:
                return data
        except json.JSONDecodeError:
            continue

    # Fallback: búsqueda más simple por los tres campos en cualquier orden
    simple_pattern = r'\{[^{}]*"filename"[^{}]*\}'
    potential_matches = re.findall(simple_pattern, content)
    for match in potential_matches:
        try:
            data = json.loads(match)
            if isinstance(data, dict) and "filename" in data and "content" in data and "topic_summary" in data:
                return data
        except json.JSONDecodeError:
            continue

    return None


def save_memory_from_proposal(session_id: str, proposal: dict) -> tuple[bool, str]:
    """
    Guarda un archivo de memoria a partir de una propuesta detectada.
    Ahora espera que la propuesta contenga 'memory_data' (JSON completo ya construido en Python)
    o los campos legacy filename/content/topic_summary.

    Returns:
        Tupla (success: bool, message: str)
    """
    try:
        # Nuevo formato: memory_data ya viene completo desde agent.py
        if "memory_data" in proposal and proposal["memory_data"]:
            memory_data = proposal["memory_data"]
            filename = memory_data.get("metadata", {}).get("filename", "memoria.json")
        else:
            # Formato legacy (fallback defensivo)
            filename = proposal.get("filename", "")
            content = proposal.get("content", {})
            topic_summary = proposal.get("topic_summary", "")

            if not filename or not content:
                return False, "Propuesta incompleta: faltan filename o content"

            if not filename.endswith(".json"):
                filename += ".json"

            from datetime import datetime
            memory_data = {
                "metadata": {
                    "saved_at": datetime.now().isoformat(),
                    "session_id": session_id,
                    "topic": topic_summary,
                    "filename": filename
                },
                "content": content
            }

        # Guardar archivo
        mem_dir = get_memory_dir(session_id)
        mem_dir.mkdir(parents=True, exist_ok=True)
        filepath = mem_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(memory_data, f, ensure_ascii=False, indent=2)

        return True, f"Archivo de memoria '{filename}' guardado correctamente"
    except Exception as e:
        return False, f"Error al guardar: {str(e)}"


def load_memory_file(session_id: str, filename: str) -> dict:
    """Carga un archivo de memoria JSON."""
    filepath = get_memory_dir(session_id) / filename
    if not filepath.exists():
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_memory_file(session_id: str, filename: str, data: dict) -> bool:
    """Guarda un archivo de memoria JSON."""
    mem_dir = get_memory_dir(session_id)
    mem_dir.mkdir(parents=True, exist_ok=True)
    filepath = mem_dir / filename
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def delete_memory_file(session_id: str, filename: str) -> bool:
    """Elimina un archivo de memoria y limpia el directorio padre si queda vacío."""
    filepath = get_memory_dir(session_id) / filename
    if filepath.exists():
        try:
            filepath.unlink()
            # Verificar si el directorio padre quedó vacío y eliminarlo si es así
            parent_dir = filepath.parent
            if parent_dir.exists() and not any(parent_dir.iterdir()):
                parent_dir.rmdir()
            return True
        except Exception:
            return False
    return False


def list_all_sessions_with_memory() -> List[str]:
    """Lista todas las sesiones que tienen archivos de memoria."""
    if not memory_base_dir.exists():
        return []
    sessions = []
    for item in memory_base_dir.iterdir():
        if item.is_dir() and any(item.glob("*.json")):
            sessions.append(item.name)
    return sorted(sessions, reverse=True)


# ==================== INICIALIZACIÓN CACHED ====================
@st.cache_resource
def init_core_components():
    """Inicializa componentes core (cached)."""
    # 1. Cliente Ollama
    ollama_client = OllamaClient(
        base_url="http://localhost:11434",
        model="llama3.2:3b",
        timeout=300,
    )

    # 2. Gestor de fuentes RAG
    rag_source_manager = RagSourceManager(storage_file="./data/rag_sources.json")

    # 3. Retriever RAG con gestor de fuentes
    retriever = RAGRetriever(
        persist_directory="./data/chroma",
        collection_name="documents",
        rag_source_manager=rag_source_manager,
    )

    # 4. Gestor de conversaciones
    conversation_manager = ConversationManager(storage_dir="./data/conversations")

    # 5. Directorio de archivos de memoria (ya existe global, solo asegurar)
    global memory_base_dir
    memory_base_dir = Path("./data/archivos_memoria")
    memory_base_dir.mkdir(parents=True, exist_ok=True)

    return ollama_client, retriever, rag_source_manager, conversation_manager, memory_base_dir


# Cargar componentes core
try:
    ollama_client, retriever, rag_source_manager, conversation_manager, _ = init_core_components()
    core_loaded = True
except Exception as e:
    core_loaded = False
    st.error(f"Error al inicializar componentes core: {e}")
    # memory_base_dir ya está definido globalmente

# Cargar agente (depende de retriever y ollama_client)
@st.cache_resource
def init_agent(_retriever, _ollama_client, _rag_source_manager):
    """Inicializa el agente conversacional (cached)."""
    agent = ConversationalAgent(
        retriever=_retriever,
        ollama_client=_ollama_client,
        top_k=3,
        rag_source_manager=_rag_source_manager,
    )
    return agent


if core_loaded:
    agent = init_agent(retriever, ollama_client, rag_source_manager)
    agent_loaded = True
else:
    agent = None
    agent_loaded = False

# ==================== ESTADO DE SESIÓN ====================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_samples" not in st.session_state:
    st.session_state.session_samples = []

if "session_start_time" not in st.session_state:
    st.session_state.session_start_time = time.time()

if "last_inference_end_time" not in st.session_state:
    st.session_state.last_inference_end_time = None

if "processing" not in st.session_state:
    st.session_state.processing = False

if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None

if "show_new_chat_dialog" not in st.session_state:
    st.session_state.show_new_chat_dialog = False

if "rag_reindex_triggered" not in st.session_state:
    st.session_state.rag_reindex_triggered = False

# Configuración de ventana de contexto (persistente)
if "context_window_scale" not in st.session_state:
    st.session_state.context_window_scale = 0.7

# Asegurar conversación actual al inicio
if core_loaded and st.session_state.current_conversation_id is None:
    current_conv = conversation_manager.ensure_current_conversation()
    st.session_state.current_conversation_id = current_conv.id
    st.session_state.messages = current_conv.messages

# ==================== ESTADO DE STREAMING ====================
if "streaming_active" not in st.session_state:
    st.session_state.streaming_active = False
if "streaming_prompt" not in st.session_state:
    st.session_state.streaming_prompt = None
if "streaming_history" not in st.session_state:
    st.session_state.streaming_history = None
if "streaming_model_config" not in st.session_state:
    st.session_state.streaming_model_config = None
if "streaming_full_response" not in st.session_state:
    st.session_state.streaming_full_response = ""
if "streaming_metrics" not in st.session_state:
    st.session_state.streaming_metrics = None

# Estado global de bloqueo por procesamiento/streaming (accesible en todas las pestañas y sidebar)
is_processing = st.session_state.get("streaming_active", False) or st.session_state.get("processing", False)

# ==================== INICIAR STREAMING (antes de renderizar UI) ====================
# Detectar nuevo prompt para iniciar streaming
if st.session_state.processing and agent_loaded and core_loaded:
    user_messages = [m for m in st.session_state.messages if m["role"] == "user"]
    if user_messages:
        last_prompt = user_messages[-1]["content"]

        # Solo iniciar streaming si no hay uno activo ya
        if not st.session_state.streaming_active:
            # Insertar punto sintético de "valle" (reposo)
            current_time = time.time()
            if st.session_state.last_inference_end_time is not None:
                idle_duration = current_time - st.session_state.last_inference_end_time
                if idle_duration > 0.5:
                    try:
                        import psutil
                        base_cpu = psutil.cpu_percent(interval=0.1)
                        base_ram = psutil.Process().memory_percent()
                    except Exception:
                        base_cpu = 1.0
                        base_ram = 10.0

                    valley_timestamp = current_time - st.session_state.session_start_time
                    st.session_state.session_samples.append(
                        (valley_timestamp, base_cpu, base_ram)
                    )

            # Obtener config del modelo
            current_conv = conversation_manager.load_conversation(
                st.session_state.current_conversation_id
            )
            model_config = current_conv.model_config if current_conv else {"temperature": 0.3, "top_k": 3}

            # Preparar historial
            history = st.session_state.messages[:-1] if st.session_state.messages else []

            # Activar modo streaming
            st.session_state.streaming_active = True
            st.session_state.streaming_prompt = last_prompt
            st.session_state.streaming_history = history
            st.session_state.streaming_model_config = model_config
            st.session_state.streaming_full_response = ""
            st.session_state.streaming_metrics = None
            # Forzar rerender para mostrar streaming
            st.rerun()

# Re-indexar RAG si se disparó el trigger
if st.session_state.rag_reindex_triggered and core_loaded:
    with st.spinner("Re-indexando fuentes RAG..."):
        stats = retriever.reindex_from_sources()
    st.session_state.rag_reindex_triggered = False
    st.toast(f"Re-indexado: {stats['sources_processed']} fuentes, {len(stats['errors'])} errores")
    if stats['errors']:
        for err in stats['errors']:
            st.error(err)
    st.rerun()

# ==================== HEADER CON BADGE RAG ====================
def get_rag_badge_status() -> tuple[str, str]:
    """Determina el estado del badge RAG."""
    if not core_loaded or not agent_loaded:
        return "🔴 Sin Conexión", "rag-disconnected"

    ollama_ok = ollama_client.check_connection() if core_loaded else False
    rag_has_docs = retriever.has_documents() if core_loaded else False
    rag_enabled = agent.is_rag_enabled() if agent_loaded else False

    if not ollama_ok:
        return "🔴 Sin Conexión (Ollama)", "rag-disconnected"
    elif not rag_enabled:
        return "🔴 Sin Conexión (RAG off)", "rag-disconnected"
    elif not rag_has_docs:
        return "🟡 Conectando (indexando...)", "rag-connecting"
    else:
        return "🟢 Conectado", "rag-connected"

badge_text, badge_class = get_rag_badge_status()

# Header layout - usando columnas con alineación correcta
col_title, col_badge = st.columns([5, 1], vertical_alignment="center")
with col_title:
    st.title("🤖 IA-Local: Asistente RAG + Monitor")
with col_badge:
    st.markdown(
        f'<div class="header-badge-container"><span class="rag-badge {badge_class}">{badge_text}</span></div>',
        unsafe_allow_html=True
    )

st.markdown("Asistente local con Llama 3.2 + monitoreo de CPU/RAM + RAG dinámico")

# Verificar conexión Ollama
if core_loaded and not ollama_client.check_connection():
    st.warning("⚠️ No se puede conectar a Ollama. Asegúrate de que esté corriendo en `http://localhost:11434`.")

# ==================== SIDEBAR IZQUIERDO: GESTOR DE CONVERSACIONES ====================
with st.sidebar:
    st.markdown("### 💬 Conversaciones")

    if is_processing:
        st.caption("🔒 Interfaz bloqueada durante generación...")

    # Botón nuevo chat
    if st.button("➕ Nuevo Chat", use_container_width=True, type="primary", disabled=is_processing):
        new_conv = conversation_manager.create_conversation()
        st.session_state.current_conversation_id = new_conv.id
        st.session_state.messages = new_conv.messages
        st.rerun()

    st.divider()

    # Lista de conversaciones
    conversations = conversation_manager.list_conversations()
    if conversations:
        for conv in conversations:
            is_active = conv["id"] == st.session_state.current_conversation_id
            col1, col2 = st.columns([5, 1])
            with col1:
                if st.button(
                    f"{'🟢 ' if is_active else '⚪ '}{conv['title']}",
                    key=f"conv_{conv['id']}",
                    use_container_width=True,
                    help=f"{conv['message_count']} mensajes · {time.strftime('%d/%m %H:%M', time.localtime(conv['updated_at']))}",
                    disabled=is_processing
                ):
                    if not is_active:
                        # Cambiar conversación
                        loaded_conv = conversation_manager.load_conversation(conv["id"])
                        if loaded_conv:
                            st.session_state.current_conversation_id = conv["id"]
                            st.session_state.messages = loaded_conv.messages
                            st.rerun()
            with col2:
                if st.button("🗑️", key=f"del_{conv['id']}", help="Eliminar conversación", disabled=is_processing):
                    conversation_manager.delete_conversation(conv["id"])
                    if is_active:
                        # Si borramos la activa, crear nueva
                        new_conv = conversation_manager.create_conversation()
                        st.session_state.current_conversation_id = new_conv.id
                        st.session_state.messages = new_conv.messages
                    st.rerun()
    else:
        st.caption("No hay conversaciones guardadas")

    st.divider()

    # Info modelo en sidebar
    if core_loaded:
        st.markdown("### 📋 Modelo")
        try:
            models = ollama_client.list_models()
            st.markdown(f"- **Activo:** `llama3.2:3b`\n- **Disponibles:** {', '.join(models[:3])}{'...' if len(models) > 3 else ''}")
        except Exception:
            st.markdown("- **Activo:** `llama3.2:3b`")

# ==================== PESTAÑAS PRINCIPALES ====================
# Track active tab via session state
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "chat"

tab_chat, tab_monitor, tab_config, tab_memory = st.tabs([
    "💬 Chat Inteligente",
    "📊 Monitor de Recursos",
    "⚙️ Configuración",
    "🧠 Archivos de Memoria"
])

# -------------------- PESTAÑA 1: CHAT INTELIGENTE --------------------
with tab_chat:
    st.session_state.active_tab = "chat"

    # ==================== MOSTRAR HISTORIAL (mensajes completados) ====================
    # Renderizar TODOS los mensajes del historial en orden cronológico estricto
    # (incluye el último user message recién agregado via chat_input)
    for idx, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            # Botón "Guardar como Memoria" para mensajes del asistente
            if message["role"] == "assistant" and core_loaded:
                # Estado para mostrar/ocultar la tarjeta de propuesta por mensaje
                show_proposal_key = f"show_memory_proposal_{idx}"
                if show_proposal_key not in st.session_state:
                    st.session_state[show_proposal_key] = False

                col_btn, col_spacer = st.columns([1, 5])
                with col_btn:
                    if st.button(
                        "💾 Guardar como Memoria",
                        key=f"btn_save_memory_{idx}",
                        help="Genera una propuesta de memoria a partir de esta respuesta",
                        use_container_width=True
                    ):
                        st.session_state[show_proposal_key] = not st.session_state[show_proposal_key]
                        st.rerun()

                # Mostrar tarjeta de propuesta si el usuario hizo clic en el botón
                if st.session_state[show_proposal_key]:
                    st.divider()
                    st.success("💾 **Propuesta de memoria lista para guardar**")

                    # Generar propuesta determinista en Python
                    history_for_fallback = st.session_state.messages[:idx]  # Historial hasta este mensaje
                    proposed_filename = f"memoria_{idx}_{int(time.time())}.json"
                    proposed_topic = "Respuesta del asistente guardada por el usuario"

                    memory_data = build_memory_json_from_response(
                        assistant_response=message["content"],
                        suggested_filename=proposed_filename,
                        tema=proposed_topic,
                        history=history_for_fallback
                    )

                    proposal = {
                        "filename": proposed_filename,
                        "topic_summary": proposed_topic,
                        "memory_data": memory_data
                    }

                    # Tarjeta visual de la propuesta
                    with st.container(border=True):
                        # Nombre de archivo EDITABLE por el usuario
                        edited_filename = st.text_input(
                            "📁 Nombre del archivo",
                            value=proposal['filename'],
                            key=f"edit_filename_{idx}",
                            help="Puedes modificar el nombre antes de guardar"
                        )
                        st.markdown(f"**📝 Tema:** {proposal['topic_summary']}")

                        with st.expander("📋 Ver contenido completo (JSON generado)", expanded=False):
                            st.json(proposal["memory_data"])

                        # Botones de acción
                        col_save, col_discard = st.columns(2)
                        with col_save:
                            if st.button(
                                "💾 Guardar memoria",
                                key=f"save_memory_user_{idx}",
                                type="primary",
                                use_container_width=True
                            ):
                                # Actualizar filename en la propuesta si el usuario lo editó
                                if edited_filename != proposal['filename']:
                                    proposal['filename'] = edited_filename
                                    if "memory_data" in proposal and "metadata" in proposal["memory_data"]:
                                        proposal["memory_data"]["metadata"]["filename"] = edited_filename

                                success, msg = save_memory_from_proposal(
                                    st.session_state.current_conversation_id,
                                    proposal
                                )
                                if success:
                                    st.success(msg)
                                    st.session_state[show_proposal_key] = False
                                    st.rerun()
                                else:
                                    st.error(msg)
                        with col_discard:
                            if st.button(
                                "❌ Descartar",
                                key=f"discard_memory_user_{idx}",
                                use_container_width=True
                            ):
                                st.toast("Propuesta de memoria descartada")
                                st.session_state[show_proposal_key] = False
                                st.rerun()

            # FALLBACK DEFENSIVO: Detectar propuestas de memoria en mensajes del asistente
            # (para cuando el LLM imprime el JSON en lugar de usar la herramienta)
            if message["role"] == "assistant" and core_loaded:
                proposal = detect_json_memory_proposal(message["content"])
                if proposal:
                    st.divider()
                    st.info("💡 **Se detectó una propuesta de guardado de memoria** (el modelo mostró el JSON en lugar de usar la herramienta)")

                    # Mostrar preview de la propuesta
                    with st.expander("📋 Ver propuesta detectada", expanded=True):
                        st.json(proposal)

                    # Botones de acción
                    col_save, col_discard = st.columns(2)
                    with col_save:
                        if st.button(
                            "💾 Guardar en memoria estática",
                            key=f"save_memory_fallback_{idx}",
                            type="primary",
                            use_container_width=True
                        ):
                            success, msg = save_memory_from_proposal(
                                st.session_state.current_conversation_id,
                                proposal
                            )
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    with col_discard:
                        if st.button(
                            "❌ Descartar",
                            key=f"discard_memory_fallback_{idx}",
                            use_container_width=True
                        ):
                            st.toast("Propuesta de memoria descartada")
                            st.rerun()

    # Banner visual de bloqueo (solo modo legacy processing, NO streaming que ya tiene spinner)
    if st.session_state.get("processing", False) and not st.session_state.get("streaming_active", False):
        st.info("⏳ Procesando respuesta... Por favor espera.")

    # ==================== STREAMING EN TIEMPO REAL ====================
    # Si hay streaming activo, ejecutar generador y mostrar en la burbuja del assistant
    # DEBAJO de todos los mensajes del historial (orden cronológico: User -> Assistant)
    if st.session_state.streaming_active and agent_loaded and core_loaded:
        # Determinar spinner contextual
        prompt = st.session_state.streaming_prompt or ""
        if prompt.strip().startswith("/memory"):
            spinner_text = "🧠 Procesando memoria..."
        elif prompt.strip().startswith("/rag"):
            spinner_text = "🔍 Consultando base RAG..."
        else:
            spinner_text = "✨ Generando respuesta..."

        # Placeholder para la respuesta en streaming
        with st.chat_message("assistant"):
            with st.spinner(spinner_text):
                # Crear generador que consume ask_stream
                def response_generator():
                    full_response = ""
                    try:
                        stream = agent.ask_stream(
                            pregunta=st.session_state.streaming_prompt,
                            history=st.session_state.streaming_history,
                            source=None,
                            top_k=st.session_state.streaming_model_config.get("top_k", 3),
                            temperature=st.session_state.streaming_model_config.get("temperature", 0.3),
                            session_samples=st.session_state.session_samples,
                            session_start_time=st.session_state.session_start_time,
                            context_window_scale=st.session_state.context_window_scale,
                            session_id=st.session_state.current_conversation_id,
                        )
                        for chunk_content, metrics in stream:
                            full_response = chunk_content
                            st.session_state.streaming_full_response = full_response
                            if metrics and metrics.get("done"):
                                st.session_state.streaming_metrics = metrics
                                st.session_state.streaming_active = False
                            yield full_response
                    except Exception as e:
                        yield f"Ocurrió un error: {e}"
                        st.session_state.streaming_active = False

                    # Al terminar, persistir respuesta completa y hacer rerun
                    if full_response and not st.session_state.streaming_active:
                        assistant_message = {"role": "assistant", "content": full_response}
                        st.session_state.messages.append(assistant_message)

                        # Manejar propuestas de memoria
                        if st.session_state.streaming_metrics and st.session_state.streaming_metrics.get("tool_results"):
                            memory_proposals = [tr for tr in st.session_state.streaming_metrics["tool_results"] if tr.get("type") == "memory_proposal"]
                            if memory_proposals:
                                assistant_message["memory_proposals"] = [p["data"] for p in memory_proposals]

                        # Persistir en conversation_manager
                        conversation_manager.update_messages(
                            st.session_state.current_conversation_id,
                            st.session_state.messages
                        )

                        # Guardar métricas finales
                        if st.session_state.streaming_metrics:
                            st.session_state.last_metrics = st.session_state.streaming_metrics

                        st.session_state.last_inference_end_time = time.time()
                        st.session_state.processing = False
                        # Limpiar estado de streaming
                        st.session_state.streaming_prompt = None
                        st.session_state.streaming_history = None
                        st.session_state.streaming_model_config = None
                        st.session_state.streaming_full_response = ""
                        st.session_state.streaming_metrics = None
                        # Rerun para que el mensaje final aparezca en el bucle principal
                        st.rerun()

                # Usar write_stream para mostrar token por token
                st.write_stream(response_generator())

    # Spinner "Pensando..." durante procesamiento (solo modo legacy/ask, NO streaming)
    if st.session_state.processing and not st.session_state.streaming_active:
        with st.chat_message("assistant"):
            # Mostrar spinner contextual según el último mensaje
            last_user_msg = st.session_state.messages[-1]["content"] if st.session_state.messages else ""
            if last_user_msg.strip().startswith("/memory"):
                spinner_text = "Buscando en archivos de memoria..."
            elif last_user_msg.strip().startswith("/rag"):
                spinner_text = "Consultando base de conocimiento RAG..."
            else:
                spinner_text = "Pensando..."
            with st.spinner(spinner_text):
                pass

    # Ayuda de comandos
    with st.expander("💡 Comandos disponibles", expanded=False):
        st.markdown("""
        - **Conversación general**: Escribe tu pregunta normalmente (sin RAG ni memoria automática)
        - **`/memory <término>`**: Busca en tus archivos de memoria guardados e inyecta el contenido completo
        - **`/rag <consulta>`**: Busca en la base de conocimiento documental (RAG) e inyecta el contexto relevante
        """)

    # Chat input fijo al fondo (renderizado dentro de la pestaña Chat)
    prompt = st.chat_input(
        "Escribe tu pregunta o usa /memory /rag...",
        disabled=not (core_loaded and agent_loaded) or is_processing
    )

    if prompt:
        if not core_loaded or not agent_loaded:
            st.error("Componentes no disponibles. Revisa la consola.")
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.processing = True
            st.rerun()

# -------------------- PESTAÑA 2: MONITOR DE RECURSOS --------------------
with tab_monitor:
    st.session_state.active_tab = "monitor"
    st.subheader("📊 Métricas de Rendimiento - Sesión Acumulativa")

    session_samples = st.session_state.get("session_samples", [])
    if session_samples:
        all_cpu = [s[1] for s in session_samples]
        all_ram = [s[2] for s in session_samples]
        session_duration = session_samples[-1][0] if session_samples else 0
        total_inferences = len(st.session_state.messages) // 2

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("⏱️ Duración sesión", f"{session_duration:.1f}s")
        with col2:
            st.metric("🖥️ CPU Promedio Sesión", f"{sum(all_cpu)/len(all_cpu):.1f}%", delta=f"Pico: {max(all_cpu):.1f}%")
        with col3:
            st.metric("💾 RAM Promedio Sesión", f"{sum(all_ram)/len(all_ram):.1f}%", delta=f"Pico: {max(all_ram):.1f}%")
        with col4:
            st.metric("📊 Total Muestras", f"{len(session_samples)} ({total_inferences} inferencias)")

        st.divider()

        dashboard_path = Path("performance_dashboard.png")
        if dashboard_path.exists():
            st.image(
                str(dashboard_path),
                caption="Evolución CPU/RAM - Sesión completa (picos=inferencias, valles=reposo)",
                use_container_width=True,
            )
            st.info(
                "💡 **Nota técnica:** Gráfica de línea de tiempo continua de la sesión. "
                "Picos = inferencias del modelo; valles = reposo mientras el usuario escribe. "
                "Generada con `psutil` + `matplotlib`."
            )
        else:
            st.info("ℹ️ El gráfico se generará tras la próxima consulta.")
    else:
        st.info("ℹ️ Realiza una consulta en **Chat Inteligente** para iniciar el monitoreo.")

    # Detalle última inferencia
    if "last_metrics" in st.session_state and st.session_state.last_metrics:
        with st.expander("🔍 Detalle de la última inferencia", expanded=False):
            m = st.session_state.last_metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("⏱️ Tiempo respuesta", f"{m.get('elapsed_time', 0):.2f}s")
            with col2:
                st.metric("🖥️ CPU Promedio", f"{m.get('avg_cpu', 0):.1f}%", delta=f"Pico: {m.get('cpu_peak', 0):.1f}%")
            with col3:
                st.metric("💾 RAM Promedio", f"{m.get('avg_ram', 0):.1f}%", delta=f"Pico: {m.get('ram_peak', 0):.1f}%")
            with col4:
                st.metric("📊 Muestras", f"{m.get('samples', 0)}")
            # Indicador RAG usado
            rag_used = m.get("rag_used", False)
            rag_fallback = m.get("rag_fallback", False)
            if rag_used:
                st.success("✅ RAG utilizado para esta respuesta")
            elif rag_fallback:
                st.warning("⚠️ Respuesta en modo offline (sin RAG)")

# -------------------- PESTAÑA 3: CONFIGURACIÓN --------------------
with tab_config:
    st.session_state.active_tab = "config"
    st.subheader("⚙️ Configuración del Modelo y RAG")

    # --- Parámetros del Modelo ---
    st.markdown("### 🤖 Parámetros del Modelo")
    col1, col2 = st.columns(2)
    with col1:
        temperature = st.slider(
            "Temperatura",
            min_value=0.0, max_value=1.0, value=0.3, step=0.05,
            help="Controla la creatividad de las respuestas.",
            key="config_temperature",
            disabled=is_processing
        )
    with col2:
        top_k = st.slider(
            "Top-K (chunks)",
            min_value=1, max_value=10, value=3, step=1,
            help="Número de fragmentos de contexto a recuperar.",
            key="config_top_k",
            disabled=is_processing
        )

    # Guardar config en conversación actual
    if core_loaded and st.session_state.current_conversation_id:
        conversation_manager.update_model_config(
            st.session_state.current_conversation_id,
            {"temperature": temperature, "top_k": top_k}
        )

    st.divider()

    # --- Ventana de Contexto ---
    st.markdown("### 🧠 Ventana de Contexto")
    st.caption("Controla cuánto historial de conversación se envía al modelo (ahorra tokens y latencia)")

    context_scale = st.slider(
        "Escala de ventana de contexto",
        min_value=0.1,
        max_value=1.0,
        value=st.session_state.context_window_scale,
        step=0.1,
        help="0.1 = Solo últimos 2-4 mensajes (bajo contexto) | 0.7 = Balanceado | 1.0 = Historial completo",
        key="context_window_slider",
        disabled=is_processing
    )

    # Etiquetas visuales
    if context_scale <= 0.4:
        st.markdown("**Nivel:** 🔴 **Bajo (0.1-0.4)** - Solo lo esencial, máxima velocidad")
    elif context_scale <= 0.7:
        st.markdown("**Nivel:** 🟡 **Medio (0.5-0.7)** - Balanceado, recomendado")
    else:
        st.markdown("**Nivel:** 🟢 **Alto (0.8-1.0)** - Contexto completo, mayor precisión")

    if context_scale != st.session_state.context_window_scale:
        st.session_state.context_window_scale = context_scale
        st.success(f"Ventana de contexto actualizada a {context_scale:.1f}")
        st.rerun()

    st.divider()

    # --- Fuentes RAG Dinámicas ---
    st.markdown("### 📚 Fuentes RAG Dinámicas")
    st.caption("Configura fuentes de conocimiento (URLs, archivos locales, carpetas, o GitHub)")

    # Mostrar fuentes actuales
    sources = rag_source_manager.list_sources() if core_loaded else []
    enabled_sources = [s for s in sources if s.enabled]

    if enabled_sources:
        st.markdown("**Fuentes activas:**")
        for source in enabled_sources:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                status = "✅" if source.last_indexed_at else "⏳"
                st.markdown(f"{status} **{source.name}** (`{source.source_type}`)")
                st.caption(f"📍 {source.location[:80]}{'...' if len(source.location) > 80 else ''}")
                if source.last_indexed_at:
                    st.caption(f"Última indexación: {time.strftime('%d/%m %H:%M', time.localtime(source.last_indexed_at))}")
            with col2:
                if st.button("🔄 Re-indexar", key=f"reidx_{source.id}", use_container_width=True, disabled=is_processing):
                    st.session_state.rag_reindex_triggered = True
                    st.rerun()
            with col3:
                if st.button("🗑️ Eliminar", key=f"delsrc_{source.id}", use_container_width=True, disabled=is_processing):
                    rag_source_manager.remove_source(source.id)
                    st.rerun()
    else:
        st.info("No hay fuentes RAG configuradas. Añade una abajo.")

    st.divider()

    # Formulario para añadir nueva fuente (sin límite)
    st.markdown("**Añadir nueva fuente:**")
    with st.form("add_source_form", clear_on_submit=True):
        new_name = st.text_input("Nombre", placeholder="Ej: Techbox Docs, Mi Obsidian, GitHub Repo...")
        new_type = st.selectbox(
            "Tipo",
            options=[st.value for st in SourceType],
            format_func=lambda x: {
                "url": "🌐 URL (página web, raw GitHub, etc.)",
                "local_file": "📄 Archivo local (.md, .txt, .pdf)",
                "local_folder": "📁 Carpeta local (recursivo .md)",
                "github_folder": "🐙 Carpeta GitHub (owner/repo/folder)"
            }[x]
        )

        # Campo location según tipo
        if new_type == "url":
            new_location = st.text_input("URL", placeholder="https://raw.githubusercontent.com/.../file.md")
            st.caption("💡 Use URLs raw (raw.githubusercontent.com, raw.githack.com) o archivos .md/.txt directos. Evite páginas HTML.")
        elif new_type == "local_file":
            new_location = st.text_input("Ruta local", placeholder="C:/Users/.../documento.md o ./docs/archivo.txt")
        elif new_type == "local_folder":
            new_location = st.text_input("Ruta carpeta", placeholder="C:/Users/.../obsidian_vault o ./docs")
        else:  # github_folder
            new_location = st.text_input("Owner/Repo/Folder", placeholder="usuario/repo/carpeta")
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                github_branch = st.text_input("Branch", value="main")
            with col_b2:
                st.caption("Ej: estefglez/techbox-mx/main/docs")

        submitted = st.form_submit_button("➕ Añadir fuente", type="primary", use_container_width=True, disabled=is_processing)

        if submitted and new_name and new_location:
            # Validación básica de URL antes de añadir
            if new_type == "url":
                clean_url = new_location.strip().strip('"').strip("'").strip()
                if not clean_url.startswith(("http://", "https://")):
                    st.error("La URL debe empezar con http:// o https://")
                    st.stop()
                # Advertencia si no parece raw
                if "github.com" in clean_url and "/raw/" not in clean_url:
                    st.warning("⚠️ Detectada URL de GitHub que no es 'raw'. Use raw.githubusercontent.com/... para archivos directos.")

            metadata = {}
            if new_type == "github_folder":
                parts = new_location.split("/")
                if len(parts) >= 3:
                    metadata = {
                        "owner": parts[0],
                        "repo": parts[1],
                        "folder_path": "/".join(parts[2:]),
                        "branch": github_branch
                    }
                else:
                    st.error("Formato GitHub: owner/repo/folder_path")
                    st.stop()

            rag_source_manager.add_source(
                name=new_name,
                source_type=new_type,
                location=new_location,
                enabled=True,
                metadata=metadata
            )
            st.success(f"Fuente '{new_name}' añadida. Se indexará automáticamente.")
            st.session_state.rag_reindex_triggered = True
            st.rerun()

    st.divider()

    # Estado RAG
    st.markdown("### 📊 Estado del RAG")
    stats = rag_source_manager.get_stats() if core_loaded else {"total": 0, "enabled": 0, "indexed": 0}
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total fuentes", stats["total"])
    with col2:
        st.metric("Habilitadas", stats["enabled"])
    with col3:
        st.metric("Indexadas", stats["indexed"])

    if core_loaded and retriever.has_documents():
        st.success(f"✅ ChromaDB tiene documentos indexados ({retriever.collection.count()} chunks)")
    else:
        st.warning("⚠️ ChromaDB vacío - añade fuentes y re-indexa")

    # Botón limpiar todo
    if st.button("🗑️ Limpiar ChromaDB y reiniciar", type="secondary", use_container_width=True, disabled=is_processing):
        if core_loaded:
            retriever.clear_collection()
            st.success("ChromaDB limpiado")
            st.rerun()


# -------------------- PESTAÑA 4: ARCHIVOS DE MEMORIA --------------------
with tab_memory:
    st.session_state.active_tab = "memory"
    st.subheader("🧠 Archivos de Memoria por Sesión")
    st.caption("Gestiona los archivos JSON de memoria guardados por sesión. El agente puede proponer guardar memorias automáticamente.")

    # Selector de sesión
    all_sessions = list_all_sessions_with_memory()
    current_session_id = st.session_state.current_conversation_id

    if current_session_id and current_session_id not in all_sessions:
        # Añadir sesión actual si no está en la lista (aún no tiene archivos)
        session_options = [current_session_id] + all_sessions
    else:
        session_options = all_sessions
        if current_session_id and current_session_id not in session_options:
            session_options.insert(0, current_session_id)

    if not session_options:
        st.info("ℹ️ No hay sesiones con archivos de memoria aún. El agente creará archivos automáticamente cuando identifique información clave.")
    else:
        # Selector de sesión
        col_sel, col_info = st.columns([3, 1])
        with col_sel:
            selected_session = st.selectbox(
                "Seleccionar sesión",
                options=session_options,
                format_func=lambda x: f"{'🟢 ACTUAL - ' if x == current_session_id else '⚪ '}{x}",
                key="memory_session_selector",
                disabled=is_processing
            )
        with col_info:
            if selected_session == current_session_id:
                st.markdown("`Sesión actual`")

        # Botón para purgar memorias de la conversación ACTUAL (rápido, sin selector)
        if current_session_id:
            st.divider()
            col_purge1, col_purge2 = st.columns([3, 1])
            with col_purge1:
                st.markdown("**⚡ Acción rápida:**")
            with col_purge2:
                if st.button("🗑️ Purgar memorias de conversación ACTUAL", type="secondary", use_container_width=True, disabled=is_processing, help="Elimina todos los archivos de memoria JSON de la sesión activa actual"):
                    mem_dir = get_memory_dir(current_session_id)
                    try:
                        import shutil
                        if mem_dir.exists():
                            shutil.rmtree(mem_dir)
                            st.success(f"✅ Memorias de la conversación actual purgadas correctamente")
                        else:
                            st.info("La conversación actual no tiene archivos de memoria para purgar")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al purgar: {e}")

        # Mostrar archivos de memoria de la sesión seleccionada
        memory_files = list_memory_files(selected_session)

        if memory_files:
            st.markdown(f"### 📁 Archivos de memoria en `{selected_session}` ({len(memory_files)} archivos)")

            for mem_file in memory_files:
                with st.expander(f"📄 {mem_file.name}", expanded=False):
                    mem_data = load_memory_file(selected_session, mem_file.name)

                    # Mostrar contenido formateado
                    st.json(mem_data)

                    # Botones de acción
                    col_dl, col_del = st.columns(2)
                    with col_dl:
                        # Descargar archivo
                        st.download_button(
                            "⬇️ Descargar",
                            data=json.dumps(mem_data, ensure_ascii=False, indent=2),
                            file_name=mem_file.name,
                            mime="application/json",
                            key=f"dl_{selected_session}_{mem_file.name}",
                            use_container_width=True
                        )
                    with col_del:
                        if st.button("🗑️ Eliminar", key=f"del_{selected_session}_{mem_file.name}", use_container_width=True, disabled=is_processing):
                            if delete_memory_file(selected_session, mem_file.name):
                                st.success(f"Archivo {mem_file.name} eliminado")
                                st.rerun()
                            else:
                                st.error("Error al eliminar")
        else:
            st.info(f"La sesión `{selected_session}` no tiene archivos de memoria aún.")

        # Sección para crear archivo de memoria manual
        st.divider()
        st.markdown("### ➕ Crear archivo de memoria manual")

        with st.form("create_memory_form", clear_on_submit=True):
            mem_name = st.text_input(
                "Nombre del archivo",
                placeholder="ej: preferencias_usuario, contexto_proyecto, correcciones_tecnicas",
                help="Se añadirá automáticamente .json"
            )
            mem_content = st.text_area(
                "Contenido (JSON)",
                placeholder='{"clave": "valor", "lista": [1, 2, 3]}',
                height=150,
                help="Ingresa JSON válido"
            )

            submitted = st.form_submit_button("💾 Guardar archivo de memoria", type="primary", use_container_width=True, disabled=is_processing)

            if submitted and mem_name:
                # Asegurar extensión .json
                if not mem_name.endswith(".json"):
                    mem_name += ".json"

                try:
                    data = json.loads(mem_content) if mem_content.strip() else {}
                    target_session = selected_session if selected_session else current_session_id

                    if target_session and save_memory_file(target_session, mem_name, data):
                        st.success(f"Archivo {mem_name} guardado en sesión {target_session}")
                        st.rerun()
                    else:
                        st.error("Error al guardar. Verifica que hay una sesión seleccionada.")
                except json.JSONDecodeError as e:
                    st.error(f"JSON inválido: {e}")

        # Opción para limpiar directorio de memoria de una sesión
        if memory_files:
            st.divider()
            if st.button(f"🗑️ Eliminar TODOS los archivos de memoria de `{selected_session}`", type="secondary", use_container_width=True, disabled=is_processing):
                mem_dir = get_memory_dir(selected_session)
                try:
                    import shutil
                    shutil.rmtree(mem_dir)
                    st.success(f"Directorio de memoria de {selected_session} eliminado")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")