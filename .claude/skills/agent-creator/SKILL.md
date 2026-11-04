---
name: agent-creator
description: "Úsala cuando el usuario quiera crear un nuevo subagente o rol para el proyecto (revisor de seguridad, escritor de tests, documentador, depurador, especialista de base de datos...) o cuando una tarea se repita lo bastante como para justificar un rol propio. Genera el archivo .claude/agents/<nombre>.md con descripción, herramientas mínimas y prompt. Actívala ante frases como crea un agente, necesito un rol, añade un subagente."
---

# Crear subagentes

Un subagente es un especialista con su propio contexto, herramientas y prompt. Trabaja aislado: NO ve la conversación, solo lo que le pases. Cada rol nuevo es más mantenimiento, así que primero decide si hace falta.

## ¿Crear agente, skill o comando?
- **Skill**: conocimiento o procedimiento que cualquier agente puede cargar ("cómo revisar fechas").
- **Comando**: un prompt que TÚ lanzas a mano con `/nombre`.
- **Subagente**: solo si se cumple al menos una: (a) necesita permisos distintos (solo lectura, o solo escribir en una carpeta), (b) su trabajo ensucia el contexto principal (leer mucho, ejecutar muchas pruebas), (c) quieres trabajo en paralelo o una revisión independiente.

## Pasos
1. Define el rol en una frase y su entrada/salida (qué recibe, qué devuelve).
2. Elige herramientas con mínimo privilegio:
   - Solo analizar: `Read, Grep, Glob`
   - Analizar y ejecutar pruebas: añade `Bash` (y deja claro qué comandos puede usar)
   - Construir: `Edit, Write`
   - Investigar en internet: `WebSearch, WebFetch` (puede no estar disponible con tu proxy)
3. Escribe la `description` como cuándo usarlo: "Úsalo para X. Úsalo proactivamente cuando Y." Es lo que decide si se delega a él.
4. Usa `model: inherit` salvo motivo claro. Con proxies, los alias de modelo (sonnet, haiku) los reasigna el proxy.
5. Copia `template.md` de esta skill a `.claude/agents/<nombre>.md` del proyecto y rellénalo. Mantén el prompt corto: rol, antes de empezar, cómo trabaja, límites, formato de respuesta.
6. Regístralo en `AGENTS.md` (sección "Roles disponibles": nombre y cuándo usarlo).
7. Pruébalo con una tarea pequeña y real. Comprueba que respeta el formato y los límites. Ajusta.

## Roles frecuentes (como punto de partida)
`debugger` (reproduce y aísla fallos), `test-writer` (solo escribe tests), `security-reviewer` (solo lectura: secretos, entradas, dependencias), `docs-writer` (README y docs), `ui-reviewer` (revisa la interfaz con el navegador), `db-migrator`.

## Cuidado
- Un agente con `Bash` y sin límites es tan peligroso como el agente principal. Pon límites explícitos en su prompt.
- Los agentes se invocan desde la sesión principal. No dependas de que un subagente lance a otro.
- Tras crear o editar un agente, reinicia Claude Code o usa `/agents` para que lo recargue.
