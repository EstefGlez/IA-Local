import json
import requests
from typing import List, Dict, Any, Optional


class OllamaClient:
    """
    Cliente para interactuar con el servidor local de Ollama.
    Envuelve las llamadas HTTP a la API de Ollama para generar respuestas
    usando el endpoint /api/chat.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2:3b",
        timeout: int = 60
    ):
        """
        Inicializa el cliente de Ollama.

        Args:
            base_url: URL base del servidor Ollama (default: http://localhost:11434)
            model: Nombre del modelo a usar (default: llama3.2:3b)
            timeout: Tiempo máximo de espera para las peticiones en segundos (default: 60)
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None
    ) -> str:
        """
        Envía una lista de mensajes a Ollama y devuelve la respuesta de texto.

        Args:
            messages: Lista de diccionarios con claves "role" y "content".
                      Ejemplo: [{"role": "user", "content": "Hola"}]
            model: Nombre del modelo a usar. Si se proporciona, sobreescribe el modelo por defecto.

        Returns:
            El contenido de la respuesta generada por Ollama.

        Raises:
            ConnectionError: Si no se puede conectar a Ollama.
            ValueError: Si la respuesta de Ollama contiene un error.
        """
        if model is None:
            model = self.model

        payload = {
            "model": model,
            "messages": messages,
            "stream": False
        }

        url = f"{self.base_url}/api/chat"

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()  # Lanza excepción para códigos de error HTTP

            result = response.json()

            # Ollama devuelve una respuesta con la estructura:
            # {"model": "...", "created_at": "...", "message": {"role": "assistant", "content": "..."}, ...}
            if "message" in result and "content" in result["message"]:
                return result["message"]["content"]
            else:
                # Si la estructura no es la esperada, devolvemos el texto completo o un mensaje de error
                raise ValueError(f"Respuesta inesperada de Ollama: {result}")

        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(
                f"No se pudo conectar a Ollama en {self.base_url}. "
                f"Asegúrate de que Ollama esté ejecutándose. Error: {str(e)}"
            )
        except requests.exceptions.Timeout as e:
            raise ConnectionError(
                f"Timeout al conectar con Ollama después de {self.timeout} segundos. "
                f"El modelo podría estar tardando demasiado en responder. Error: {str(e)}"
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(
                f"Error en la petición a Ollama: {str(e)}"
            )


# Test rápido si se ejecuta este archivo directamente
if __name__ == "__main__":
    # Crear una instancia del cliente
    client = OllamaClient()

    # Mensaje de prueba
    test_messages = [
        {"role": "user", "content": "Hola, preséntate"}
    ]

    print("Probando conexión a Ollama...")
    try:
        response = client.chat(test_messages)
        print("Respuesta de Ollama:")
        print(response)
    except ConnectionError as e:
        print(f"Error de conexión: {e}")
    except Exception as e:
        print(f"Error inesperado: {e}")