# Spec: Fix Chronological Message Rendering Order in Streaming

## Objetivo
Corregir el orden visual de renderizado en `app.py` para que los mensajes se muestren estrictamente en orden cronológico: User → Assistant, tanto para mensajes completados como durante streaming.

## Contexto
- **Archivo**: `app.py` (líneas 524-772 aprox.)
- **Problema actual**: 
  1. El bloque de streaming (líneas 524-596) se ejecuta ANTES del bucle de renderizado de mensajes completados (líneas 598-736)
  2. Esto causa que la burbuja del asistente (streaming) aparezca VISUALMENTE ANTES que el mensaje del usuario
  3. El filtro en línea 600-602 intenta evitar duplicados pero no arregla el orden
- **Flujo correcto deseado**:
  1. Usuario envía prompt → se agrega a `messages` → `st.rerun()`
  2. Renderizado: PRIMERO todos los mensajes del historial (incluyendo el último user message)
  3. SI hay streaming activo: renderizar burbuja del asistente DEBAJO del último user message
  4. Al terminar streaming: agregar respuesta final a `messages` → `st.rerun()` → se muestra como mensaje completado normal

## Comportamiento esperado
- **RF1 - User message visible immediately**: Al enviar prompt, el mensaje del usuario aparece INMEDIATAMENTE en la UI
- **RF2 - Assistant below user**: Durante streaming, la burbuja del asistente se renderiza DEBAJO del mensaje del usuario
- **RF3 - Chronological loop**: El bucle `for msg in st.session_state.messages` dibuja estrictamente en orden cronológico
- **RF4 - Final response in history**: Al concluir streaming, la respuesta completa se agrega a `messages` y persiste
- **RF5 - No visual flicker**: Un solo rerun por ciclo, sin parpadeo ni duplicados visuales

## Restricciones
- No cambiar la lógica de `st.session_state.messages` ni `ConversationManager`
- Mantener `st.write_stream()` para streaming token-por-token
- Mantener spinners contextuales
- Verificar compilación: `python -m py_compile app.py`

## Salida esperada
- `app.py` con orden de renderizado corregido
- Verificación de compilación exitosa