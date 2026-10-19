"""Fondo animado del vídeo 02: la casa del farero junto al mar, de noche.

Cielo despejado con estrellas que titilan, luna con su reflejo en el agua, olas que avanzan
hacia la orilla, un faro que gira despacio y la casa con la ventana encendida.
Todo lo que se mueve tiene un número entero de ciclos por bucle (ver fondo.py).
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from fondo import H, N, W, col, desplazar, ruido_tileable, smooth

rng = np.random.default_rng(5)
HORIZONTE = 600
LUNA = (1000, 200)
LAMPARA = (1500, 277)  # linterna del faro
GIROS_FARO = 6  # vueltas por bucle de 2 min: una cada 20 s

CIELO_ARRIBA, CIELO_HORIZONTE = col(0.02, 0.03, 0.07), col(0.12, 0.15, 0.23)
MAR_LEJOS, MAR_CERCA = col(0.075, 0.095, 0.155), col(0.012, 0.018, 0.032)
TIERRA_LEJOS, ACANTILADO, ROCAS = col(0.05, 0.065, 0.10), col(0.024, 0.03, 0.048), col(0.01, 0.014, 0.024)
PARED, TEJADO = col(0.15, 0.17, 0.23), col(0.05, 0.06, 0.09)
TORRE, BANDA = col(0.17, 0.18, 0.23), col(0.07, 0.08, 0.11)
VENTANA, LUZ_FARO = col(1.0, 0.62, 0.26), col(1.0, 0.93, 0.75)
LUZ_LUNA, NUBE, NUBE_LUNA = col(0.80, 0.85, 0.95), col(0.09, 0.11, 0.16), col(0.30, 0.33, 0.42)
SS = 2  # supermuestreo para siluetas suaves


def mascara(dibujar):
    img = Image.new("L", (W * SS, H * SS), 0)
    dibujar(ImageDraw.Draw(img), lambda pts: [(x * SS, y * SS) for x, y in pts])
    return np.asarray(img.resize((W, H), Image.LANCZOS), np.float32) / 255


def capa_estrellas(k_grupos=6, n=420):
    """Varias capas de estrellas; cada capa titila con su propio ritmo."""
    capas = np.zeros((k_grupos, HORIZONTE, W), np.float32)
    yy, xx = np.mgrid[-3:4, -3:4]
    for _ in range(n):
        x, y = rng.uniform(4, W - 4), rng.uniform(4, HORIZONTE - 30) ** 1.0
        if np.hypot(x - LUNA[0], y - LUNA[1]) < 110:
            continue
        b = (0.12 + 0.88 * rng.random() ** 3) * smooth(HORIZONTE - 20, HORIZONTE - 200, y)
        s = rng.uniform(0.55, 1.1)
        xi, yi = int(x), int(y)
        g = np.exp(-(((xx - (x - xi)) ** 2 + (yy - (y - yi)) ** 2) / (2 * s * s)))
        capas[rng.integers(k_grupos), yi - 3:yi + 4, xi - 3:xi + 4] += b * g
    ritmos = [(int(c), rng.uniform(0, 2 * np.pi)) for c in rng.integers(10, 40, k_grupos)]
    return capas, ritmos


def escena_estatica():
    Y, X = np.mgrid[0:H, 0:W].astype(np.float32)
    yy = Y[:, :1] / H
    img = np.zeros((H, W, 3), np.float32)
    t = np.clip(Y[:HORIZONTE, :1] / HORIZONTE, 0, 1)[..., None] ** 1.5
    img[:HORIZONTE] = CIELO_ARRIBA + (CIELO_HORIZONTE - CIELO_ARRIBA) * t
    d = (Y[HORIZONTE:, :1] - HORIZONTE)[..., None] / (H - HORIZONTE)
    img[HORIZONTE:] = MAR_LEJOS + (MAR_CERCA - MAR_LEJOS) * np.clip(d * 1.6, 0, 1) ** 0.7

    dist = np.hypot(X - LUNA[0], Y - LUNA[1])
    textura = 1 - 0.16 * smooth(0.2, 1.2, ruido_tileable(H, W, 2.4, semilla=51))
    luna = (smooth(40, 35, dist) * 0.72 * textura + np.exp(-dist / 70) * 0.10 + np.exp(-dist / 320) * 0.08) * (Y < HORIZONTE)

    # tierra: cabo lejano a la izquierda, acantilado a la derecha, rocas delante
    def cabo(dw, p):
        dw.polygon(p([(0, HORIZONTE + 2), (0, 556), (70, 546), (150, 552), (240, 566), (330, 584), (420, HORIZONTE + 2)]), fill=255)
    borde = [(1290, 664), (1318, 600), (1345, 560), (1372, 525), (1398, 494), (1428, 474)]
    meseta = [(1428 + i * 40, 468 - 6 * np.sin(i / 2.0) - i * 0.6) for i in range(13)]

    orilla = [(1920, 455), (1920, 690), (1800, 684), (1700, 677), (1600, 672), (1500, 668), (1400, 666), (1296, 663)]

    def acantilado(dw, p):
        dw.polygon(p([(1290, 664), (1300, 640)] + borde[1:] + meseta + orilla), fill=255)

    def rocas(dw, p):
        dw.polygon(p([(0, H), (0, 962), (70, 944), (140, 958), (210, 978), (300, 992), (390, 1018), (470, 1046), (520, H)]), fill=255)
        dw.polygon(p([(1920, H), (1920, 975), (1850, 985), (1770, 1006), (1700, 1036), (1650, H)]), fill=255)

    m_cabo, m_acant, m_rocas = mascara(cabo), mascara(acantilado), mascara(rocas)
    # luz de luna en la cara izquierda del acantilado
    borde_x = np.argmax(m_acant > 0.5, axis=1).astype(np.float32)[:, None]
    brillo_acant = np.exp(-np.maximum(X - borde_x, 0) / 70) * 0.05 + 0.012 * ruido_tileable(H, W, 1.6, semilla=52)
    xs = np.array([x for x, _ in orilla[1:]][::-1], np.float32)
    ys = np.array([y for _, y in orilla[1:]][::-1], np.float32)
    agua_y = np.interp(np.arange(W), xs, ys)[None, :]
    espuma = (np.exp(-((Y - agua_y - 2) / 3.5) ** 2) * (X > 1292)).astype(np.float32)

    # faro (torre con dos bandas, galería, linterna) y casa del farero
    lx, ly = LAMPARA

    def torre(dw, p):
        dw.polygon(p([(lx - 25, 472), (lx - 17, 300), (lx + 17, 300), (lx + 25, 472)]), fill=255)

    def bandas(dw, p):
        for y0, y1 in ((330, 350), (400, 420)):
            w0, w1 = 17 + 8 * (y0 - 300) / 172, 17 + 8 * (y1 - 300) / 172
            dw.polygon(p([(lx - w0, y0), (lx + w0, y0), (lx + w1, y1), (lx - w1, y1)]), fill=255)

    def remate(dw, p):
        dw.rectangle(p([(lx - 27, 292), (lx + 27, 300)]), fill=255)  # galería
        dw.rectangle(p([(lx - 15, 262), (lx - 12, 292)]), fill=255)
        dw.rectangle(p([(lx + 12, 262), (lx + 15, 292)]), fill=255)
        dw.polygon(p([(lx - 19, 263), (lx, 242), (lx + 19, 263)]), fill=255)  # cúpula

    def linterna(dw, p):
        dw.rectangle(p([(lx - 12, 264), (lx + 12, 292)]), fill=255)

    cx = 1715

    def paredes(dw, p):
        dw.rectangle(p([(cx - 75, 398), (cx + 75, 466)]), fill=255)

    def tejado(dw, p):
        dw.polygon(p([(cx - 92, 401), (cx, 344), (cx + 92, 401)]), fill=255)
        dw.rectangle(p([(cx + 40, 350), (cx + 56, 384)]), fill=255)  # chimenea

    ventanas_pts = [(cx - 55, 418, cx - 27, 444), (cx + 27, 418, cx + 55, 444)]

    def ventanas(dw, p):
        for x0, y0, x1, y1 in ventanas_pts:
            dw.rectangle(p([(x0, y0), (x1, y1)]), fill=255)

    m_vent = mascara(ventanas)
    for x0, y0, x1, y1 in ventanas_pts:  # cruz del marco
        m_vent[(y0 + y1) // 2 - 1:(y0 + y1) // 2 + 1, x0:x1 + 1] *= 0.15
        m_vent[y0:y1 + 1, (x0 + x1) // 2 - 1:(x0 + x1) // 2 + 1] *= 0.15
    vent_img = Image.fromarray((m_vent * 255).astype(np.uint8))
    m_lint = mascara(linterna)
    lint_img = Image.fromarray((m_lint * 255).astype(np.uint8))

    capas_tierra = [(m_cabo, TIERRA_LEJOS), (m_acant, ACANTILADO), (mascara(torre), TORRE), (mascara(bandas), BANDA),
                    (mascara(remate), BANDA), (mascara(paredes), PARED), (mascara(tejado), TEJADO), (m_rocas, ROCAS)]

    # haz del faro: dos conos estáticos (izquierda y derecha); en cada fotograma se ilumina uno según el giro
    dx, dy = X - lx, Y - ly
    ang = np.abs(np.arctan2(dy - np.abs(dx) * 0.035, np.abs(dx) + 1e-3))
    cono = np.exp(-(ang / 0.045) ** 2) * np.exp(-np.abs(dx) / 750) * smooth(10, 60, np.abs(dx))
    haz_izq, haz_der = (cono * (dx < 0)).astype(np.float32), (cono * (dx > 0)).astype(np.float32)
    destello = np.exp(-np.hypot(dx, dy) / 26).astype(np.float32)

    estrellas, ritmos = capa_estrellas()
    viñeta = (1 - 0.42 * smooth(0.45, 1.25, np.hypot((X - W / 2) / (W / 2), (Y - H / 2) / (H / 2))))[..., None]
    dither = (rng.random((H, W, 1), np.float32) - rng.random((H, W, 1), np.float32)) / 255
    return dict(base=img, luna=luna.astype(np.float32), capas=capas_tierra, brillo_acant=brillo_acant, m_acant=m_acant,
                vent=m_vent, glow=np.asarray(vent_img.filter(ImageFilter.GaussianBlur(24)), np.float32) / 255,
                glow2=np.asarray(vent_img.filter(ImageFilter.GaussianBlur(80)), np.float32) / 255,
                lint=m_lint, lint_glow=np.asarray(lint_img.filter(ImageFilter.GaussianBlur(14)), np.float32) / 255,
                haz_izq=haz_izq, haz_der=haz_der, destello=destello, espuma=espuma,
                estrellas=estrellas, ritmos=ritmos, viñeta=viñeta, dither=dither)


def preparar_dinamico():
    d = np.arange(H - HORIZONTE, dtype=np.float32) + 1.0
    K, d0 = 87480.0, 60.0
    s = K / (d + d0)  # distancia sobre el agua de cada fila (perspectiva)
    dsdy = K / (d + d0) ** 2
    olas = []
    for lam, ciclos, amp in ((90, 4, 1.0), (53, 5, 0.8), (31, 7, 0.6), (18, 10, 0.45)):
        f = dsdy / lam  # ciclos por píxel en pantalla: se apagan antes de llegar a Nyquist
        a = amp * smooth(0.32, 0.12, f)
        curva = ruido_tileable(8, W, 1.5, semilla=int(lam))[0] * 2.6  # ondula y rompe las crestas
        olas.append((2 * np.pi * s / lam, ciclos, a, curva, rng.uniform(0, 2 * np.pi)))
    manchas = 0.4 + 0.6 * smooth(-1.3, 1.3, ruido_tileable(H - HORIZONTE, W, 1.9, estirar=3.0, semilla=41))
    fino = smooth(-0.3, 1.1, ruido_tileable(H - HORIZONTE, W, 1.2, estirar=6.0, semilla=43))
    nubes = ruido_tileable(H, W, 2.2, estirar=3.0, semilla=42)
    luz_vent = [(rng.uniform(0.02, 0.04), int(c), rng.uniform(0, 6.28)) for c in (60, 97, 157)]
    return dict(olas=olas, manchas=manchas, fino=fino, d=d, nubes=nubes, luz_vent=luz_vent)


ESTATICA = DINAMICA = None


def init():
    global ESTATICA, DINAMICA
    ESTATICA, DINAMICA = escena_estatica(), preparar_dinamico()


def fotograma(i):
    e, dn = ESTATICA, DINAMICA
    fase = i / N
    img = e["base"].copy()
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]

    # estrellas que titilan y nubes finas que pasan despacio
    brillo = sum(capa * (1 + 0.35 * np.sin(2 * np.pi * c * fase + p)) for capa, (c, p) in zip(e["estrellas"], e["ritmos"]))
    n = desplazar(dn["nubes"], fase * W)
    dens = smooth(0.7, 2.0, n) * smooth(0.06, 0.18, yy) * (1 - smooth(0.42, 0.54, yy)) * 0.55
    img[:HORIZONTE] += (brillo * (1 - dens[:HORIZONTE]))[..., None] * col(0.85, 0.88, 1.0)
    img += (e["luna"] * (1 - 0.7 * dens))[..., None] * LUZ_LUNA
    c_nube = NUBE + (NUBE_LUNA - NUBE) * np.exp(-np.hypot(np.arange(W) - LUNA[0], (yy * H) - LUNA[1]) / 300)[..., None]
    img = img * (1 - dens[..., None]) + c_nube * dens[..., None]

    # mar: olas que avanzan hacia la orilla, más brillo cerca del horizonte y camino de luna
    h = np.zeros((H - HORIZONTE, W), np.float32)
    total = 0
    for fila, ciclos, a, curva, fi in dn["olas"]:
        h += a[:, None] * np.sin(fila[:, None] + curva[None, :] + fi - 2 * np.pi * ciclos * fase)
        total += a
    h = h / np.maximum(total, 1e-3)[:, None] * desplazar(dn["manchas"], fase * W)
    d = dn["d"][:, None]
    reflejo = 0.10 * smooth(0, 0.9, h) * np.exp(-d / 260) + 0.05 * smooth(0, 0.9, h)
    ancho = 22 + 0.6 * d
    camino = np.exp(-((np.arange(W)[None, :] - LUNA[0]) / ancho) ** 2)
    destellos = camino * (0.10 + 1.6 * smooth(0.12, 0.7, h) * dn["fino"]) * (0.45 + 0.55 * np.exp(-d / 220))
    img[HORIZONTE:] += (reflejo[..., None] * col(0.55, 0.62, 0.78) + destellos[..., None] * LUZ_LUNA)

    for m, c in e["capas"]:
        img = img * (1 - m[..., None]) + c * m[..., None]
    img += (e["brillo_acant"] * e["m_acant"])[..., None] * LUZ_LUNA
    vaiven = 0.5 + 0.5 * np.sin(2 * np.pi * 10 * fase - np.arange(W) / 55.0)
    img += (e["espuma"] * (0.05 + 0.11 * vaiven[None, :]))[..., None] * LUZ_LUNA

    # casa: luz de lámpara con un parpadeo muy leve
    f = 1 + sum(a * np.sin(2 * np.pi * c * fase + p) for a, c, p in dn["luz_vent"])
    img += (e["vent"] * f * 0.95)[..., None] * VENTANA * (1 - img)
    img += (e["glow"] * 0.34 * f + e["glow2"] * 0.12 * f)[..., None] * VENTANA

    # faro: el haz barre a un lado y a otro; destello cuando mira hacia nosotros
    th = 2 * np.pi * GIROS_FARO * fase
    s_izq, s_der, frente = max(-np.sin(th), 0), max(np.sin(th), 0), max(np.cos(th), 0)
    img += (e["haz_izq"] * 0.13 * s_izq ** 1.3 + e["haz_der"] * 0.13 * s_der ** 1.3)[..., None] * LUZ_FARO
    img += (e["lint"] * (0.40 + 0.35 * frente) + e["lint_glow"] * 0.30)[..., None] * LUZ_FARO * (1 - img)
    img += (e["destello"] * 0.55 * frente ** 6)[..., None] * LUZ_FARO

    img = img * e["viñeta"] + e["dither"]
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
