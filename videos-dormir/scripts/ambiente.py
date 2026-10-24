"""Genera los sonidos de fondo como bucles perfectos (sin cortes al repetirse).

    output/<vídeo>/ambiente_loop.wav  -> 10 min de lluvia, olas o chimenea (según proyecto.py)
    output/<vídeo>/pad_loop.wav       -> música ambiental muy suave (acordes lentos)

Todo se construye en el dominio de la frecuencia o con convolución circular,
así que el final de cada archivo enlaza exactamente con su principio.
"""
import numpy as np
import scipy.fft as fft
from scipy.io import wavfile

import proyecto

SR = 48000
OUT = proyecto.OUT
rng = np.random.default_rng(7)


def ruido_con_espectro(n, puntos_hz, puntos_db):
    """Ruido periódico de n muestras cuyo espectro sigue la curva (hz, dB) dada."""
    f = fft.rfftfreq(n, 1 / SR)
    db = np.interp(np.log10(np.maximum(f, 10)), np.log10(puntos_hz), puntos_db)
    mag = 10 ** (db / 20)
    fase = rng.uniform(0, 2 * np.pi, f.size)
    x = fft.irfft(mag * np.exp(1j * fase), n, workers=-1)
    return (x / np.std(x)).astype(np.float32)


def conv_circular(x, kernel):
    k = np.zeros(x.size, np.float32)
    k[: kernel.size] = kernel
    return fft.irfft(fft.rfft(x, workers=-1) * fft.rfft(k, workers=-1), x.size, workers=-1).astype(np.float32)


def envolvente_lenta(n, profundidad, ciclos):
    """Variación lenta de intensidad, periódica dentro del bucle."""
    t = np.arange(n) / n
    e = np.zeros(n, np.float32)
    for c in ciclos:
        e += np.sin(2 * np.pi * c * t + rng.uniform(0, 2 * np.pi)).astype(np.float32)
    return 1 + profundidad * e / len(ciclos)


def gotas(n, por_segundo, kernels, amp_media, sigma=0.6):
    """Tren de impactos (Poisson) convolucionado con varias formas de gota; devuelve (L, R)."""
    canales = [np.zeros(n, np.float32), np.zeros(n, np.float32)]
    total = int(por_segundo * n / SR)
    pos = rng.integers(0, n, total)
    amp = amp_media * rng.lognormal(0, sigma, total).astype(np.float32)
    pan = rng.uniform(0, np.pi / 2, total)
    tipo = rng.integers(0, len(kernels), total)
    for k, kernel in enumerate(kernels):
        sel = tipo == k
        for c, g in enumerate((np.cos(pan[sel]), np.sin(pan[sel]))):
            tren = np.zeros(n, np.float32)
            np.add.at(tren, pos[sel], amp[sel] * g)
            canales[c] += conv_circular(tren, kernel)
    return canales


def kernel_ruido(ms, decay_ms, centro_hz):
    m = int(SR * ms / 1000)
    t = np.arange(m) / SR
    k = rng.standard_normal(m) * np.exp(-t / (decay_ms / 1000))
    # suavizado simple para quitar agudos ásperos
    ancho = max(1, int(SR / centro_hz / 2))
    k = np.convolve(k, np.hanning(ancho * 2 + 1), "same")
    return (k / np.abs(k).max()).astype(np.float32)


def kernel_plip(f0, decay_ms):
    """Gota sobre agua/madera: tono corto que sube ligeramente de frecuencia."""
    m = int(SR * decay_ms * 5 / 1000)
    t = np.arange(m) / SR
    f = f0 * (1 + 0.35 * (1 - np.exp(-t / 0.006)))
    k = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (decay_ms / 1000))
    k *= np.minimum(1, t / 0.0008)  # ataque suave
    return (k / np.abs(k).max()).astype(np.float32)


