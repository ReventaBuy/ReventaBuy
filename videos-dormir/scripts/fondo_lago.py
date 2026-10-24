"""Fondo animado del vídeo 05: una barca con un farol en un lago en calma, de noche.

Cielo con estrellas y luna creciente, montañas y orilla con pinos y una cabaña encendida a lo lejos,
agua con ondas suaves y reflejos, una barca de madera que se mece con su farol, juncos y luciérnagas.
Pensado para comprimir bien: los movimientos son lentos y locales (nada cambia de brillo en toda la imagen).
Todo lo que se mueve tiene un número entero de ciclos por bucle (ver fondo.py).
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from fondo import H, N, W, capa_pinos, col, desplazar, mascara_bajo, perfil, ruido_tileable, smooth

rng = np.random.default_rng(55)
HORIZONTE = 585
LUNA = (1500, 165)
BARCA = (1330, 800)  # centro de la línea de flotación
CABANA = (560, 568)
SS = 2

CIELO_ARRIBA, CIELO_HORIZONTE = col(0.02, 0.03, 0.075), col(0.10, 0.13, 0.20)
MONTE_LEJOS, MONTE_CERCA = col(0.08, 0.10, 0.155), col(0.05, 0.065, 0.10)
ORILLA = col(0.018, 0.024, 0.04)
AGUA_LEJOS, AGUA_CERCA = col(0.06, 0.08, 0.13), col(0.012, 0.018, 0.032)
MADERA, MADERA_LUZ, MANTA = col(0.05, 0.032, 0.022), col(0.34, 0.19, 0.09), col(0.17, 0.06, 0.05)
FAROL, LUZ_LUNA, JUNCO = col(1.0, 0.72, 0.36), col(0.82, 0.86, 0.95), col(0.012, 0.016, 0.022)


def silueta(dibujar, tam=(W, H)):
    img = Image.new("L", (tam[0] * SS, tam[1] * SS), 0)
    dibujar(ImageDraw.Draw(img), lambda pts: [(x * SS, y * SS) for x, y in pts])
    return np.asarray(img.resize(tam, Image.LANCZOS), np.float32) / 255


def sprite_barca():
    """La barca (casco, manta, mástil y farol) en un recuadro propio: RGBA y posición del farol."""
    bw, bh = 520, 260
    cx, cy = bw / 2, 190  # línea de flotación dentro del recuadro
    casco = Image.new("L", (bw * SS, bh * SS), 0)
    d = ImageDraw.Draw(casco)
    t = np.linspace(-1, 1, 60)
    borda = [(cx + 230 * u, cy - 38 - 26 * u ** 4) for u in t]           # borde superior, sube en proa y popa
    fondo_ = [(cx + 230 * u * (1 - 0.18 * (1 - u ** 2)), cy + 18 - 10 * u ** 4) for u in t[::-1]]
    d.polygon([(x * SS, y * SS) for x, y in borda + fondo_], fill=255)
    m_casco = np.asarray(casco.resize((bw, bh), Image.LANCZOS), np.float32) / 255
    manta = Image.new("L", (bw * SS, bh * SS), 0)
    ImageDraw.Draw(manta).ellipse([(cx - 120) * SS, (cy - 70) * SS, (cx + 70) * SS, (cy - 22) * SS], fill=255)
    m_manta = np.asarray(manta.resize((bw, bh), Image.LANCZOS), np.float32) / 255 * (1 - m_casco)
    mastil = Image.new("L", (bw * SS, bh * SS), 0)
    dm = ImageDraw.Draw(mastil)
    fx, fy = cx + 175, cy - 150  # farol
    dm.line([((cx + 175) * SS, (cy - 60) * SS), (fx * SS, (fy + 12) * SS)], fill=255, width=4 * SS)
    dm.rectangle([(fx - 12) * SS, (fy - 16) * SS, (fx + 12) * SS, (fy + 14) * SS], fill=255)
    m_mastil = np.asarray(mastil.resize((bw, bh), Image.LANCZOS), np.float32) / 255
    vidrio = silueta(lambda dd, p: dd.rectangle(p([(fx - 8, fy - 12), (fx + 8, fy + 10)]), fill=255), (bw, bh))
    yy = np.arange(bh, dtype=np.float32)[:, None]
    xx = np.arange(bw, dtype=np.float32)[None, :]
    luz = np.exp(-np.hypot(xx - fx, yy - fy) / 150)  # el farol ilumina la madera cercana
    sombra = 1 - 0.6 * np.clip((yy - (cy - 30)) / 45, 0, 1)  # el casco se oscurece hacia el agua
    rgb = (MADERA * (1 + 0.15 * np.sin(yy / 3.0))[..., None] + MADERA_LUZ * (luz * 0.8)[..., None]) * sombra[..., None]
    rgb = rgb * m_casco[..., None] + MANTA * (0.6 + 0.9 * luz)[..., None] * m_manta[..., None]
    rgb = rgb * (1 - m_mastil[..., None]) + col(0.05, 0.035, 0.03) * m_mastil[..., None]
    rgb = rgb * (1 - vidrio[..., None]) + FAROL * vidrio[..., None]
    alfa = np.clip(m_casco + m_manta + m_mastil, 0, 1)
    return np.dstack([rgb, alfa]).astype(np.float32), (fx, fy), (cx, cy)


def escena_estatica():
    Y, X = np.mgrid[0:H, 0:W].astype(np.float32)
    img = np.zeros((H, W, 3), np.float32)
    t = (Y[:HORIZONTE, :1] / HORIZONTE)[..., None] ** 1.5
    img[:HORIZONTE] = CIELO_ARRIBA + (CIELO_HORIZONTE - CIELO_ARRIBA) * t
    d = (Y[HORIZONTE:, :1] - HORIZONTE)[..., None] / (H - HORIZONTE)
    img[HORIZONTE:] = AGUA_LEJOS + (AGUA_CERCA - AGUA_LEJOS) * np.clip(d * 1.5, 0, 1) ** 0.7

    # luna creciente
    d1 = np.hypot(X - LUNA[0], Y - LUNA[1])
    d2 = np.hypot(X - (LUNA[0] - 20), Y - (LUNA[1] - 13))
    luna = (smooth(44, 41, d1) * smooth(38, 42, d2) * 0.85 + np.exp(-d1 / 70) * 0.07 + np.exp(-d1 / 320) * 0.06) * (Y < HORIZONTE)

    # estrellas en grupos que titilan
    grupos = 5
    estrellas = np.zeros((grupos, HORIZONTE, W), np.float32)
    yy, xx = np.mgrid[-3:4, -3:4]
    for _ in range(300):
        x, y = rng.uniform(4, W - 4), rng.uniform(4, HORIZONTE - 120)
        if np.hypot(x - LUNA[0], y - LUNA[1]) < 100:
            continue
        b = (0.10 + 0.8 * rng.random() ** 3) * smooth(HORIZONTE - 100, HORIZONTE - 300, y)
        xi, yi, s = int(x), int(y), rng.uniform(0.55, 1.0)
        estrellas[rng.integers(grupos), yi - 3:yi + 4, xi - 3:xi + 4] += b * np.exp(-(((xx - (x - xi)) ** 2 + (yy - (y - yi)) ** 2) / (2 * s * s)))
    ritmos = [(int(c), rng.uniform(0, 2 * np.pi)) for c in rng.integers(8, 30, grupos)]

    # montañas, orilla con pinos y cabaña lejana
    m_lejos = mascara_bajo(perfil(W, 540, 230, 61, 1.9))
    m_cerca = mascara_bajo(perfil(W, 572, 120, 62, 1.8))
    pinos = [(x, HORIZONTE + rng.uniform(-2, 4), rng.uniform(26, 62), rng.uniform(12, 22)) for x in np.sort(rng.uniform(-20, W + 20, 170))
             if abs(x - CABANA[0]) > 40]
    m_pinos, _, _ = capa_pinos(pinos)
    m_orilla = np.maximum(m_pinos, ((Y > HORIZONTE - 6) & (Y < HORIZONTE + 1)).astype(np.float32))
    cab = silueta(lambda dd, p: (dd.rectangle(p([(CABANA[0] - 22, CABANA[1] - 16), (CABANA[0] + 22, CABANA[1] + 12)]), fill=255),
                                 dd.polygon(p([(CABANA[0] - 28, CABANA[1] - 14), (CABANA[0], CABANA[1] - 34), (CABANA[0] + 28, CABANA[1] - 14)]), fill=255)))
    m_orilla = np.maximum(m_orilla, cab)
    vent = np.exp(-np.hypot(X - CABANA[0], Y - (CABANA[1] - 2)) / 3.5) * 0.9 + np.exp(-np.hypot(X - CABANA[0], Y - CABANA[1]) / 30) * 0.12
    # niebla baja sobre la orilla
    niebla = (np.exp(-((Y - (HORIZONTE - 8)) / 22) ** 2) * 0.10).astype(np.float32)

    # juncos en primer plano (izquierda): tallos que se mecen, se dibujan en cada fotograma
    juncos = [(rng.uniform(-10, 330), rng.uniform(1000, 1090), rng.uniform(150, 330), rng.uniform(2, 4.5), rng.uniform(0, 6.28))
              for _ in range(26)]
    barca, farol, linea = sprite_barca()
    viñeta = (1 - 0.45 * smooth(0.4, 1.25, np.hypot((X - W / 2) / (W / 2), (Y - H / 2) / (H / 2))))[..., None]
    dither = (rng.random((H, W, 1), np.float32) - rng.random((H, W, 1), np.float32)) / 255
    return dict(base=img, luna=luna.astype(np.float32), estrellas=estrellas, ritmos=ritmos,
                montes=[(m_lejos, MONTE_LEJOS), (m_cerca, MONTE_CERCA)], m_orilla=m_orilla, vent=vent.astype(np.float32),
                niebla=niebla, juncos=juncos, barca=barca, farol=farol, linea=linea, viñeta=viñeta, dither=dither)


def preparar_dinamico():
    d = np.arange(H - HORIZONTE, dtype=np.float32) + 1.0
    K, d0 = 87480.0, 60.0
    s = K / (d + d0)
    dsdy = K / (d + d0) ** 2
    olas = []
    for lam, ciclos, amp in ((110, 3, 1.0), (64, 4, 0.7), (38, 6, 0.45)):  # ondas largas y lentas: lago en calma
        f = dsdy / lam
        a = amp * smooth(0.32, 0.12, f)
        curva = ruido_tileable(8, W, 1.5, semilla=int(lam) + 7)[0] * 2.4
        olas.append((2 * np.pi * s / lam, ciclos, a, curva, rng.uniform(0, 2 * np.pi)))
    manchas = 0.45 + 0.55 * smooth(-1.3, 1.3, ruido_tileable(H - HORIZONTE, W, 1.9, estirar=3.0, semilla=91))
    fino = smooth(-0.3, 1.1, ruido_tileable(H - HORIZONTE, W, 1.2, estirar=6.0, semilla=92))
    luciernagas = dict(x=rng.uniform(40, 520, 12), y=rng.uniform(820, 1000, 12), ax=rng.uniform(10, 30, 12),
                       ay=rng.uniform(6, 16, 12), cx=rng.integers(1, 3, 12), cy=rng.integers(1, 4, 12),
                       parpadeo=rng.integers(5, 14, 12), fase=rng.uniform(0, 6.28, 12))
    farol = [(rng.uniform(0.03, 0.06), int(c), rng.uniform(0, 6.28)) for c in (233, 377, 610)]
    return dict(olas=olas, manchas=manchas, fino=fino, d=d, luciernagas=luciernagas, farol=farol)


ESTATICA = DINAMICA = None


def init():
    global ESTATICA, DINAMICA
    ESTATICA, DINAMICA = escena_estatica(), preparar_dinamico()


def fotograma(i):
    e, dn = ESTATICA, DINAMICA
    fase = i / N
    img = e["base"].copy()

    # cielo
    brillo = sum(cp * (1 + 0.35 * np.sin(2 * np.pi * c * fase + p)) for cp, (c, p) in zip(e["estrellas"], e["ritmos"]))
    img[:HORIZONTE] += brillo[..., None] * col(0.85, 0.88, 1.0)
    img += e["luna"][..., None] * col(0.92, 0.90, 0.82)
    for m, c in e["montes"]:
        img = img * (1 - m[..., None]) + c * m[..., None]

    # agua: ondas lentas, reflejo de la luna y de la orilla
    h = np.zeros((H - HORIZONTE, W), np.float32)
    total = 0
    for fila, ciclos, a, curva, fi in dn["olas"]:
        h += a[:, None] * np.sin(fila[:, None] + curva[None, :] + fi - 2 * np.pi * ciclos * fase)
        total += a
    h = h / np.maximum(total, 1e-3)[:, None] * desplazar(dn["manchas"], fase * W)
    d = dn["d"][:, None]
    agua = img[HORIZONTE:]
    agua += (0.04 * smooth(0, 0.9, h))[..., None] * col(0.55, 0.62, 0.78)
    camino = np.exp(-((np.arange(W)[None, :] - LUNA[0]) / (20 + 0.5 * d)) ** 2)
    agua += (camino * (0.08 + 1.3 * smooth(0.15, 0.75, h) * dn["fino"]) * (0.45 + 0.55 * np.exp(-d / 220)))[..., None] * LUZ_LUNA
    orilla_refl = np.exp(-d / 26)[..., None] * 0.7  # reflejo oscuro de la orilla junto al horizonte
    agua *= 1 - orilla_refl
    img[HORIZONTE:] = agua

    # orilla, cabaña y niebla
    m = e["m_orilla"][..., None]
    img = img * (1 - m) + ORILLA * m
    img += e["vent"][..., None] * col(1.0, 0.65, 0.3)
    img += e["niebla"][..., None] * col(0.35, 0.40, 0.50)

    # barca meciéndose (arriba y abajo, y un leve cabeceo) con su reflejo
    f = 1 + sum(a * np.sin(2 * np.pi * c * fase + p) for a, c, p in dn["farol"])  # llama del farol (solo local)
    dy = 3.0 * np.sin(2 * np.pi * 12 * fase) + 1.5 * np.sin(2 * np.pi * 19 * fase + 1)
    ang = 0.7 * np.sin(2 * np.pi * 12 * fase + 0.8)
    spr = Image.fromarray((np.clip(e["barca"], 0, 1) * 255).astype(np.uint8), "RGBA").rotate(ang, resample=Image.BICUBIC, center=e["linea"])
    s = np.asarray(spr, np.float32) / 255
    bh, bw = s.shape[:2]
    x0, y0 = int(BARCA[0] - e["linea"][0]), int(BARCA[1] - e["linea"][1] + dy)
    # reflejo: la barca invertida, oscura y ondulada por el agua
    refl = s[::-1].copy()
    ry0 = y0 + 2 * int(e["linea"][1]) - bh + 6
    for k in range(bh):
        desp = int(4 * np.sin(k / 6.0 + 2 * np.pi * 8 * fase))
        refl[k] = np.roll(refl[k], desp, axis=0)
    refl[..., 3] *= 0.45 * np.linspace(1, 0.2, bh)[:, None]
    for capa, yy0 in ((refl, ry0), (s, y0)):
        zona = img[yy0:yy0 + bh, x0:x0 + bw]
        a = capa[: zona.shape[0], : zona.shape[1], 3:]
        rgb = capa[: zona.shape[0], : zona.shape[1], :3] * (0.35 if capa is refl else 1.0)
        img[yy0:yy0 + bh, x0:x0 + bw] = zona * (1 - a) + rgb * a
    # luz del farol: halo y su reflejo en el agua
    fx, fy = x0 + e["farol"][0], y0 + e["farol"][1]
    gx0, gx1, gy0, gy1 = int(fx - 260), int(fx + 260), int(fy - 220), min(H, int(fy + 420))
    yy, xx = np.mgrid[gy0:gy1, gx0:gx1].astype(np.float32)
    borde = smooth(0, 90, xx - gx0) * smooth(0, 90, gx1 - xx) * smooth(0, 90, yy - gy0) * smooth(0, 90, gy1 - yy)
    halo = (np.exp(-np.hypot(xx - fx, yy - fy) / 28) * 0.55 + np.exp(-np.hypot(xx - fx, yy - fy) / 110) * 0.18) * borde
    ry = 2 * BARCA[1] - fy  # posición del reflejo del farol
    hh = h[np.clip(yy.astype(int) - HORIZONTE, 0, H - HORIZONTE - 1), np.clip(xx.astype(int), 0, W - 1)]
    rastro = np.exp(-((xx - fx) / (14 + 0.12 * np.abs(yy - ry))) ** 2) * np.exp(-np.abs(yy - ry) / 160) * (yy > BARCA[1] + 8)
    rastro *= (0.25 + 0.9 * smooth(0.1, 0.8, hh)) * borde
    img[gy0:gy1, gx0:gx1] += ((halo + rastro * 0.55) * f)[..., None] * FAROL

    # juncos (se mecen despacio) y luciérnagas
    capa = Image.new("L", (520 * SS, 420 * SS), 0)
    dj = ImageDraw.Draw(capa)
    for x, base, alto, grosor, ph in e["juncos"]:
        mec = 10 * np.sin(2 * np.pi * 2 * fase + ph) + 4 * np.sin(2 * np.pi * 5 * fase + ph * 2)
        pts = [((x + mec * (k / 10) ** 2) * SS, (base - 660 - alto * k / 10) * SS) for k in range(11)]
        dj.line(pts, fill=255, width=int(grosor * SS))
        if grosor > 3.2:  # espiga de la enea
            ex, ey = pts[-2]
            dj.ellipse([ex - 5 * SS, ey - 4 * SS, ex + 5 * SS, ey + 30 * SS], fill=255)
    mj = np.asarray(capa.resize((520, 420), Image.LANCZOS), np.float32)[..., None] / 255
    img[660:1080, 0:520] = img[660:1080, 0:520] * (1 - mj) + JUNCO * mj
    lc = dn["luciernagas"]
    for k in range(len(lc["x"])):
        x = lc["x"][k] + lc["ax"][k] * np.sin(2 * np.pi * lc["cx"][k] * fase + lc["fase"][k])
        y = lc["y"][k] + lc["ay"][k] * np.sin(2 * np.pi * lc["cy"][k] * fase + lc["fase"][k] * 1.7)
        b = max(0.0, np.sin(2 * np.pi * lc["parpadeo"][k] * fase + lc["fase"][k])) ** 3
        xi, yi = int(x), int(y)
        yy, xx = np.mgrid[yi - 12:yi + 13, xi - 12:xi + 13]
        g = np.exp(-np.hypot(xx - x, yy - y) / 3.0) * 0.8 * b
        img[yi - 12:yi + 13, xi - 12:xi + 13] += g[..., None] * col(1.0, 0.9, 0.45)

    img = img * e["viñeta"] + e["dither"]
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
