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


FUENTES = Path(__file__).resolve().parent.parent / "fuentes"


def estilo_impacto(frame, conf):
    """Miniatura pensada para destacar entre otras: foco grande, contraste cálido/frío y texto enorme.

    conf: recorte=(x0, y0, x1, y1) sobre el fotograma 1920x1080 (16:9), texto_ancho=px disponibles a la izquierda,
          variantes=[(nombre, [línea1, línea2], subtítulo), ...]. Guarda miniatura.png y miniatura_<nombre>.png.
    """
    x0, y0, x1, y1 = conf["recorte"]
    base = Image.fromarray(frame).crop((x0, y0, x1, y1)).resize((1280, 720), Image.LANCZOS)
    x = np.asarray(base, np.float32) / 255
    lum = (x @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
    x = lum + (x - lum) * 1.3                                   # colores más vivos
    x = np.clip(x * 1.15, 0, 1) ** 0.8                           # más luz sin quemar la ventana
    x += np.array([0.0, 0.025, 0.06], np.float32) * (1 - lum) ** 3  # sombras azuladas: contraste con el naranja
    calido = np.clip((x[..., :1] - x[..., 2:]) * 4, 0, 1)        # zonas de luz cálida (ventanas, reflejos)
    x += calido * x * conf.get("calidez", 0.0)
    u = np.linspace(0, 1, 1280, dtype=np.float32)[None, :, None]
    frio = 1 - np.clip((u - 0.30) / 0.12, 0, 1)                   # zona del texto: noche azul, no marrón
    x = x * (1 - 0.6 * frio) + (x @ np.array([0.2, 0.3, 0.5], np.float32))[..., None] * np.array([0.55, 0.8, 1.6], np.float32) * 0.6 * frio
    x *= 0.6 + 0.4 * np.clip((u - 0.18) / 0.3, 0, 1)             # y algo más oscura para que el texto resalte
    fondo_img = Image.fromarray((np.clip(x, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
    negra = str(FUENTES / "Poppins-Black.ttf")
    semi = str(FUENTES / "Poppins-SemiBold.ttf")
    ancho = conf.get("texto_ancho", 480)
    for k, (nombre, lineas, sub) in enumerate(conf["variantes"]):
        img = fondo_img.copy()
        tam = 160
        while max(ImageFont.truetype(negra, tam).getbbox(l)[2] for l in lineas) > ancho and tam > 60:
            tam -= 2
        f = ImageFont.truetype(negra, tam)
        alto_linea = int(tam * 1.02)
        y = 360 - (alto_linea * len(lineas) + 70) // 2
        for j, linea in enumerate(lineas):
            color = (255, 250, 240) if j == 0 else (255, 188, 96)
            sombra = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(sombra).text((52, y + 6), linea, font=f, fill=(0, 0, 0, 230))
            img.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(14)))
            ImageDraw.Draw(img).text((48, y), linea, font=f, fill=color, stroke_width=4, stroke_fill=(18, 12, 20))
            y += alto_linea
        fs = ImageFont.truetype(semi, 38)
        while fs.getbbox(sub)[2] > ancho - 20 and fs.size > 24:
            fs = ImageFont.truetype(semi, fs.size - 2)
        texto_con_sombra(img, (52, y + 14), sub, fs, CREMA, 8)
        img = img.convert("RGB")
        img.save(OUT / f"miniatura_{nombre}.png")
        if k == 0:
            img.save(OUT / "miniatura.png")
        print("ok", OUT / f"miniatura_{nombre}.png", f"(texto {tam}px)")


if __name__ == "__main__":
    escena = fondo.cargar_escena()
    if "miniatura_impacto" in proyecto.CONF:
        conf = proyecto.CONF["miniatura_impacto"]
        estilo_impacto(escena.fotograma(conf.get("frame", 300)), conf)
        sys.exit()
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
