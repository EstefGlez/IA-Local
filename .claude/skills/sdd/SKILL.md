---
name: sdd
description: "Úsala siempre que trabajes con Spec-Driven Development (SDD): redactar, revisar o cambiar specs, planes y tareas dentro de specs/, o implementar y validar tareas de una spec. Actívala también cuando el usuario diga spec, especificación, requisitos, plan técnico, tareas o criterios de aceptación, aunque no nombre SDD."
---

# Spec-Driven Development (SDD)

Primero se define QUÉ debe hacer el sistema y cómo se comprueba; después se implementa. Así el agente no rellena huecos inventando.

## Flujo
Constitución → Spec → Clarificación → Plan → Tareas → Implementación → Validación → Cambio.

- Nunca pases a la fase siguiente sin aprobación explícita del usuario.
- La spec manda: si algo no está en la spec, no se implementa. Si falta una decisión, para y pregunta.
- Un cambio de requisitos se hace primero en la spec, luego en plan y tareas, y al final en el código.
- Cada spec vive en `specs/NNN-nombre/` con `spec.md`, `plan.md` y `tasks.md`.
- El comando de tests es el que indique `AGENTS.md` (sección Comandos). Si no existe, pregunta cuál usar.
- El `plan.md` de la raíz del proyecto (hoja de ruta) NO es el `plan.md` de una spec. No los mezcles.
- Al terminar cada fase actualiza `MEMORY.md` (skill `project-context`).

## Constitución (`docs/constitution.md`, una vez por proyecto)
6 principios innegociables, cortos y verificables, máximo 15 líneas: simplicidad del stack, relación spec-código, separación lógica/interfaz, política de tests, protección de datos del usuario, idioma del código y textos. Se propone y se espera aprobación antes de escribirla.

## Plantilla de spec (`spec.md`)
```
# Spec NNN — <Nombre>
Estado: borrador | aprobada | implementada

## Contexto y objetivo
## Usuarios
## Historias de usuario
- HU-1. Como <rol>, quiero <acción> para <beneficio>.
## Definiciones (solo si hay términos ambiguos)
## Requisitos funcionales
## Requisitos no funcionales
## Casos límite
## Fuera de alcance
## Criterios de finalización
## Dudas abiertas
- [NECESITA ACLARACIÓN] <duda>
```
La spec describe el QUÉ y el POR QUÉ. Nada de stack, arquitectura ni nombres de archivos.

## Requisitos en EARS (en español)
- RF-x: CUANDO <evento>, EL SISTEMA <respuesta>.
- RF-x: SI <condición no deseada>, ENTONCES EL SISTEMA <respuesta>.
- RF-x: MIENTRAS <estado>, EL SISTEMA <respuesta>.
- RF-x: EL SISTEMA <comportamiento permanente>.
Cada RF debe poder verificarse: nada de "rápido", "bonito" o "intuitivo" sin criterio medible. Una frase = un comportamiento.

## Clarificación
Revisar la spec como un QA: (1) ambigüedades, (2) contradicciones, (3) casos límite no cubiertos, (4) conflictos con la constitución. Solo detectar, no proponer soluciones. Lista numerada.

## Plan (`plan.md`)
Archivos y responsabilidades · funciones puras de lógica · algoritmo en pseudocódigo · interfaz · decisiones justificadas con su alternativa descartada · estrategia de tests. Indica qué RF cubre cada parte.

## Tareas (`tasks.md`)
```
- [ ] **Tn. <Descripción>.** RF-x, RF-y
  - Hecho cuando: <comprobación verificable>.
```
Máximo 20-30 min por tarea, en orden de dependencia. Si salen más de 10, propón dividir la spec.

## Implementación
Una sola tarea cada vez: tests primero (en rojo), después el código, tests en verde, marcar la tarea y parar.

## Validación
Recorrer la spec RF por RF: qué test lo cubre y su resultado. Los RF de interfaz se verifican en el navegador (MCP `chrome-devtools` si está disponible, incluida vista móvil). Si algo falla, decirlo; no arreglar en esta fase.
