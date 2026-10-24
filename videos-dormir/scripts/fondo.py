"""Fondo animado: cabaña en el bosque, de noche, bajo la lluvia (vídeo 01).

También es el motor de render de todas las escenas: genera un bucle perfecto de 2 minutos
(output/<vídeo>/fondo_loop.mp4) con la escena que indique proyecto.py. Todo lo que se mueve
vuelve exactamente al punto de partida.

    python3 scripts/fondo.py frame [n]  -> output/<vídeo>/fondo_frame.png (para revisar)
    python3 scripts/fondo.py video [nombre.mp4]  -> output/<vídeo>/fondo_loop.mp4 (u otro nombre)
"""
import importlib
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
import scipy.fft as fft
from PIL import Image, ImageDraw, ImageFilter

import proyecto

W, H, FPS, LOOP = 1920, 1080, 24, 120  # segundos del bucle
N = FPS * LOOP
OUT = proyecto.OUT
rng = np.random.default_rng(11)


def col(*rgb):
    return np.array(rgb, np.float32)


CIELO_ARRIBA, CIELO_HORIZONTE = col(0.025, 0.04, 0.08), col(0.13, 0.155, 0.215)
MONTE_LEJOS, MONTE_CERCA = col(0.09, 0.11, 0.155), col(0.055, 0.07, 0.105)
ARBOLES_FONDO, ARBOLES_DELANTE = col(0.03, 0.04, 0.062), col(0.008, 0.011, 0.018)
COLINA = col(0.02, 0.026, 0.04)
NUBE, NUBE_LUNA = col(0.10, 0.115, 0.155), col(0.34, 0.37, 0.44)
NIEBLA, LLUVIA, VENTANA = col(0.19, 0.22, 0.29), col(0.55, 0.60, 0.70), col(1.0, 0.60, 0.24)
LUNA = (1460, 210)


def ruido_tileable(h, w, beta, estirar=1.0, semilla=0):
    """Ruido fractal periódico en ambas direcciones (se puede desplazar sin costuras)."""
    r = np.random.default_rng(semilla)
    ky = fft.fftfreq(h)[:, None]
    kx = fft.rfftfreq(w)[None, :] * estirar
    k = np.sqrt(kx ** 2 + ky ** 2)
    k[0, 0] = 1
    amp = 1 / k ** beta
    amp[0, 0] = 0
    z = amp * np.exp(2j * np.pi * r.random(amp.shape))
    x = fft.irfft2(z, (h, w))
    return ((x - x.mean()) / x.std()).astype(np.float32)


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def perfil(n, base, amp, semilla, beta=1.6):
    """Línea de montaña/colina: ruido 1D fractal."""
    r = np.random.default_rng(semilla)
    k = fft.rfftfreq(n * 2)
    k[0] = 1
    z = (1 / k ** beta) * np.exp(2j * np.pi * r.random(k.size))
    z[0] = 0
    y = fft.irfft(z, n * 2)[:n]
    return base - amp * (y - y.min()) / (y.max() - y.min())


def mascara_bajo(perfil_y):
    yy = np.arange(H)[:, None]
    return np.clip(yy - perfil_y[None, :] + 0.5, 0, 1).astype(np.float32)


def pino(d, x, base, alto, ancho, ss):
    """Silueta de pino con ramas irregulares (dibujado a escala ss)."""
    pts_izq, pts_der = [], []
    niveles = int(alto / 14) + 4
    for i in range(niveles + 1):
        f = i / niveles
        y = base - alto + f * alto * 0.92
        w = ancho * (0.06 + 0.94 * f) * (1 if i % 2 == 0 else 0.62) * rng.uniform(0.85, 1.1)
        pts_izq.append((x - w / 2, y))
        pts_der.append((x + w / 2 * rng.uniform(0.85, 1.1), y))
    poly = [(x, base - alto - alto * 0.04)] + pts_der + [(x + ancho * 0.06, base)] + [(x - ancho * 0.06, base)] + pts_izq[::-1]
    d.polygon([(px * ss, py * ss) for px, py in poly], fill=255)


def capa_pinos(lista, ss=2):
    img = Image.new("L", (W * ss, H * ss), 0)
    d = ImageDraw.Draw(img)
    for x, base, alto, ancho in lista:
        pino(d, x, base, alto, ancho, ss)
    return np.asarray(img.resize((W, H), Image.LANCZOS), np.float32) / 255, img, d


