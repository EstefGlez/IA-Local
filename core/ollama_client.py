"""Cliente para comunicarse con la API local de Ollama."""

import json
import requests
from typing import Optional, List, Dict, Generator


class OllamaClient:
    """Cliente HTTP para interactuar con la API de Ollama en localhost."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2:3b",
        timeout: int = 300,
    ):
        """
        Inicializa el cliente de Ollama.

        Args:
            base_url: URL base del servidor Ollama (por defecto http://localhost:11434)
            model: Nombre del modelo a usar (por defecto llama3.2:3b)
            timeout: Timeout en segundos para las peticiones HTTP (por defecto 120s)
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._generate_endpoint = f"{self.base_url}/api/generate"
        self._chat_endpoint = f"{self.base_url}/api/chat"

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        num_ctx: Optional[int] = None,
    ) -> str:
        """
        Envía un prompt a Ollama y devuelve la respuesta generada.
        Usa el endpoint /api/generate (completion simple).

        Args:
            prompt: El texto del prompt a enviar al modelo
            model: Modelo a usar (sobrescribe el del constructor si se proporciona)
            temperature: Temperatura para el muestreo (0.0 - 1.0)
            top_p: Top-p para nucleus sampling
            max_tokens: Número máximo de tokens a generar (None = sin límite, default 2048)
            stream: Si True, usa streaming (no implementado en esta versión)

        Returns:
            La respuesta generada por el modelo como string

        Raises:
            requests.RequestException: Si hay error en la petición HTTP
            ValueError: Si la respuesta no tiene el formato esperado
        """
        if stream:
            raise NotImplementedError("Streaming no está implementado aún. Usa stream=False.")

        payload = {
            "model": model or self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_ctx": num_ctx or 4096,
                "num_predict": max_tokens or 2048,
                "keep_alive": "5m",
            },
        }

        try:
            response = requests.post(
                self._generate_endpoint,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            if "response" not in data:
                raise ValueError(f"Respuesta inesperada de Ollama: {data}")

            return data["response"].strip()

        except requests.RequestException as e:
            raise requests.RequestException(f"Error al comunicarse con Ollama: {e}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"Respuesta no es JSON válido: {e}") from e

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: Optional[int] = None,
        num_ctx: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
    ) -> Dict:
        """
        Envía una conversación completa (chat history) a Ollama usando /api/chat.
        Este es el método preferido para mantener contexto conversacional.

        Args:
            messages: Lista de mensajes en formato [{"role": "user|assistant|system|tool", "content": "...", "tool_calls": [...], "tool_name": "..."}]
            model: Modelo a usar (sobrescribe el del constructor si se proporciona)
            temperature: Temperatura para el muestreo (0.0 - 1.0)
            top_p: Top-p para nucleus sampling
            max_tokens: Número máximo de tokens a generar (None = sin límite, default 2048)
            num_ctx: Tamaño de la ventana de contexto (default 4096)
            tools: Lista de definiciones de herramientas para function calling

        Returns:
            Diccionario con la respuesta completa: {"content": str, "tool_calls": List[Dict] | None}

        Raises:
            requests.RequestException: Si hay error en la petición HTTP
            ValueError: Si la respuesta no tiene el formato esperado
        """
        payload = {
            "model": model or self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_ctx": num_ctx or 4096,
                "num_predict": max_tokens or 2048,
                "keep_alive": "5m",
            },
        }

        if tools:
            payload["tools"] = tools

        try:
            response = requests.post(
                self._chat_endpoint,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            if "message" not in data:
                raise ValueError(f"Respuesta inesperada de Ollama chat: {data}")

            message = data["message"]
            content = message.get("content", "").strip()
            tool_calls = message.get("tool_calls", None)

            return {
                "content": content,
                "tool_calls": tool_calls
            }

        except requests.RequestException as e:
            raise requests.RequestException(f"Error al comunicarse con Ollama chat: {e}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"Respuesta no es JSON válido: {e}") from e

    def generate_with_context(
        self,
        prompt: str,
        context: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: Optional[int] = None,
        num_ctx: Optional[int] = None,
    ) -> str:
        """
        Envía un prompt con contexto (para RAG) a Ollama.

        Args:
            prompt: La pregunta del usuario
            context: El contexto recuperado del RAG
            model: Modelo a usar (sobrescribe el del constructor si se proporciona)
            temperature: Temperatura para el muestreo
            top_p: Top-p para nucleus sampling
            max_tokens: Número máximo de tokens a generar

        Returns:
            La respuesta generada por el modelo
        """
        full_prompt = f"""Contexto:
{context}

Pregunta: {prompt}

Responde basándote únicamente en el contexto proporcionado. Si el contexto no contiene la información necesaria, di que no tienes suficiente información."""

        return self.generate(
            prompt=full_prompt,
            model=model,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            num_ctx=num_ctx,
        )

    def check_connection(self) -> bool:
        """
        Verifica si Ollama está disponible y respondiendo.

        Returns:
            True si Ollama responde correctamente, False en caso contrario
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def list_models(self) -> list:
        """
        Lista los modelos disponibles en Ollama.

        Returns:
            Lista de nombres de modelos disponibles

        Raises:
            requests.RequestException: Si hay error en la petición
        """
        response = requests.get(f"{self.base_url}/api/tags", timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        return [model["name"] for model in data.get("models", [])]

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: Optional[int] = None,
        num_ctx: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
    ) -> Generator[Dict, None, None]:
        """
        Envía una conversación a Ollama usando /api/chat con streaming activado.
        Genera tokens progresivamente a medida que el modelo los produce.

        Args:
            messages: Lista de mensajes en formato [{"role": "user|assistant|system|tool", "content": "..."}]
            model: Modelo a usar (sobrescribe el del constructor si se proporciona)
            temperature: Temperatura para el muestreo (0.0 - 1.0)
            top_p: Top-p para nucleus sampling
            max_tokens: Número máximo de tokens a generar (None = sin límite, default 2048)
            num_ctx: Tamaño de la ventana de contexto (default 4096)
            tools: Lista de definiciones de herramientas para function calling

        Yields:
            Diccionarios con chunks de respuesta: {"content": str, "tool_calls": List[Dict] | None, "done": bool}
            - content: fragmento de texto generado (acumulativo en cada yield)
            - tool_calls: herramientas invocadas (solo en el último chunk si done=True)
            - done: True cuando la generación terminó

        Raises:
            requests.RequestException: Si hay error en la petición HTTP
            ValueError: Si la respuesta no tiene el formato esperado
        """
        payload = {
            "model": model or self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_ctx": num_ctx or 4096,
                "num_predict": max_tokens or 2048,
                "keep_alive": "5m",
            },
        }

        if tools:
            payload["tools"] = tools

        try:
            response = requests.post(
                self._chat_endpoint,
                json=payload,
                timeout=self.timeout,
                stream=True,
            )
            response.raise_for_status()

            accumulated_content = ""
            final_tool_calls = None

            for line in response.iter_lines():
                if not line:
                    continue

                try:
                    data = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    continue

                if "message" not in data:
                    continue

                message = data["message"]
                chunk_content = message.get("content", "")
                accumulated_content += chunk_content

                # Tool calls solo aparecen en el último mensaje
                if message.get("tool_calls"):
                    final_tool_calls = message["tool_calls"]

                yield {
                    "content": accumulated_content,
                    "tool_calls": final_tool_calls,
                    "done": data.get("done", False),
                }

        except requests.RequestException as e:
            raise requests.RequestException(f"Error al comunicarse con Ollama chat stream: {e}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"Respuesta no es JSON válido en streaming: {e}") from e


if __name__ == "__main__":
    # Prueba rápida del cliente
    client = OllamaClient()
    print("Verificando conexión con Ollama...")
    if client.check_connection():
        print("✓ Ollama está disponible")
        print(f"Modelos disponibles: {client.list_models()}")
        print("\nProbando generación simple...")
        try:
            response = client.generate("¿Qué es la inteligencia artificial?")
            print(f"Respuesta: {response[:200]}...")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("✗ No se puede conectar a Ollama. Asegúrate de que esté corriendo en http://localhost:11434")