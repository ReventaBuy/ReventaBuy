"""Genera los sonidos de fondo como bucles perfectos (sin cortes al repetirse).

    output/lluvia_loop.wav  -> 10 min de lluvia suave
    output/pad_loop.wav     -> música ambiental muy suave (acordes lentos)

Todo se construye en el dominio de la frecuencia o con convolución circular,
así que el final de cada archivo enlaza exactamente con su principio.
"""
import numpy as np
import scipy.fft as fft
from scipy.io import wavfile
from pathlib import Path

SR = 48000
OUT = Path(__file__).resolve().parent.parent / "output"
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
    OUT.mkdir(exist_ok=True)
    guardar("lluvia_loop.wav", *lluvia())
    # Re mayor: Dmaj7 – Bm7 – Gmaj7 – Asus2 (números MIDI; bajo + acorde abierto)
    acordes = [
        [38, 50, 54, 57, 61],
        [35, 47, 50, 54, 57],
        [31, 43, 50, 54, 59],
        [33, 45, 47, 52, 57],
    ]
    guardar("pad_loop.wav", *pad(acordes))
