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

    def ask(self, pregunta: str, source: str = None) -> str:
        """
        Procesa una pregunta utilizando el pipeline RAG.

        Args:
            pregunta: Pregunta del usuario.
            source: Optional source filter (e.g., "techbox", "obsidian").
                   If provided, only results from this source will be considered.

        Returns:
            Respuesta generada basada en el contexto recuperado.
        """
        # 1. Buscar fragmentos relevantes
        chunks = self.retriever.search(pregunta, top_k=3, source=source)

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

    # Cargar y indexar el documento de Techbox con source="techbox"
    techbox_url = "https://raw.githubusercontent.com/EstefGlez/techbox-mx/refs/heads/main/especificaciones-techbox.md"
    print(f"Cargando documento de Techbox desde: {techbox_url}")
    techbox_doc = Document(location=techbox_url, source_type="techbox")
    retriever.add_document(techbox_doc)
    print("Documento de Techbox indexado correctamente.")

    # Cargar y indexar documentos de Obsidian con source="obsidian"
    obsidian_folder = r"C:\Users\estef\Downloads\Portafolio Sprints\Notebook-TripleTen\Arsenal_Tecnico"
    print(f"Cargando documentos de Obsidian desde: {obsidian_folder}")
    try:
        retriever.load_folder(obsidian_folder, source_type="obsidian")
        print("Documentos de Obsidian indexados correctamente.")
    except Exception as e:
        print(f"Advertencia: No se pudo cargar la carpeta de Obsidian: {e}")
        print("Continuando solo con el documento de Techbox...")

    # Crear el cliente de Ollama
    ollama_client = OllamaClient()

    # Crear el agente conversacional
    agent = ConversationalAgent(retriever, ollama_client)

    # Probar pregunta sobre envíos con source="techbox"
    pregunta_envio = "¿cuánto tarda el envío?"
    print(f"\nPregunta (Techbox): {pregunta_envio}")

    try:
        respuesta_envio = agent.ask(pregunta_envio, source="techbox")
        print("\nRespuesta:")
        print(respuesta_envio)
    except Exception as e:
        print(f"\nError durante la ejecución: {e}")

    # Probar pregunta sobre pandas/SQL con source="obsidian" (si se cargaron documentos)
    print(f"\n" + "="*50)
    pregunta_obsidian = "¿Cómo se hace un groupby en pandas?"
    print(f"Pregunta (Obsidian): {pregunta_obsidian}")

    try:
        respuesta_obsidian = agent.ask(pregunta_obsidian, source="obsidian")
        print("\nRespuesta:")
        print(respuesta_obsidian)
    except Exception as e:
        print(f"\nError durante la ejecución: {e}")