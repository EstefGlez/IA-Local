---
description: "SDD · Valida la implementación contra la spec, RF por RF (solo lectura)"
argument-hint: "[NNN-nombre]"
---
Usa el subagente `reviewer` (si no puedes, aplica tú la skill `review-changes`). Solo lectura.

Valida `specs/$ARGUMENTS`: lee spec, plan, tareas y `git diff` contra la rama base, ejecuta los tests y recorre la spec RF por RF (qué test lo cubre y su resultado). Verifica criterios de finalización y constitución.
Empieza con `VEREDICTO: APROBADO` o `VEREDICTO: CAMBIOS NECESARIOS` y, si hay cambios, lista numerada con `archivo:línea`, qué incumple y qué se espera.
