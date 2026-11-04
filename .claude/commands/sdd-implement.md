---
description: "SDD · Implementa UNA tarea de tasks.md (tests primero)"
argument-hint: "[NNN-nombre] [Tn]"
---
Sigue las skills `work-protocol`, `git-safety` y `sdd`.

Spec: $1 · Tarea: $2
1. Comprueba la rama de trabajo (nunca main).
2. Lee `specs/$1/tasks.md` (tarea $2), `plan.md`, `docs/constitution.md` y `AGENTS.md`.
3. Implementa SOLO esa tarea: tests primero (en rojo), luego el código. Ejecuta los tests y no la des por hecha con tests en rojo.
4. Marca la tarea en `tasks.md`, haz commit de checkpoint y PARA. No empieces la siguiente.
5. Si la tarea o el plan son incorrectos, para y explícalo. Si es la última tarea de la spec, actualiza `MEMORY.md`.
Termina con un reporte corto (skill `handoff-report`).
