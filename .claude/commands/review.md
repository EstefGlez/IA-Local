---
description: "Revisión tipo pull request de la rama actual (solo lectura) con el subagente reviewer"
argument-hint: "[foco opcional: seguridad, tests, UI...]"
---
Usa el subagente `reviewer` (si no puedes, aplica tú la skill `review-changes`). Solo lectura.

Revisa los cambios de la rama actual contra la rama base (`git diff <base>...HEAD`), con el encargo o spec que los originó. Foco extra: $ARGUMENTS
Devuelve `VEREDICTO: ...` y la lista numerada con `archivo:línea`. Sin modificar nada.
