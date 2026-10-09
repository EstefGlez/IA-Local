import chromadb
from sentence_transformers import SentenceTransformer
import hashlib
import requests
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
            response = requests.get(api_url)
            response.raise_for_status()  # Raise an exception for bad status codes

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

                    # Create a Document with the raw URL and source type
                    document = Document(location=raw_url, source_type=source_type)

                    # Add the document to the retriever
                    self.add_document(document)
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