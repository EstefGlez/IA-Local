# 🤖 IA-Local: Asistente RAG Local + Monitor de Recursos + Gestión de Modelos

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.38+-FF4B4B.svg)](https://streamlit.io)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-000000.svg)](https://ollama.ai)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20DB-8A2BE2.svg)](https://www.trychroma.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-MVP%20Release-brightgreen.svg)](#)

---

## 🎯 Descripción General

**IA-Local** es un asistente de inteligencia artificial **100% local** que combina:

- 🧠 **RAG (Retrieval-Augmented Generation)** — Responde preguntas basándose **exclusivamente** en tus documentos (no en conocimiento general del modelo)
- 💬 **Chat con streaming token-por-token** — Respuestas en tiempo real vía Ollama (`/api/chat` con `stream=true`)
- 🧠 **Memoria persistente** — Guarda y recupera conocimiento entre sesiones (archivos JSON por conversación)
- 🔍 **Búsqueda en historial** — Busca en conversaciones pasadas e inyecta contexto al chat actual
- ⚙️ **Gestión dinámica de modelos Ollama** — Lista, selecciona y descarga modelos (`llama3.2`, `mistral`, `gemma`, etc.) con progreso en vivo
- 📊 **Monitor de recursos en tiempo real** — Mide CPU/RAM del proceso asistente con `psutil` + gráficas `matplotlib`/`seaborn`

> **Una sola app Streamlit, 6 pestañas funcionales, cero dependencias en la nube.**

---

## 🔧 Stack Tecnológico

| Componente | Tecnología | Versión |
|------------|------------|---------|
| **Modelo LLM** | Llama 3.2 (3B/1B), Mistral, Gemma, etc. vía **Ollama** | Latest |
| **RAG / Embeddings** | `chromadb` + `sentence-transformers` (all-MiniLM-L6-v2) | 0.4.x / 2.2.x |
| **Backend Asistente** | Python, arquitectura POO (clases desacopladas) | 3.10+ |
| **Fuente RAG** | Documentos locales / URLs (GitHub raw, Obsidian, PDFs, etc.) | — |
| **Memoria** | Archivos JSON por sesión + índice en ChromaDB opcional | — |
| **Monitoreo Recursos** | `psutil` (muestreo 0.5s) + `pandas` (agregaciones/rolling) | 5.9.x / 2.1.x |
| **Visualización** | Streamlit + `matplotlib`/`seaborn` | 1.38+ / 3.8+ |
| **Interfaz** | Streamlit (single-page app, 6 tabs) | 1.38+ |
| **Limpieza Texto** | `core.utils.text_cleaner` (HTML, entidades, normalización) | Custom |

---

## 📁 Estructura del Proyecto

```
IA-Local/
├── .env                    # Variables de entorno (NO versionar)
├── .env.example            # Plantilla para variables de entorno
├── .gitignore              # Archivos excluidos de Git
├── README.md               # Este archivo
├── requirements.txt        # Dependencias de Python
├── app.py                  # Interfaz principal Streamlit (6 tabs)
├── core/
│   ├── __init__.py         # Paquete core
│   ├── document.py         # Clase Document (carga, chunking, metadatos)
│   ├── retriever.py        # Clase RAGRetriever (ChromaDB + embeddings)
│   ├── ollama_client.py    # Clase OllamaClient (chat, stream, pull, tags)
│   ├── agent.py            # Clase ConversationalAgent (orquesta RAG + LLM + memoria)
│   ├── conversation_manager.py # Gestión de sesiones/historial de chat
│   ├── rag_source_manager.py   # Gestión de fuentes RAG (URL, local, Obsidian)
│   └── utils/
│       ├── monitor.py      # ResourceMonitor (psutil sampling + pandas)
│       └── text_cleaner.py # Limpieza HTML, entidades, normalización
├── data/
│   ├── chroma/             # Base vectorial ChromaDB (persistente, gitignored)
│   ├── archivos_memoria/   # Memorias JSON por sesión (gitignored)
│   └── conversations/      # Historial de chats por sesión (gitignored)
├── specs/                  # Especificaciones técnicas por feature (SDD)
└── tests/                  # (pendiente) Tests unitarios e integración
```

---

## ✨ Características del MVP Release

### 1. 💬 **Chat con Streaming en Tiempo Real**
- **Endpoint**: `OllamaClient.chat_stream()` → `POST /api/chat` con `stream=true`
- **UI**: `st.write_stream` renderiza token-por-token en burbuja assistant
- **Spinners contextuales**: `🧠 Procesando memoria...` | `🔍 Consultando base RAG...` | `✨ Generando respuesta...`
- **Compatibilidad dual**: `ask()` legacy (tests/métricas) + `ask_stream()` (UI)

### 2. 🧠 **Memoria Persistente por Conversación**
- **Guardado**: Botón `💾 Guardar como Memoria` en cada respuesta del asistente
- **Formato**: JSON estructurado (`metadata` + `content`) en `data/archivos_memoria/{session_id}/`
- **Recuperación**: Comando explícito `/memory <query>` — búsqueda determinista en archivos JSON
- **Inyección**: Contenido completo inyectado como contexto en el prompt
- **Purga granular**: Botón `🗑️ Purgar memorias de conversación ACTUAL` (solo sesión activa)

### 3. 🔍 **RAG Determinista con Comandos Explícitos**
- **Comando**: `/rag <query>` — búsqueda semántica en ChromaDB
- **Sin tool-calling automático**: Flujo 100% determinista, controlado por el usuario
- **Fuentes escalables**: Sin límite de fuentes simultáneas (antes: máx. 2)
- **Gestión de fuentes**: Pestaña Config → agregar/eliminar/reindexar fuentes (URL, local, Obsidian)

### 4. 🔍 **Búsqueda en Historial + Contexto Pendiente**
- **Pestaña dedicada**: `🔍 Buscar en Historial` (5ª pestaña)
- **Filtrado**: Case-insensitive sobre `st.session_state.messages`
- **Resultados**: Expandibles con preview 100 chars + contenido completo
- **Acción**: `📌 Usar este mensaje como contexto` → guarda en `pending_context`
- **Flujo**: Buscar → Seleccionar contexto → Ir a Chat → Ver banner "📌 Contexto de Búsqueda Seleccionado" → Enviar prompt (contexto + prompt van juntos)

### 5. ⚙️ **Gestión Dinámica de Modelos Ollama** *(Nueva pestaña 6ª)*
- **Conexión**: Badge de estado + `GET /api/tags` para listar modelos instalados
- **Modelo Activo**: Selectbox que muta `ollama_client.model` y persiste en `session_state['current_model']`
- **Descarga interactiva**: `st.text_input` + botón `Descargar Modelo` → `POST /api/pull` con `st.status` mostrando:
  - Estado: `downloading` / `verifying` / `success`
  - Progreso: `% completado` + `bytes descargados / total`
- **Manejo de errores**: `requests.RequestException` capturado y mostrado en UI

### 6. 📊 **Monitor de Recursos en Tiempo Real**
- **ResourceMonitor**: Clase en `core.utils.monitor` usando `psutil.Process()`
- **Muestreo**: Cada 0.5s (configurable via `MONITOR_INTERVAL`) durante la generación
- **Métricas**: % CPU, RAM (MB), timestamps
- **Procesamiento**: `pandas.DataFrame` → agregaciones (mean, max, std) + `rolling()` suavizado
- **Visualización**: Gráficas `matplotlib`/`seaborn` embebidas en Streamlit (pestaña Monitor)

---

## 📋 Pestañas de la Interfaz (6 Tabs)

| # | Pestaña | Icono | Funcionalidad Principal |
|---|---------|-------|------------------------|
| 1 | **Chat** | 💬 | Chat principal con streaming, memoria, RAG, búsqueda |
| 2 | **Monitor** | 📊 | Gráficas CPU/RAM en tiempo real del proceso asistente |
| 3 | **Config** | ⚙️ | Parámetros (temp, top-k, contexto), fuentes RAG, limpiar ChromaDB |
| 4 | **Memoria** | 🧠 | Ver/eliminar memorias por sesión, purge actual, crear manual |
| 5 | **Buscar** | 🔍 | Búsqueda en historial + selección de contexto pendiente |
| 6 | **Modelos** | ⚙️ | Estado Ollama, modelo activo, descarga de modelos con progreso |

> **Seguridad**: Todas las pestañas respetan `is_processing` — botones/inputs deshabilitados mientras el asistente genera respuesta.

---

## 🛠️ Instalación y Configuración

### Prerrequisitos
- **Python 3.10+**
- **Git** (opcional, para versionado)
- **Ollama instalado y corriendo** — [Descargar desde ollama.ai](https://ollama.ai)
- Acceso a internet para descargar dependencias y modelos

### Pasos de instalación

```bash
# 1. Clonar repositorio
git clone https://github.com/EstefGlez/IA-Local.git
cd IA-Local

# 2. Crear entorno virtual
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno (VER SECCIÓN SEGURIDAD ABAJO)
cp .env.example .env
# Editar .env si necesitas cambiar valores por defecto

# 5. Instalar y verificar Ollama
ollama pull llama3.2:3b          # Modelo recomendado (3B params)
# ollama pull llama3.2:1b        # Alternativa para RAM limitada
ollama run llama3.2:3b "test"    # Verificar que responde

# 6. Ejecutar la aplicación
streamlit run app.py
```

> ⚠️ **IMPORTANTE**: Ollama debe estar **corriendo en background** (`ollama serve` o simplemente haber ejecutado `ollama run` una vez) antes de lanzar `streamlit run app.py`. La app se conecta a `http://localhost:11434` por defecto.

---

## 🔐 Seguridad y Configuración de Entorno

### Archivo `.env` (NO versionar — está en `.gitignore`)

```bash
# Copiar plantilla y personalizar
cp .env.example .env
```

### Variables de entorno disponibles

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `OLLAMA_HOST` | URL del servidor Ollama | `http://localhost:11434` |
| `OLLAMA_MODEL` | Modelo activo por defecto | `llama3.2:3b` |
| `EMBEDDING_MODEL` | Modelo de embeddings (sentence-transformers) | `all-MiniLM-L6-v2` |
| `CHROMA_PATH` | Ruta persistente ChromaDB | `./data/chroma` |
| `COLLECTION_NAME` | Nombre colección vectorial | `documents` |
| `STREAMLIT_SERVER_PORT` | Puerto Streamlit | `8501` |
| `STREAMLIT_SERVER_ADDRESS` | Bind address Streamlit | `localhost` |
| `STREAMLIT_SERVER_HEADLESS` | Modo headless | `true` |
| `CHUNK_SIZE` | Tamaño de chunks para RAG | `500` |
| `CHUNK_OVERLAP` | Traslape entre chunks | `50` |
| `TOP_K_RESULTS` | Resultados top-k en búsqueda RAG | `3` |
| `MONITOR_INTERVAL` | Intervalo muestreo recursos (seg) | `0.5` |
| `MAX_SAMPLES` | Máximo muestras en memoria | `1000` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |

> ✅ **Buena práctica**: Nunca commitees `.env`. Usa `.env.example` como plantilla compartida. Cada desarrollador/entorno crea su propio `.env` local.

---

## 🧪 Comandos de Chat Disponibles

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `/memory <query>` | Busca en memorias guardadas e inyecta contexto | `/memory envíos internacionales` |
| `/rag <query>` | Consulta RAG sobre documentos indexados | `/rag políticas de devolución` |
| *(texto libre)* | Chat normal con streaming (usa RAG automático si hay fuentes) | `¿Cuánto tarda el envío?` |

> **Nota**: El RAG automático se activa solo si hay fuentes indexadas. Los comandos `/memory` y `/rag` son **explícitos y deterministas** — el usuario decide cuándo usar cada fuente.

---

## 🏗️ Arquitectura - Flujo de Datos

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Usuario       │────▶│  Conversational  │────▶│  OllamaClient   │
│   (Streamlit)   │     │  Agent           │     │  (HTTP → Ollama)│
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
       ┌─────────────┐   ┌──────────────┐   ┌──────────────┐
       │ RAGRetriever│   │   Memoria    │   │  Contexto    │
       │ (ChromaDB)  │   │  (JSON files)│   │  Pendiente   │
       └─────────────┘   └──────────────┘   └──────────────┘
              │
              ▼
       ┌─────────────┐
       │ Document    │
       │ (chunks)    │
       └─────────────┘
```

**Monitor paralelo**: `ResourceMonitor` (thread) muestrea `psutil` del proceso Ollama mientras `ConversationalAgent` genera respuesta.

---

## 📖 Uso Rápido

```bash
# Activar entorno
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# Lanzar app
streamlit run app.py

# Abrir en navegador: http://localhost:8501
```

### Flujo típico de trabajo:
1. **Pestaña Modelos** → Verificar conexión Ollama, seleccionar/descargar modelo
2. **Pestaña Config** → Agregar fuentes RAG (URL Techbox, Obsidian, PDFs) → Reindexar
3. **Pestaña Chat** → Preguntar sobre documentos → Usar `/memory` o `/rag` para control explícito
4. **Pestaña Buscar** → Buscar en historial → Seleccionar contexto → Volver a Chat → Enviar
5. **Pestaña Memoria** → Guardar respuestas clave → Consultar después con `/memory`
6. **Pestaña Monitor** → Ver consumo CPU/RAM de la última respuesta

---

## 🚀 Roadmap Post-MVP

- [ ] Tests unitarios e integración (`pytest` + `pytest-asyncio`)
- [ ] Exportar reportes de monitor (CSV, PNG, PDF)
- [ ] Soporte multi-documento con namespaces en ChromaDB
- [ ] Autenticación simple (para despliegue compartido)
- [ ] Dockerfile + docker-compose para despliegue reproducible
- [ ] Integración como plugin en `SDK-Chatbot` (opción 4: modelo local)
- [ ] API REST opcional (FastAPI) para consumo externo
- [ ] Métricas de calidad RAG (precision@k, recall@k, MRR)

---

## 🤝 Contribuir

1. Fork del repositorio
2. Crear rama: `git checkout -b feature/NuevaFeature`
3. Commit: `git commit -m 'feat: descripción breve'`
4. Push: `git push origin feature/NuevaFeature`
5. Abrir Pull Request

---

## 📝 Licencia

MIT License — Uso educativo y comercial permitido. Ver `LICENSE` para detalles.

---

## 🙏 Créditos

- **Ollama** — Servir modelos locales de forma simple
- **ChromaDB** — Base vectorial embebida
- **sentence-transformers** — Embeddings de calidad
- **Streamlit** — UI rápida y bonita
- **psutil / pandas / matplotlib / seaborn** — Observabilidad y datos

---

*Desarrollado con ❤️ para las entregas de POO + Sistemas Operativos — 2026*