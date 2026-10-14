# Plan: Extend Safety Lock to All Controls

## Archivos y responsabilidades

| Archivo | Responsabilidad |
|---------|-----------------|
| `app.py` | Definir `is_processing` global + aplicar `disabled` a controles en Config y Memoria |

## Algoritmo / Cambios

### 1. Definir `is_processing` GLOBAL (antes de tabs, línea ~510)
```python
# Estado global de bloqueo
is_processing = st.session_state.get("streaming_active", False) or st.session_state.get("processing", False)
```

### 2. Pestaña Configuración (líneas ~850-1032)
- Sliders: `temperature`, `top_k`, `context_scale` → `disabled=is_processing`
- Botones RAG: "Re-indexar", "Eliminar fuente" → `disabled=is_processing`
- Formulario "Añadir fuente": `st.form_submit_button` → `disabled=is_processing`
- Botón "Limpiar ChromaDB" → `disabled=is_processing`

### 3. Pestaña Memoria (líneas ~1035-1145)
- Selectbox sesión → `disabled=is_processing`
- Botones "Eliminar" archivo → `disabled=is_processing`
- Formulario "Crear archivo manual": `st.form_submit_button` → `disabled=is_processing`
- Botón "Eliminar TODOS" → `disabled=is_processing`

### 4. Eliminar definiciones duplicadas de `is_processing` en sidebar y tab_chat (usar la global)

## Decisiones con alternativa descartada

| Decisión | Alternativa descartada | Justificación |
|----------|------------------------|---------------|
| `is_processing` global antes de tabs | Definir en cada pestaña | Single source of truth, DRY |
| `st.download_button` sin bloqueo | Bloquear con CSS hack | Solo lectura, no modifica estado, riesgo bajo |
| `st.form_submit_button` con disabled | Deshabilitar form completo | Control granular, UX clara |

## Estrategia de tests

| Test | Qué verifica |
|------|--------------|
| Visual: Config sliders during streaming | Disabled, no aceptan input |
| Visual: Config RAG buttons during streaming | Disabled |
| Visual: Memoria selectbox/buttons during streaming | Disabled |
| Visual: After completion | All re-enabled |
| Compilation | `python -m py_compile app.py` |

## RF coverage

| RF | Cobertura | Estado |
|----|-----------|--------|
| RF1 (Config sliders) | `disabled=is_processing` en sliders | ✅ Implementado |
| RF2 (Config RAG) | `disabled=is_processing` en botones + form submit | ✅ Implementado |
| RF3 (Memoria) | `disabled=is_processing` en selectbox, botones, form submit | ✅ Implementado |
| RF4 (Consistencia) | Variable global única | ✅ Implementado |
| RF5 (Compile) | Smoke test | ✅ Verificado |

## Resumen de cambios realizados

### `app.py`
- **Global (línea ~513)**: `is_processing` definida una vez antes de tabs, accesible en todas las pestañas
- **Sidebar**: Eliminada definición duplicada; usa variable global
- **Tab Chat**: Eliminada definición duplicada; usa variable global
- **Tab Config (sliders)**: temperatura, top_k, context_scale → `disabled=is_processing`
- **Tab Config (botones RAG)**: "Re-indexar", "Eliminar fuente" → `disabled=is_processing`
- **Tab Config (formulario)**: "Añadir fuente" submit → `disabled=is_processing`
- **Tab Config (botón)**: "Limpiar ChromaDB" → `disabled=is_processing`
- **Tab Memoria (selectbox)**: "Seleccionar sesión" → `disabled=is_processing`
- **Tab Memoria (botones)**: "Eliminar" archivo → `disabled=is_processing`
- **Tab Memoria (formulario)**: "Crear archivo manual" submit → `disabled=is_processing`
- **Tab Memoria (botón)**: "Eliminar TODOS" → `disabled=is_processing`
- **No bloqueado**: `st.download_button` (solo lectura), pestaña Monitor (solo métricas)
- **Compilación verificada**: `python -m py_compile app.py` → OK