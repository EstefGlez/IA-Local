# Plan: Safety Lock and Concurrency Control

## Archivos y responsabilidades

| Archivo | Responsabilidad |
|---------|-----------------|
| `app.py` | Lógica de bloqueo centralizada + aplicación a chat_input, sidebar buttons |

## Algoritmo / Cambios

### 1. Variable de estado bloqueado (línea ~520, al inicio de tab_chat)
```python
is_processing = st.session_state.get("streaming_active", False) or st.session_state.get("processing", False)
```

### 2. Aplicar a chat_input (línea ~760)
```python
prompt = st.chat_input(
    "Escribe tu pregunta o usa /memory /rag...",
    disabled=not (core_loaded and agent_loaded) or is_processing
)
```

### 3. Aplicar a sidebar buttons (líneas ~457, 472, 486)
```python
# Nuevo Chat
if st.button("➕ Nuevo Chat", ..., disabled=is_processing):

# Seleccionar conversación
if st.button(..., disabled=is_processing):

# Eliminar conversación
if st.button("🗑️", ..., disabled=is_processing):
```

### 4. Indicador visual en chat (después del bucle de mensajes, antes de streaming)
```python
if is_processing and not st.session_state.streaming_active:
    st.info("⏳ Procesando respuesta... Por favor espera.")
```

### 5. Indicador visual en sidebar (opcional, sutil)
```python
if is_processing:
    st.sidebar.caption("🔒 Interfaz bloqueada durante generación")
```

## Decisiones con alternativa descartada

| Decisión | Alternativa descartada | Justificación |
|----------|------------------------|---------------|
| Variable `is_processing` combinada | Variables separadas en cada uso | DRY, single source of truth |
| `disabled` en botones nativos | Ocultar botones con `if not is_processing` | Mantiene layout estable, UX más clara |
| Banner `st.info` en chat | Toast o spinner global | Visible sin interrumpir, se auto-limpia al rerun |

## Estrategia de tests

| Test | Qué verifica |
|------|--------------|
| Visual: Send prompt during streaming | chat_input disabled, sidebar buttons disabled |
| Visual: Send prompt during legacy processing | Same blocking behavior |
| Visual: After completion | All controls re-enabled automatically |
| Compilation | `python -m py_compile app.py` |

## RF coverage

| RF | Cobertura | Estado |
|----|-----------|--------|
| RF1 (chat_input) | `disabled=... or is_processing` | ✅ Implementado |
| RF2 (sidebar) | `disabled=is_processing` en botones críticos | ✅ Implementado |
| RF3 (visual) | `st.info` banner (legacy) + sidebar caption | ✅ Implementado |
| RF4 (no opaque) | Auto-clear on rerun when flags reset | ✅ Implementado |
| RF5 (compile) | Smoke test | ✅ Verificado |

## Resumen de cambios realizados

### `app.py` 
- **Sidebar (líneas ~456-493)**: Variable `is_processing` definida; `disabled=is_processing` en "Nuevo Chat", botones de selección de conversación, botones de eliminación; caption "🔒 Interfaz bloqueada..." cuando activo
- **Pestaña Chat (línea ~530)**: Variable `is_processing` definida al inicio
- **Banner legacy (línea ~671)**: `st.info("⏳ Procesando respuesta... Por favor espera.")` solo cuando `processing=True` y NO `streaming_active`
- **Chat input (línea ~775)**: `disabled=not (core_loaded and agent_loaded) or is_processing`
- **Compilación verificada**: `python -m py_compile app.py` → OK