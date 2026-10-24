"""Fondo animado del vídeo 04: una ventana iluminada en una noche de lluvia, con un gato dormido dentro.

Vista desde fuera: pared de tablas mojada, ventana de cuatro cristales con luz cálida, cortinas, una lámpara
y una estantería; un gato dormido en el alféizar interior que mueve la cola despacio; gotas en el cristal
(algunas resbalan) y lluvia que brilla al pasar por delante de la luz.
Todo lo que se mueve tiene un número entero de ciclos por bucle (ver fondo.py).

Variable de entorno LLUVIA: "1" lluvia normal (por defecto), "suave" llovizna, "amainando" pasa de una a otra
a lo largo del bucle (para la parte oscura del vídeo, que así pesa mucho menos).
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from fondo import H, N, W, col, ruido_tileable, smooth

rng = np.random.default_rng(41)
# geometría de la ventana (marco exterior y cristal)
MX0, MX1, MY0, MY1 = 1010, 1690, 200, 840
GX0, GX1, GY0, GY1 = 1038, 1662, 228, 812
MULL_X, MULL_Y = 1350, 520
LAMPARA = (1170, 420)

PARED, PARED_LUZ = col(0.055, 0.07, 0.095), col(1.0, 0.62, 0.32)
INTERIOR, INTERIOR_LUZ = col(0.30, 0.17, 0.10), col(1.0, 0.74, 0.46)
CORTINA, MARCO, GATO = col(0.36, 0.12, 0.08), col(0.62, 0.58, 0.52), col(0.025, 0.02, 0.025)
LLUVIA_FRIA, LLUVIA_CALIDA = col(0.35, 0.42, 0.55), col(1.0, 0.75, 0.48)
SS = 2


def silueta(dibujar, tam=(W, H)):
    img = Image.new("L", (tam[0] * SS, tam[1] * SS), 0)
    dibujar(ImageDraw.Draw(img), lambda pts: [(x * SS, y * SS) for x, y in pts])
    return np.asarray(img.resize(tam, Image.LANCZOS), np.float32) / 255


def cola(fase):
    """Puntos de la cola: sale de la grupa, recorre el alféizar y la punta sube y baja despacio."""
    sube = 0.5 - 0.5 * np.cos(2 * np.pi * 3 * fase)  # 3 movimientos por bucle (uno cada 40 s)
    u = np.linspace(0, 1, 24)
    xs = 1300 + 130 * u - 10 * np.sin(np.pi * u)
    ys = 802 - 4 * np.sin(np.pi * u) - (8 + 30 * sube) * u ** 3
    return list(zip(xs, ys)), 15 - 7 * u


def escena_estatica():
    Y, X = np.mgrid[0:H, 0:W].astype(np.float32)
    # pared de tablas horizontales, cada una con su tono, su veta y una junta oscura
    tabla = 46
    fila = (Y // tabla).astype(int)
    tono = 1 + 0.10 * rng.standard_normal(fila.max() + 2)[fila]
    dentro = (Y % tabla) / tabla
    veta = 1 + 0.05 * ruido_tileable(H, W, 1.4, estirar=0.08, semilla=81)
    pared = PARED * (tono * veta * (1.05 - 0.18 * dentro) * (1 - 0.55 * smooth(0.9, 1.0, dentro)))[..., None]

    # luz cálida que sale de la ventana y baña la pared (y la lluvia de delante)
    cx, cy = (MX0 + MX1) / 2, (MY0 + MY1) / 2
    dx = np.maximum(np.abs(X - cx) - (MX1 - MX0) / 2, 0)
    dy = np.maximum(np.abs(Y - cy) - (MY1 - MY0) / 2, 0)
    luz = (np.exp(-np.hypot(dx, dy * 1.3) / 170) * 0.55 + np.exp(-np.hypot(dx, dy) / 520) * 0.25).astype(np.float32)
    luz += (np.exp(-np.hypot(X - cx, Y - (MY1 + 60)) / 260) * 0.25 * (Y > MY1)).astype(np.float32)  # más luz bajo el alféizar

    # interior: pared cálida, lámpara, estantería con libros y cortinas
    d_l = np.hypot(X - LAMPARA[0], Y - LAMPARA[1])
    interior = INTERIOR + (INTERIOR_LUZ - INTERIOR) * (np.exp(-d_l / 380) * 0.95)[..., None]
    interior += (np.exp(-d_l / 40) * 0.6 + np.exp(-d_l / 110) * 0.25)[..., None] * col(1.0, 0.85, 0.6)
    pantalla = silueta(lambda d, p: d.polygon(p([(LAMPARA[0] - 46, 392), (LAMPARA[0] + 46, 392), (LAMPARA[0] + 64, 448), (LAMPARA[0] - 64, 448)]), fill=255))
    interior = interior * (1 - pantalla[..., None]) + col(1.0, 0.86, 0.62) * pantalla[..., None]
    pie = silueta(lambda d, p: d.rectangle(p([(LAMPARA[0] - 4, 448), (LAMPARA[0] + 4, 690)]), fill=255))
    interior = interior * (1 - pie[..., None] * 0.85) + col(0.12, 0.07, 0.05) * pie[..., None] * 0.85

    def libros(d, p):
        x = 1430
        d.rectangle(p([(1415, 452), (1615, 462)]), fill=255)  # balda
        while x < 1600:
            ancho, alto = rng.uniform(12, 22), rng.uniform(46, 78)
            d.rectangle(p([(x, 452 - alto), (x + ancho, 452)]), fill=255)
            x += ancho + rng.uniform(1, 4)
    m_libros = silueta(libros)
    interior = interior * (1 - m_libros[..., None]) + (col(0.16, 0.07, 0.05) + 0.1 * INTERIOR_LUZ) * m_libros[..., None]

    def cortinas(d, p):
        recoge = lambda t: 92 - 62 * smooth(0.25, 0.7, t) + 12 * smooth(0.85, 1.0, t)  # recogidas a media altura
        izq = [(GX0, GY0)] + [(GX0 + recoge(t), GY0 + t * (GY1 - GY0)) for t in np.linspace(0, 1, 40)] + [(GX0, GY1)]
        der = [(GX1, GY0)] + [(GX1 - recoge(t), GY0 + t * (GY1 - GY0)) for t in np.linspace(0, 1, 40)] + [(GX1, GY1)]
        d.polygon(p(izq), fill=255)
        d.polygon(p(der), fill=255)
    m_cort = silueta(cortinas)
    pliegues = 0.75 + 0.25 * np.sin(X / 7.0) * np.sin(X / 23.0 + 1)
    c_cort = CORTINA * (pliegues * (0.6 + 0.8 * np.exp(-d_l / 500)))[..., None]
    interior = interior * (1 - m_cort[..., None]) + c_cort * m_cort[..., None]

    # el gato (cuerpo, cabeza y orejas); la cola se dibuja en cada fotograma
    def gato(d, p):  # tumbado, mirando hacia la lámpara
        d.ellipse(p([(1120, 712), (1300, 808)]), fill=255)   # cuerpo
        d.ellipse(p([(1210, 700), (1318, 806)]), fill=255)   # grupa
        d.ellipse(p([(1088, 700), (1162, 806)]), fill=255)   # pecho
        d.ellipse(p([(1062, 668), (1142, 744)]), fill=255)   # cabeza
        d.polygon(p([(1134, 690), (1126, 648), (1102, 676)]), fill=255)  # oreja
        d.polygon(p([(1096, 674), (1074, 646), (1066, 690)]), fill=255)  # oreja
    m_gato = silueta(gato)
    # alféizar interior donde está tumbado
    m_alf_int = silueta(lambda d, p: d.rectangle(p([(GX0, 806), (GX1, GY1)]), fill=255))
    interior = interior * (1 - m_alf_int[..., None]) + col(0.38, 0.24, 0.15) * m_alf_int[..., None]

    # cristal: tono frío muy leve y reflejo del cielo arriba
    vidrio = np.zeros((H, W), np.float32)
    vidrio[GY0:GY1, GX0:GX1] = 1
    reflejo = (0.07 * np.clip(1 - (Y - GY0) / 300, 0, 1) * vidrio).astype(np.float32)

    # gotas fijas en el cristal (pequeñas lentes: borde oscuro y un brillo)
    gotas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dg = ImageDraw.Draw(gotas)
    for _ in range(750):
        x, y, r = rng.uniform(GX0, GX1), rng.uniform(GY0, GY1), rng.uniform(1.0, 3.8) ** 1.1
        dg.ellipse([x - r, y - r, x + r, y + r * 1.15], fill=(10, 8, 12, 70))
        dg.ellipse([x - r * 0.45, y + r * 0.1, x + r * 0.35, y + r * 0.7], fill=(255, 230, 200, 120))
    gotas = gotas.filter(ImageFilter.GaussianBlur(0.5))

    # marco blanco con travesaños y alféizar exterior
    def marco(d, p):
        d.rectangle(p([(MX0, MY0), (MX1, GY0)]), fill=255)
        d.rectangle(p([(MX0, GY1), (MX1, MY1)]), fill=255)
        d.rectangle(p([(MX0, MY0), (GX0, MY1)]), fill=255)
        d.rectangle(p([(GX1, MY0), (MX1, MY1)]), fill=255)
        d.rectangle(p([(MULL_X - 9, GY0), (MULL_X + 9, GY1)]), fill=255)
        d.rectangle(p([(GX0, MULL_Y - 9), (GX1, MULL_Y + 9)]), fill=255)
        d.rectangle(p([(MX0 - 24, MY1), (MX1 + 24, MY1 + 30)]), fill=255)  # alféizar exterior
    m_marco = silueta(marco)
    sombra_alf = np.clip((Y - (MY1 + 22)) / 8, 0, 1) * (Y < MY1 + 31)  # canto inferior del alféizar, más oscuro
    c_marco = MARCO * (0.35 + 0.9 * luz + 0.25 * np.exp(-np.minimum(np.abs(X - GX0), np.abs(X - GX1)) / 10))[..., None]
    c_marco *= (1 - 0.5 * sombra_alf)[..., None]

    # maceta con una planta en el alféizar exterior
    px = 1622  # centro de la maceta, en el extremo derecho del alféizar exterior
    def maceta(d, p):
        d.polygon(p([(px - 30, 796), (px + 30, 796), (px + 23, 840), (px - 23, 840)]), fill=255)
        d.rectangle(p([(px - 34, 790), (px + 34, 800)]), fill=255)
    def hojas(d, p):
        for ang, largo in zip(np.linspace(-1.1, 1.1, 11), rng.uniform(50, 95, 11)):
            t = np.linspace(0, 1, 16)
            curva = ang + 0.35 * np.sign(ang) * t  # las hojas se arquean hacia fuera
            cx_, cy_ = px + np.cumsum(np.sin(curva)) * largo / 16, 792 - np.cumsum(np.cos(curva)) * largo / 16
            ancho = 7 * np.sin(np.pi * t) + 1
            izq = [(x - w * np.cos(c), y - w * np.sin(c)) for x, y, w, c in zip(cx_, cy_, ancho, curva)]
            der = [(x + w * np.cos(c), y + w * np.sin(c)) for x, y, w, c in zip(cx_, cy_, ancho, curva)]
            d.polygon(p(izq + der[::-1]), fill=255)
    m_maceta, m_hojas = silueta(maceta), silueta(hojas)

    viñeta = (1 - 0.5 * smooth(0.35, 1.2, np.hypot((X - 1250) / (W / 2), (Y - H / 2) / (H / 2))))[..., None]
    dither = (rng.random((H, W, 1), np.float32) - rng.random((H, W, 1), np.float32)) / 255
    return dict(pared=pared.astype(np.float32), luz=luz, interior=interior.astype(np.float32), m_gato=m_gato,
                vidrio=vidrio, reflejo=reflejo, gotas=np.asarray(gotas, np.float32) / 255, m_marco=m_marco,
                c_marco=c_marco.astype(np.float32), m_maceta=m_maceta, m_hojas=m_hojas, d_l=d_l.astype(np.float32),
                viñeta=viñeta, dither=dither)


def preparar_dinamico():
    n = 520
    lluvia = dict(x=rng.uniform(0, W, n), y=rng.uniform(0, H, n), largo=rng.uniform(22, 60, n),
                  vueltas=rng.integers(70, 100, n), alfa=rng.uniform(0.25, 0.6, n))
    m = 26  # gotas que resbalan por el cristal
    resbalan = dict(x=rng.uniform(GX0 + 10, GX1 - 10, m), y0=rng.uniform(GY0, GY0 + 200, m),
                    ciclos=rng.integers(1, 4, m), fase=rng.random(m), r=rng.uniform(3, 5.5, m))
    return dict(lluvia=lluvia, resbalan=resbalan)


ESTATICA = DINAMICA = None


def init():
    global ESTATICA, DINAMICA
    ESTATICA, DINAMICA = escena_estatica(), preparar_dinamico()


def fotograma(i):
    e, dn = ESTATICA, DINAMICA
    fase = i / N

    # interior con el gato y su cola
    # la luz es eléctrica y estable: un parpadeo global obligaría a recomprimir media imagen en cada fotograma
    inter = e["interior"].copy()
    gx0, gy0, gx1, gy1 = 1040, 630, 1480, 830  # zona del gato y su cola
    cola_pts, grosor = cola(fase)
    capa = Image.new("L", ((gx1 - gx0) * SS, (gy1 - gy0) * SS), 0)
    dc = ImageDraw.Draw(capa)
    for (x0, y0), (x1, y1), g in zip(cola_pts[:-1], cola_pts[1:], grosor):
        dc.line([((x0 - gx0) * SS, (y0 - gy0) * SS), ((x1 - gx0) * SS, (y1 - gy0) * SS)], fill=255, width=int(g * SS))
        dc.ellipse([(x1 - gx0 - g / 2) * SS, (y1 - gy0 - g / 2) * SS, (x1 - gx0 + g / 2) * SS, (y1 - gy0 + g / 2) * SS], fill=255)
    m = np.maximum(e["m_gato"][gy0:gy1, gx0:gx1], np.asarray(capa.resize((gx1 - gx0, gy1 - gy0), Image.LANCZOS), np.float32) / 255)
    zona = inter[gy0:gy1, gx0:gx1] * (1 - m[..., None]) + GATO * m[..., None]
    borde = np.clip(m - np.roll(np.roll(m, 3, axis=0), 2, axis=1), 0, 1)
    inter[gy0:gy1, gx0:gx1] = zona + (borde * 0.45)[..., None] * col(1.0, 0.7, 0.4)

    # cristal: interior + reflejo + gotas fijas + gotas que resbalan con su rastro
    v = e["vidrio"][..., None]
    img = e["pared"] * (1 - v) + inter * col(0.94, 0.96, 1.0) * v
    img += e["reflejo"][..., None] * col(0.5, 0.6, 0.8)
    g = e["gotas"]
    img = img * (1 - g[..., 3:]) + g[..., :3] * g[..., 3:]
    r = dn["resbalan"]
    capa = Image.new("RGBA", (GX1 - GX0, GY1 - GY0), (0, 0, 0, 0))
    dr = ImageDraw.Draw(capa)
    for x, y0, c, ph, rad in zip(r["x"] - GX0, r["y0"] - GY0, r["ciclos"], r["fase"], r["r"]):
        u = (c * fase + ph) % 1.0
        y = y0 + u * (GY1 - GY0 - y0)
        dr.line([(x, y0), (x, y - rad)], fill=(255, 220, 180, 34), width=2)  # rastro: el cristal queda más limpio
        dr.ellipse([x - rad, y - rad * 1.2, x + rad, y + rad * 1.2], fill=(15, 10, 12, 90))
        dr.ellipse([x - rad * 0.4, y, x + rad * 0.35, y + rad * 0.8], fill=(255, 235, 210, 150))
    gd = np.asarray(capa.filter(ImageFilter.GaussianBlur(0.6)), np.float32) / 255
    zona = img[GY0:GY1, GX0:GX1]
    img[GY0:GY1, GX0:GX1] = zona * (1 - gd[..., 3:]) + gd[..., :3] * gd[..., 3:]

    # luz sobre la pared, marco, maceta
    img += e["luz"][..., None] * PARED_LUZ * 0.22 * (1 - v)
    m = e["m_marco"][..., None]
    img = img * (1 - m) + e["c_marco"] * m
    for mk, c in ((e["m_maceta"], col(0.30, 0.13, 0.08) * 0.6), (e["m_hojas"], col(0.05, 0.12, 0.07))):
        img = img * (1 - mk[..., None]) + c * mk[..., None]

    # lluvia: brilla cálida al pasar por delante de la luz de la ventana
    capa = Image.new("L", (W, H), 0)
    dl = ImageDraw.Draw(capa)
    ll = dn["lluvia"]
    modo = os.environ.get("LLUVIA", "1")
    cantidad = {"1": 1.0, "suave": 0.2}.get(modo, 1 - 0.8 * float(smooth(0.05, 0.9, fase)))
    k = int(len(ll["x"]) * 0.5 * cantidad)  # la lluvia dibujada es lo que más pesa al comprimir
    ys = (ll["y"][:k] + fase * ll["vueltas"][:k] * (H + 80)) % (H + 80) - 80
    xs = (ll["x"][:k] + ys * 0.10) % W
    for x, y, lg, al in zip(xs, ys, ll["largo"][:k], ll["alfa"][:k]):
        if e["luz"][int(np.clip(y + lg / 2, 0, H - 1)), int(np.clip(x, 0, W - 1))] < 0.15:
            continue  # lejos de la luz no se vería: no se dibuja (y el vídeo pesa mucho menos)
        dl.line([(x, y), (x + lg * 0.10, y + lg)], fill=int(al * 255), width=1)
    a = np.asarray(capa.filter(ImageFilter.GaussianBlur(0.9)), np.float32) / 255 * 1.6  # trazos suaves, como de noche
    brillo = 0.05 + 1.3 * e["luz"]
    c_ll = LLUVIA_FRIA * 0.4 + LLUVIA_CALIDA * e["luz"][..., None] * 1.3
    img = img * (1 - (a * np.minimum(brillo, 1))[..., None]) + c_ll * (a * brillo)[..., None]

    img = img * e["viñeta"] + e["dither"]
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
