# Spec: Safety Lock and Concurrency Control in app.py

## Objetivo
Implementar bloqueo de seguridad y control de concurrencia durante la generación/streaming del agente para prevenir acciones concurrentes del usuario que podrían corromper el estado.

## Contexto
- **Archivo**: `app.py`
- **Estados activos**: `streaming_active` (streaming token-por-token) y `processing` (modo legacy ask())
- **Riesgo actual**: Usuario puede enviar nuevo prompt, crear nuevo chat, cambiar/borrar conversación mientras el modelo está generando

## Comportamiento esperado
- **RF1 - Chat input bloqueado**: `st.chat_input` deshabilitado durante `streaming_active` o `processing`
- **RF2 - Sidebar bloqueado**: Botones "Nuevo Chat", selección de conversación, eliminación deshabilitados durante estados activos
- **RF3 - Indicador visual**: Banner/estado claro mostrando "Procesando..." o "Generando respuesta..." cuando bloqueado
- **RF4 - Sin estado opaco**: UI nunca se queda en estado indefinido; bloqueo se libera automáticamente al terminar
- **RF5 - Compilación**: `python -m py_compile app.py` sin errores

## Restricciones
- Streamlit `st.chat_input` soporta parámetro `disabled` (bool)
- `st.button` soporta parámetro `disabled` (bool)
- No usar `st.stop()` ni fragmentar el flujo; mantener single-rerun pattern
- Mantener compatibilidad con modo legacy (`processing`) y streaming (`streaming_active`)

## Salida esperada
- `app.py` con lógica de bloqueo centralizada y aplicada a inputs/botones críticos
- Verificación de compilación exitosa