def lluvia(segundos=600):
    n = SR * segundos
    # Base: lluvia lejana, cálida (agudos recortados para que no "sise")
    hz = [20, 60, 150, 400, 1000, 2500, 5000, 9000, 16000, 24000]
    db = [-34, -24, -18, -11, -7, -7, -11, -20, -32, -48]
    comun = ruido_con_espectro(n, hz, db)
    L = 0.75 * ruido_con_espectro(n, hz, db) + 0.45 * comun
    R = 0.75 * ruido_con_espectro(n, hz, db) + 0.45 * comun
    # Rumor grave (lluvia sobre el tejado / bosque)
    grave = ruido_con_espectro(n, [20, 50, 120, 300, 800, 24000], [-6, 0, -4, -14, -30, -70])
    L += 0.35 * grave
    R += 0.35 * grave
    env = envolvente_lenta(n, 0.18, [3, 7, 13, 29])
    L *= env
    R *= env
    # Textura de gotas: muchas finas, algunas medianas y pocas "plip" cercanas
    finas = gotas(n, 260, [kernel_ruido(6, 1.2, 3500), kernel_ruido(8, 2.0, 2500)], 0.22)
    medianas = gotas(n, 22, [kernel_ruido(14, 3.5, 1800), kernel_ruido(18, 5.0, 1200)], 0.45)
    plips = gotas(n, 3, [kernel_plip(1400, 9), kernel_plip(2100, 7), kernel_plip(2900, 5)], 0.18, 0.4)
    for capa in (finas, medianas, plips):
        L += capa[0] * env
        R += capa[1] * env
    return L, R


def envolvente_olas(n, ctrl_hz, olas, subida, caida, cola=6.0):
    """Suma circular de envolventes de ola a baja resolución, luego interpolada a audio."""
    m = int(n / SR * ctrl_hz)
    env = np.zeros((2, m), np.float32)
    for t0, amp, pan, s, c in olas:
        s, c = s * subida, c * caida
        tau = np.arange(-s, c * cola, 1 / ctrl_hz)
        forma = np.where(tau < 0, 0.5 - 0.5 * np.cos(np.pi * (tau + s) / s), np.exp(-np.maximum(tau, 0) / c))
        idx = (int(t0 * ctrl_hz) + np.arange(tau.size)) % m  # circular: el bucle no tiene costura
        np.add.at(env[0], idx, amp * np.cos(pan) * forma)
        np.add.at(env[1], idx, amp * np.sin(pan) * forma)
    x_ctrl = np.arange(m + 1) / ctrl_hz
    x = np.arange(n) / SR
    return [np.interp(x, x_ctrl, np.append(e, e[0])).astype(np.float32) for e in env]


def chisporroteo(n, env, por_segundo, amp):
    """Espuma: miles de chasquidos diminutos, cada uno de ruido distinto (sin tono), con densidad según la envolvente."""
    p = np.clip(env / env.max() * por_segundo / SR, 0, 0.5)
    tren = np.zeros(n, np.float32)
    pos = np.flatnonzero(rng.random(n, dtype=np.float32) < p)
    tren[pos] = rng.lognormal(0, 0.6, pos.size)
    t = np.arange(int(SR * 0.004)) / SR
    rafagas = conv_circular(tren, np.exp(-t / 0.0006).astype(np.float32))
    ruido = ruido_con_espectro(n, [20, 800, 2000, 3500, 6000, 10000, 24000], [-60, -24, -6, 0, -3, -18, -60])
    return amp * ruido * rafagas


def mar(segundos=600):
    """Olas suaves en la orilla: se acercan, rompen, la espuma chisporrotea y el agua se retira."""
    n = SR * segundos
    # mar de fondo: rumor grave y continuo que respira despacio
    lento = envolvente_lenta(n, 0.18, [2, 5, 11])
    fondo = [ruido_con_espectro(n, [20, 45, 100, 250, 600, 1500, 4000, 24000], [-12, -3, 0, -7, -17, -27, -42, -75]) * lento
             for _ in range(2)]
    # una ola cada 7–15 s, cada una con su fuerza, su duración y su lado
    olas, t = [], 0.0
    while t < segundos:
        olas.append((t, rng.lognormal(0, 0.3), rng.uniform(0.45, 1.12), rng.uniform(0.8, 1.25), rng.uniform(0.8, 1.3)))
        t += rng.uniform(7, 15)

    def etapa(retraso, factor=1.0):
        return [(t0 + retraso * s, a * factor, p, s, c) for t0, a, p, s, c in olas]

    llegada = envolvente_olas(n, 200, olas, subida=3.5, caida=1.6)                # crece al acercarse
    rompe = envolvente_olas(n, 200, etapa(3.5), subida=1.3, caida=1.8)            # rompe: rugido suave
    espuma = envolvente_olas(n, 200, etapa(4.0, 0.8), subida=1.4, caida=3.2)      # se extiende y burbujea
    retirada = envolvente_olas(n, 200, etapa(7.0, 0.35), subida=1.6, caida=3.0)   # vuelve por la arena
    grave = ([20, 50, 120, 300, 700, 1500, 4000, 24000], [-24, -8, 0, -2, -10, -22, -40, -75])
    rugido = ([20, 80, 250, 600, 1400, 3000, 6000, 12000, 24000], [-40, -18, -6, 0, -2, -9, -20, -36, -70])
    siseo = ([20, 400, 1200, 2500, 4500, 8000, 12000, 24000], [-60, -26, -8, -2, 0, -8, -22, -60])
    canales = []
    for c in range(2):
        # siempre queda algo de espuma lejana: las olas no arrancan desde el silencio
        y = 0.55 * fondo[c] + 0.13 * ruido_con_espectro(n, *siseo) * envolvente_lenta(n, 0.3, [3, 7, 13])
        y += ruido_con_espectro(n, *grave) * (0.8 * llegada[c] + 0.5 * rompe[c])
        y += ruido_con_espectro(n, *rugido) * rompe[c]
        y += ruido_con_espectro(n, *siseo) * (0.55 * espuma[c] + 0.35 * retirada[c])
        y += chisporroteo(n, espuma[c] + 0.6 * retirada[c], 2500, 0.18)
        canales.append(y)
    return canales