def escena_estatica():
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    cielo = CIELO_ARRIBA + (CIELO_HORIZONTE - CIELO_ARRIBA) * (yy ** 1.6)
    cielo = np.broadcast_to(cielo, (H, W, 3)).copy()
    # brillo de la luna detrás de las nubes
    Y, X = np.mgrid[0:H, 0:W].astype(np.float32)
    dist = np.hypot(X - LUNA[0], Y - LUNA[1])
    halo = np.exp(-dist / 300) * 0.12 + np.exp(-dist / 80) * 0.12
    disco = smooth(44, 36, dist) * 0.38
    luz_luna = np.exp(-dist / 520).astype(np.float32)

    capas = []  # (máscara, color) de atrás hacia delante
    m_lejos = mascara_bajo(perfil(W, 650, 250, 12, 1.9))
    m_cerca = mascara_bajo(perfil(W, 760, 200, 5, 1.8))
    colina = 905 - 70 * np.exp(-((np.arange(W) - 640) / 520.0) ** 2) - 20 * np.sin(np.arange(W) / 300.0)

    fondo = [(x, colina[int(np.clip(x, 0, W - 1))] + rng.uniform(-6, 30), rng.uniform(60, 140), rng.uniform(26, 44))
             for x in np.sort(rng.uniform(-40, W + 40, 120))]
    m_fondo, _, _ = capa_pinos(fondo)
    delante = [(-10, 1100, 760, 230), (120, 1110, 620, 190), (260, 1130, 420, 150),
               (1700, 1110, 720, 220), (1860, 1100, 820, 250), (1540, 1140, 430, 150)]
    m_delante, _, _ = capa_pinos(delante)
    # colina y cabaña (silueta)
    ss = 2
    img = Image.new("L", (W * ss, H * ss), 0)
    d = ImageDraw.Draw(img)
    d.polygon([(0, colina[0] * ss)] + [(x * ss, colina[x] * ss) for x in range(0, W, 8)] + [(W * ss, colina[-1] * ss), (W * ss, H * ss), (0, H * ss)], fill=255)
    cx, cy = 640, int(colina[640]) + 4
    d.rectangle([(cx - 75) * ss, (cy - 70) * ss, (cx + 75) * ss, cy * ss], fill=255)
    d.polygon([((cx - 92) * ss, (cy - 66) * ss), (cx * ss, (cy - 128) * ss), ((cx + 92) * ss, (cy - 66) * ss)], fill=255)
    d.rectangle([(cx + 34) * ss, (cy - 128) * ss, (cx + 50) * ss, (cy - 88) * ss], fill=255)
    m_colina = np.asarray(img.resize((W, H), Image.LANCZOS), np.float32) / 255

    # ventanas de la cabaña
    vent = Image.new("L", (W, H), 0)
    dv = ImageDraw.Draw(vent)
    for x0 in (cx - 52, cx + 18):
        dv.rectangle([x0, cy - 50, x0 + 30, cy - 22], fill=255)
    vent_m = np.asarray(vent, np.float32) / 255
    # cruz del marco de la ventana
    for x0 in (cx - 52, cx + 18):
        vent_m[cy - 37:cy - 35, x0:x0 + 31] *= 0.15
        vent_m[cy - 50:cy - 21, x0 + 14:x0 + 16] *= 0.15
    glow = np.asarray(vent.filter(ImageFilter.GaussianBlur(28)), np.float32) / 255
    glow2 = np.asarray(vent.filter(ImageFilter.GaussianBlur(90)), np.float32) / 255

    capas = [(m_lejos, MONTE_LEJOS), (m_cerca, MONTE_CERCA)]
    capas_frente = [(m_fondo, ARBOLES_FONDO), (m_colina, COLINA), (m_delante, ARBOLES_DELANTE)]
    viñeta = (1 - 0.45 * smooth(0.45, 1.25, np.hypot((X - W / 2) / (W / 2), (Y - H / 2) / (H / 2))))[..., None]
    dither = (rng.random((H, W, 1), np.float32) - rng.random((H, W, 1), np.float32)) / 255
    return dict(cielo=cielo, halo=halo, disco=disco, luz_luna=luz_luna, capas=capas, frente=capas_frente,
                vent=vent_m, glow=glow, glow2=glow2, viñeta=viñeta, dither=dither, m_cerca=m_cerca)


def preparar_dinamico():
    nubes = ruido_tileable(H, W, 2.1, estirar=2.2, semilla=21)
    nubes_fino = ruido_tileable(H, W, 1.7, estirar=1.8, semilla=22)
    niebla = ruido_tileable(H, W, 2.0, estirar=3.0, semilla=23)
    gotas = 260
    lluvia = dict(x=rng.uniform(0, W, gotas), y=rng.uniform(0, H, gotas), largo=rng.uniform(18, 46, gotas),
                  vueltas=rng.integers(80, 110, gotas), alfa=rng.uniform(0.06, 0.15, gotas))
    fuego = [(rng.uniform(0.04, 0.08), int(c), rng.uniform(0, 6.28)) for c in (150, 233, 377, 610, 987)]
    return dict(nubes=nubes, nubes_fino=nubes_fino, niebla=niebla, lluvia=lluvia, fuego=fuego)


