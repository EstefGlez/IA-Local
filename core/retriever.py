import chromadb
from sentence_transformers import SentenceTransformer
import uuid
from pathlib import Path
from typing import List
from .document import Document


class RAGRetriever:
    """
    A Retrieval-Augmented Generation (RAG) retriever that uses ChromaDB as a
    vector database and SentenceTransformers for generating embeddings.
    """

    def __init__(self, persist_directory: str = "./data/chroma", collection_name: str = "documents"):
        """
        Initialize the RAGRetriever.

        Args:
            persist_directory: Directory where ChromaDB will store its data.
            collection_name: Name of the ChromaDB collection to use.
        """
        # Ensure the persist directory exists
        Path(persist_directory).mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=persist_directory)
        # Get or create the collection
        self.collection = self.client.get_or_create_collection(name=collection_name)

        # Initialize the sentence transformer model for embeddings
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')

    def add_document(self, document: Document) -> None:
        """
        Add a document to the vector database.
        The document is split into chunks, each chunk is embedded and stored.

        Args:
            document: A Document instance to be indexed.
        """
        # Get chunks from the document
        chunks = document.get_chunks()
        if not chunks:
            return  # No content to add

        # Generate embeddings for each chunk
        embeddings = self.encoder.encode(chunks).tolist()

        # Prepare data for ChromaDB
        ids = [str(uuid.uuid4()) for _ in chunks]
        metadatas = [{"source": document.source, "chunk_index": i} for i in range(len(chunks))]

        # Add to the collection
        self.collection.add(
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )

    def search(self, query: str, top_k: int = 3) -> List[str]:
        """
        Search for the most relevant chunks for a given query.

        Args:
            query: The query string to search for.
            top_k: Number of top results to return.

        Returns:
            A list of the top_k most relevant text chunks.
        """
        # Generate embedding for the query
        query_embedding = self.encoder.encode([query]).tolist()[0]

        # Query the collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )

        # Extract the documents (chunks) from the results
        # results['documents'] is a list of lists (one list per query)
        if results['documents'] and len(results['documents']) > 0:
            return results['documents'][0]
        return []