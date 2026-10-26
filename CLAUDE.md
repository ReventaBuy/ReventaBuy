# ReventaBuy

## Dos tipos de vídeo, separados

| Tipo | Skills | Carpeta |
|---|---|---|
| 1. Refugio del Sueño (YouTube, vídeos largos para dormir) | `video-dormir` | `videos-dormir/` |
| 2. Instagram (Reels y demás contenido de Instagram) | `ig-*` (13 skills) | `instagram/` |

Reglas:

- **Cuando el usuario pida un vídeo, elige él el tipo.** Si no lo ha dicho, pregúntale
  cuál de los dos quiere antes de hacer nada. No lo deduzcas por el tema.
- **Usa solo las skills de ese tipo.** En un vídeo de Refugio del Sueño no se usa ninguna
  skill `ig-*`; en contenido de Instagram no se usa `video-dormir` ni su flujo.
- **Pregunta qué voz quiere en cada vídeo**, de cualquiera de los dos tipos, antes de generar
  ninguna voz. No la elijas tú ni repitas la del vídeo anterior sin preguntar.
- **No se mezclan hasta que el usuario lo diga.** Solo si pide expresamente combinar los
  dos tipos (por ejemplo, sacar un Reel de un vídeo de Refugio del Sueño), y solo para ese
  encargo.

`instagram/` es la carpeta de datos de las skills `ig-*`, en la raíz del repo: `voice.md`
(la voz de la cuenta), y `swipe.md`, `plan.md` y `log.md` cuando las skills los escriben.
Las skills `ig-*` vienen de https://github.com/Jakeschincariol/instagram-agent-skill (MIT,
licencia en `.claude/skills/INSTAGRAM-AGENT-LICENSE`).
