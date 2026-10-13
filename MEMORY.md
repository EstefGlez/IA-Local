# Estado actual del proyecto

## ✅ Completado
- [x] Clase `Document` - Carga y chunking de documentos
- [x] Clase `RAGRetriever` - Embeddings con ChromaDB + sentence-transformers
- [x] Clase `OllamaClient` - Cliente HTTP para API local de Ollama (POST a /api/generate, modelo llama3.2:3b)
- [x] Clase `ConversationalAgent` - Orquesta RAG + Ollama: búsqueda → contexto → generación
- [x] Archivos de configuración: `.env`, `.env.example`, `.gitignore`, `requirements.txt`
- [x] **Refactor de memoria**: Trigger ligero `save_json_memory` (solo suggested_filename + tema) + función determinista `build_memory_json_from_response()` que empaqueta fielmente toda la respuesta Markdown
- [x] **Fix crítico memoria**: System prompt reforzado (prohíbe save_json_memory en saludos/casual) + validación de contenido sustancial en `build_memory_json_from_response()` con fallback a historial

## 🚧 En progreso / Próximos pasos
1. Instalar Ollama y descargar modelo `llama3.2:3b`
2. Verificar que Ollama responde desde terminal
3. Construir interfaz Streamlit (app.py)
4. Implementar `ResourceMonitor` con psutil
5. Conectar monitor al asistente y visualizar con matplotlib/seaborn

## Decisiones importantes
- **Vector DB**: ChromaDB (persistente en `data/chroma/`)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **Modelo LLM**: llama3.2:3b vía Ollama (fallback: llama3.2:1b si RAM limitada)
- **RAG Source**: Especificaciones Techbox desde URL GitHub raw + Obsidian (source_type)
- **Interfaz**: Streamlit (una app, dos pestañas)
- **Agent params**: top_k=3, temperature=0.3 (factual), system_instruction anti-alucinación

## Errores a evitar
- No asumir que Ollama está instalado - verificar con `check_connection()` antes de usar
- Encoding UTF-8 en Windows: usar `sys.stdout.reconfigure(encoding='utf-8')` si hay problemas
- Mostrar salida cruda de terminal en tests, no resumir
- No hacer push a main sin permiso del usuario

## Rama actual
`ia/2026-10-09-ollama-client` - Implementación de OllamaClient + ConversationalAgent completada