def modulacion(n, hz_corte, profundidad):
    """Variación lenta e irregular (por debajo de hz_corte), periódica en el bucle, alrededor de 1."""
    m = int(n / SR * 100)
    f = fft.rfftfreq(m, 1 / 100)
    mag = 1 / (1 + (f / hz_corte) ** 4)
    mag[0] = 0
    x = fft.irfft(mag * np.exp(2j * np.pi * rng.random(f.size)), m)
    x /= np.abs(x).max()
    xs = np.interp(np.arange(n) / SR, np.arange(m + 1) / 100, np.append(x, x[0]))
    return (1 + profundidad * xs).astype(np.float32)


def chasquidos(n, por_segundo, actividad, tau_ms, color, sigma):
    """Chasquidos del fuego: ráfagas de ruido (sin tono) con densidad según la actividad."""
    p = np.clip(actividad / actividad.mean() * por_segundo / SR, 0, 0.5)
    tren = np.zeros(n, np.float32)
    pos = np.flatnonzero(rng.random(n, dtype=np.float32) < p)
    a = rng.lognormal(0, sigma, pos.size).astype(np.float32)
    tren[pos] = np.minimum(a, np.percentile(a, 90))  # tope: ningún estallido demasiado fuerte
    t = np.arange(int(SR * tau_ms * 8 / 1000)) / SR
    rafagas = conv_circular(tren, np.exp(-t / (tau_ms / 1000)).astype(np.float32))
    return ruido_con_espectro(n, *color) * rafagas


def chimenea(segundos=600):
    """Fuego de leña en la chimenea y, fuera, un viento muy suave."""
    n = SR * segundos
    canales = []
    for _ in range(2):
        llamas = modulacion(n, 0.8, 0.35) * modulacion(n, 0.05, 0.2)
        rumor = ruido_con_espectro(n, [20, 40, 80, 200, 500, 1500, 5000, 24000], [-20, -6, 0, -4, -14, -30, -50, -80]) * llamas
        siseo = ruido_con_espectro(n, [20, 1000, 3000, 6000, 12000, 24000], [-80, -30, -10, -6, -16, -50]) * modulacion(n, 0.3, 0.5)
        actividad = np.maximum(modulacion(n, 0.5, 0.8), 0.05) * llamas  # los chasquidos llegan a rachas
        finos = chasquidos(n, 17, actividad, 0.8, ([20, 1500, 3500, 7000, 12000, 24000], [-60, -8, 0, -8, -26, -60]), 0.4)
        medios = chasquidos(n, 4, actividad, 2.5, ([20, 400, 1200, 3000, 6000, 24000], [-50, -8, 0, -5, -22, -60]), 0.45)
        gordos = chasquidos(n, 0.35, actividad, 8.0, ([20, 150, 500, 1500, 4000, 24000], [-40, -6, 0, -6, -24, -70]), 0.4)
        viento = ruido_con_espectro(n, [20, 60, 150, 400, 1000, 3000, 24000], [-10, 0, -3, -15, -35, -60, -90]) * modulacion(n, 0.08, 0.6)
        # el crepitar es lo protagonista; el rumor de las llamas y el viento quedan suaves de fondo
        y = 0.40 * rumor + 0.06 * siseo + 0.55 * finos + 1.3 * medios + 1.6 * gordos + 0.12 * viento
        k = 6 * np.sqrt(np.mean(y ** 2))  # limitador suave: los picos no pasan de ~15 dB sobre la media
        canales.append(k * np.tanh(y / k))
    return canales


