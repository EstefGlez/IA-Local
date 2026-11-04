---
description: "Ejecuta un encargo (p. ej. el que te da Claude web) con protocolo: entender, rama, plan, implementar, verificar y reportar"
argument-hint: "[pega aquí el encargo]"
---
Encargo recibido:

$ARGUMENTS

Sigue este orden y no te saltes pasos:
1. Skill `task-brief`: comprueba que el encargo tiene objetivo, contexto, restricciones y criterios de aceptación. Pregunta lo que falte (máx. 3 preguntas) y reformula en 3-5 líneas lo que vas a hacer.
2. Skill `git-safety`: rama de trabajo (la del encargo si trae `Rama:`). Nunca en main.
3. Skill `project-context`: lee AGENTS.md, contexto.md, README.md, plan.md y MEMORY.md.
4. Skill `work-protocol`: si el encargo dice `Plan primero: sí` (o toca varios archivos), presenta el plan y ESPERA mi aprobación. Después implementa paso a paso y verifica con comandos reales.
5. Haz commit de checkpoint, actualiza `plan.md`/`MEMORY.md` y termina con la skill `handoff-report`. PARA ahí.
