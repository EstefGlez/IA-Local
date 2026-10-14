from core.retriever import RAGRetriever
from core.ollama_client import OllamaClient
from core.document import Document
from core.agent import ConversationalAgent

if __name__ == "__main__":
    print("Inicializando componentes del agente...")

    # 1. Inicializar el retriever y cargar fuentes
    retriever = RAGRetriever()
    
    # Cargar Techbox (fuente de negocio)
    techbox_url = "https://raw.githubusercontent.com/EstefGlez/techbox-mx/refs/heads/main/especificaciones-techbox.md"
    print(f"Cargando Techbox desde: {techbox_url}")
    techbox_doc = Document(location=techbox_url, source_type="techbox")
    retriever.add_document(techbox_doc)

    # 2. Inicializar cliente y agente
    ollama_client = OllamaClient()
    agent = ConversationalAgent(retriever=retriever, ollama_client=ollama_client)

    # 3. Prueba de pregunta de negocio (Techbox) con top_k reducido
    pregunta = "¿Cuánto tiempo tardan los envíos?"
    print(f"\nPregunta: {pregunta}")
    
    try:
        # Pasamos top_k=1 para agilizar la respuesta del modelo local
        respuesta = agent.ask(pregunta, source="techbox", top_k=1)
        print("\n--- Respuesta del Agente ---")
        print(respuesta)
    except Exception as e:
        print(f"Error al ejecutar la consulta: {e}")