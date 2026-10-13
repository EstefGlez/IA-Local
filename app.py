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
from core.agent import ConversationalAgent
from core.conversation_manager import ConversationManager
from core.rag_source_manager import RagSourceManager, SourceType


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

    return ollama_client, retriever, rag_source_manager, conversation_manager


# Cargar componentes core
try:
    ollama_client, retriever, rag_source_manager, conversation_manager = init_core_components()
    core_loaded = True
except Exception as e:
    core_loaded = False
    st.error(f"Error al inicializar componentes core: {e}")

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

# Asegurar conversación actual al inicio
if core_loaded and st.session_state.current_conversation_id is None:
    current_conv = conversation_manager.ensure_current_conversation()
    st.session_state.current_conversation_id = current_conv.id
    st.session_state.messages = current_conv.messages

# ==================== PROCESAMIENTO DE INFERENCIA (antes de renderizar UI) ====================
if st.session_state.processing and agent_loaded and core_loaded:
    user_messages = [m for m in st.session_state.messages if m["role"] == "user"]
    if user_messages:
        last_prompt = user_messages[-1]["content"]

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

        # Obtener config del modelo de la conversación actual
        current_conv = conversation_manager.load_conversation(
            st.session_state.current_conversation_id
        )
        model_config = current_conv.model_config if current_conv else {"temperature": 0.3, "top_k": 3}

        # Preparar historial para el agente (excluir el último mensaje del usuario que se pasa aparte)
        history = st.session_state.messages[:-1] if st.session_state.messages else []

        # Llamada al agente con historial completo
        try:
            respuesta, metrics = agent.ask(
                pregunta=last_prompt,
                history=history,  # Pasar historial completo
                source=None,  # Buscar en todas las fuentes
                top_k=model_config.get("top_k", 3),
                temperature=model_config.get("temperature", 0.3),
                session_samples=st.session_state.session_samples,
                session_start_time=st.session_state.session_start_time,
            )
        except Exception as e:
            respuesta = f"Ocurrió un error al procesar la solicitud: {e}"
            metrics = {}

        # Guardar respuesta
        st.session_state.messages.append(
            {"role": "assistant", "content": respuesta}
        )

        # Persistir en conversation_manager
        conversation_manager.update_messages(
            st.session_state.current_conversation_id,
            st.session_state.messages
        )

        # Guardar métricas
        if metrics:
            st.session_state.last_metrics = metrics
        else:
            dashboard_path = Path("performance_dashboard.png")
            st.session_state.last_metrics = {
                "elapsed_time": 0, "avg_cpu": 0, "cpu_peak": 0,
                "avg_ram": 0, "ram_peak": 0, "samples": 0,
                "dashboard_path": str(dashboard_path) if dashboard_path.exists() else None,
                "session_samples": st.session_state.session_samples,
                "rag_used": False, "rag_fallback": True,
            }

        st.session_state.last_inference_end_time = time.time()
        st.session_state.processing = False
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

    # Botón nuevo chat
    if st.button("➕ Nuevo Chat", use_container_width=True, type="primary"):
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
                    help=f"{conv['message_count']} mensajes · {time.strftime('%d/%m %H:%M', time.localtime(conv['updated_at']))}"
                ):
                    if not is_active:
                        # Cambiar conversación
                        loaded_conv = conversation_manager.load_conversation(conv["id"])
                        if loaded_conv:
                            st.session_state.current_conversation_id = conv["id"]
                            st.session_state.messages = loaded_conv.messages
                            st.rerun()
            with col2:
                if st.button("🗑️", key=f"del_{conv['id']}", help="Eliminar conversación"):
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

tab_chat, tab_monitor, tab_config = st.tabs([
    "💬 Chat Inteligente",
    "📊 Monitor de Recursos",
    "⚙️ Configuración"
])

# -------------------- PESTAÑA 1: CHAT INTELIGENTE --------------------
with tab_chat:
    st.session_state.active_tab = "chat"
    # Mostrar historial
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Spinner "Pensando..." durante procesamiento
    if st.session_state.processing:
        with st.chat_message("assistant"):
            with st.spinner("Pensando y consultando contexto local..."):
                pass

    # Chat input fijo al fondo (renderizado dentro de la pestaña Chat)
    prompt = st.chat_input(
        "Escribe tu pregunta...",
        disabled=not (core_loaded and agent_loaded)
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
            key="config_temperature"
        )
    with col2:
        top_k = st.slider(
            "Top-K (chunks)",
            min_value=1, max_value=10, value=3, step=1,
            help="Número de fragmentos de contexto a recuperar.",
            key="config_top_k"
        )

    # Guardar config en conversación actual
    if core_loaded and st.session_state.current_conversation_id:
        conversation_manager.update_model_config(
            st.session_state.current_conversation_id,
            {"temperature": temperature, "top_k": top_k}
        )

    st.divider()

    # --- Fuentes RAG Dinámicas ---
    st.markdown("### 📚 Fuentes RAG Dinámicas")
    st.caption("Configura hasta 2 fuentes de conocimiento (URLs, archivos locales, carpetas, o GitHub)")

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
                if st.button("🔄 Re-indexar", key=f"reidx_{source.id}", use_container_width=True):
                    st.session_state.rag_reindex_triggered = True
                    st.rerun()
            with col3:
                if st.button("🗑️ Eliminar", key=f"delsrc_{source.id}", use_container_width=True):
                    rag_source_manager.remove_source(source.id)
                    st.rerun()
    else:
        st.info("No hay fuentes RAG configuradas. Añade una abajo.")

    st.divider()

    # Formulario para añadir nueva fuente (máx 2)
    max_sources = 2
    can_add = len(enabled_sources) < max_sources

    if can_add:
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

            submitted = st.form_submit_button("➕ Añadir fuente", type="primary", use_container_width=True)

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
    else:
        st.warning(f"Máximo {max_sources} fuentes simultáneas. Elimina una para añadir otra.")

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
    if st.button("🗑️ Limpiar ChromaDB y reiniciar", type="secondary", use_container_width=True):
        if core_loaded:
            retriever.clear_collection()
            st.success("ChromaDB limpiado")
            st.rerun()