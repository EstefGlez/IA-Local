---
name: task-brief
description: "Úsala cada vez que recibas una tarea, un encargo o un prompt largo (del usuario o del arquitecto en Claude web) ANTES de actuar. Comprueba que estén claros objetivo, contexto, restricciones, criterios de aceptación y formato de salida, pregunta lo que falte y confirma tu comprensión. Úsala también cuando una petición sea vaga como mejora esto, arregla esto o añade un buscador."
---

# Entender el encargo antes de actuar

La mayoría de errores de un agente vienen de decisiones que nadie tomó y él rellenó solo.

## Las 6 piezas
1. **Objetivo**: qué debe conseguirse, en una frase.
2. **Contexto**: proyecto, tecnologías, archivos implicados.
3. **Tarea exacta**: algo concreto, no "un sistema".
4. **Restricciones**: stack que se mantiene, qué no tocar, dependencias permitidas.
5. **Criterios de aceptación**: cómo sabremos que está terminado (casos límite incluidos).
6. **Salida esperada**: qué debes devolver (reporte, archivos, comandos).

## Qué hacer
- Si falta alguna pieza que cambie el resultado, pregunta. Máximo 3 preguntas, en un solo mensaje, numeradas.
- Si falta algo menor, di tu suposición explícita y sigue.
- Antes de actuar, reformula en 3-5 líneas: "Entiendo que: objetivo / archivos que voy a tocar / qué NO voy a tocar / cómo comprobaré que está hecho".
- Si el encargo dice `Plan primero: sí`, o la tarea toca más de 2 archivos, o puede resolverse de varias formas: presenta un plan breve y ESPERA aprobación.
- Si el encargo es demasiado grande para una sola tarea, propón dividirlo en tareas de 20-30 minutos y empieza por la primera.
- Nunca añadas funcionalidades que no se pidieron.
