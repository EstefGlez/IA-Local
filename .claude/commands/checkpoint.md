---
description: "Guarda el trabajo: actualiza plan.md/MEMORY.md y hace commit en la rama de trabajo"
argument-hint: "[mensaje de commit opcional]"
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git add:*), Bash(git commit:*), Bash(git branch:*), Bash(git log:*)
---
Aplica las skills `git-safety` y `project-context`.

1. `git branch --show-current`. Si estás en main/master: PARA y avísame.
2. `git status --short` y `git diff --stat`. Si hay archivos que no esperabas (o `.env`, claves, binarios), PARA y pregunta.
3. Actualiza `plan.md` (marca lo hecho) y `MEMORY.md` (estado, decisiones, próximos pasos).
4. `git add` de archivos concretos y `git commit` con mensaje `tipo: resumen`. Si di mensaje, úsalo: $ARGUMENTS
5. Muéstrame el hash y `git log --oneline -3`. No hagas push.
