# Plan: Fix Chronological Message Rendering Order

## Archivos y responsabilidades

| Archivo | Responsabilidad |
|---------|-----------------|
| `app.py` | Reordenar bloques de renderizado en pestaña Chat (líneas ~524-772) |

## Algoritmo / Cambio de estructura

### Orden actual (INCORRECTO):
```
1. if streaming_active: render assistant streaming bubble
2. for msg in messages_to_show: render completed messages
3. if processing: render "thinking" spinner
4. chat_input
```

### Orden corregido:
```
1. for msg in st.session_state.messages: render ALL completed messages chronologically
   (incluye el último user message recién agregado)
2. if streaming_active: render assistant streaming bubble BELOW
3. if processing AND NOT streaming_active: render "thinking" spinner
4. chat_input
```

### Cambios específicos en `app.py`:

**Paso 1**: Mover el bloque de streaming (líneas 524-596) para que esté DESPUÉS del bucle de renderizado de mensajes (líneas 598-736).

**Paso 2**: Eliminar el filtro `messages_to_show` (líneas 599-602) que ocultaba el último user message. Ahora TODOS los mensajes se renderizan en el bucle principal.

**Paso 3**: Ajustar la lógica del generador `response_generator()` para que al terminar:
- Agregue la respuesta a `st.session_state.messages`
- Desactive `streaming_active`
- Haga `st.rerun()` para que el mensaje aparezca en el bucle principal la próxima vez

**Paso 4**: El spinner "Pensando..." (líneas 737-749) solo debe mostrarse si `processing=True` Y `streaming_active=False` (es decir, en modo legacy/ask() no streaming).

## Decisiones con alternativa descartada

| Decisión | Alternativa descartada | Justificación |
|----------|------------------------|---------------|
| Render user message first in main loop | Mantener filtro messages_to_show | Más simple, semántica natural: el historial es la fuente de verdad |
| Streaming bubble after main loop | Streaming bubble before + filter | Evita lógica de filtrado compleja y orden visual correcto por defecto |
| Un solo rerun al final | Múltiples reruns durante streaming | Menos flicker, Streamlit maneja write_stream sin reruns intermedios |

## Estrategia de tests

| Test | Qué verifica |
|------|--------------|
| Visual: User sends prompt | User bubble appears immediately, then assistant streams below |
| Visual: Streaming completes | Final response appears in history, no duplicate |
| Visual: Multiple turns | Strict User→Assistant→User→Assistant order |
| Compilation | `python -m py_compile app.py` |

## RF coverage

| RF | Cobertura | Estado |
|----|-----------|--------|
| RF1 (User immediate) | Main loop renders all messages including latest user | ✅ Implementado |
| RF2 (Assistant below) | Streaming block after main loop | ✅ Implementado |
| RF3 (Chronological) | Single loop over session_state.messages | ✅ Implementado |
| RF4 (Final in history) | Generator appends to messages on done + rerun | ✅ Implementado |
| RF5 (No flicker) | Single rerun cycle | ✅ Implementado |

## Resumen de cambios realizados

### `app.py` (líneas 520-771)
- **Reordenado bloques**: Historial completo → Streaming → Spinner legacy → Chat input
- **Eliminado filtro `messages_to_show`**: Ahora `for msg in st.session_state.messages` renderiza todo sin filtrar
- **Generador actualizado**: Al terminar streaming (`done=True`), hace `st.rerun()` para que la respuesta final aparezca en el bucle principal
- **Spinner legacy condicionado**: Solo si `processing and not streaming_active`
- **Compilación verificada**: `python -m py_compile app.py` → OK