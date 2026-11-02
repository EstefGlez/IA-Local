---
description: "Crea un subagente nuevo para el proyecto (rol, herramientas mínimas, prompt)"
argument-hint: "[rol que necesitas]"
---
Aplica la skill `agent-creator`.

Rol pedido: $ARGUMENTS

Primero dime si de verdad hace falta un subagente o basta una skill o comando (con tu razón en 2 líneas). Si hace falta, propón nombre, `description`, herramientas mínimas y el prompt, y ESPERA mi aprobación antes de crear `.claude/agents/<nombre>.md` y registrarlo en `AGENTS.md`.
