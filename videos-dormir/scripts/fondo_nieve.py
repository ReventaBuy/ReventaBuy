"""Fondo animado del vídeo 03: cabaña nevada con la chimenea encendida, de noche.

Cielo de invierno con estrellas y luna creciente, montañas y pinos nevados, humo que sale de la
chimenea, la ventana con el fuego titilando y su luz sobre la nieve, y copos cayendo despacio.
Todo lo que se mueve tiene un número entero de ciclos por bucle (ver fondo.py).

Variable de entorno NIEVE: "1" nieva (por defecto), "0" no nieva, "parando" deja de nevar a lo largo del bucle.
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from fondo import H, N, W, capa_pinos, col, desplazar, mascara_bajo, perfil, ruido_tileable, smooth

rng = np.random.default_rng(23)
LUNA = (1560, 170)
CX = 820  # centro de la cabaña

CIELO_ARRIBA, CIELO_HORIZONTE = col(0.02, 0.03, 0.075), col(0.11, 0.13, 0.20)
MONTE_LEJOS, MONTE_CERCA = col(0.19, 0.22, 0.30), col(0.12, 0.145, 0.205)
ARBOLES_FONDO, ARBOLES_DELANTE = col(0.035, 0.045, 0.07), col(0.012, 0.016, 0.026)
NIEVE, NIEVE_BRILLO = col(0.16, 0.18, 0.25), col(0.62, 0.68, 0.80)
MADERA, TEJADO, PIEDRA = col(0.07, 0.05, 0.045), col(0.40, 0.44, 0.54), col(0.09, 0.09, 0.11)
VENTANA, HUMO, COPO = col(1.0, 0.60, 0.24), col(0.30, 0.32, 0.38), col(0.86, 0.89, 0.96)
NUBE, NUBE_LUNA = col(0.09, 0.105, 0.15), col(0.30, 0.33, 0.42)


def bordes_arriba(m, grosor=4):
    """Bordes de una silueta que miran hacia arriba: ahí se acumula la nieve."""
    sombra = np.roll(m, grosor, axis=0)
    sombra[:grosor] = 0
    b = np.clip(m - sombra, 0, 1)
    return np.asarray(Image.fromarray((b * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255


def estrellas(n=240, grupos=5):
    capas = np.zeros((grupos, 640, W), np.float32)
    yy, xx = np.mgrid[-3:4, -3:4]
    for _ in range(n):
        x, y = rng.uniform(4, W - 4), rng.uniform(4, 600)
        if np.hypot(x - LUNA[0], y - LUNA[1]) < 110:
            continue
        b = (0.10 + 0.8 * rng.random() ** 3) * smooth(600, 380, y)
        s = rng.uniform(0.55, 1.0)
        xi, yi = int(x), int(y)
        capas[rng.integers(grupos), yi - 3:yi + 4, xi - 3:xi + 4] += b * np.exp(-(((xx - (x - xi)) ** 2 + (yy - (y - yi)) ** 2) / (2 * s * s)))
    return capas, [(int(c), rng.uniform(0, 2 * np.pi)) for c in rng.integers(10, 40, grupos)]


def escena_estatica():
    Y, X = np.mgrid[0:H, 0:W].astype(np.float32)
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    cielo = np.broadcast_to(CIELO_ARRIBA + (CIELO_HORIZONTE - CIELO_ARRIBA) * yy ** 1.5, (H, W, 3)).copy()

    # luna creciente con halo
    d1 = np.hypot(X - LUNA[0], Y - LUNA[1])
    d2 = np.hypot(X - (LUNA[0] - 22), Y - (LUNA[1] - 14))
    luna = smooth(48, 45, d1) * smooth(42, 46, d2) * 0.85 + np.exp(-d1 / 75) * 0.07 + np.exp(-d1 / 330) * 0.06
    luz_luna = np.exp(-d1 / 600).astype(np.float32)

    m_lejos = mascara_bajo(perfil(W, 640, 260, 31, 1.9))
    m_cerca = mascara_bajo(perfil(W, 770, 190, 33, 1.8))
    colina = 905 - 70 * np.exp(-((np.arange(W) - CX) / 560.0) ** 2) - 18 * np.sin(np.arange(W) / 310.0)
    fondo_pinos = [(x, colina[int(np.clip(x, 0, W - 1))] + rng.uniform(-6, 30), rng.uniform(60, 140), rng.uniform(26, 44))
                   for x in np.sort(rng.uniform(-40, W + 40, 120)) if abs(x - CX) > 110]
    m_fondo, _, _ = capa_pinos(fondo_pinos)
    delante = [(-10, 1100, 760, 230), (120, 1110, 620, 190), (260, 1130, 420, 150),
               (1700, 1110, 720, 220), (1860, 1100, 820, 250), (1540, 1140, 430, 150)]
    m_delante, _, _ = capa_pinos(delante)

    ss = 2
    def silueta(dibujar):
        img = Image.new("L", (W * ss, H * ss), 0)
        dibujar(ImageDraw.Draw(img), lambda pts: [(x * ss, y * ss) for x, y in pts])
        return np.asarray(img.resize((W, H), Image.LANCZOS), np.float32) / 255

    m_colina = silueta(lambda d, p: d.polygon(p([(0, colina[0])] + [(x, colina[x]) for x in range(0, W, 8)] + [(W, colina[-1]), (W, H), (0, H)]), fill=255))
    cy = int(colina[CX]) + 4
    m_paredes = silueta(lambda d, p: d.rectangle(p([(CX - 80, cy - 74), (CX + 80, cy)]), fill=255))
    m_tejado = silueta(lambda d, p: d.polygon(p([(CX - 100, cy - 68), (CX, cy - 138), (CX + 100, cy - 68)]), fill=255))
    m_chimenea = silueta(lambda d, p: d.rectangle(p([(CX + 36, cy - 140), (CX + 54, cy - 98)]), fill=255))
    chimenea_top = (CX + 45, cy - 142)

    ventanas = [(CX - 58, cy - 54, CX - 26, cy - 24), (CX + 22, cy - 54, CX + 54, cy - 24)]
    vent = Image.new("L", (W, H), 0)
    dv = ImageDraw.Draw(vent)
    for v in ventanas:
        dv.rectangle(v, fill=255)
    vent_m = np.asarray(vent, np.float32) / 255
    for x0, y0, x1, y1 in ventanas:
        vent_m[(y0 + y1) // 2 - 1:(y0 + y1) // 2 + 1, x0:x1 + 1] *= 0.15
        vent_m[y0:y1 + 1, (x0 + x1) // 2 - 1:(x0 + x1) // 2 + 1] *= 0.15
    glow = np.asarray(vent.filter(ImageFilter.GaussianBlur(26)), np.float32) / 255
    glow2 = np.asarray(vent.filter(ImageFilter.GaussianBlur(90)), np.float32) / 255
    # luz cálida de las ventanas sobre la nieve, delante de la cabaña
    charco = np.exp(-(((X - CX) / 190) ** 2 + ((Y - (cy + 40)) / 45) ** 2)) * (Y > cy)

    # nieve del suelo: algo más clara arriba de la colina, con una textura suave
    tex = 1 + 0.06 * ruido_tileable(H, W, 1.8, estirar=0.4, semilla=61)
    suelo = (NIEVE * (1.15 - 0.45 * np.clip((Y - colina[None, :]) / 220, 0, 1))[..., None] * tex[..., None]).astype(np.float32)

    capas = [(m_lejos, MONTE_LEJOS), (m_cerca, MONTE_CERCA)]
    nieve_bordes = [bordes_arriba(m_lejos, 5) * 0.35, bordes_arriba(m_cerca, 5) * 0.4]
    frente = [(m_fondo, ARBOLES_FONDO, bordes_arriba(m_fondo, 3) * 0.5)]
    delante_capa = (m_delante, ARBOLES_DELANTE, bordes_arriba(m_delante, 4) * 0.45)

    # humo: penacho que sube desde la chimenea y se inclina un poco hacia la derecha
    alto = np.clip(chimenea_top[1] - Y, 0, None)
    centro = chimenea_top[0] + 0.28 * alto
    ancho = 8 + 0.32 * alto
    penacho = (np.exp(-((X - centro) / ancho) ** 2) * np.exp(-alto / 300) * smooth(0, 25, alto)).astype(np.float32)

    estr, ritmos = estrellas()
    viñeta = (1 - 0.42 * smooth(0.45, 1.25, np.hypot((X - W / 2) / (W / 2), (Y - H / 2) / (H / 2))))[..., None]
    dither = (rng.random((H, W, 1), np.float32) - rng.random((H, W, 1), np.float32)) / 255
    return dict(cielo=cielo, luna=luna.astype(np.float32), luz_luna=luz_luna, capas=capas, nieve_bordes=nieve_bordes,
                frente=frente, delante=delante_capa, colina=m_colina, suelo=suelo, paredes=m_paredes, tejado=m_tejado,
                chimenea=m_chimenea, vent=vent_m, glow=glow, glow2=glow2, charco=charco.astype(np.float32),
                penacho=penacho, estrellas=estr, ritmos=ritmos, viñeta=viñeta, dither=dither)


def preparar_dinamico():
    nubes = ruido_tileable(H, W, 2.1, estirar=2.4, semilla=71)
    humo = ruido_tileable(H, W, 1.9, estirar=0.6, semilla=72)
    n = 650
    z = rng.random(n) ** 1.3  # profundidad: casi todos los copos están lejos y son pequeños
    copos = dict(x=rng.uniform(0, W, n), y=rng.uniform(0, H + 40, n), z=z,
                 vueltas=(2 + np.floor(z * 5)).astype(int), radio=0.7 + 2.6 * z ** 1.5,
                 vaiven=6 + 24 * z, ciclos=rng.integers(3, 10, n), fase=rng.uniform(0, 2 * np.pi, n), alfa=0.30 + 0.6 * z)
    fuego = [(rng.uniform(0.04, 0.08), int(c), rng.uniform(0, 6.28)) for c in (150, 233, 377, 610, 987)]
    return dict(nubes=nubes, humo=humo, copos=copos, fuego=fuego)


ESTATICA = DINAMICA = None


def init():
    global ESTATICA, DINAMICA
    ESTATICA, DINAMICA = escena_estatica(), preparar_dinamico()


def capa_copos(c, fase, sel, desenfoque):
    capa = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(capa)
    ys = (c["y"][sel] + fase * c["vueltas"][sel] * (H + 40)) % (H + 40) - 20
    xs = c["x"][sel] + c["vaiven"][sel] * np.sin(2 * np.pi * c["ciclos"][sel] * fase + c["fase"][sel])
    for x, y, r, a in zip(xs, ys, c["radio"][sel], c["alfa"][sel]):
        d.ellipse([x - r, y - r, x + r, y + r], fill=int(a * 255))
    if desenfoque:
        capa = capa.filter(ImageFilter.GaussianBlur(desenfoque))
    return (np.asarray(capa, np.float32) / 255)[..., None]


def fotograma(i):
    e, dn = ESTATICA, DINAMICA
    fase = i / N
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    img = e["cielo"].copy()

    # estrellas y luna, tapadas a ratos por nubes finas
    n = desplazar(dn["nubes"], fase * W)
    dens = smooth(0.2, 1.6, n) * (1 - smooth(0.38, 0.6, yy)) * 0.7
    brillo = sum(cp * (1 + 0.35 * np.sin(2 * np.pi * c * fase + p)) for cp, (c, p) in zip(e["estrellas"], e["ritmos"]))
    img[:640] += (brillo * (1 - dens[:640]))[..., None] * col(0.85, 0.88, 1.0)
    img += (e["luna"] * (1 - 0.75 * dens))[..., None] * col(0.92, 0.90, 0.82)
    c_nube = NUBE + (NUBE_LUNA - NUBE) * e["luz_luna"][..., None]
    img = img * (1 - dens[..., None]) + c_nube * dens[..., None]

    # montañas nevadas
    for (m, c), nb in zip(e["capas"], e["nieve_bordes"]):
        img = img * (1 - m[..., None]) + c * m[..., None]
        img += nb[..., None] * NIEVE_BRILLO * 0.5
    for m, c, nb in e["frente"]:
        img = img * (1 - m[..., None]) + c * m[..., None]
        img = img * (1 - nb[..., None]) + NIEVE_BRILLO * 0.55 * nb[..., None]
    # suelo nevado, cabaña y su luz
    m = e["colina"][..., None]
    img = img * (1 - m) + e["suelo"] * m
    f = 1 + sum(a * np.sin(2 * np.pi * c * fase + p) for a, c, p in dn["fuego"])
    img += (e["charco"] * 0.22 * f)[..., None] * VENTANA * m
    for mk, c in ((e["paredes"], MADERA), (e["tejado"], TEJADO), (e["chimenea"], PIEDRA)):
        img = img * (1 - mk[..., None]) + c * mk[..., None]

    # humo que sube despacio (la textura sube una altura de pantalla por bucle)
    t = e["penacho"]
    hm = np.roll(dn["humo"], int(round(fase * H)), axis=0)
    a_humo = (t * smooth(-0.9, 1.0, -hm) * 0.6)[..., None]
    img = img * (1 - a_humo) + (HUMO + 0.25 * e["luz_luna"][..., None] * NUBE_LUNA) * a_humo

    img += (e["vent"] * f * 0.95)[..., None] * VENTANA * (1 - img)
    img += (e["glow"] * 0.38 * f + e["glow2"] * 0.15 * f)[..., None] * VENTANA

    md, cd, nbd = e["delante"]
    img = img * (1 - md[..., None]) + cd * md[..., None]
    img = img * (1 - nbd[..., None]) + NIEVE_BRILLO * 0.5 * nbd[..., None]

    # copos: lejanos pequeños y nítidos, cercanos grandes y desenfocados
    modo = os.environ.get("NIEVE", "1")
    cantidad = {"1": 1.0, "0": 0.0}.get(modo, 1 - float(smooth(0.05, 0.9, fase)))  # "parando": deja de nevar
    c = dn["copos"]
    for sel, des in ((c["z"] < 0.6, 0.6), (c["z"] >= 0.6, 1.6)):
        if cantidad > 0:
            a = capa_copos(c, fase, sel, des) * cantidad
            img = img * (1 - a) + COPO * a

    img = img * e["viñeta"] + e["dither"]
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
