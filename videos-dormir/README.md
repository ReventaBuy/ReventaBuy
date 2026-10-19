# Refugio del Sueño — vídeos para dormir

Cada vídeo del canal tiene su carpeta en `videos/<id>/` (guion y ficha de YouTube) y su
configuración en `scripts/proyecto.py` (escena, sonido ambiente, acordes, textos de la miniatura).
Lo generado va a `output/<id>/` y no se sube a git.

| Vídeo | Tema | Escena | Sonido |
|---|---|---|---|
| 01 | Relajación guiada para el insomnio | Cabaña en el bosque bajo la lluvia | Lluvia |
| 02 | Meditación para dormir con ansiedad | Casa del farero junto al mar | Olas |

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
