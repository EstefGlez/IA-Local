import requests
from pathlib import Path


class Document:
    """
    Represents a source document that can be loaded from a URL or local file.
    Provides methods to load content and split it into chunks for RAG processing.
    """

    def __init__(self, source: str):
        """
        Initialize a Document.

        Args:
            source: Either a URL (starting with http:// or https://) or a local file path.
        """
        self.source = source
        self.content = None
        self.chunks = None

        # Determine if source is a URL or file path
        self.is_url = source.startswith(("http://", "https://"))

    def load_content(self) -> str:
        """
        Load the document content from URL or local file.

        Returns:
            The raw text content of the document.
        """
        if self.is_url:
            response = requests.get(self.source)
            response.raise_for_status()  # Raise an exception for bad status codes
            self.content = response.text
        else:
            # Local file path
            with open(self.source, "r", encoding="utf-8") as f:
                self.content = f.read()
        return self.content

    def chunk_content(self, chunk_size: int = 500, overlap: int = 50) -> list[str]:
        """
        Split the document content into overlapping chunks.

        Args:
            chunk_size: Target size of each chunk in characters.
            overlap: Number of characters to overlap between consecutive chunks.

        Returns:
            List of text chunks.
        """
        if self.content is None:
            self.load_content()

        # Ensure we have content
        if not self.content:
            self.chunks = []
            return self.chunks

        chunks = []
        start = 0
        content_length = len(self.content)

        while start < content_length:
            # Calculate end index for this chunk
            end = start + chunk_size

            # If we're not at the end, try to break at a space to avoid cutting words
            if end < content_length:
                # Look back for a space to avoid breaking words
                while end > start and self.content[end] not in (" ", "\n", "\t", "."):
                    end -= 1
                # If we couldn't find a good breaking point, just use the original end
                if end == start:
                    end = start + chunk_size

            chunk = self.content[start:end]
            chunks.append(chunk)

            # Move start for next chunk, accounting for overlap
            start = end - overlap
            # Ensure we make progress
            if start >= content_length - overlap:
                break

        self.chunks = chunks
        return self.chunks

    def get_chunks(self, chunk_size: int = 500, overlap: int = 50) -> list[str]:
        """
        Get the document chunks, generating them if necessary.

        Args:
            chunk_size: Target size of each chunk in characters.
            overlap: Number of characters to overlap between consecutive chunks.

        Returns:
            List of text chunks.
        """
        if self.chunks is None:
            return self.chunk_content(chunk_size, overlap)
        return self.chunks