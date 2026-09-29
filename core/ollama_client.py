import json
import requests
from typing import Dict, Any, Optional
from pathlib import Path


class OllamaClient:
    """
    Cliente para interactuar con el servidor local de Ollama.
    Envuelve las llamadas HTTP a la API de Ollama para generar respuestas
    usando modelos cuantizados como Llama 3.2.
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
        self.generate_endpoint = f"{self.base_url}/api/generate"

    def _make_payload(
        self,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Crea el payload para la petición a la API de Ollama.

        Args:
            prompt: El prompt principal para generar la respuesta
            context: Contexto adicional (opcional)
            temperature: Parámetro de creatividad (0.0 a 1.0)
            max_tokens: Número máximo de tokens a generar (opcional)
            stream: Si se debe usar modo streaming

        Returns:
            Diccionario con el payload para la petición
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
            }
        }

        if context:
            payload["context"] = context

        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens

        return payload

    def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Genera una respuesta usando el modelo de Ollama.

        Args:
            prompt: El prompt para generar la respuesta
            context: Contexto adicional obtenido del RAG (opcional)
            temperature: Parámetro de creatividad (0.0 a 1.0)
            max_tokens: Número máximo de tokens a generar (opcional)

        Returns:
            La respuesta generada como string

        Raises:
            ConnectionError: Si no se puede conectar a Ollama
            ValueError: Si la respuesta de Ollama contiene un error
        """
        payload = self._make_payload(
            prompt=prompt,
            context=context,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False
        )

        try:
            response = requests.post(
                self.generate_endpoint,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()  # Lanza excepción para códigos de error HTTP

            result = response.json()

            if "error" in result:
                raise ValueError(f"Error de Ollama: {result['error']}")

            return result.get("response", "")

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

    def check_connection(self) -> bool:
        """
        Verifica si el servidor Ollama está disponible y responde.

        Returns:
            True si Ollama está disponible, False en caso contrario
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def list_models(self) -> list[str]:
        """
        Lista los modelos disponibles en el servidor Ollama.

        Returns:
            Lista de nombres de modelos disponibles

        Raises:
            ConnectionError: Si no se puede conectar a Ollama
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"No se pudo obtener la lista de modelos: {str(e)}")


# Ejemplo de uso (solo para testing)
if __name__ == "__main__":
    # Test básico de conexión
    client = OllamaClient()

    print("Verificando conexión a Ollama...")
    if client.check_connection():
        print("✅ Conexión establecida con Ollama")

        print("\nListando modelos disponibles:")
        try:
            models = client.list_models()
            if models:
                for model in models:
                    print(f"  - {model}")
            else:
                print("  No se encontraron modelos")
        except ConnectionError as e:
            print(f"❌ Error al listar modelos: {e}")

        print("\nProbando generación de texto:")
        try:
            response = client.generate(
                prompt="¿Qué es la inteligencia artificial? Responde en una oración.",
                temperature=0.3,
                max_tokens=50
            )
            print(f"Respuesta: {response.strip()}")
        except Exception as e:
            print(f"❌ Error al generar texto: {e}")
    else:
        print("❌ No se pudo conectar a Ollama. Asegúrate de que:")
        print("   1. Ollama esté instalado y ejecutándose")
        print("   2. El servicio esté accesible en http://localhost:11434")
        print("   3. No haya firewalls bloqueando la conexión")