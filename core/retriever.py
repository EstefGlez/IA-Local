import chromadb
from sentence_transformers import SentenceTransformer
import hashlib
import requests
from pathlib import Path
from typing import List, Dict, Any
from .document import Document
from .rag_source_manager import RagSourceManager, SourceType


class RAGRetriever:
    """
    A Retrieval-Augmented Generation (RAG) retriever that uses ChromaDB as a
    vector database and SentenceTransformers for generating embeddings.
    """

    def __init__(
        self,
        persist_directory: str = "./data/chroma",
        collection_name: str = "documents",
        rag_source_manager: RagSourceManager = None,
    ):
        """
        Initialize the RAGRetriever.

        Args:
            persist_directory: Directory where ChromaDB will store its data.
            collection_name: Name of the ChromaDB collection to use.
            rag_source_manager: Optional RagSourceManager for dynamic source management.
        """
        # Ensure the persist directory exists
        Path(persist_directory).mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=persist_directory)
        # Get or create the collection
        self.collection = self.client.get_or_create_collection(name=collection_name)

        # Initialize the sentence transformer model for embeddings
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')

        # Optional dynamic source manager
        self.rag_source_manager = rag_source_manager

    def add_document(self, document: Document) -> None:
        """
        Add a document to the vector database.
        The document is split into chunks, each chunk is embedded and stored.
        Uses deterministic hash IDs and upsert to avoid duplicates.

        Args:
            document: A Document instance to be indexed.
        """
        # Get chunks from the document
        chunks = document.get_chunks()
        if not chunks:
            return  # No content to add

        # Generate embeddings for each chunk
        embeddings = self.encoder.encode(chunks).tolist()

        # Prepare data for ChromaDB - use deterministic hash IDs based on content + source + chunk_index
        ids = []
        for i, chunk in enumerate(chunks):
            # Create a deterministic ID using MD5 hash of source + chunk_index + chunk content
            content_hash = hashlib.md5(f"{document.source}_{i}_{chunk}".encode('utf-8')).hexdigest()
            ids.append(content_hash)

        metadatas = [{"source": document.source, "chunk_index": i} for i in range(len(chunks))]

        # Use upsert to avoid duplicates (updates if exists, inserts if new)
        self.collection.upsert(
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )

    def search(self, query: str, top_k: int = 3, source: str = None) -> List[str]:
        """
        Search for the most relevant chunks for a given query.

        Args:
            query: The query string to search for.
            top_k: Number of top results to return.
            source: Optional source filter (e.g., "techbox", "obsidian").
                   If provided, only results from this source will be returned.

        Returns:
            A list of the top_k most relevant text chunks.
        """
        # Generate embedding for the query
        query_embedding = self.encoder.encode([query]).tolist()[0]

        # Build where clause for metadata filtering if source is specified
        where_clause = {"source": source} if source else None

        # Query the collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_clause
        )

        # Extract the documents (chunks) from the results
        # results['documents'] is a list of lists (one list per query)
        if results['documents'] and len(results['documents']) > 0:
            return results['documents'][0]
        return []

    def load_folder(self, folder_path: str, source_type: str) -> None:
        """
        Load all .md files from a folder and add them to the vector database.

        Args:
            folder_path: Path to the folder containing .md files.
            source_type: Source type identifier to assign to all documents from this folder.
        """
        folder = Path(folder_path)
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        # Find all .md files in the folder (recursively)
        md_files = list(folder.rglob("*.md"))

        if not md_files:
            print(f"No .md files found in {folder_path}")
            return

        print(f"Found {len(md_files)} .md files to process from {folder_path}")

        # Process each .md file
        for md_file in md_files:
            try:
                # Create a Document with the file location and source type
                document = Document(location=str(md_file), source_type=source_type)

                # Add the document to the retriever
                self.add_document(document)
                print(f"Processed: {md_file.name}")

            except Exception as e:
                print(f"Error processing {md_file.name}: {str(e)}")

        print(f"Finished loading folder: {folder_path}")

    def load_from_github_folder(self, owner: str, repo: str, folder_path: str, source_type: str, branch: str = "main") -> None:
        """
        Load all .md files from a GitHub repository folder and add them to the vector database.

        Args:
            owner: GitHub repository owner (username or organization)
            repo: GitHub repository name
            folder_path: Path to the folder within the repository (can be nested)
            source_type: Source type identifier to assign to all documents from this folder
            branch: Git branch to use (default: "main")
        """
        # Construct the GitHub API URL to get the repository tree
        api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"

        try:
            print(f"Fetching repository tree from: {api_url}")
            response = requests.get(
                api_url,
                timeout=Document.REQUEST_TIMEOUT,
                headers={"User-Agent": "IA-Local-RAG/1.0"}
            )
            response.raise_for_status()

            tree_data = response.json()

            # Filter for .md files in the specified folder
            md_files = []
            for item in tree_data.get('tree', []):
                # Check if it's a file (blob), not a directory
                if item.get('type') == 'blob':
                    item_path = item.get('path', '')
                    # Check if the path starts with folder_path and ends with .md
                    if item_path.startswith(folder_path) and item_path.endswith('.md'):
                        md_files.append(item)

            if not md_files:
                print(f"No .md files found in {owner}/{repo}/{folder_path} on branch {branch}")
                return

            print(f"Found {len(md_files)} .md files to process from {owner}/{repo}/{folder_path}")

            # Process each .md file
            processed_count = 0
            for item in md_files:
                try:
                    file_path = item['path']
                    # Construct the raw GitHub URL
                    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"

                    # Validate and fetch with timeout
                    content, chunks = self._validate_and_fetch_url(raw_url, source_type)
                    self._add_chunks_to_collection(chunks, source_type)
                    print(f"Processed: {file_path}")
                    processed_count += 1

                except Exception as e:
                    print(f"Error processing {item.get('path', 'unknown')}: {str(e)}")

            print(f"Finished loading GitHub folder: {owner}/{repo}/{folder_path} ({processed_count} files processed)")

        except requests.exceptions.RequestException as e:
            print(f"Error fetching from GitHub API: {str(e)}")
            raise
        except Exception as e:
            print(f"Error processing GitHub folder: {str(e)}")
            raise

    def clear_collection(self) -> None:
        """Elimina todos los documentos de la colección actual."""
        try:
            # Obtener todos los IDs y eliminarlos
            all_docs = self.collection.get()
            if all_docs and all_docs.get('ids'):
                self.collection.delete(ids=all_docs['ids'])
                print(f"[RAGRetriever] Colección limpiada: {len(all_docs['ids'])} documentos eliminados")
        except Exception as e:
            print(f"[RAGRetriever] Error limpiando colección: {e}")

    def _validate_and_fetch_url(self, url: str, source_name: str) -> tuple[str, list[str]]:
        """
        Valida y descarga una URL, retornando el contenido y lista de chunks.
        Ahora maneja automáticamente:
        - Conversión de GitHub tree/blob a raw.githubusercontent.com
        - Scraping de páginas web generales (con BeautifulSoup si está disponible)

        Args:
            url: URL a descargar
            source_name: Nombre de la fuente para logging

        Returns:
            Tupla (contenido, lista_chunks)

        Raises:
            ValueError: Si la URL no es válida o no apunta a contenido texto
            requests.exceptions.RequestException: Si falla la descarga
            ImportError: Si se requiere BeautifulSoup pero no está instalado
        """
        # Validar que sea una URL válida
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"URL inválida: {url}")

        # Crear documento y cargar contenido (con timeout y conversión automática)
        doc = Document(location=url, source_type=source_name)
        content = doc.load_content()

        # Obtener chunks
        chunks = doc.get_chunks()
        if not chunks:
            raise ValueError("No se pudieron generar chunks del contenido descargado")

        return content, chunks

    def reindex_from_sources(self) -> Dict[str, Any]:
        """
        Re-indexa todas las fuentes habilitadas del RagSourceManager.

        Returns:
            Dict con estadísticas: sources_processed, documents_added, errors.
        """
        if self.rag_source_manager is None:
            return {"sources_processed": 0, "documents_added": 0, "errors": ["No hay RagSourceManager configurado"]}

        # Limpiar colección actual
        self.clear_collection()

        stats = {"sources_processed": 0, "documents_added": 0, "errors": []}
        enabled_sources = self.rag_source_manager.list_enabled_sources()

        for source in enabled_sources:
            try:
                # Limpiar location: quitar comillas dobles/simples al inicio/final y espacios
                clean_location = source.location.strip().strip('"').strip("'").strip()

                if source.source_type == SourceType.URL.value:
                    # Validar y descargar con timeout estricto
                    content, chunks = self._validate_and_fetch_url(clean_location, source.name)
                    # Agregar chunks directamente para mejor control
                    self._add_chunks_to_collection(chunks, source.name)
                    stats["documents_added"] += len(chunks)

                elif source.source_type == SourceType.LOCAL_FILE.value:
                    doc = Document(location=clean_location, source_type=source.name)
                    # Verificar que el archivo existe
                    if not Path(clean_location).exists():
                        raise FileNotFoundError(f"Archivo no encontrado: {clean_location}")
                    self.add_document(doc)
                    stats["documents_added"] += len(doc.get_chunks()) if doc.chunks else 1

                elif source.source_type == SourceType.LOCAL_FOLDER.value:
                    # Verificar que la carpeta existe
                    if not Path(clean_location).exists():
                        raise FileNotFoundError(f"Carpeta no encontrada: {clean_location}")
                    self.load_folder(clean_location, source.name)
                    # Contar archivos .md procesados
                    md_files = list(Path(clean_location).rglob("*.md"))
                    stats["documents_added"] += len(md_files)

                elif source.source_type == SourceType.GITHUB_FOLDER.value:
                    # metadata debería tener owner, repo, folder_path, branch
                    meta = source.metadata
                    self.load_from_github_folder(
                        owner=meta.get("owner", ""),
                        repo=meta.get("repo", ""),
                        folder_path=meta.get("folder_path", ""),
                        source_type=source.name,
                        branch=meta.get("branch", "main"),
                    )
                    stats["documents_added"] += 1

                self.rag_source_manager.mark_indexed(source.id)
                stats["sources_processed"] += 1

            except requests.exceptions.RequestException as e:
                error_msg = f"Error de red en {source.name}: {str(e)}"
                stats["errors"].append(error_msg)
                print(f"[RAGRetriever] {error_msg}")
            except ValueError as e:
                error_msg = f"Error de validación en {source.name}: {str(e)}"
                stats["errors"].append(error_msg)
                print(f"[RAGRetriever] {error_msg}")
            except Exception as e:
                error_msg = f"Error indexando {source.name}: {str(e)}"
                stats["errors"].append(error_msg)
                print(f"[RAGRetriever] {error_msg}")

        return stats

    def _add_chunks_to_collection(self, chunks: list[str], source_name: str) -> None:
        """
        Agrega chunks directamente a la colección ChromaDB.

        Args:
            chunks: Lista de chunks de texto
            source_name: Nombre de la fuente para metadatos
        """
        if not chunks:
            return

        # Generate embeddings for each chunk
        embeddings = self.encoder.encode(chunks).tolist()

        # Prepare data for ChromaDB
        ids = []
        for i, chunk in enumerate(chunks):
            content_hash = hashlib.md5(f"{source_name}_{i}_{chunk}".encode('utf-8')).hexdigest()
            ids.append(content_hash)

        metadatas = [{"source": source_name, "chunk_index": i} for i in range(len(chunks))]

        self.collection.upsert(
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )

    def has_documents(self) -> bool:
        """Verifica si la colección tiene documentos indexados."""
        try:
            count = self.collection.count()
            return count > 0
        except Exception:
            return False