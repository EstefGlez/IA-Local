import requests
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
import re


class Document:
    """
    Represents a source document that can be loaded from a URL or local file.
    Provides methods to load content and split it into chunks for RAG processing.
    """

    # Timeout for URL requests (seconds)
    REQUEST_TIMEOUT = 10

    # GitHub URL patterns for conversion to raw.githubusercontent.com
    GITHUB_TREE_BLOB_PATTERN = re.compile(
        r'https?://github\.com/([^/]+)/([^/]+)/(tree|blob)/([^/]+)/(.+)'
    )

    def __init__(self, location: str, source_type: str = None):
        """
        Initialize a Document.

        Args:
            location: Either a URL (starting with http:// or https://) or a local file path.
            source_type: The source type identifier (e.g., "techbox", "obsidian").
        """
        self.location = location
        self.source = source_type  # e.g., "techbox" or "obsidian"
        self.content = None
        self.chunks = None

        # Determine if location is a URL or file path
        self.is_url = location.startswith(("http://", "https://"))

    def _convert_github_url(self, url: str) -> str:
        """
        Convierte URLs de GitHub con '/tree/' o '/blob/' a raw.githubusercontent.com.

        Args:
            url: URL original de GitHub

        Returns:
            URL convertida a raw.githubusercontent.com si aplica, sino la original
        """
        match = self.GITHUB_TREE_BLOB_PATTERN.match(url)
        if match:
            owner, repo, _, branch, file_path = match.groups()
            return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"
        return url

    def _scrape_webpage(self, url: str) -> str:
        """
        Extrae el texto principal de una página web usando BeautifulSoup.
        Elimina scripts, estilos y ruido visual.

        Args:
            url: URL de la página web a scrapear

        Returns:
            Texto limpio extraído de la página

        Raises:
            requests.exceptions.RequestException: Si falla la petición
            ValueError: Si no se puede extraer contenido útil
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError("beautifulsoup4 es requerido para scraping web. Instala con: pip install beautifulsoup4")

        try:
            response = requests.get(
                url,
                timeout=self.REQUEST_TIMEOUT,
                headers={"User-Agent": "IA-Local-RAG/1.0"}
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Eliminar elementos no deseados
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript', 'iframe', 'svg']):
                element.decompose()

            # Intentar extraer contenido principal
            # Prioridad: main > article > div[role=main] > body
            main_content = (
                soup.find('main') or
                soup.find('article') or
                soup.find('div', role='main') or
                soup.find('body')
            )

            if main_content is None:
                raise ValueError("No se pudo encontrar contenido principal en la página")

            # Extraer texto de párrafos, encabezados y elementos de texto
            text_parts = []
            for elem in main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'th', 'blockquote', 'pre', 'code']):
                text = elem.get_text(strip=True)
                if text and len(text) > 10:  # Filtrar ruido muy corto
                    text_parts.append(text)

            # Si no hay estructura semántica, usar todo el texto del body
            if not text_parts:
                full_text = main_content.get_text(separator='\n', strip=True)
                text_parts = [line for line in full_text.split('\n') if line.strip() and len(line.strip()) > 10]

            result = '\n\n'.join(text_parts)

            if not result or not result.strip():
                raise ValueError("No se pudo extraer texto significativo de la página")

            return result

        except requests.exceptions.Timeout:
            raise requests.exceptions.RequestException(f"Timeout al scrapear URL ({self.REQUEST_TIMEOUT}s): {url}")
        except requests.exceptions.ConnectionError:
            raise requests.exceptions.RequestException(f"Error de conexión a: {url}")
        except requests.exceptions.HTTPError as e:
            raise requests.exceptions.RequestException(f"Error HTTP {e.response.status_code}: {url}")
        except requests.exceptions.RequestException as e:
            raise requests.exceptions.RequestException(f"Error descargando {url}: {str(e)}")

    def load_content(self) -> str:
        """
        Load the document content from URL or local file.

        Returns:
            The raw text content of the document.

        Raises:
            requests.exceptions.RequestException: If URL request fails (timeout, connection error, etc.)
            FileNotFoundError: If local file doesn't exist
            ValueError: If content type is not text/markdown or URL is invalid
        """
        if self.is_url:
            # Validate URL format
            if not self.location.startswith(("http://", "https://")):
                raise ValueError(f"URL inválida: {self.location}")

            # Convert GitHub tree/blob URLs to raw.githubusercontent.com
            original_url = self.location
            self.location = self._convert_github_url(self.location)

            try:
                response = requests.get(
                    self.location,
                    timeout=self.REQUEST_TIMEOUT,
                    headers={"User-Agent": "IA-Local-RAG/1.0"}
                )
                response.raise_for_status()

                # Validate content type
                content_type = response.headers.get("Content-Type", "").lower()
                is_text_content = any(ct in content_type for ct in ["text/", "application/json", "application/x-yaml"])

                # Check if response is HTML (likely a webpage, not a raw file)
                content_lower = response.text.lower().strip()
                is_html = content_lower.startswith("<!doctype html") or content_lower.startswith("<html")

                # If it's HTML, always scrape to extract clean text
                # Raw text files (markdown, .txt, etc.) won't have HTML structure
                if is_html:
                    # It's a webpage - use scraping to extract main text
                    self.content = self._scrape_webpage(original_url)
                else:
                    # It's a raw text file or markdown
                    self.content = response.text

                if not self.content or not self.content.strip():
                    raise ValueError("El contenido descargado está vacío")

            except requests.exceptions.Timeout:
                raise requests.exceptions.RequestException(f"Timeout al descargar URL ({self.REQUEST_TIMEOUT}s): {self.location}")
            except requests.exceptions.ConnectionError:
                raise requests.exceptions.RequestException(f"Error de conexión a: {self.location}")
            except requests.exceptions.HTTPError as e:
                raise requests.exceptions.RequestException(f"Error HTTP {e.response.status_code}: {self.location}")
            except requests.exceptions.RequestException as e:
                raise requests.exceptions.RequestException(f"Error descargando {self.location}: {str(e)}")
            except ImportError as e:
                # BeautifulSoup not available
                raise requests.exceptions.RequestException(f"Para procesar páginas web se requiere beautifulsoup4: {str(e)}")
        else:
            # Local file path
            path = Path(self.location)
            if not path.exists():
                raise FileNotFoundError(f"Archivo no encontrado: {self.location}")
            if not path.is_file():
                raise ValueError(f"La ruta no es un archivo: {self.location}")

            try:
                with open(self.location, "r", encoding="utf-8") as f:
                    self.content = f.read()
            except UnicodeDecodeError:
                # Try with different encoding
                with open(self.location, "r", encoding="latin-1") as f:
                    self.content = f.read()

            if not self.content or not self.content.strip():
                raise ValueError("El archivo está vacío")

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