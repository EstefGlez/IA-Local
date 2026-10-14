# Estado actual del proyecto

## ✅ Completado
- [x] Clase `Document` - Carga y chunking de documentos
- [x] Clase `RAGRetriever` - Embeddings con ChromaDB + sentence-transformers
- [x] Clase `OllamaClient` - Cliente HTTP para API local de Ollama (POST a /api/generate, modelo llama3.2:3b)
- [x] Clase `ConversationalAgent` - Orquesta RAG + Ollama: búsqueda → contexto → generación
- [x] Archivos de configuración: `.env`, `.env.example`, `.gitignore`, `requirements.txt`
- [x] **Refactor de memoria v1**: Trigger ligero `save_json_memory` (solo suggested_filename + tema) + función determinista `build_memory_json_from_response()` que empaqueta fielmente toda la respuesta Markdown
- [x] **Fix crítico memoria v1**: System prompt reforzado (prohíbe save_json_memory en saludos/casual) + validación de contenido sustancial en `build_memory_json_from_response()` con fallback a historial
- [x] **Refactor de memoria v2**: Desvincular totalmente del system prompt. Eliminar tool save_json_memory del agente. Guardado de memoria vía botón "💾 Guardar como Memoria" en UI (app.py) que invoca build_memory_json_from_response() determinísticamente para la respuesta seleccionada.

## 🚧 En progreso / Próximos pasos
1. Instalar Ollama y descargar modelo `llama3.2:3b`
2. Verificar que Ollama responde desde terminal
3. Construir interfaz Streamlit (app.py)
4. Implementar `ResourceMonitor` con psutil
5. Conectar monitor al asistente y visualizar con matplotlib/seaborn

## ✅ Recientemente completado (2026-10-14)
- **Refactor arquitectura agente**: Ruteador de comandos explícitos `/memory` y `/rag` en `ConversationalAgent.ask()`
- **Eliminar tool-calling automático**: Flujo determinista, sin tool calls del LLM para memoria/RAG
- **System prompt limpio**: Solo identidad + estilo, sin lógica de herramientas ni restricciones de directorios
- **RAG escalable**: Eliminado límite de 2 fuentes simultáneas en UI y backend
- **Comando /memory**: Búsqueda determinista en archivos JSON con contenido completo inyectado
- **Comando /rag**: Consulta RAG determinista con contexto inyectado
- **Spinner contextual**: UI muestra acción según comando usado

## ✅ Streaming en tiempo real (2026-10-14 - tarde)
- **OllamaClient.chat_stream()**: Streaming real token-por-token via endpoint /api/chat con stream=true
- **ConversationalAgent.ask_stream()**: Generador que mantiene ruteador comandos y yield progresivo
- **UI Streaming**: st.write_stream en burbuja assistant con respuesta incremental
- **Spinners contextuales**: '🧠 Procesando memoria...', '🔍 Consultando base RAG...', '✨ Generando respuesta...'
- **Estado sesión optimizado**: Variables streaming_* para control preciso sin re-renderizados innecesarios
- **Compatibilidad dual**: ask() legacy para tests/métricas + ask_stream() para UI

## ✅ Fix bug duplicación streaming (2026-10-14 - tarde)
- **OllamaClient.chat_stream()**: Ahora yield solo delta (chunk["message"]["content"]), no acumulado
- **ConversationalAgent.ask_stream()**: Acumula localmente para sanitización final; yield deltas progresivos
- **Eliminado overhead**: Sin sanitización en chunks parciales (solo en done=True)
- **Compilación verificada**: python -m py_compile core/ollama_client.py core/agent.py app.py ✅

## ✅ Fix orden cronológico mensajes streaming (2026-10-14 - tarde)
- **Renderizado estricto User → Assistant**: Bucle principal renderiza TODO el historial primero
- **Streaming DEBAJO**: Burbuja asistente se dibuja después del bucle principal
- **User message inmediato**: Se agrega a messages y renderiza en mismo rerun
- **Final response persistida**: Al terminar streaming, respuesta completa va a messages + rerun
- **Spinner legacy condicionado**: Solo modo ask() (no streaming)
- **Compilación verificada**: python -m py_compile app.py ✅

## ✅ Bloqueo seguridad y concurrencia (2026-10-14 - tarde)
- **Variable unificada**: `is_processing = streaming_active or processing`
- **chat_input deshabilitado**: `disabled=... or is_processing`
- **Sidebar botones deshabilitados**: Nuevo Chat, seleccionar/borrar conversación
- **Indicadores visuales**: Banner legacy "⏳ Procesando..." + sidebar caption "🔒 Interfaz bloqueada..."
- **Auto-limpieza**: Se libera automáticamente al terminar (rerun con flags reset)
- **Compilación verificada**: python -m py_compile app.py ✅

## ✅ Bloqueo global extendido a todas las pestañas (2026-10-14 - tarde)
- **Variable global única**: `is_processing` definida antes de tabs, accesible en todo app.py
- **Pestaña Config**: Sliders (temp, top-k, contexto) + botones RAG + form submit + limpiar ChromaDB
- **Pestaña Memoria**: Selectbox sesión + botones eliminar + form submit crear + eliminar todos
- **No bloqueado**: download_button (solo lectura), Monitor (solo métricas)
- **Consistencia estricta**: Una sola bandera controla toda la UI interactiva
- **Compilación verificada**: python -m py_compile app.py ✅

## ✅ Fix NameError is_processing (2026-10-14 - tarde)
- **Problema**: Variable `is_processing` definida después del sidebar (línea ~518) pero usada en sidebar (línea ~456)
- **Solución**: Movida la definición a línea 359, justo después de inicializar `st.session_state` y antes del sidebar
- **Verificación**: `python -m py_compile app.py` ✅

## Decisiones importantes
- **Vector DB**: ChromaDB (persistente en `data/chroma/`)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **Modelo LLM**: llama3.2:3b vía Ollama (fallback: llama3.2:1b si RAM limitada)
- **RAG Source**: Especificaciones Techbox desde URL GitHub raw + Obsidian (source_type)
- **Interfaz**: Streamlit (una app, dos pestañas)
- **Agent params**: top_k=3, temperature=0.3 (factual), system_instruction anti-alucinación
- **Memorias**: Guardado vía UI (botón "Guardar como Memoria"), lectura vía comando explícito `/memory <query>`
- **RAG**: Consulta vía comando explícito `/rag <query>`, sin límites de fuentes simultáneas

## Errores a evitar
- No asumir que Ollama está instalado - verificar con `check_connection()` antes de usar
- Encoding UTF-8 en Windows: usar `sys.stdout.reconfigure(encoding='utf-8')` si hay problemas
- Mostrar salida cruda de terminal en tests, no resumir
- No hacer push a main sin permiso del usuario

## Rama actual
`ia/2026-10-09-ollama-client` - Streaming en tiempo real + spinners contextuales + optimización UI completada