"""Interfaz Streamlit para IA-Local: Chat + Monitor de Recursos."""

import time
from pathlib import Path
import streamlit as st

# Configuración de página
st.set_page_config(
    page_title="IA-Local: Asistente + Monitor",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilo personalizado (mejorado de Gemini)
st.markdown(
    """
    <style>
        .block-container { padding-top: 2rem; }
        .stChatMessage { border-radius: 10px; margin-bottom: 10px; }
        .metric-card {
            background: #f0f2f6;
            padding: 0.75rem;
            border-radius: 0.5rem;
            margin: 0.25rem 0;
        }
    </style>
""",
    unsafe_allow_html=True,
)

# Imports directos correctos (mi versión)
from core.ollama_client import OllamaClient
from core.retriever import RAGRetriever
from core.document import Document
from core.agent import ConversationalAgent


@st.cache_resource
def init_agent():
    """Inicializa el agente conversacional con RAG (cached)."""
    with st.spinner("Inicializando componentes del agente..."):
        # 1. Cliente Ollama
        ollama_client = OllamaClient(
            base_url="http://localhost:11434",
            model="llama3.2:3b",
            timeout=300,
        )

        # 2. Retriever RAG
        retriever = RAGRetriever(
            persist_directory="./data/chroma",
            collection_name="documents",
        )

        # 3. Cargar documento Techbox si no está indexado
        if retriever.collection.count() == 0:
            with st.spinner("📥 Indexando documento Techbox (primera vez)..."):
                doc = Document(
                    location="https://raw.githubusercontent.com/EstefGlez/techbox-mx/refs/heads/main/especificaciones-techbox.md",
                    source_type="techbox",
                )
                retriever.add_document(doc)
                st.success("✅ Documento indexado correctamente")

        # 4. Agente conversacional
        agent = ConversationalAgent(
            retriever=retriever,
            ollama_client=ollama_client,
            top_k=3,
        )

        return agent, ollama_client


# Cargar agente
try:
    agent, ollama_client = init_agent()
    agent_loaded = True
except Exception as e:
    agent_loaded = False
    st.error(f"Error al inicializar el agente: {e}")

# ==================== BARRA LATERAL ====================
with st.sidebar:
    st.title("⚙️ Configuración")

    temperature = st.slider(
        "Temperatura",
        min_value=0.0,
        max_value=1.0,
        value=0.3,
        step=0.05,
        help="Controla la creatividad de las respuestas.",
    )

    top_k = st.slider(
        "Top-K (chunks)",
        min_value=1,
        max_value=5,
        value=3,
        step=1,
        help="Número de fragmentos de contexto a recuperar.",
    )

    st.divider()

    # Info del modelo (estilo Gemini)
    st.markdown("### 📋 Info del Modelo")
    try:
        models = ollama_client.list_models() if agent_loaded else ["llama3.2:3b"]
        st.markdown(f"- **Modelo activo:** `llama3.2:3b`\n- **Disponibles:** {', '.join(models)}")
    except Exception:
        st.markdown("- **Modelo activo:** `llama3.2:3b`")

    st.divider()

    if st.button("🗑️ Limpiar Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_samples = []
        st.session_state.session_start_time = time.time()
        st.session_state.last_inference_end_time = None
        st.session_state.processing = False
        if "last_metrics" in st.session_state:
            del st.session_state.last_metrics
        st.rerun()

# ==================== INICIALIZAR ESTADO DE SESIÓN ====================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_samples" not in st.session_state:
    st.session_state.session_samples = []  # Lista acumulada: (timestamp_abs, cpu%, ram%)

if "session_start_time" not in st.session_state:
    st.session_state.session_start_time = time.time()

if "last_inference_end_time" not in st.session_state:
    st.session_state.last_inference_end_time = None

if "processing" not in st.session_state:
    st.session_state.processing = False

# ==================== PROCESAMIENTO DE INFERENCIA (al inicio, antes de renderizar UI) ====================
if st.session_state.processing and agent_loaded:
    # Obtener el último mensaje del usuario (el que disparó el processing)
    user_messages = [m for m in st.session_state.messages if m["role"] == "user"]
    if user_messages:
        last_prompt = user_messages[-1]["content"]

        # Insertar punto sintético de "valle" (reposo) si hay inferencia previa
        current_time = time.time()
        if st.session_state.last_inference_end_time is not None:
            idle_duration = current_time - st.session_state.last_inference_end_time
            if idle_duration > 0.5:  # Solo si hubo pausa significativa
                # Punto de valle: CPU/RAM base del sistema
                try:
                    import psutil
                    base_cpu = psutil.cpu_percent(interval=0.1)
                    base_ram = psutil.Process().memory_percent()
                except Exception:
                    base_cpu = 1.0
                    base_ram = 10.0

                # Timestamp absoluto desde inicio de sesión
                valley_timestamp = current_time - st.session_state.session_start_time
                st.session_state.session_samples.append(
                    (valley_timestamp, base_cpu, base_ram)
                )

        # Llamada al agente con parámetros de sesión para gráfica acumulativa
        try:
            respuesta, metrics = agent.ask(
                pregunta=last_prompt,
                source="techbox",
                top_k=top_k,
                temperature=temperature,
                session_samples=st.session_state.session_samples,
                session_start_time=st.session_state.session_start_time,
            )
        except Exception as e:
            respuesta = f"Ocurrió un error al procesar la solicitud: {e}"
            metrics = {}

        # Guardar respuesta del asistente
        st.session_state.messages.append(
            {"role": "assistant", "content": respuesta}
        )

        # Guardar métricas y actualizar tiempo de fin de inferencia
        if metrics:
            st.session_state.last_metrics = metrics
            # session_samples se modifica in-place por el monitor, ya está actualizada
        else:
            # Fallback si no hay métricas (monitor no disponible)
            dashboard_path = Path("performance_dashboard.png")
            st.session_state.last_metrics = {
                "elapsed_time": 0,
                "avg_cpu": 0,
                "cpu_peak": 0,
                "avg_ram": 0,
                "ram_peak": 0,
                "samples": 0,
                "dashboard_path": str(dashboard_path) if dashboard_path.exists() else None,
                "session_samples": st.session_state.session_samples,
            }

        # Actualizar timestamp de fin de inferencia para próximo valle
        st.session_state.last_inference_end_time = time.time()

        # Resetear flag de procesamiento
        st.session_state.processing = False

        # Rerun para renderizar la respuesta sin spinner
        st.rerun()

# ==================== CUERPO PRINCIPAL ====================
st.title("🤖 IA-Local: Asistente RAG + Monitor de Recursos")
st.markdown(
    "Asistente local con Llama 3.2 + monitoreo de CPU/RAM en tiempo real"
)

# Verificar conexión Ollama
if agent_loaded and not ollama_client.check_connection():
    st.warning("⚠️ No se puede conectar a Ollama. Asegúrate de que esté corriendo en `http://localhost:11434`.")

# Pestañas principales
tab_chat, tab_monitor = st.tabs(["💬 Chat Inteligente", "📊 Monitor de Recursos y Rendimiento"])

# -------------------- PESTAÑA 1: CHAT INTELIGENTE --------------------
with tab_chat:
    # Mostrar historial
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Mostrar spinner "Pensando..." SOLO durante el procesamiento (antes del input fijo)
    if st.session_state.processing:
        with st.chat_message("assistant"):
            with st.spinner("Pensando y consultando contexto local..."):
                # El procesamiento real ya ocurrió en el rerun anterior
                # Aquí solo mostramos el spinner visual mientras se completa el rerun
                pass

# -------------------- PESTAÑA 2: MONITOR DE RECURSOS --------------------
with tab_monitor:
    st.subheader("📊 Métricas de Rendimiento - Sesión Acumulativa")

    # Métricas de sesión (acumuladas)
    session_samples = st.session_state.get("session_samples", [])
    if session_samples:
        # Calcular métricas acumuladas de la sesión
        all_cpu = [s[1] for s in session_samples]
        all_ram = [s[2] for s in session_samples]
        session_duration = session_samples[-1][0] if session_samples else 0
        total_inferences = len(st.session_state.messages) // 2  # user + assistant pairs

        # Tarjetas de métricas en grid 4 columnas
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

        # Gráfico de rendimiento acumulativo
        dashboard_path = Path("performance_dashboard.png")
        if dashboard_path.exists():
            st.image(
                str(dashboard_path),
                caption="Evolución de CPU y RAM - Sesión completa (picos=inferencias, valles=reposo)",
                use_container_width=True,
            )
            st.info(
                "💡 **Nota técnica:** Esta gráfica muestra la línea de tiempo continua de toda la sesión. "
                "Los picos corresponden a inferencias del modelo; los valles son periodos de reposo "
                "mientras el usuario escribe. Generada con `psutil` + `matplotlib`."
            )
        else:
            st.info(
                "ℹ️ El gráfico de rendimiento se generará tras la próxima consulta."
            )
    else:
        st.info(
            "ℹ️ Realiza una consulta en la pestaña **Chat Inteligente** para iniciar "
            "el monitoreo de la sesión."
        )

    # Métricas de la última inferencia (detalle)
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

# ==================== INPUT FIJO AL FINAL (fuera de tabs) ====================
prompt = st.chat_input("Escribe tu pregunta sobre Techbox...", disabled=not agent_loaded)

if prompt:
    if not agent_loaded:
        st.error("El agente no está disponible. Revisa la consola.")
    else:
        # Agregar mensaje del usuario al historial
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Activar flag de procesamiento para el siguiente rerun
        st.session_state.processing = True
        st.rerun()