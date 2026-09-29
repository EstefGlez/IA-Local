# Contexto del Proyecto: Asistente IA Local con Monitor de Recursos

## Objetivo

Un solo proyecto base que cubre dos entregas de clase distintas:

- **POO (Programación Orientada a Objetos):** un asistente de dudas que corre
  100% local, usando un modelo de lenguaje cuantizado (tipo Llama) y RAG
  (Retrieval-Augmented Generation) para responder con base en documentos
  reales — no en el conocimiento general del modelo.
- **Sistemas Operativos:** un panel de monitoreo de recursos ("mini
  administrador de tareas") que mide en tiempo real cuánto CPU/RAM consume
  el proceso del asistente mientras responde preguntas.

**Nota de integridad académica:** ambas entregas comparten el mismo código
base (el asistente es "el proceso" que el monitor vigila). Confirmar con
ambos profesores que reutilizar el mismo proyecto, visto desde dos ángulos
distintos, es aceptable en la escuela antes de entregarlo así.

**Nota aparte, no parte de la entrega escolar:** más adelante, este asistente
podría integrarse como una cuarta opción descargable en el SDK de chatbot
(`SDK-Chatbot`), para clientes que prefieran correr su propio modelo en vez
de usar los proveedores en la nube. No implementar esto todavía — es una
idea para después de que ambas entregas de clase estén terminadas y
calificadas.

## Parte A: Asistente local con RAG (para POO)

### Modelo de IA

- Corre vía **Ollama** (herramienta gratuita para servir modelos cuantizados
  localmente — no está instalada todavía en esta PC, es el primer paso).
- Modelo recomendado para empezar: **`llama3.2:3b`** — balance razonable
  entre calidad y consumo de RAM para una PC con 8GB de RAM total. Si la PC
  se siente muy lenta o se queda sin memoria al correrlo, cambiar a
  **`llama3.2:1b`** (más chico, más rápido, algo menos preciso).

### Fuente de RAG

**Documento de especificaciones de Techbox** (tu ecommerce) — accedido por
URL, igual que el patrón que ya usas en otro proyecto. Es la única fuente
de conocimiento del asistente: permite personalizarlo "por negocio, por
página web" — el mismo patrón que ya usa el SDK-Chatbot, solo que aquí el
modelo corre local en vez de en la nube.

**Nota importante:** la bóveda de Obsidian NO es fuente de RAG para este
asistente — su rol es distinto, ver la sección de Parte B más abajo.

### Estructura orientada a objetos (para la entrega de POO)

- **`Document`** — representa un documento fuente: de dónde vino (URL o
  ruta local), su contenido crudo, y sus fragmentos ("chunks") ya
  divididos para procesar.
- **`RAGRetriever`** — genera embeddings de los documentos, los guarda en
  un índice vectorial local (ej. `chromadb` o `faiss`), y dado un query,
  regresa los fragmentos más relevantes.
- **`OllamaClient`** — envuelve las llamadas HTTP a la API local de Ollama
  (que corre en `http://localhost:11434` por defecto), para mandar
  preguntas y recibir respuestas del modelo cuantizado.
- **`ConversationalAgent`** — la clase orquestadora: recibe una pregunta,
  usa `RAGRetriever` para traer contexto relevante, arma el prompt
  (contexto + pregunta), se lo manda a `OllamaClient`, y regresa la
  respuesta.

### Interfaz

Versión mínima en **Streamlit** (nada de línea de comandos), reutilizando
el patrón ya conocido de `app.py` del SDK-Chatbot. Básica por ahora —
funcional para la demo en clase, pulirla visualmente puede esperar.

## Parte B: Monitor de recursos (para Sistemas Operativos)

### Qué mide

- **`ResourceMonitor`** — clase que usa `psutil` para tomar muestras
  periódicas (ej. cada 0.5 segundos) del proceso donde corre Ollama/el
  asistente: porcentaje de CPU, uso de RAM en MB, mientras responde una
  pregunta.
- Guarda las muestras en una lista/estructura simple mientras dura la
  respuesta, desde que se manda la pregunta hasta que llega la respuesta
  completa.

### Procesamiento de los datos: aplicando técnicas de tu bóveda de Obsidian

Las muestras crudas de `psutil` (timestamp, % CPU, RAM en MB) se convierten
en un DataFrame de pandas, y se procesan siguiendo las mismas técnicas
documentadas en tu bóveda de análisis de datos (ver `Groupby_Agg_Transform`,
`Visualizacion`, `Analisis_Estadistico` en tu índice maestro):

- Agregaciones simples sobre las muestras (promedio, máximo, desviación
  estándar de CPU/RAM durante una respuesta).
- Suavizado con media móvil (`rolling`) para que la gráfica no se vea
  ruidosa muestra a muestra.
- Visualización con `matplotlib`/`seaborn`, siguiendo el mismo estilo que
  ya usas en tus proyectos del bootcamp (código modular, bien etiquetado).

**Idea extra, opcional:** el bloque de "Prompt de Contexto para IAs" que
tienes en tu índice maestro (el que describe tu stack y estándar de
trabajo) se le puede dar directamente a Claude Code como contexto adicional
al pedirle que escriba el código de esta parte — así el código generado
sigue tus propias convenciones (snake_case, celdas modulares, etc.) en vez
de un estilo genérico.

### Interfaz visual

Misma app de Streamlit que la Parte A (puede ser una segunda pestaña/vista
dentro del mismo `app.py`, para poder mostrar ambas partes juntas en la
demo), con las gráficas de `matplotlib`/`seaborn` embebidas.

### Cómo se conecta con la Parte A

El monitor corre en paralelo mientras el `ConversationalAgent` procesa una
pregunta — es decir, "vigila" el mismo proceso que la Parte A pone a
trabajar. Técnicamente esto puede requerir correr el monitoreo en un hilo
(`threading`) separado del hilo principal que espera la respuesta del
modelo, para poder tomar muestras mientras el modelo "piensa".

## Stack tecnológico (resumen)

| Pieza | Tecnología |
|---|---|
| Modelo cuantizado | Llama 3.2 (3B o 1B) vía Ollama |
| RAG / embeddings | `chromadb` |
| Backend del asistente | Python, estructurado en clases (POO) |
| Fuente de RAG | Doc de especificaciones de Techbox, por URL |
| Monitoreo de recursos | `psutil` |
| Procesamiento de métricas | `pandas`, siguiendo técnicas de la bóveda de Obsidian |
| Visualización | Streamlit + `matplotlib`/`seaborn` |
| Interfaz | Streamlit (una sola app, ambas partes) |

## Estructura de carpetas propuesta

```
AsistenteIA-Local/
├── contexto.md
├── requirements.txt
├── core/
│   ├── document.py          # clase Document
│   ├── retriever.py         # clase RAGRetriever
│   ├── ollama_client.py     # clase OllamaClient
│   └── agent.py             # clase ConversationalAgent
├── monitor/
│   └── resource_monitor.py  # clase ResourceMonitor
├── app.py                   # interfaz (Streamlit o consola)
└── data/
    └── (documentos indexados, si se guardan localmente)
```

## Plan de implementación (en orden)

- [ ] Instalar Ollama y descargar el modelo `llama3.2:3b`.
- [ ] Confirmar que Ollama responde correctamente desde la terminal
      (`ollama run llama3.2:3b`) antes de escribir código.
- [ ] Implementar `Document` y `RAGRetriever` con el doc de Techbox,
      confirmar que la búsqueda por similitud regresa fragmentos con
      sentido.
- [ ] Implementar `OllamaClient`, probar una llamada simple sin RAG todavía.
- [ ] Implementar `ConversationalAgent`, uniendo RAG + modelo, probar con
      preguntas reales sobre Techbox.
- [ ] Construir la interfaz de chat en Streamlit (Parte A funcionando de
      punta a punta).
- [ ] Implementar `ResourceMonitor` de forma aislada, probarlo midiendo
      cualquier proceso simple antes de conectarlo al asistente.
- [ ] Conectar el monitor para que mida al asistente mientras responde.
- [ ] Procesar las muestras con pandas (agregaciones, media móvil) y
      graficarlas con matplotlib/seaborn, siguiendo el estilo de la
      bóveda de Obsidian.
- [ ] Agregar la vista del monitor a la misma app de Streamlit (ambas
      partes visibles en un solo lugar para la demo).

## Notas para Claude Code

- Este proyecto usa Nemotron/DeepSeek vía NVIDIA NIM como modelo de
  asistencia de código (a través del proxy Free Claude Code), no el modelo
  real de Anthropic — verificar comandos reales con `/help` si algo no
  cuadra.
- Avanzar en el orden del "Plan de implementación" de arriba, un punto a
  la vez, probando cada pieza de forma aislada antes de conectarla con la
  siguiente.
- Cuando falte una decisión (ej. `chromadb` vs `faiss`, o Streamlit vs
  Tkinter para el monitor), preguntar en vez de asumir.
