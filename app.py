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
        if "last_metrics" in st.session_state:
            del st.session_state.last_metrics
        st.rerun()

    # Métricas recientes en sidebar (estilo Gemini)
    if "last_metrics" in st.session_state:
        st.divider()
        st.markdown("### 📈 Métricas Recientes")
        m = st.session_state.last_metrics
        col_s1, col_s2 = st.columns(2)
        col_s1.metric("⏱️ Tiempo", f"{m.get('elapsed_time', 0):.2f}s")
        col_s2.metric("💾 RAM Promedio", f"{m.get('avg_ram', 0):.1f}%")
        col_s1.metric("🖥️ CPU Promedio", f"{m.get('avg_cpu', 0):.1f}%")
        col_s2.metric("📊 Muestras", f"{m.get('samples', 0)}")
        if m.get('cpu_peak'):
            st.caption(f"Picos — CPU: {m['cpu_peak']:.1f}% | RAM: {m['ram_peak']:.1f}%")

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
                start_time = time.perf_counter()
                try:
                    # Llamada correcta con todos los parámetros
                    respuesta = agent.ask(
                        pregunta=prompt,
                        source="techbox",
                        top_k=top_k,
                        temperature=temperature,
                    )
                except Exception as e:
                    respuesta = f"Ocurrió un error al procesar la solicitud: {e}"

                elapsed_time = time.perf_counter() - start_time

                st.markdown(respuesta)
                st.session_state.messages.append(
                    {"role": "assistant", "content": respuesta}
                )

                # Leer métricas reales desde el monitor (si existe archivo de log)
                # El monitor guarda métricas en session_state vía agent.py
                # Aquí capturamos lo que el monitor generó
                dashboard_path = Path("performance_dashboard.png")

                # Guardar métricas básicas + placeholders para CPU/RAM reales
                # Nota: agent.py imprime métricas pero no las retorna; usamos st.session_state para pasarlas
                st.session_state.last_metrics = {
                    "elapsed_time": elapsed_time,
                    "dashboard_path": str(dashboard_path) if dashboard_path.exists() else None,
                }

            st.rerun()

# ==================== DASHBOARD DE RECURSOS (estilo Gemini) ====================
st.divider()
st.subheader("🖥️ Monitor de Rendimiento y Recursos del Sistema")

dashboard_path = Path("performance_dashboard.png")
if dashboard_path.exists():
    col_img1, col_img2 = st.columns([2, 1])
    with col_img1:
        st.image(
            str(dashboard_path),
            caption="Evolución de CPU y RAM durante la última inferencia",
            use_container_width=True,
        )
    with col_img2:
        st.info(
            "💡 **Nota técnica:** Esta gráfica se genera automáticamente usando "
            "`psutil` y `matplotlib` para registrar los picos de hardware en "
            "tiempo real."
        )
else:
    st.info(
        "ℹ️ Realiza una consulta en el chat superior para generar la gráfica de "
        "rendimiento."
    )