# Refugio del Sueño — vídeos para dormir

Cada vídeo del canal tiene su carpeta en `videos/<id>/` (guion y ficha de YouTube) y su
configuración en `scripts/proyecto.py` (escena, sonido ambiente, acordes, textos de la miniatura).
Lo generado va a `output/<id>/` y no se sube a git.

| Vídeo | Tema | Escena | Sonido |
|---|---|---|---|
| 01 | Relajación guiada para el insomnio | Cabaña en el bosque bajo la lluvia | Lluvia |
| 02 | Meditación para dormir con ansiedad | Casa del farero junto al mar | Olas |
| 03 | Historia para dormir: La cabaña en la nieve | Cabaña nevada con humo en la chimenea | Chimenea y viento |
| 04 | Relajación profunda: lluvia en la ventana | Ventana iluminada con un gato, bajo la lluvia | Lluvia en la ventana |
| 05 | Método militar para dormir (guiado) | Barca con farol en un lago de noche | Lago nocturno con grillos |

## Hacer un vídeo

Requisitos: `pip install scipy pyloudnorm requests` y la clave de ElevenLabs en `ELEVENLABS_API_KEY`.

```bash
export VIDEO=02
python3 scripts/guion.py               # estima la duración del guion
python3 scripts/tts.py completo        # voz (ElevenLabs, voz Jhenny) -> output/02/voz.wav
python3 scripts/ambiente.py            # sonido ambiente + música en bucle
python3 scripts/fondo.py frame 600     # un fotograma para revisar la escena
python3 scripts/fondo.py video         # bucle animado de 2 min (~10 min de render)
python3 scripts/miniatura.py           # miniatura 1280x720
python3 scripts/montaje.py 3           # vídeo final de 3 h en HEVC (~350 MB)
```

Para un vídeo nuevo: añade su entrada en `scripts/proyecto.py`, escribe `videos/<id>/guion.txt`
y, si quieres otra escena, crea `scripts/fondo_<nombre>.py` con `init()` y `fotograma(i)`.

## Indicaciones del dueño del canal (para los próximos vídeos)

- **Libertad completa**: tema, guion, escena y sonido los decide Claude, sin preguntar.
- **La voz y el guion son lo más importante.** Los guiones deben tener calidad de psicólogo del sueño:
  cada frase pensada para relajar y facilitar dormir cuanto antes. Seguir siempre `GUIA_GUION.md`
  y pasar su lista de revisión antes de generar la voz.
- **Voz**: se puede elegir otra voz de ElevenLabs o ir cambiándola de vez en cuando. Se pueden probar
  varias (gastando algunos créditos en muestras) y quedarse con la mejor (`scripts/casting.py`).
  Casting del vídeo 05 (mismo fragmento): **Jhenny** (`D9MdulIxfrCUUJcGNQon`) es la que más relaja
  (la más pausada, tono más estable, más cálida, menos eses) → voz principal del canal. Mejor voz
  masculina: **Juan Carlos** (`RyfjEHnKbtma4Srae2za`), grave y cálida → para una serie de historias.
  Descartadas: Tatiana (muy melódica), Martin Alvarez y Diego Cárdenas (rápidas y con eses marcadas).
- **Audio, lo más importante**: ni el fondo puede tapar la voz ni la voz al fondo. Revisar siempre
  `output/<id>/informe_mezcla.txt` (objetivo: voz 10–14 dB sobre el fondo, peor 10 % > 7 dB;
  fondo en las pausas entre −6 y −10 dB; frases igualadas). Comprobar sonidos nuevos con espectrograma
  (sin tonos fijos ni arranques bruscos) antes de usarlos.
- **Miniatura**: tiene que ganar entre 10 vídeos. Estilo "impacto" (`miniatura_impacto` en proyecto.py):
  foco grande, contraste cálido/frío, texto enorme y corto; generar 3 variantes para la prueba A/B.
- **Entrega**: el dueño trabaja desde el iPhone. El vídeo final debe pesar < 400 MiB (límite para
  enviarlo) y se entrega en .zip; además, una versión ligera (H.264, ~50 MB) para verlo en el chat.
  Mejor ≤ 380 MB: en el iPhone el .zip del vídeo 4 (409 MB) no se descargaba y desde el PC sí; los de 315–360 MB
  sí bajaron en el móvil.
  Cuidado con lo que pesa al comprimir: la lluvia o nieve dibujadas y los parpadeos globales disparan el tamaño.
- **Publicación**: máximo un vídeo al día; ritmo recomendado 2–3 por semana, a las 19:00 (hora de España).
