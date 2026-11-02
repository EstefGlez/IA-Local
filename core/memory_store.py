"""Gestor de archivos de memoria por sesión (extraído de app.py sin cambiar lógica)."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional


class MemoryStore:
    """Reúne las 8 funciones de memoria que vivían en app.py (líneas ~84-247)."""

    def __init__(self, base_dir: str = "./data/archivos_memoria"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_memory_dir(self, session_id: str) -> Path:
        """Obtiene el directorio de memoria para una sesión."""
        return self.base_dir / session_id

    def list_memory_files(self, session_id: str) -> List[Path]:
        """Lista archivos JSON de memoria para una sesión."""
        mem_dir = self.get_memory_dir(session_id)
        if not mem_dir.exists():
            return []
        return sorted(mem_dir.glob("*.json"))

    def detect_json_memory_proposal(self, content: str) -> Optional[dict]:
        """
        Detecta si un mensaje del asistente contiene una propuesta de guardado de memoria en formato JSON.
        Busca bloques de código JSON que parezcan propuestas de memoria (con campos filename, content, topic_summary).

        Returns:
            Dict con la propuesta parseada o None si no se detecta.
        """
        import re

        # Buscar bloques de código JSON
        json_blocks = re.findall(r'```json\s*(\{[\s\S]*?\})\s*```', content)

        for block in json_blocks:
            try:
                data = json.loads(block)
                # Verificar que tiene los campos esperados de una propuesta de memoria
                if isinstance(data, dict) and "filename" in data and "content" in data and "topic_summary" in data:
                    return data
            except json.JSONDecodeError:
                continue

        # También buscar JSON inline (sin bloques de código) que parezca una propuesta
        # Usar un enfoque más flexible: buscar cualquier objeto JSON con los 3 campos requeridos
        # Buscar patrones que contengan los tres campos clave
        inline_json_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*"filename"(?:[^{}]|(?:\{[^{}]*\}))*"content"(?:[^{}]|(?:\{[^{}]*\}))*"topic_summary"(?:[^{}]|(?:\{[^{}]*\}))*\}'
        matches = re.findall(inline_json_pattern, content)

        for match in matches:
            try:
                data = json.loads(match)
                if isinstance(data, dict) and "filename" in data and "content" in data and "topic_summary" in data:
                    return data
            except json.JSONDecodeError:
                continue

        # Fallback: búsqueda más simple por los tres campos en cualquier orden
        simple_pattern = r'\{[^{}]*"filename"[^{}]*\}'
        potential_matches = re.findall(simple_pattern, content)
        for match in potential_matches:
            try:
                data = json.loads(match)
                if isinstance(data, dict) and "filename" in data and "content" in data and "topic_summary" in data:
                    return data
            except json.JSONDecodeError:
                continue

        return None

    def save_memory_from_proposal(self, session_id: str, proposal: dict) -> tuple[bool, str]:
        """
        Guarda un archivo de memoria a partir de una propuesta detectada.
        Ahora espera que la propuesta contenga 'memory_data' (JSON completo ya construido en Python)
        o los campos legacy filename/content/topic_summary.

        Returns:
            Tupla (success: bool, message: str)
        """
        try:
            # Nuevo formato: memory_data ya viene completo desde agent.py
            if "memory_data" in proposal and proposal["memory_data"]:
                memory_data = proposal["memory_data"]
                filename = memory_data.get("metadata", {}).get("filename", "memoria.json")
            else:
                # Formato legacy (fallback defensivo)
                filename = proposal.get("filename", "")
                content = proposal.get("content", {})
                topic_summary = proposal.get("topic_summary", "")

                if not filename or not content:
                    return False, "Propuesta incompleta: faltan filename o content"

                if not filename.endswith(".json"):
                    filename += ".json"

                from datetime import datetime
                memory_data = {
                    "metadata": {
                        "saved_at": datetime.now().isoformat(),
                        "session_id": session_id,
                        "topic": topic_summary,
                        "filename": filename
                    },
                    "content": content
                }

            # Guardar archivo
            mem_dir = self.get_memory_dir(session_id)
            mem_dir.mkdir(parents=True, exist_ok=True)
            filepath = mem_dir / filename

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(memory_data, f, ensure_ascii=False, indent=2)

            return True, f"Archivo de memoria '{filename}' guardado correctamente"
        except Exception as e:
            return False, f"Error al guardar: {str(e)}"

    def load_memory_file(self, session_id: str, filename: str) -> dict:
        """Carga un archivo de memoria JSON."""
        filepath = self.get_memory_dir(session_id) / filename
        if not filepath.exists():
            return {}
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_memory_file(self, session_id: str, filename: str, data: dict) -> bool:
        """Guarda un archivo de memoria JSON."""
        mem_dir = self.get_memory_dir(session_id)
        mem_dir.mkdir(parents=True, exist_ok=True)
        filepath = mem_dir / filename
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def delete_memory_file(self, session_id: str, filename: str) -> bool:
        """Elimina un archivo de memoria y limpia el directorio padre si queda vacío."""
        filepath = self.get_memory_dir(session_id) / filename
        if filepath.exists():
            try:
                filepath.unlink()
                # Verificar si el directorio padre quedó vacío y eliminarlo si es así
                parent_dir = filepath.parent
                if parent_dir.exists() and not any(parent_dir.iterdir()):
                    parent_dir.rmdir()
                return True
            except Exception:
                return False
        return False

    def list_all_sessions_with_memory(self) -> List[str]:
        """Lista todas las sesiones que tienen archivos de memoria."""
        if not self.base_dir.exists():
            return []
        sessions = []
        for item in self.base_dir.iterdir():
            if item.is_dir() and any(item.glob("*.json")):
                sessions.append(item.name)
        return sorted(sessions, reverse=True)
