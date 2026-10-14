# Spec: Extend Safety Lock to All Controls and Tabs

## Objetivo
Extender el bloqueo `is_processing` a todos los controles interactivos de todas las pestañas para garantizar consistencia total durante generación/streaming.

## Contexto
- **Archivo**: `app.py`
- **Variable existente**: `is_processing = streaming_active or processing` (definida en sidebar y tab_chat)
- **Controles objetivo**:
  - Pestaña Configuración: sliders (temperatura, top-k, contexto), botones RAG, formulario añadir fuente, botón limpiar ChromaDB
  - Pestaña Memoria: selectbox sesión, botones eliminar archivo, formulario crear memoria, botón eliminar todos
  - Pestaña Monitor: (solo lectura, sin controles críticos)

## Comportamiento esperado
- **RF1 - Config sliders bloqueados**: temperatura, top-k, context_scale con `disabled=is_processing`
- **RF2 - Config botones RAG bloqueados**: Re-indexar, Eliminar fuente, Añadir fuente (submit), Limpiar ChromaDB
- **RF3 - Memoria controles bloqueados**: selectbox sesión, botones eliminar, formulario crear (submit), eliminar todos
- **RF4 - Consistencia global**: `is_processing` definida una vez y accesible en todas las pestañas
- **RF5 - Compilación**: `python -m py_compile app.py` OK

## Restricciones
- `st.slider`, `st.selectbox`, `st.button`, `st.form_submit_button` soportan `disabled`
- `st.download_button` NO soporta `disabled` (solo lectura, no crítico)
- Definir `is_processing` en scope accesible a todas las pestañas (antes de tabs)
- No bloquear pestaña Monitor (solo métricas de lectura)

## Salida esperada
- `app.py` con bloqueo extendido a todas las pestañas interactivas
- Verificación de compilación