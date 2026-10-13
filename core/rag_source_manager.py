"""Gestor de fuentes RAG dinámicas (URLs y rutas locales)."""

import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from urllib.parse import urlparse
import requests


class SourceType(Enum):
    """Tipos de fuentes RAG soportadas."""
    URL = "url"
    LOCAL_FILE = "local_file"
    LOCAL_FOLDER = "local_folder"
    GITHUB_FOLDER = "github_folder"


@dataclass
class RagSource:
    """Representa una fuente RAG configurada."""
    id: str
    name: str  # Nombre amigable para UI
    source_type: str  # SourceType value
    location: str  # URL, ruta local, o owner/repo/folder para GitHub
    enabled: bool = True
    added_at: float = 0.0
    last_indexed_at: Optional[float] = None
    metadata: Dict[str, Any] = None  # Extra: branch, chunk_size, etc.

    def __post_init__(self):
        if self.added_at == 0.0:
            self.added_at = time.time()
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RagSource":
        return cls(**data)


class RagSourceManager:
    """Gestiona fuentes RAG configuradas por el usuario."""

    def __init__(self, storage_file: str = "./data/rag_sources.json"):
        """
        Inicializa el gestor de fuentes RAG.

        Args:
            storage_file: Archivo JSON donde persistir las fuentes.
        """
        self.storage_file = Path(storage_file)
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        self._sources: List[RagSource] = []
        self._load()

    def _load(self) -> None:
        """Carga las fuentes desde el archivo JSON."""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._sources = [RagSource.from_dict(item) for item in data]
            except Exception:
                self._sources = []
        else:
            self._sources = []

    def _save(self) -> None:
        """Guarda las fuentes al archivo JSON."""
        with open(self.storage_file, "w", encoding="utf-8") as f:
            json.dump([s.to_dict() for s in self._sources], f, ensure_ascii=False, indent=2)

    @staticmethod
    def validate_url(url: str, timeout: int = 10) -> tuple[bool, str]:
        """
        Valida que una URL sea accesible y devuelva contenido útil.

        Args:
            url: URL a validar
            timeout: Timeout en segundos para la petición

        Returns:
            Tupla (es_válida, mensaje_error_o_vacío)
        """
        if not url or not url.startswith(("http://", "https://")):
            return False, "URL inválida: debe empezar con http:// o https://"

        try:
            response = requests.head(
                url,
                timeout=timeout,
                headers={"User-Agent": "IA-Local-RAG/1.0"},
                allow_redirects=True
            )
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "").lower()
            content_length = response.headers.get("Content-Length")

            # Verificar que no sea un archivo binario muy grande
            if content_length and int(content_length) > 50 * 1024 * 1024:  # 50MB
                return False, f"Archivo demasiado grande ({int(content_length) / (1024*1024):.1f}MB). Máximo 50MB."

            return True, ""

        except requests.exceptions.Timeout:
            return False, f"Timeout validando URL ({timeout}s)"
        except requests.exceptions.ConnectionError:
            return False, "Error de conexión: la URL no es accesible"
        except requests.exceptions.HTTPError as e:
            return False, f"Error HTTP {e.response.status_code}"
        except requests.exceptions.RequestException as e:
            return False, f"Error validando URL: {str(e)}"
        except Exception as e:
            return False, f"Error inesperado: {str(e)}"

    def add_source(
        self,
        name: str,
        source_type: str,
        location: str,
        enabled: bool = True,
        metadata: Dict[str, Any] = None,
        validate: bool = True,
    ) -> RagSource:
        """
        Añade una nueva fuente RAG.

        Args:
            name: Nombre amigable para la UI.
            source_type: Tipo de fuente (url, local_file, local_folder, github_folder).
            location: URL, ruta local, o "owner/repo/folder" para GitHub.
            enabled: Si la fuente está activa para indexación.
            metadata: Metadatos extra (ej. branch para GitHub, chunk_size, overlap).
            validate: Si validar la URL antes de agregarla (solo para source_type=url).

        Returns:
            La fuente creada.

        Raises:
            ValueError: Si la validación falla y validate=True
        """
        # Validar URL si es tipo URL y validate=True
        if validate and source_type == SourceType.URL.value:
            is_valid, error_msg = self.validate_url(location)
            if not is_valid:
                raise ValueError(f"URL inválida o inaccesible: {error_msg}")

        source_id = f"src_{int(time.time() * 1000)}"
        source = RagSource(
            id=source_id,
            name=name,
            source_type=source_type,
            location=location,
            enabled=enabled,
            metadata=metadata or {},
        )
        self._sources.append(source)
        self._save()
        return source

    def remove_source(self, source_id: str) -> bool:
        """
        Elimina una fuente RAG.

        Args:
            source_id: ID de la fuente a eliminar.

        Returns:
            True si se eliminó, False si no existía.
        """
        for i, source in enumerate(self._sources):
            if source.id == source_id:
                self._sources.pop(i)
                self._save()
                return True
        return False

    def toggle_source(self, source_id: str) -> Optional[RagSource]:
        """
        Alterna el estado enabled/disabled de una fuente.

        Args:
            source_id: ID de la fuente.

        Returns:
            La fuente actualizada o None si no existe.
        """
        for source in self._sources:
            if source.id == source_id:
                source.enabled = not source.enabled
                self._save()
                return source
        return None

    def update_source(self, source_id: str, **kwargs) -> Optional[RagSource]:
        """
        Actualiza campos de una fuente existente.

        Args:
            source_id: ID de la fuente.
            **kwargs: Campos a actualizar (name, location, enabled, metadata).

        Returns:
            La fuente actualizada o None si no existe.
        """
        for source in self._sources:
            if source.id == source_id:
                for key, value in kwargs.items():
                    if hasattr(source, key):
                        setattr(source, key, value)
                self._save()
                return source
        return None

    def get_source(self, source_id: str) -> Optional[RagSource]:
        """Obtiene una fuente por ID."""
        for source in self._sources:
            if source.id == source_id:
                return source
        return None

    def list_sources(self) -> List[RagSource]:
        """Lista todas las fuentes configuradas."""
        return list(self._sources)

    def list_enabled_sources(self) -> List[RagSource]:
        """Lista solo las fuentes habilitadas."""
        return [s for s in self._sources if s.enabled]

    def mark_indexed(self, source_id: str) -> None:
        """Marca una fuente como indexada recientemente."""
        for source in self._sources:
            if source.id == source_id:
                source.last_indexed_at = time.time()
                self._save()
                break

    def get_enabled_locations_by_type(self, source_type: str) -> List[str]:
        """
        Obtiene las ubicaciones de fuentes habilitadas de un tipo específico.

        Args:
            source_type: Tipo de fuente a filtrar.

        Returns:
            Lista de ubicaciones (URLs, rutas, etc.).
        """
        return [
            s.location for s in self._sources
            if s.enabled and s.source_type == source_type
        ]

    def has_sources(self) -> bool:
        """Verifica si hay al menos una fuente habilitada."""
        return len(self.list_enabled_sources()) > 0

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de las fuentes."""
        total = len(self._sources)
        enabled = len(self.list_enabled_sources())
        indexed = sum(1 for s in self._sources if s.last_indexed_at is not None)
        return {
            "total": total,
            "enabled": enabled,
            "indexed": indexed,
            "by_type": {
                st.value: len([s for s in self._sources if s.source_type == st.value])
                for st in SourceType
            }
        }