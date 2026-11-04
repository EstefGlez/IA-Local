---
name: project-context
description: "Úsala al EMPEZAR cualquier sesión de trabajo en un proyecto y al TERMINAR cada tarea. Lee contexto.md, README.md, plan.md, AGENTS.md y MEMORY.md antes de tocar código, y al acabar actualiza plan.md y MEMORY.md con lo hecho. También úsala para crear o mejorar AGENTS.md y MEMORY.md, o cuando el usuario hable de contexto, memoria, estado del proyecto o documentación."
---

# Contexto del proyecto

Un modelo no recuerda entre sesiones. El proyecto debe recordar por él: leer al empezar, escribir al terminar.

## Al empezar (siempre)
1. Lee, si existen y por este orden: `AGENTS.md` (o `CLAUDE.md`), `contexto.md`, `README.md`, `plan.md`, `MEMORY.md`.
2. Resume en 3-5 líneas qué entendiste del proyecto y del punto actual. No supongas lo que no esté escrito.
3. Si `contexto.md` contradice el código, NO lo corrijas en silencio: anótalo en el reporte final como duda.

## Qué es cada archivo
- `contexto.md` / `README.md`: qué se construye, por qué, tecnologías y arquitectura. Los escribe el arquitecto (Claude web). Solo lectura, salvo que te pidan editarlos.
- `plan.md` (raíz): hoja de ruta con checkboxes `[ ]`/`[x]`. Marca lo hecho y añade una línea de nota; no reescribas el resto.
- `AGENTS.md`: instrucciones para agentes. Máximo 30-40 líneas. Plantilla en `templates/AGENTS.md` del kit.
- `MEMORY.md`: memoria entre sesiones. Máximo ~50 líneas: estado actual, decisiones (con su porqué), errores a evitar, próximos pasos.

## Al terminar una tarea
1. Marca la tarea en `plan.md` (si está) con `[x]` y una nota de una línea.
2. Actualiza `MEMORY.md`: estado actual, decisiones importantes (con porqué), errores a evitar. Resume o borra lo que ya no aporte.
3. Si algo se vuelve regla permanente, propón moverlo a `AGENTS.md`; no lo muevas tú sin avisar.
4. Nunca guardes claves, tokens ni datos personales en estos archivos.

## Crear AGENTS.md si no existe
Pide permiso, explora el proyecto en modo lectura y propón el borrador siguiendo la plantilla (descripción, stack y estructura, comandos exactos, convenciones, reglas y trampas, forma de trabajar, límites ✅/⚠️/🚫, verificación). Escríbelo solo tras aprobación.
