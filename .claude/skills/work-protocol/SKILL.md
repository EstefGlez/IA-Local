---
name: work-protocol
description: "Úsala SIEMPRE que vayas a modificar código o archivos de un proyecto. Define cómo trabajar con control: un paso a la vez, verificar con evidencia, no inventar, parar cuando algo falla dos veces y no declarar terminado sin pruebas. Imprescindible para modelos pequeños o locales."
---

# Protocolo de trabajo con control

Un agente rápido ejecutando un mal plan sigue ejecutando un mal plan. La velocidad solo sirve con puntos de control.

## Orden
1. Rama de trabajo (skill `git-safety`).
2. Leer contexto (skill `project-context`) y entender el encargo (skill `task-brief`).
3. Plan breve si corresponde (varios archivos, varias formas de resolverlo, o lo pide el encargo). Esperar aprobación.
4. Implementar UNA tarea. Cambios pequeños y enfocados.
5. Verificar con comandos reales (tests, lint, build; los de `AGENTS.md`). Si no hay tests, describe cómo lo comprobaste.
6. Commit de checkpoint en la rama.
7. Reporte (skill `handoff-report`) y PARAR. No empieces la siguiente tarea.

## Reglas
- **Evidencia**: "he terminado" no es una prueba; "los tests pasan" tampoco si no los ejecutaste y viste la salida. Incluye el resultado resumido.
- **No inventes**: APIs, funciones, flags ni versiones. Si no estás seguro, lee el código o la documentación, o usa la skill `web-research`. Di "no lo sé" y propón cómo averiguarlo.
- **Alcance**: toca solo lo necesario. Nada de refactors, renombrados ni "mejoras" no pedidas.
- **Dependencias**: no instales ni añadas ninguna sin preguntar y explicar por qué.
- **Dos intentos**: si el mismo enfoque falla dos veces, PARA. Explica qué probaste, qué viste y qué hipótesis tienes. No entres en bucles.
- **Contradicciones**: si el encargo, el plan o el código se contradicen, pregunta; no elijas por tu cuenta.
- **Decisiones propias**: cualquier decisión que el encargo no cubría va al reporte, en su sección.
- **Archivos sensibles**: nunca leas ni imprimas `.env`, claves ni tokens.
- **Honestidad**: si algo quedó a medias o no pudiste verificarlo, el estado es PARCIAL, no COMPLETA.
- **Brevedad**: respuestas cortas. No repitas el código que escribiste ni expliques lo obvio.
