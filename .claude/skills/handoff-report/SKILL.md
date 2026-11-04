---
name: handoff-report
description: "Úsala al terminar cualquier tarea y cuando el usuario pida reporte, resumen, informe, handoff o algo para llevar a Claude web o al arquitecto. Genera un reporte compacto y pegable (qué se hizo, archivos, verificación, decisiones, dudas, siguiente paso) para que otra IA pueda continuar sin releer todo el diff."
---

# Reporte de traspaso

Objetivo: que quien lo lea (el usuario o Claude en la web) entienda el estado exacto con el MÍNIMO de texto. Pegar un diff completo gasta muchos tokens; un buen reporte casi nunca lo necesita.

## Pasos
1. Recoge datos con comandos reales, no de memoria: `git branch --show-current`, `git log --oneline -5`, `git diff <base>...HEAD --stat`.
2. Rellena la plantilla. Máximo ~40 líneas. Español, frases cortas.
3. Imprímelo en un único bloque de código para que se copie de una vez. Guárdalo también en `docs/handoff/AAAA-MM-DD-slug.md`.

## Plantilla (úsala exacta)
```
## REPORTE · <tarea> · <fecha>
Rama: <rama> · Commits: <hashes cortos>
Estado: COMPLETA | PARCIAL | BLOQUEADA

### Qué se hizo (máx. 8 líneas)
-

### Archivos (git diff --stat)
<salida resumida>

### Verificación
<comando> → <resultado literal resumido>. Si algo no se pudo verificar, dilo aquí.

### Decisiones que el encargo no cubría
-

### Dudas o bloqueos (preguntas concretas para el arquitecto)
1.

### Riesgos
-

### Cambios que afectan a contexto.md / plan.md
-

### Siguiente paso sugerido
-
```

## Reglas
- No pegues el diff completo. Si una decisión depende de un fragmento, incluye solo ese trozo (máx. 40 líneas) bajo "Diff clave".
- Estado COMPLETA solo si los criterios de aceptación se verificaron con evidencia. Si no, PARCIAL.
- Si algo falló, dilo tal cual: qué comando, qué error. No lo escondas ni lo suavices.
- No incluyas claves, tokens ni rutas privadas.