def lluvia_ventana(segundos=600):
    """Lluvia oída desde dentro: lluvia amortiguada por el cristal, tejado, gotas en el cristal y el canalón."""
    n = SR * segundos
    env = envolvente_lenta(n, 0.15, [3, 7, 13, 29])
    canales = []
    for _ in range(2):
        fuera = ruido_con_espectro(n, [20, 60, 150, 400, 900, 1800, 3500, 7000, 24000],
                                   [-30, -16, -8, -2, 0, -5, -16, -32, -70]) * env
        tejado = ruido_con_espectro(n, [20, 50, 120, 300, 800, 24000], [-8, 0, -3, -12, -30, -80])
        cristal = chasquidos(n, 9, env, 1.2, ([20, 600, 1500, 3000, 6000, 12000, 24000], [-60, -14, -3, 0, -8, -26, -60]), 0.6)
        finas = chasquidos(n, 60, env, 0.5, ([20, 1500, 4000, 8000, 16000, 24000], [-60, -12, -4, -8, -24, -60]), 0.5)
        canales.append(0.9 * fuera + 0.35 * tejado + 0.55 * cristal + 0.25 * finas)
    # goteo del canalón en un charco: gotas con su "plic" (en una gota real el tono es natural)
    canalon = gotas(n, 0.6, [kernel_plip(1000, 30), kernel_plip(1150, 25), kernel_plip(880, 35)], 0.25, 0.3)
    salida = []
    for y, g in zip(canales, canalon):
        y = y + g
        k = 6 * np.sqrt(np.mean(y ** 2))  # limitador suave de picos
        salida.append(k * np.tanh(y / k))
    return salida


def nota(hz):
    return 440 * 2 ** ((hz - 69) / 12)  # hz aquí es número MIDI


def pad(acordes, seg_por_acorde=20.0, solape=8.0):
    """Acordes lentos con síntesis aditiva y reverb larga, en bucle perfecto."""
    n = int(SR * seg_por_acorde * len(acordes))
    buf = np.zeros(n, np.float32), np.zeros(n, np.float32)
    largo = seg_por_acorde + solape
    m = int(SR * largo)
    t = np.arange(m) / SR
    fade = int(SR * solape)
    env = np.ones(m, np.float32)
    env[:fade] = np.sin(np.linspace(0, np.pi / 2, fade)) ** 2
    env[-fade:] = np.cos(np.linspace(0, np.pi / 2, fade)) ** 2
    for i, acorde in enumerate(acordes):
        for c in range(2):
            seg = np.zeros(m, np.float32)
            for midi in acorde:
                f = nota(midi)
                peso = 1.0 if midi >= 45 else 0.6
                for p in range(1, 7):
                    if f * p > 2500:
                        break
                    detune = 1 + rng.uniform(-0.002, 0.002)
                    amp = peso / p ** 1.6
                    trem = 1 + 0.08 * np.sin(2 * np.pi * rng.uniform(0.05, 0.12) * t + rng.uniform(0, 6.3))
                    seg += (amp * trem * np.sin(2 * np.pi * f * p * detune * t + rng.uniform(0, 6.3))).astype(np.float32)
            seg *= env
            ini = int(SR * (i * seg_por_acorde - solape / 2)) % n
            idx = (ini + np.arange(m)) % n  # se enrolla al principio: bucle sin costuras
            np.add.at(buf[c], idx, seg)
    # Reverb: respuesta al impulso sintética de 6 s, oscura
    ir_n = SR * 6
    ti = np.arange(ir_n) / SR
    salida = []
    for c in range(2):
        ir = rng.standard_normal(ir_n).astype(np.float32) * np.exp(-ti / 1.6).astype(np.float32)
        ir = np.convolve(ir, np.hanning(41), "same").astype(np.float32)
        ir[0] += 6.0  # parte de señal directa
        salida.append(conv_circular(buf[c], ir))
    return salida


def guardar(nombre, L, R, pico_db=-3.0):
    x = np.stack([L, R], axis=1)
    x *= 10 ** (pico_db / 20) / np.abs(x).max()
    wavfile.write(OUT / nombre, SR, (x * 32767).astype(np.int16))
    print("guardado", OUT / nombre, f"{x.shape[0] / SR / 60:.1f} min")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    generador = {"lluvia": lluvia, "mar": mar, "chimenea": chimenea, "lluvia_ventana": lluvia_ventana}[proyecto.CONF["ambiente"]]
    guardar("ambiente_loop.wav", *generador())
    guardar("pad_loop.wav", *pad(proyecto.CONF["acordes"]))
