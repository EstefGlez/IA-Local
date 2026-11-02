---
name: review-changes
description: "Úsala para revisar cambios hechos por un agente o por el usuario, como si fuera un pull request: git diff, rama pendiente de fusionar, resultado de una tarea. Actívala cuando pidan revisar, validar, auditar, code review, explicar los cambios o comprobar si algo está bien, y siempre antes de dar una tarea por terminada."
---

# Revisar cambios

Regla: si no aprobarías ese cambio en una revisión hecha por otra persona, tampoco lo apruebes porque lo haya escrito una IA. Esta skill es de solo lectura: no modifica nada.

## Cómo
1. Detecta la rama base (`main` o `master`) y lee `git diff <base>...HEAD`. Lee también la spec, el plan o el encargo que originó el cambio.
2. Ejecuta los tests y comandos de verificación de `AGENTS.md` (solo lectura/ejecución, sin editar).
3. Vuelve a los criterios de aceptación y comprueba uno por uno, con evidencia.
4. Revisa técnicamente:
   - **Scope**: ¿tocó solo lo necesario o hay cambios sin relación?
   - **Implementación**: ¿se entiende qué hace cada cambio y por qué?
   - **Arquitectura**: ¿respeta las convenciones y decisiones del proyecto?
   - **Complejidad**: ¿añadió dependencias, abstracciones o código que no hacía falta?
   - **Riesgo**: ¿puede romper algo que ya funcionaba? Secretos, datos del usuario, fechas, casos límite.
   - **Tests**: ¿comprueban los casos importantes o solo existen para decir que hay tests? Que estén en verde no cierra la tarea.

## Formato de respuesta
Empieza SIEMPRE con una de estas dos líneas:
- `VEREDICTO: APROBADO`
- `VEREDICTO: CAMBIOS NECESARIOS`

Si hay cambios necesarios, lista numerada con: `archivo:línea`, qué incumple (criterio, RF o principio) y qué se espera. Las sugerencias que no incumplen nada van aparte, bajo "Opcional", y no bloquean.

## Modo explicación (si el usuario no entiende un cambio)
Sin modificar nada, explica: 1) qué problema resuelve cada cambio, 2) por qué esta solución, 3) qué alternativas había, 4) qué riesgos tiene, 5) qué podría romperse.
