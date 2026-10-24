"""Configuración de cada vídeo del canal.

Se elige el vídeo con la variable de entorno VIDEO (por defecto "01"):

    VIDEO=02 python3 scripts/montaje.py

    videos/<id>/   guion.txt y youtube.md (van a git)
    output/<id>/   audio y vídeo generados (fuera de git)
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOZ_JHENNY = "D9MdulIxfrCUUJcGNQon"  # ElevenLabs: Jhenny — latina, suave, meditativa

VIDEOS = {
    "01": dict(
        escena="fondo",  # módulo del fondo animado: cabaña bajo la lluvia
        ambiente="lluvia",
        # Re mayor: Dmaj7 – Bm7 – Gmaj7 – Asus2 (números MIDI; bajo + acorde abierto)
        acordes=[[38, 50, 54, 57, 61], [35, 47, 50, 54, 57], [31, 43, 50, 54, 59], [33, 45, 47, 52, 57]],
        voz=VOZ_JHENNY,
        capitulo_final="Lluvia para dormir (sin voz)",
        miniatura=("¿NO PUEDES", "DORMIR?", "Relajación guiada · 3 h de lluvia"),
        archivo="Meditacion_guiada_para_dormir_3h",
    ),
    "02": dict(
        escena="fondo_mar",  # casa del farero junto al mar, de noche
        ambiente="mar",
        # Fa mayor: Fmaj7 – Dm7 – Bbmaj7 – Csus2
        acordes=[[41, 48, 52, 57, 60], [38, 50, 53, 57, 60], [34, 46, 50, 53, 57], [36, 48, 50, 55, 60]],
        voz=VOZ_JHENNY,
        capitulo_final="Olas del mar para dormir (sin voz)",
        miniatura=("¿TU MENTE", "NO PARA?", "Meditación para la ansiedad · 3 h de olas"),
        frame_miniatura=360,  # el haz del faro barre hacia el mar
        texto_y=330,  # texto sobre el mar, para no tapar la luna
        archivo="Meditacion_para_dormir_con_ansiedad_3h",
    ),
    "03": dict(
        escena="fondo_nieve",  # cabaña nevada con chimenea, de noche
        ambiente="chimenea",
        # La menor: Am9 – Fmaj7 – Cmaj7 – G6
        acordes=[[33, 45, 52, 55, 59], [29, 41, 48, 52, 57], [36, 48, 52, 55, 59], [31, 43, 50, 55, 57]],
        voz=VOZ_JHENNY,
        capitulo_final="Chimenea y nieve para dormir (sin voz)",
        miniatura=("UNA HISTORIA", "PARA DORMIR", "La cabaña en la nieve · 3 h de chimenea"),
        archivo="Historia_para_dormir_la_cabana_en_la_nieve_3h",
        oscurecer_min=24,  # la imagen se oscurece antes de que acabe la voz (cabe en < 400 MB)
    ),
}

ID = os.environ.get("VIDEO", "01")
CONF = VIDEOS[ID]
DIR = ROOT / "videos" / ID
OUT = ROOT / "output" / ID
