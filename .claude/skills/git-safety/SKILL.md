---
name: git-safety
description: "Úsala SIEMPRE antes de modificar archivos en un repositorio git y al cerrar cada tarea. Crea una rama de trabajo, hace commits pequeños y prohíbe comandos destructivos (push --force, reset --hard, clean, rm -rf) sin permiso explícito. Actívala también cuando el usuario hable de ramas, commits, deshacer cambios, merge o proteger el proyecto."
---

# Seguridad con git

Cada encargo trabaja en su propia rama. Así el trabajo del agente siempre se puede revisar, descartar o fusionar sin riesgo para `main`.

## Antes de tocar nada
1. `git status --short` y `git branch --show-current`.
2. Si no es un repo git: avisa y propón `git init` (pide permiso). No continúes sin red de seguridad.
3. Si hay cambios sin commit del usuario: PARA y pregunta (commit, stash o seguir). No mezcles su trabajo con el tuyo.
4. Si estás en `main`, `master` o `develop`: crea rama `ia/AAAA-MM-DD-slug` (slug corto en minúsculas con guiones). Si el encargo trae `Rama:`, usa ese nombre.

## Durante
- Commits pequeños, uno por tarea terminada: `tipo: resumen` (feat, fix, refactor, test, docs, chore).
- Añade archivos concretos (`git add ruta/archivo`), no `git add -A` a ciegas. Nunca incluyas `.env`, claves, `node_modules` ni binarios grandes; revisa `.gitignore`.
- Antes de cada commit: `git diff --stat` y revisa que solo estén los archivos esperados.

## Prohibido sin permiso explícito del usuario
`git push` (cualquier forma), `git push --force`, `git reset --hard`, `git clean`, `git checkout -- .`, `git restore .`, `git rebase`, `git branch -D`, `git stash drop`, borrar la carpeta `.git`, `rm -rf`, hacer merge a `main`.

## Fusionar es decisión del usuario
Al terminar, indica cómo revisar y fusionar, sin ejecutarlo:
```
git diff main...HEAD --stat
git switch main
git merge --no-ff <rama>
```

## Recetas para deshacer (explícaselas al usuario si las necesita)
- Deshacer el último commit conservando los cambios: `git reset --soft HEAD~1`
- Descartar los cambios de UN archivo: `git restore ruta/archivo`
- Descartar toda la rama de trabajo: `git switch main` y luego `git branch -D <rama>`
- Ver qué cambió un commit: `git show <hash> --stat`
