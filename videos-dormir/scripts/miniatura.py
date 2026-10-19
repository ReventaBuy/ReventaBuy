"""Miniatura de YouTube (1280x720) a partir de un fotograma del fondo, más clara y con texto grande.

    VIDEO=02 python3 scripts/miniatura.py   -> output/<vídeo>/miniatura.png
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fondo  # noqa: E402
import proyecto  # noqa: E402

OUT = proyecto.OUT
FUENTE = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
FUENTE_FINA = "/usr/share/fonts/opentype/inter/InterDisplay-Medium.otf"
CREMA, AMBAR = (246, 236, 214), (255, 184, 92)


def texto_con_sombra(img, xy, texto, fuente, color, sombra=18):
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(capa).text(xy, texto, font=fuente, fill=(0, 0, 0, 200))
    img.alpha_composite(capa.filter(ImageFilter.GaussianBlur(sombra)))
    ImageDraw.Draw(img).text(xy, texto, font=fuente, fill=color)


if __name__ == "__main__":
    escena = fondo.cargar_escena()
    x = escena.fotograma(proyecto.CONF.get("frame_miniatura", int(fondo.N * 0.3))).astype(np.float32) / 255
    # más luz y contraste para que se lea en pequeño (en el vídeo se mantiene oscuro)
    x = np.clip(x * 1.25, 0, 1) ** 0.62
    img = Image.fromarray((x * 255).astype(np.uint8)).resize((1280, 720), Image.LANCZOS).convert("RGBA")
    grande = ImageFont.truetype(FUENTE, 118)
    medio = ImageFont.truetype(FUENTE_FINA, 44)
    linea1, linea2, subtitulo = proyecto.CONF["miniatura"]
    y0 = proyecto.CONF.get("texto_y", 52)  # altura del bloque de texto
    texto_con_sombra(img, (64, y0), linea1, grande, CREMA)
    texto_con_sombra(img, (64, y0 + 120), linea2, grande, AMBAR)
    texto_con_sombra(img, (70, y0 + 268), subtitulo, medio, CREMA, 10)
    img.convert("RGB").save(OUT / "miniatura.png")
    print("ok", OUT / "miniatura.png")
