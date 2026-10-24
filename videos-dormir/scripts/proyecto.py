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
        miniatura_impacto=dict(recorte=(60, 400, 940, 895), texto_ancho=620, frame=864, calidez=0.6,
                               variantes=[("A", ["¿NO PUEDES", "DORMIR?"], "relajación guiada · lluvia")]),
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
        miniatura_impacto=dict(recorte=(520, 60, 1920, 848), texto_ancho=560, frame=360, calidez=0.6,
                               texto_centro_y=480,  # sobre el mar, para no tapar la luna
                               variantes=[("A", ["¿TU MENTE", "NO PARA?"], "meditación para la ansiedad")]),
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
        miniatura_impacto=dict(
            recorte=(240, 400, 1120, 895), texto_ancho=620, frame=864, calidez=0.6,
            variantes=[("A", ["UNA HISTORIA", "PARA DORMIR"], "la cabaña en la nieve"),
                       ("B", ["UNA NOCHE", "DE NIEVE"], "historia para dormir · voz suave"),
                       ("C", ["NIEVA.", "TÚ DUERMES."], "historia para dormir · chimenea")]),
        archivo="Historia_para_dormir_la_cabana_en_la_nieve_3h",
        bucle_transicion="fondo_parando.mp4",  # al acabar la historia deja de nevar poco a poco…
        bucle_oscuro="fondo_sin_nieve.mp4",  # …y el resto de la noche está en calma (pesa mucho menos)
        crf_claro=28, audio_kbps=112,  # la nieve cayendo pesa mucho: así cabe en < 400 MB
    ),
    "04": dict(
        escena="fondo_ventana",  # ventana iluminada bajo la lluvia, con un gato en el alféizar
        ambiente="lluvia_ventana",
        # Mi mayor: Emaj7 – C#m7 – Amaj7 – Bsus2
        acordes=[[40, 47, 51, 56, 59], [37, 49, 52, 56, 59], [33, 45, 52, 56, 61], [35, 47, 49, 54, 59]],
        voz=VOZ_JHENNY,
        capitulo_final="Lluvia para dormir (sin voz)",
        miniatura_impacto=dict(
            recorte=(481, 182, 1741, 891), texto_ancho=470, frame=300,
            variantes=[("A", ["CIERRA", "LOS OJOS"], "y escucha la lluvia"),
                       ("B", ["TU CUERPO", "PESA…"], "relajación profunda · voz suave"),
                       ("C", ["DUERME", "YA."], "con la lluvia en la ventana")]),
        archivo="Relajacion_profunda_para_dormir_lluvia_en_la_ventana_3h",
        bucle_transicion="fondo_amainando.mp4",  # al acabar la voz, la lluvia visible amaina (el sonido sigue)…
        bucle_oscuro="fondo_suave.mp4",  # …y en la parte oscura queda una llovizna ligera (pesa mucho menos)
        crf_claro=28, crf_oscuro=34, audio_kbps=112,  # la lluvia en movimiento pesa mucho: así cabe en < 400 MB
    ),
}

ID = os.environ.get("VIDEO", "01")
CONF = VIDEOS[ID]
DIR = ROOT / "videos" / ID
OUT = ROOT / "output" / ID
