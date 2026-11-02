---
description: "Genera el reporte compacto para llevar a Claude web (qué se hizo, archivos, pruebas, dudas, siguiente paso)"
argument-hint: "[tarea o nota opcional]"
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git branch:*)
---
Aplica la skill `handoff-report`. Solo lectura, salvo guardar el reporte en `docs/handoff/`.

Tarea / nota: $ARGUMENTS

Recoge los datos ejecutando tú los comandos (rama actual, `git log --oneline -5`, `git status --short`, `git diff <base>...HEAD --stat`, donde base es main o master). Rellena la plantilla exacta, sin pegar el diff completo. Imprímela en un único bloque de código para copiarla de una vez.
