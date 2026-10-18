"""Foto de perfil del canal (800x800): la cabaña con la ventana encendida bajo la luna y la lluvia.

Todo lo importante cabe en el círculo central, que es lo que YouTube muestra.

    python3 scripts/avatar.py   -> output/avatar.png
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parent.parent / "output"
S = 1600  # se dibuja al doble y se reduce para suavizar bordes
CREMA, AMBAR = (243, 231, 204), (255, 184, 92)
SILUETA, COLINA = (8, 12, 22), (14, 20, 34)


def degradado():
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32) / S
    d = np.hypot(xx - 0.62, yy - 0.30)
    t = np.clip(d / 0.85, 0, 1)[..., None]
    centro, borde = np.array([38, 52, 86], np.float32), np.array([7, 11, 22], np.float32)
    return Image.fromarray((centro * (1 - t) + borde * t).astype(np.uint8))


def pino(d, x, base, alto, ancho, color):
    niveles = 7
    for i in range(niveles):
        f0, f1 = i / niveles, (i + 1) / niveles
        y0 = base - alto + f0 * alto * 0.9
        y1 = base - alto + f1 * alto * 0.9 + alto * 0.08
        w = ancho * (0.25 + 0.75 * f1)
        d.polygon([(x, y0), (x - w / 2, y1), (x + w / 2, y1)], fill=color)
    d.rectangle([x - ancho * 0.05, base - alto * 0.1, x + ancho * 0.05, base], fill=color)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    img = degradado().convert("RGBA")

    # luna creciente con halo
    halo = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse([980, 260, 1260, 540], fill=(200, 210, 235, 90))
    img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(70)))
    luna = Image.new("L", (S, S), 0)
    dl = ImageDraw.Draw(luna)
    dl.ellipse([1010, 290, 1230, 510], fill=255)
    dl.ellipse([940, 250, 1150, 460], fill=0)
    img.paste(Image.new("RGBA", (S, S), CREMA + (255,)), (0, 0), luna)

    # lluvia fina
    lluvia = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(lluvia)
    rng = np.random.default_rng(3)
    for _ in range(140):
        x, y, l = rng.uniform(0, S), rng.uniform(0, S * 0.8), rng.uniform(40, 90)
        dr.line([(x, y), (x + l * 0.1, y + l)], fill=(170, 185, 215, int(rng.uniform(40, 90))), width=3)
    img.alpha_composite(lluvia)

    d = ImageDraw.Draw(img)
    # colina
    d.ellipse([-500, 1080, 2100, 2300], fill=COLINA)
    # pinos a los lados de la cabaña
    for x, base, alto, ancho in [(380, 1190, 430, 190), (300, 1230, 300, 140), (1230, 1190, 470, 200), (1340, 1240, 320, 150)]:
        pino(d, x, base, alto, ancho, SILUETA)
    # cabaña
    cx, base = 800, 1150
    d.rectangle([cx - 230, base - 230, cx + 230, base + 40], fill=SILUETA)
    d.polygon([(cx - 290, base - 215), (cx, base - 430), (cx + 290, base - 215)], fill=SILUETA)
    d.rectangle([cx + 110, base - 420, cx + 160, base - 300], fill=SILUETA)

    # ventanas cálidas con resplandor
    ventanas = [(cx - 160, base - 160, cx - 60, base - 60), (cx + 60, base - 160, cx + 160, base - 60)]
    brillo = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    db = ImageDraw.Draw(brillo)
    for v in ventanas:
        db.rectangle(v, fill=AMBAR + (255,))
    img.alpha_composite(brillo.filter(ImageFilter.GaussianBlur(60)))
    img.alpha_composite(brillo.filter(ImageFilter.GaussianBlur(18)))
    d = ImageDraw.Draw(img)
    for x0, y0, x1, y1 in ventanas:
        d.rectangle([x0, y0, x1, y1], fill=(255, 205, 130))
        mx, my = (x0 + x1) // 2, (y0 + y1) // 2
        d.rectangle([mx - 5, y0, mx + 5, y1], fill=SILUETA)
        d.rectangle([x0, my - 5, x1, my + 5], fill=SILUETA)

    img.convert("RGB").resize((800, 800), Image.LANCZOS).save(OUT / "avatar.png")
    # vista previa recortada en círculo, como se verá en YouTube
    m = Image.new("L", (800, 800), 0)
    ImageDraw.Draw(m).ellipse([0, 0, 799, 799], fill=255)
    prev = Image.new("RGB", (800, 800), (255, 255, 255))
    prev.paste(Image.open(OUT / "avatar.png"), (0, 0), m)
    prev.save(OUT / "_avatar_circulo.png")
    print("ok", OUT / "avatar.png")
