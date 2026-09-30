from .retriever import RAGRetriever
from .ollama_client import OllamaClient
from .document import Document


class ConversationalAgent:
    """
    Agente conversacional que orquesta el flujo completo de RAG:
    - Recupera fragmentos relevantes usando RAGRetriever
    - Construye un prompt con el contexto recuperado
    - Genera una respuesta usando OllamaClient
    """

    def __init__(self, retriever: RAGRetriever, ollama_client: OllamaClient):
        """
        Inicializa el agente con las dependencias necesarias.

        Args:
            retriever: Instancia de RAGRetriever para buscar fragmentos relevantes.
            ollama_client: Instancia de OllamaClient para generar respuestas.
        """
        self.retriever = retriever
        self.ollama_client = ollama_client

    def ask(self, pregunta: str) -> str:
        """
        Procesa una pregunta utilizando el pipeline RAG.

        Args:
            pregunta: Pregunta del usuario.

        Returns:
            Respuesta generada basada en el contexto recuperado.
        """
        # 1. Buscar fragmentos relevantes
        chunks = self.retriever.search(pregunta, top_k=3)

        # 2. Construir el system prompt con el contexto
        if chunks:
            contexto = "\n\n".join(chunks)
            system_prompt = (
                f"Responde basándote únicamente en el siguiente contexto: "
                f"{contexto}. "
                f"Si la pregunta no se puede responder con ese contexto, "
                f"dilo honnestamente en vez de inventar."
            )
        else:
            # Si no hay contexto, instructimos al modelo que diga que no sabe
            system_prompt = (
                "No se encontró contexto relevante para responder la pregunta. "
                "Indica que no tienes suficiente información para responder."
            )

        # 3. Preparar los mensajes para el chat
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": pregunta}
        ]

        # 4. Obtener respuesta del modelo
        respuesta = self.ollama_client.chat(messages)
        return respuesta


# Test rápido si se ejecuta este archivo directamente
if __name__ == "__main__":
    print("Inicializando componentes para el test...")

    # Crear el retriever
    retriever = RAGRetriever()

    # Cargar y indexar el documento de Techbox
    techbox_url = "https://raw.githubusercontent.com/EstefGlez/techbox-mx/refs/heads/main/especificaciones-techbox.md"
    print(f"Cargando documento desde: {techbox_url}")
    doc = Document(techbox_url)
    doc.load_content()  # Cargar el contenido
    doc.chunk_content()  # Dividir en chunks
    retriever.add_document(doc)  # Indexar los chunks
    print("Documento indexado correctamente.")

    # Crear el cliente de Ollama
    ollama_client = OllamaClient()

    # Crear el agente conversacional
    agent = ConversationalAgent(retriever, ollama_client)

    # Hacer una pregunta de prueba
    pregunta = "¿cuánto tarda el envío?"
    print(f"\nPregunta: {pregunta}")

    try:
        respuesta = agent.ask(pregunta)
        print("\nRespuesta:")
        print(respuesta)
    except Exception as e:
        print(f"\nError durante la ejecución: {e}")