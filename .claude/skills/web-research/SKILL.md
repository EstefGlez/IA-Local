---
name: web-research
description: "Úsala cuando necesites información que no está en el proyecto: documentación de una librería o API, versiones actuales, mensajes de error, comparar opciones, buenas prácticas o cualquier dato reciente. Actívala antes de usar una API o flag del que no estés seguro, y cuando el usuario diga busca, investiga, consulta la documentación o averigua en internet."
---

# Investigación en línea

Un modelo pequeño inventa con confianza. Investigar antes es más barato que depurar una invención.

## Escalera de herramientas (usa la primera que funcione)
1. **Herramientas nativas** `WebSearch` / `WebFetch`, si existen. Con proxies a otros modelos pueden no estar disponibles: prueba UNA vez y, si fallan, pasa al siguiente nivel sin insistir.
2. **MCP de documentación o búsqueda** configurado en el proyecto (por ejemplo `context7` para documentación de librerías). Revisa con `/mcp`.
3. **Descarga directa** de URLs concretas con `curl` o `WebFetch`: documentación oficial, README del repo, notas de versión, `package.json` del paquete.
4. **Si nada funciona**: dilo claramente y devuelve al usuario una lista de lo que necesitas saber, para que lo consulte (por ejemplo en Claude web) y te lo pase.

## Reglas
- Fuentes oficiales primero (documentación, repositorio oficial, notas de versión). Foros y blogs solo como apoyo.
- Comprueba la versión que usa el proyecto (`package.json`, `requirements.txt`, lockfile) y busca la documentación de ESA versión.
- Cada afirmación importante lleva su URL. Distingue hecho (dicho por la fuente) de inferencia (tuya).
- Si las fuentes se contradicen o no encuentras la respuesta, dilo. No rellenes huecos.
- No copies texto largo de las páginas: resume con tus palabras y cita la fuente.
- Anota la fecha de la consulta: la información caduca.

## Resultado
Si el hallazgo servirá más adelante, guárdalo en `docs/research/<tema>.md` (máx. 60 líneas): pregunta, respuesta corta, fuentes con URL, fecha, y dudas abiertas. Para uso inmediato basta un resumen de 5 líneas con enlaces.