def desplazar(tex, px):
    """Desplaza en horizontal con precisión sub-píxel (textura periódica)."""
    i = int(np.floor(px))
    a = px - i
    t0 = np.roll(tex, -i, axis=1)
    return t0 * (1 - a) + np.roll(t0, -1, axis=1) * a


ESTATICA = DINAMICA = None


def init():
    global ESTATICA, DINAMICA
    ESTATICA, DINAMICA = escena_estatica(), preparar_dinamico()


def fotograma(i):
    e, dn = ESTATICA, DINAMICA
    fase = i / N  # 0..1 a lo largo del bucle
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    # nubes: dos capas que avanzan una "anchura" por bucle (sin costuras)
    n = 0.75 * desplazar(dn["nubes"], fase * W) + 0.35 * desplazar(dn["nubes_fino"], fase * W * 2)
    dens = smooth(-0.9, 1.0, n) * (1 - smooth(0.40, 0.62, yy)) * 0.95
    lumin = e["luz_luna"][..., None]
    c_nube = NUBE + (NUBE_LUNA - NUBE) * lumin * (0.4 + 0.6 * smooth(0.0, 1.2, n))[..., None]
    img = e["cielo"].copy()
    luna = (e["halo"] + e["disco"])[..., None] * col(0.75, 0.80, 0.90)
    img += luna * (1 - 0.8 * dens)[..., None]
    img = img * (1 - dens[..., None]) + c_nube * dens[..., None]
    for m, c in e["capas"]:
        img = img * (1 - m[..., None]) + c * m[..., None]
    # niebla en el valle, moviéndose al revés que las nubes
    nb = desplazar(dn["niebla"], -fase * W)
    banda = np.exp(-((yy - 0.70) / 0.09) ** 2)
    a_niebla = (smooth(-1.0, 1.2, nb) * banda * 0.55)[..., None]
    img = img * (1 - a_niebla) + NIEBLA * a_niebla
    for m, c in e["frente"]:
        img = img * (1 - m[..., None]) + c * m[..., None]
    # fuego: parpadeo suave con frecuencias enteras (periódico en el bucle)
    f = 1 + sum(a * np.sin(2 * np.pi * c * fase + p) for a, c, p in dn["fuego"])
    img += (e["vent"] * f * 0.95)[..., None] * VENTANA * (1 - img)
    img += (e["glow"] * 0.38 * f + e["glow2"] * 0.16 * f)[..., None] * VENTANA
    # lluvia: trazos finos que caen y vuelven arriba un número entero de veces por bucle
    capa = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(capa)
    ll = dn["lluvia"]
    ys = (ll["y"] + fase * ll["vueltas"] * (H + 60)) % (H + 60) - 60
    xs = (ll["x"] + ys * 0.08) % W
    for x, y, lg, al in zip(xs, ys, ll["largo"], ll["alfa"]):
        d.line([(x, y), (x + lg * 0.08, y + lg)], fill=int(al * 255), width=1)
    a_ll = (np.asarray(capa, np.float32) / 255)[..., None]
    img = img * (1 - a_ll) + LLUVIA * a_ll
    img = img * e["viñeta"] + e["dither"]
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


def ffmpeg_salida(ruta):
    return subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-tune", "film", "-x264-params", "aq-mode=3:open-gop=0",
         "-g", str(FPS * 4), "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
         "-color_trc", "bt709", "-movflags", "+faststart", str(ruta)], stdin=subprocess.PIPE)


ESCENA = None  # módulo de la escena que se está renderizando


def cargar_escena(nombre=None):
    global ESCENA
    ESCENA = importlib.import_module(nombre or proyecto.CONF["escena"])
    ESCENA.init()
    return ESCENA


def render_tramo(args):
    k, ini, fin = args
    ruta = OUT / f"_tramo{k}.mp4"
    p = ffmpeg_salida(ruta)
    for i in range(ini, fin):
        p.stdin.write(ESCENA.fotograma(i).tobytes())
    p.stdin.close()
    p.wait()
    return ruta


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    modo = sys.argv[1] if len(sys.argv) > 1 else "frame"
    if modo == "frame":
        escena = cargar_escena()
        Image.fromarray(escena.fotograma(int(sys.argv[2]) if len(sys.argv) > 2 else 0)).save(OUT / "fondo_frame.png")
        print("ok", OUT / "fondo_frame.png")
    else:
        trozos = 4
        cortes = [N * k // trozos for k in range(trozos + 1)]
        with Pool(trozos, initializer=cargar_escena) as pool:
            rutas = pool.map(render_tramo, [(k, cortes[k], cortes[k + 1]) for k in range(trozos)])
        lista = OUT / "_tramos.txt"
        lista.write_text("".join(f"file '{r.name}'\n" for r in rutas))
        salida = OUT / (sys.argv[2] if len(sys.argv) > 2 else "fondo_loop.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy",
                        "-movflags", "+faststart", str(salida)], check=True)
        for r in rutas:
            r.unlink()
        lista.unlink()
        print("ok", salida)
