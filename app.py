"""Interfaz Streamlit para IA-Local: Chat + Monitor de Recursos."""

import os
import time
import streamlit as st
from pathlib import Path

# Configuración de página
st.set_page_config(
    page_title="IA-Local: Asistente + Monitor",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos CSS personalizados
st.markdown("""
<style>
    .stChatMessage { padding: 0.5rem; }
    .metric-card {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .metric-label { font-weight: 600; color: #333; }
    .metric-value { font-size: 1.2rem; color: #1f77b4; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def init_agent():
    """Inicializa el agente conversacional con RAG (cached)."""
    from core.ollama_client import OllamaClient
    from core.retriever import RAGRetriever
    from core.document import Document
    from core.agent import ConversationalAgent

    # 1. Configurar cliente Ollama
    ollama_client = OllamaClient(
        base_url="http://localhost:11434",
        model="llama3.2:3b",
        timeout=300,
    )

    # 2. Configurar retriever RAG
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

    # 4. Crear agente conversacional
    agent = ConversationalAgent(
        retriever=retriever,
        ollama_client=ollama_client,
        top_k=3,
    )

    return agent, ollama_client


def display_metrics_sidebar(elapsed_time: float, cpu_avg: float, cpu_peak: float,
                           ram_avg: float, ram_peak: float, samples: int,
                           dashboard_path: str):
    """Muestra métricas en la barra lateral."""
    with st.sidebar:
        st.header("📊 Métricas de la Última Respuesta")

        # Tarjetas de métricas
        col1, col2 = st.columns(2)
        with col1:
            st.metric("⏱️ Tiempo", f"{elapsed_time:.2f}s")
            st.metric("🖥️ CPU Promedio", f"{cpu_avg:.1f}%")
        with col2:
            st.metric("📦 RAM Promedio", f"{ram_avg:.1f}%")
            st.metric("🔢 Muestras", f"{samples}")

        st.divider()

        # Picos
        st.subheader("📈 Picos")
        c1, c2 = st.columns(2)
        with c1:
            st.metric("CPU Pico", f"{cpu_peak:.1f}%")
        with c2:
            st.metric("RAM Pico", f"{ram_peak:.1f}%")

        st.divider()

        # Gráfica de dashboard
        st.subheader("📈 Evolución de Recursos")
        if os.path.exists(dashboard_path):
            st.image(dashboard_path, use_container_width=True)
        else:
            st.info("La gráfica se generará después de la primera pregunta")


def main():
    st.title("🤖 IA-Local: Asistente RAG + Monitor de Recursos")
    st.caption("Asistente local con Llama 3.2 + monitoreo CPU/RAM en tiempo real")

    # Inicializar agente
    try:
        agent, ollama_client = init_agent()
    except Exception as e:
        st.error(f"❌ Error inicializando el agente: {e}")
        st.info("Verifica que Ollama esté corriendo en `http://localhost:11434` con el modelo `llama3.2:3b`")
        st.stop()

    # Verificar conexión Ollama
    if not ollama_client.check_connection():
        st.warning("⚠️ No se puede conectar a Ollama. Asegúrate de que esté corriendo.")
        if st.button("🔄 Reintentar conexión"):
            st.rerun()

    # Inicializar estado de chat
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_metrics" not in st.session_state:
        st.session_state.last_metrics = None

    # Sidebar: Configuración
    with st.sidebar:
        st.header("⚙️ Configuración")

        # Parámetros del modelo
        temperature = st.slider("Temperatura", 0.0, 1.0, 0.3, 0.1)
        top_k = st.slider("Top-K (chunks)", 1, 5, 3)

        st.divider()

        # Info del modelo
        st.subheader("📋 Info del Modelo")
        models = ollama_client.list_models()
        st.write(f"**Modelo activo:** `llama3.2:3b`")
        st.write(f"**Modelos disponibles:** {', '.join(models)}")

        st.divider()

        # Limpiar chat
        if st.button("🗑️ Limpiar Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.last_metrics = None
            st.rerun()

    # Área principal: Chat
    chat_container = st.container()

    with chat_container:
        # Mostrar historial
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Input de chat
        if prompt := st.chat_input("Escribe tu pregunta sobre Techbox..."):
            # Agregar mensaje de usuario
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.chat_message("user"):
                st.markdown(prompt)

            # Generar respuesta con monitor
            with st.chat_message("assistant"):
                with st.spinner("🤔 Pensando..."):
                    start_time = time.perf_counter()

                    # Llamar al agente (internamente usa monitor_resources)
                    respuesta = agent.ask(
                        pregunta=prompt,
                        source="techbox",
                        top_k=top_k,
                        temperature=temperature,
                    )

                    elapsed_time = time.perf_counter() - start_time

                st.markdown(respuesta)

                # Guardar mensaje
                st.session_state.messages.append({"role": "assistant", "content": respuesta})

                # Leer métricas del monitor (se generan en agent.py y guardan en archivo)
                dashboard_path = "performance_dashboard.png"
                if os.path.exists(dashboard_path):
                    # Parsear métricas del output del monitor (aprox desde archivo o recalcular)
                    # Por simplicidad, mostramos la gráfica y métricas básicas
                    st.session_state.last_metrics = {
                        "elapsed_time": elapsed_time,
                        "dashboard_path": dashboard_path,
                    }

            # Actualizar sidebar con métricas
            st.rerun()

    # Mostrar métricas en sidebar si hay datos
    if st.session_state.last_metrics:
        metrics = st.session_state.last_metrics
        # Leer muestras del monitor para métricas detalladas
        # Como el monitor ya guardó la gráfica, la mostramos
        display_metrics_sidebar(
            elapsed_time=metrics["elapsed_time"],
            cpu_avg=0, cpu_peak=0,
            ram_avg=0, ram_peak=0,
            samples=0,
            dashboard_path=metrics["dashboard_path"],
        )


if __name__ == "__main__":
    main()