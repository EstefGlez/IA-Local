"""Interfaz Streamlit para IA-Local: Chat + Monitor de Recursos."""

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
        if "last_metrics" in st.session_state:
            del st.session_state.last_metrics
        st.rerun()

# ==================== CUERPO PRINCIPAL ====================
st.title("🤖 IA-Local: Asistente RAG + Monitor de Recursos")
st.markdown(
    "Asistente local con Llama 3.2 + monitoreo de CPU/RAM en tiempo real"
)

# Verificar conexión Ollama
if agent_loaded and not ollama_client.check_connection():
    st.warning("⚠️ No se puede conectar a Ollama. Asegúrate de que esté corriendo en `http://localhost:11434`.")

# Inicializar historial de chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Pestañas principales
tab_chat, tab_monitor = st.tabs(["💬 Chat Inteligente", "📊 Monitor de Recursos y Rendimiento"])

# -------------------- PESTAÑA 1: CHAT INTELIGENTE --------------------
with tab_chat:
    # Mostrar historial
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Entrada de chat
    if prompt := st.chat_input("Escribe tu pregunta sobre Techbox..."):
        if not agent_loaded:
            st.error("El agente no está disponible. Revisa la consola.")
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Pensando y consultando contexto local..."):
                    try:
                        # Llamada correcta con todos los parámetros - ahora retorna (respuesta, metrics)
                        respuesta, metrics = agent.ask(
                            pregunta=prompt,
                            source="techbox",
                            top_k=top_k,
                            temperature=temperature,
                        )
                    except Exception as e:
                        respuesta = f"Ocurrió un error al procesar la solicitud: {e}"
                        metrics = {}

                    st.markdown(respuesta)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": respuesta}
                    )

                    # Guardar métricas reales retornadas por el agente
                    if metrics:
                        st.session_state.last_metrics = metrics
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
                        }

                st.rerun()

# -------------------- PESTAÑA 2: MONITOR DE RECURSOS --------------------
with tab_monitor:
    st.subheader("📊 Métricas de Rendimiento de la Última Inferencia")

    if "last_metrics" in st.session_state and st.session_state.last_metrics:
        m = st.session_state.last_metrics

        # Tarjetas de métricas en grid 4 columnas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("⏱️ Tiempo de respuesta", f"{m.get('elapsed_time', 0):.2f}s")
        with col2:
            cpu_avg = m.get('avg_cpu', 0)
            cpu_peak = m.get('cpu_peak', 0)
            st.metric("🖥️ CPU Promedio", f"{cpu_avg:.1f}%", delta=f"Pico: {cpu_peak:.1f}%" if cpu_peak else None)
        with col3:
            ram_avg = m.get('avg_ram', 0)
            ram_peak = m.get('ram_peak', 0)
            st.metric("💾 RAM Promedio", f"{ram_avg:.1f}%", delta=f"Pico: {ram_peak:.1f}%" if ram_peak else None)
        with col4:
            st.metric("📊 Muestras", f"{m.get('samples', 0)}")

        st.divider()

        # Gráfico de rendimiento
        dashboard_path = Path(m.get('dashboard_path', 'performance_dashboard.png'))
        if dashboard_path.exists():
            st.image(
                str(dashboard_path),
                caption="Evolución de CPU y RAM durante la última inferencia",
                use_container_width=True,
            )
            st.info(
                "💡 **Nota técnica:** Esta gráfica se genera automáticamente usando "
                "`psutil` y `matplotlib` para registrar los picos de hardware en "
                "tiempo real."
            )
        else:
            st.info(
                "ℹ️ El gráfico de rendimiento se generará tras la próxima consulta."
            )
    else:
        st.info(
            "ℹ️ Realiza una consulta en la pestaña **Chat Inteligente** para generar "
            "las métricas y el gráfico de rendimiento."
        )