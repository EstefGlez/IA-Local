# 🤖 Asistente IA Local con Monitor de Recursos

Un solo proyecto base que cubre dos entregas de clase distintas:
- **POO (Programación Orientada a Objetos):** Un asistente de dudas que corre 100% local, usando un modelo de lenguaje cuantizado (tipo Llama) y RAG (Retrieval-Augmented Generation) para responder con base en documentos reales.
- **Sistemas Operativos:** Un panel de monitoreo de recursos ("mini administrador de tareas") que mide en tiempo real cuánto CPU/RAM consume el proceso del asistente mientras responde preguntas.

## 🎯 Objetivo del Proyecto

Crear un asistente de inteligencia artificial totalmente local que:
1. Responda preguntas basándose exclusivamente en un documento de especificaciones proporcionado (no en conocimiento general del modelo)
2. Monitoree y visualize en tiempo real el consumo de recursos (CPU/RAM) del propio proceso del asistente

**Nota de integridad académica:** Ambas entregas comparten el mismo código base (el asistente es "el proceso" que el monitor vigila). Se debe confirmar con ambos profesores que reutilizar el mismo proyecto, visto desde dos ángulos distintos, es aceptable en la escuela antes de entregarlo así.

## 🔧 Stack Tecnológico

| Componente | Tecnología |
|------------|------------|
| Modelo cuantizado | Llama 3.2 (3B o 1B) vía Ollama |
| RAG / embeddings | `chromadb` + `sentence-transformers` |
| Backend del asistente | Python, estructurado en clases (POO) |
| Fuente de RAG | Doc de especificaciones de Techbox, por URL |
| Monitoreo de recursos | `psutil` |
| Procesamiento de métricas | `pandas` (siguiendo técnicas de la bóveda de Obsidian) |
| Visualización | Streamlit + `matplotlib`/`seaborn` |
| Interfaz | Streamlit (una sola app, ambas partes) |

## 📁 Estructura del Proyecto

```
AsistenteIA-Local/
├── .env                 # Variables de entorno (NO versionar)
├── .env.example         # Plantilla para variables de entorno
├── .gitignore           # Archivos excluidos de Git
├── README.md            # Este archivo
├── requirements.txt     # Dependencias de Python
├── core/
│   ├── __init__.py      # Paquete core
│   ├── document.py      # Clase Document
│   ├── retriever.py     # Clase RAGRetriever
│   ├── ollama_client.py # Clase OllamaClient (pendiente)
│   └── agent.py         # Clase ConversationalAgent (pendiente)
├── monitor/
│   └── resource_monitor.py # Clase ResourceMonitor (pendiente)
├── app.py               # Interfaz principal (Streamlit) (pendiente)
└── data/
    └── chroma/          # Base de datos vectorial ChromaDB (excluida de Git)
```

## 📋 Características Implementadas ✅

- [x] **Clase `Document`**: Carga contenido desde URL o archivo local, lo divide en chunks con traslape
- [x] **Clase `RAGRetriever`**: Usa ChromaDB como base vectorial y sentence-transformers para embeddings
- [x] **Pruebas funcionales**: Verificación de que la búsqueda encuentra información específica (ej. tiempos de envío: 24-72 horas)
- [x] **Archivos de configuración**: `.env`, `.env.example`, `.gitignore` preparados para desarrollo y GitHub

## 🚧 Próximos Steps (Según Plan de Implementación)

1. [ ] Instalar Ollama y descargar el modelo `llama3.2:3b`
2. [ ] Confirmar que Ollama responde correctamente desde la terminal
3. [ ] Implementar `OllamaClient` y probar llamadas simples
4. [ ] Implementar `ConversationalAgent` (unir RAG + modelo)
5. [ ] Construir interfaz de chat en Streamlit (Parte A funcionando)
6. [ ] Implementar `ResourceMonitor` de forma aislada
7. [ ] Conectar el monitor para que mida al asistente mientras responde
8. [ ] Procesar muestras con pandas y graficarlas con matplotlib/seaborn
9. [ ] Agregar la vista del monitor a la misma app de Streamlit

## 🛠️ Instalación y Configuración

### Prerrequisitos
- Python 3.8+
- Git (opcional, para versionado)
- Acceso a internet para descargar dependencias y modelo

### Pasos de instalación

1. **Clonar o descargar el repositorio**
   ```bash
   # Si clonas desde GitHub:
   git clone <url-del-repositorio>
   cd AsistenteIA-Local
   ```

2. **Crear entorno virtual (recomendado)**
   ```bash
   python -m venv venv
   # En Windows:
   venv\Scripts\activate
   # En macOS/Linux:
   source venv/bin/activate
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno**
   ```bash
   # Copiar la plantilla y ajustar si es necesario
   cp .env.example .env
   # Editar .env si necesitas cambiar valores por defecto
   ```

5. **Instalar Ollama y el modelo**
   ```bash
   # Instalar Ollama desde https://ollama.ai
   # Luego descargar el modelo recomendado:
   ollama pull llama3.2:3b
   # Alternativa para PCs con poca RAM:
   # ollama pull llama3.2:1b
   ```

6. **Verificar que Ollama esté funcionando**
   ```bash
   ollama run llama3.2:3b "¿Qué es la inteligencia artificial?"
   # Debería responder basado en el conocimiento general del modelo
   ```

## 🧪 Ejecución de Pruebas

Ya existe un script de prueba para verificar el funcionamiento del RAG:

```bash
python test_retriever.py
```

Este script:
1. Descarga el documento de especificaciones de Techbox desde GitHub
2. Lo procesa y lo indexa en ChromaDB
3. Realiza una búsqueda de prueba: "¿cuánto tarda el envío?"
4. Verifica que encuentre la respuesta esperada: "Entre 24 y 72 horas dentro de México"

## 📖 Uso Futuro (Una vez completada la implementación)

Una vez que se completen todos los componentes:

```bash
# Activar entorno virtual si no está activo
# venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Ejecutar la aplicación Streamlit
streamlit run app.py
```

La aplicación tendrá dos secciones/pestañas:
1. **Asistente IA**: Interfaz de chat para hacer preguntas sobre el documento de Techbox
2. **Monitor de Recursos**: Gráficas en tiempo real mostrando CPU/RAM consumidas por el proceso de Ollama/asistente

## 📚 Fuentes de Conocimiento

El asistente actualmente está configurado para usar como única fuente de conocimiento:
- [Especificaciones de Techbox](https://raw.githubusercontent.com/EstefGlez/techbox-mx/refs/heads/main/especificaciones-techbox.md)
  (documento de ejemplo para la demo - puede reemplazarse por cualquier otro documento URL)

## 💡 Ideas Futuras (Post-Entrega)

- Integrar el asistente como una cuarta opción descargable en el SDK de chatbot (`SDK-Chatbot`)
- Permitir cargar múltiples documentos de especificaciones
- Añadir soporte para diferentes modelos de Llama (3B, 1B, 7B, etc.)
- Implementar historial de conversaciones
- Exportar reportes de monitoreo de recursos
- Soporte para documentos locales además de URLs

## 👥 Contribuir

Este es un proyecto académico, pero si deseas sugerir mejoras:

1. Haz un fork del repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Haz commit de tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto se crea con fines educativos. Ver las políticas de tu institución sobre uso y distribución de código académico.

---
*Desarrollado con ❤️ usando Python, Ollama y Streamlit*
*Última actualización: Septiembre 2026*