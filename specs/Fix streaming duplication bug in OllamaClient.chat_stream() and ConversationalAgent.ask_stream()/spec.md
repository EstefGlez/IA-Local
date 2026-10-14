# Spec: Fix Streaming Duplication Bug

## Objetivo
Corregir el bug de duplicación acumulativa en el streaming de respuestas de Ollama, de modo que cada `yield` devuelva únicamente el delta/fragmento actual (`chunk["message"]["content"]`) en lugar de la respuesta completa acumulada hasta ese momento.

## Contexto
- **Archivos afectados**: `core/ollama_client.py` (método `chat_stream`) y `core/agent.py` (método `ask_stream`)
- **Problema actual**: En `OllamaClient.chat_stream()` (líneas 293-320), se acumula `accumulated_content += chunk_content` y se hace `yield {"content": accumulated_content, ...}`. Esto causa que cada chunk enviado al frontend contenga todo el texto previo más el nuevo fragmento, resultando en duplicación visual exponencial.
- **Impacto en `ask_stream`**: El método `ConversationalAgent.ask_stream()` consume este generador y aplica `sanitize_model_response()` sobre el contenido ya acumulado, propagando y empeorando el bug.

## Comportamiento esperado
- `OllamaClient.chat_stream()` debe hacer `yield` de **solo el delta** del chunk actual: `chunk["message"]["content"]` (sin acumular).
- El campo `done` en el yield indica cuándo termina la generación.
- `ConversationalAgent.ask_stream()` debe acumular los deltas localmente si necesita la respuesta completa para sanitización final, pero debe hacer `yield` de los deltas progresivos al frontend.

## Restricciones
- No cambiar la firma pública de `chat_stream()` ni `ask_stream()`.
- Mantener compatibilidad con el campo `tool_calls` (que solo aparece en el último chunk cuando `done=True`).
- El campo `done: bool` debe seguir indicando correctamente el final del stream.
- Verificar compilación con: `python -m py_compile core/ollama_client.py core/agent.py app.py`

## Criterios de aceptación
1. **RF1 - Delta-only streaming**: Cada `yield` de `chat_stream()` contiene solo `chunk["message"]["content"]` (el fragmento nuevo), no el texto acumulado.
2. **RF2 - Correct done flag**: El campo `done` es `True` solo en el último chunk.
3. **RF3 - Tool calls preserved**: `tool_calls` se incluye solo en el último chunk (cuando `done=True`).
3. **RF4 - ask_stream yields deltas**: `ask_stream()` hace `yield` de deltas progresivos al frontend, no de respuestas acumuladas.
4. **RF5 - Final sanitization works**: La sanitización final en `ask_stream()` (cuando `done=True`) recibe la respuesta completa acumulada localmente.
5. **RF6 - Compilation passes**: `python -m py_compile core/ollama_client.py core/agent.py app.py` ejecuta sin errores.

## Salida esperada
- `core/ollama_client.py`: `chat_stream()` corregido
- `core/agent.py`: `ask_stream()` corregido para acumular localmente y yield deltas
- Verificación de compilación exitosa