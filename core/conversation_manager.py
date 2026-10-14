"""Gestor de conversaciones locales en JSON."""

import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class Conversation:
    """Representa una conversación guardada."""
    id: str
    title: str
    messages: List[Dict[str, str]]
    created_at: float
    updated_at: float
    model_config: Dict[str, Any]  # temperatura, top_k, etc.

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Conversation":
        return cls(**data)


class ConversationManager:
    """Gestiona conversaciones persistentes en archivos JSON."""

    def __init__(self, storage_dir: str = "./data/conversations"):
        """
        Inicializa el gestor de conversaciones.

        Args:
            storage_dir: Directorio donde guardar los archivos JSON de conversaciones.
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._current_conversation_id: Optional[str] = None

    def _get_filepath(self, conversation_id: str) -> Path:
        """Obtiene la ruta del archivo para un ID de conversación."""
        return self.storage_dir / f"{conversation_id}.json"

    def create_conversation(
        self,
        title: str = None,
        model_config: Dict[str, Any] = None,
    ) -> Conversation:
        """
        Crea una nueva conversación vacía.

        Args:
            title: Título opcional (se autogenera si no se da).
            model_config: Configuración del modelo (temperatura, top_k, etc.).

        Returns:
            La nueva conversación creada.
        """
        conv_id = f"conv_{int(time.time() * 1000)}"
        if title is None:
            title = f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        if model_config is None:
            model_config = {"temperature": 0.3, "top_k": 3}

        conversation = Conversation(
            id=conv_id,
            title=title,
            messages=[],
            created_at=time.time(),
            updated_at=time.time(),
            model_config=model_config,
        )

        self._save(conversation)
        self._current_conversation_id = conv_id
        return conversation

    def _save(self, conversation: Conversation) -> None:
        """Guarda una conversación en disco."""
        conversation.updated_at = time.time()
        filepath = self._get_filepath(conversation.id)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(conversation.to_dict(), f, ensure_ascii=False, indent=2)

    def load_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Carga una conversación desde disco.

        Args:
            conversation_id: ID de la conversación a cargar.

        Returns:
            La conversación cargada o None si no existe.
        """
        filepath = self._get_filepath(conversation_id)
        if not filepath.exists():
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Conversation.from_dict(data)
        except Exception:
            return None

    def save_conversation(self, conversation: Conversation) -> None:
        """Guarda/actualiza una conversación existente."""
        self._save(conversation)

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Elimina una conversación.

        Args:
            conversation_id: ID de la conversación a eliminar.

        Returns:
            True si se eliminó, False si no existía.
        """
        filepath = self._get_filepath(conversation_id)
        if filepath.exists():
            filepath.unlink()
            if self._current_conversation_id == conversation_id:
                self._current_conversation_id = None
            return True
        return False

    def list_conversations(self) -> List[Dict[str, Any]]:
        """
        Lista todas las conversaciones disponibles (metadatos ligeros).

        Returns:
            Lista de dicts con id, title, created_at, updated_at, message_count.
        """
        conversations = []
        for filepath in sorted(self.storage_dir.glob("conv_*.json"), reverse=True):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                conversations.append({
                    "id": data["id"],
                    "title": data["title"],
                    "created_at": data["created_at"],
                    "updated_at": data["updated_at"],
                    "message_count": len(data.get("messages", [])),
                })
            except Exception:
                continue
        return conversations

    def get_current_conversation(self) -> Optional[Conversation]:
        """Obtiene la conversación actualmente activa."""
        if self._current_conversation_id:
            return self.load_conversation(self._current_conversation_id)
        return None

    def set_current_conversation(self, conversation_id: str) -> bool:
        """
        Establece la conversación activa.

        Args:
            conversation_id: ID de la conversación a activar.

        Returns:
            True si existe y se activó, False en caso contrario.
        """
        if self._get_filepath(conversation_id).exists():
            self._current_conversation_id = conversation_id
            return True
        return False

    def add_message(self, conversation_id: str, role: str, content: str) -> bool:
        """
        Añade un mensaje a una conversación existente.

        Args:
            conversation_id: ID de la conversación.
            role: "user" o "assistant".
            content: Contenido del mensaje.

        Returns:
            True si se añadió correctamente.
        """
        conversation = self.load_conversation(conversation_id)
        if conversation is None:
            return False

        conversation.messages.append({"role": role, "content": content})
        self._save(conversation)
        return True

    def update_messages(self, conversation_id: str, messages: List[Dict[str, str]]) -> bool:
        """
        Reemplaza todos los mensajes de una conversación.

        Args:
            conversation_id: ID de la conversación.
            messages: Nueva lista de mensajes.

        Returns:
            True si se actualizó correctamente.
        """
        conversation = self.load_conversation(conversation_id)
        if conversation is None:
            return False

        conversation.messages = messages
        self._save(conversation)
        return True

    def update_model_config(self, conversation_id: str, model_config: Dict[str, Any]) -> bool:
        """
        Actualiza la configuración del modelo de una conversación.

        Args:
            conversation_id: ID de la conversación.
            model_config: Nueva configuración (temperatura, top_k, etc.).

        Returns:
            True si se actualizó correctamente.
        """
        conversation = self.load_conversation(conversation_id)
        if conversation is None:
            return False

        conversation.model_config = model_config
        self._save(conversation)
        return True

    def ensure_current_conversation(self, model_config: Dict[str, Any] = None) -> Conversation:
        """
        Asegura que hay una conversación activa, creándola si no existe.

        Args:
            model_config: Configuración del modelo para la nueva conversación.

        Returns:
            La conversación actual (existente o nueva).
        """
        if self._current_conversation_id:
            conv = self.load_conversation(self._current_conversation_id)
            if conv:
                return conv

        # No hay conversación activa o no se pudo cargar, crear nueva
        return self.create_conversation(model_config=model_config)