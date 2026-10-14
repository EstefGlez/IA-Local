# Plan: Fix Streaming Duplication Bug

## Archivos y responsabilidades

| Archivo | Responsabilidad |
|---------|-----------------|
| `core/ollama_client.py` | `OllamaClient.chat_stream()` - Generador de streaming puro (delta-only) |
| `core/agent.py` | `ConversationalAgent.ask_stream()` - Consumidor que acumula localmente y yield deltas |

## Funciones puras / Algoritmo

### `OllamaClient.chat_stream()` - Algoritmo corregido
```python
def chat_stream(...):
    # 1. Preparar payload y hacer request streaming
    # 2. Para cada línea del response:
    #    a. Parsear JSON
    #    b. Extraer chunk_content = message.get("content", "")  # SOLO el delta
    #    c. Extraer tool_calls si existen (solo en último mensaje)
    #    d. done = data.get("done", False)
    #    e. yield {"content": chunk_content, "tool_calls": tool_calls_if_done, "done": done}
    #    f. NO acumular content en variable externa
```

### `ConversationalAgent.ask_stream()` - Algoritmo corregido
```python
def ask_stream(...):
    # 1. Procesar comandos /memory, /rag (igual que antes)
    # 2. Construir messages
    # 3. Llamar a ollama_client.chat_stream()
    # 4. Acumular localmente: local_accumulated += chunk["content"]
    # 5. Para cada chunk del stream:
    #    a. Si NOT done: yield (chunk["content"], partial_metrics)  # DELTA al frontend
    #    b. Si done:
    #       - Sanitizar local_accumulated (respuesta completa)
    #       - yield (sanitized_final_response, final_metrics)  # RESPUESTA COMPLETA FINAL
```

## Decisiones con alternativa descartada

| Decisión | Alternativa descartada | Justificación |
|----------|------------------------|---------------|
| `chat_stream` yield solo delta | Yield acumulado + flag `is_delta` | Más simple, semántica clara: cada yield = un fragmento atómico |
| `ask_stream` acumula localmente | `ask_stream` no acumula, pide respuesta completa al final | Acumular localmente evita petición extra y permite sanitización correcta |
| Mantener firma `yield (str, dict)` | Cambiar a `yield (delta, metrics, is_final)` | Compatibilidad hacia atrás; `done` en metrics indica final |

## Estrategia de tests

| Test | Qué verifica |
|------|--------------|
| Unit: `chat_stream` yields deltas | Mock `requests.post` stream; verificar que cada yield tiene `content` = solo chunk actual |
| Unit: `chat_stream` done flag | Verificar `done=True` solo en último yield |
| Unit: `chat_stream` tool_calls | Verificar `tool_calls` solo presente cuando `done=True` |
| Integration: `ask_stream` yields deltas | Mock `ollama_client.chat_stream`; verificar yields progresivos son deltas |
| Integration: `ask_stream` final sanitization | Verificar que yield final tiene respuesta sanitizada completa |
| Smoke: Compilation | `python -m py_compile core/ollama_client.py core/agent.py app.py` |

## RF coverage

| RF | Cobertura | Estado |
|----|-----------|--------|
| RF1 (delta-only) | `chat_stream` yield logic + unit test | ✅ Implementado |
| RF2 (done flag) | `chat_stream` done logic + unit test | ✅ Implementado |
| RF3 (tool_calls) | `chat_stream` tool_calls logic + unit test | ✅ Implementado |
| RF4 (ask_stream deltas) | `ask_stream` yield logic + integration test | ✅ Implementado |
| RF5 (final sanitization) | `ask_stream` done branch + integration test | ✅ Implementado |
| RF6 (compilation) | Smoke test al final | ✅ Verificado |

## Resumen de cambios realizados

### `core/ollama_client.py` (líneas 293-316)
- Eliminada variable `accumulated_content` y `final_tool_calls`
- Ahora hace `yield` de `chunk_content` directamente (delta puro)
- `tool_calls` solo se incluye cuando `done=True`
- Actualizada docstring: "DELTA únicamente, no acumulativo"

### `core/agent.py` (líneas 1118-1234)
- Añadida variable local `accumulated_content = ""` para acumular deltas
- En cada iteración: `accumulated_content += chunk_content`
- Para chunks parciales (`done=False`): `yield (chunk_content, partial_metrics)` — solo delta
- Para chunk final (`done=True`): sanitiza `accumulated_content` y `yield (final_response, final_metrics)`
- Eliminada sanitización innecesaria en chunks parciales (overhead evitado)
- Ambos bloques (MONITOR_AVAILABLE y else) actualizados idénticamente