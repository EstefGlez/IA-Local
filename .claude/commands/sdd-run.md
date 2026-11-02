---
description: "SDD · Coordinador: ejecuta el flujo completo con los subagentes planner, implementer y reviewer"
argument-hint: "[idea o petición]"
---
Eres el COORDINADOR del flujo SDD (skill `sdd`). No escribes código ni editas archivos: repartes el trabajo entre los subagentes `planner`, `implementer` y `reviewer` y hablas conmigo. Si no puedes invocar subagentes, avísame y ejecuta las fases tú mismo, una a una, respetando las aprobaciones.

Petición: $ARGUMENTS
Si es un cambio pequeño que no merece una spec, sugiere `/task` y para.

Antes de nada, aplica la skill `git-safety` (rama de trabajo; nunca en main).

## Fases
1. **Spec**: pide a `planner` que redacte `specs/NNN-nombre/spec.md`. Si devuelve preguntas, házmelas de una en una y vuelve a llamarle con las respuestas.
2. **Clarificación**: pide a `reviewer` que revise la spec como QA (solo detecta). Enséñame el resultado; si hay problemas, `planner` corrige. PARA hasta que apruebe la spec.
3. **Plan y tareas**: pide a `planner` plan.md y tasks.md. Enséñame un resumen y PARA hasta que los apruebe.
4. **Implementación**: llama a `implementer` UNA vez por tarea (T1, T2…), en orden. Tras cada tarea comprueba que los tests están en verde; si no, para y avísame.
5. **Validación**: pide a `reviewer` que valide la spec RF por RF.
6. **Correcciones**: si dice CAMBIOS NECESARIOS, vuelve a `implementer` con la lista exacta y después otra vez a `reviewer`. Máximo 2 vueltas; si sigue fallando, para y explícame qué ocurre.
7. **Cierre**: aplica la skill `handoff-report` (hecho, veredicto del reviewer, pendiente).

## Transmitir el contexto
Los subagentes NO ven esta conversación. En cada llamada pásales: la fase y qué se espera; mi petición original con mis palabras y decisiones; las rutas de los archivos que deben leer; y el resultado de la fase anterior.

## Reglas
- Nunca te saltes una aprobación mía (spec, y plan con tareas).
- No resuelvas tú las dudas: pregúntamelas.
- Avísame en una línea al empezar cada fase.
