"""Monta el vídeo final: voz + lluvia + música + fondo animado.

    python3 scripts/montaje.py [horas] [voz.wav]   (por defecto 3 h y output/voz.wav)

Cronología:
  0:00          fundido de entrada; la voz empieza a los VOZ_INICIO segundos
  fin de voz    la música se apaga en 3 min, la lluvia sube un poco y la imagen se oscurece
  último minuto fundido a negro y a silencio
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
from scipy.io import wavfile

SR, LOOP = 48000, 120  # LOOP: duración del bucle de vídeo (s)
OUT = Path(__file__).resolve().parent.parent / "output"
VOZ_INICIO = 6.0
LUFS = {"voz": -19.0, "lluvia_con_voz": -30.0, "lluvia_sola": -27.0, "pad": -33.0}
def codec(crf):
    return ["-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-tune", "film", "-x264-params", "aq-mode=3:open-gop=0",
            "-g", "96", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]


def leer_wav(ruta):
    sr, x = wavfile.read(ruta)
    assert sr == SR, f"{ruta}: se esperaba {SR} Hz"
    x = x.astype(np.float32) / (32768 if x.dtype == np.int16 else 1)
    return x if x.ndim == 2 else np.stack([x, x], axis=1)


def ganancia(x, objetivo):
    medido = pyln.Meter(SR).integrated_loudness(x)
    return 10 ** ((objetivo - medido) / 20)


def rampa(t, t0, t1, a, b):
    """Interpola de a (antes de t0) a b (después de t1) con curva suave."""
    u = np.clip((t - t0) / max(t1 - t0, 1e-9), 0, 1)
    return a + (b - a) * (0.5 - 0.5 * np.cos(np.pi * u))


def audio(dur, voz_wav, salida):
    lluvia, pad, voz = leer_wav(OUT / "lluvia_loop.wav"), leer_wav(OUT / "pad_loop.wav"), leer_wav(voz_wav)
    voz = voz * ganancia(voz, LUFS["voz"])
    g_ll = ganancia(lluvia[:SR * 120], LUFS["lluvia_con_voz"])
    subida = 10 ** ((LUFS["lluvia_sola"] - LUFS["lluvia_con_voz"]) / 20)
    pad = pad * ganancia(pad, LUFS["pad"])
    fin_voz = VOZ_INICIO + voz.shape[0] / SR
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                          "-c:a", "aac", "-b:a", "192k", str(salida)], stdin=subprocess.PIPE)
    trozo = SR * 30
    total = int(dur * SR)
    pico = 0.0
    for ini in range(0, total, trozo):
        n = min(trozo, total - ini)
        idx = np.arange(ini, ini + n)
        t = idx / SR
        y = lluvia[idx % lluvia.shape[0]] * (g_ll * rampa(t, fin_voz + 20, fin_voz + 140, 1, subida))[:, None]
        y += pad[idx % pad.shape[0]] * (rampa(t, 0, 15, 0, 1) * rampa(t, fin_voz, fin_voz + 180, 1, 0))[:, None]
        iv = idx - int(VOZ_INICIO * SR)
        ok = (iv >= 0) & (iv < voz.shape[0])
        y[ok] += voz[iv[ok]]
        y *= (rampa(t, 0, 5, 0, 1) * rampa(t, dur - 60, dur, 1, 0))[:, None]
        pico = max(pico, float(np.abs(y).max()))
        p.stdin.write(np.clip(y, -1, 1).astype(np.float32).tobytes())
    p.stdin.close()
    p.wait()
    print(f"audio: {dur / 3600:.2f} h, pico {20 * math.log10(pico):.1f} dBFS, fin de la voz {fin_voz / 60:.1f} min")
    return fin_voz


def variante(nombre, filtro, crf=20):
    """Re-codifica el bucle aplicando un filtro (oscurecer, fundidos) con los mismos parámetros."""
    ruta = OUT / f"_fondo_{nombre}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(OUT / "fondo_loop.mp4"), "-filter_complex", filtro,
                    *codec(crf), "-an", str(ruta)], check=True)
    return ruta


def video(dur, fin_voz, audio_m4a, salida):
    vueltas = math.ceil(dur / LOOP)
    claras = max(1, math.ceil((fin_voz + 60) / LOOP))
    oscuro = 0.6  # opacidad del negro encima de la imagen después de la voz
    negro = f"color=black:s=1920x1080:r=24:d={LOOP},format=rgba"
    inicio = variante("inicio", "[0:v]fade=in:st=0:d=4")
    transicion = variante("transicion", f"{negro},fade=in:st=0:d={LOOP}:alpha=1,colorchannelmixer=aa={oscuro}[n];[0:v][n]overlay", 23)
    # la parte oscura casi nadie la mira: más compresión, mucho menos peso
    oscura = variante("oscura", f"{negro},colorchannelmixer=aa={oscuro}[n];[0:v][n]overlay", 25)
    ultima = dur - (vueltas - 1) * LOOP
    final = variante("final", f"{negro},colorchannelmixer=aa={oscuro}[n];[0:v][n]overlay,fade=out:st={max(0, ultima - 60)}:d=60", 25)
    lista = [inicio] + [OUT / "fondo_loop.mp4"] * (claras - 1) + [transicion] + [oscura] * (vueltas - claras - 2) + [final]
    (OUT / "_lista.txt").write_text("".join(f"file '{r.name}'\n" for r in lista))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(OUT / "_lista.txt"),
                    "-i", str(audio_m4a), "-map", "0:v", "-map", "1:a", "-c", "copy", "-t", str(dur),
                    "-movflags", "+faststart", str(salida)], check=True)
    for r in {inicio, transicion, oscura, final, OUT / "_lista.txt"}:
        r.unlink()


def capitulos(fin_voz, salida):
    datos = json.loads((OUT / "capitulos.json").read_text())
    lineas = []
    for i, (t, titulo) in enumerate(datos["capitulos"]):
        t = 0 if i == 0 else t + VOZ_INICIO
        lineas.append(f"{int(t // 60)}:{int(t % 60):02d} {titulo}")
    lineas.append(f"{int(fin_voz // 60) + 1}:00 Lluvia para dormir (sin voz)")
    salida.write_text("\n".join(lineas) + "\n")
    print("capítulos:\n" + "\n".join(lineas))


if __name__ == "__main__":
    horas = float(sys.argv[1]) if len(sys.argv) > 1 else 3
    voz_wav = Path(sys.argv[2]) if len(sys.argv) > 2 else OUT / "voz.wav"
    dur = horas * 3600
    fin_voz = audio(dur, voz_wav, OUT / "_audio.m4a")
    if (OUT / "capitulos.json").exists():
        capitulos(fin_voz, OUT / "capitulos_youtube.txt")
    video(dur, fin_voz, OUT / "_audio.m4a", OUT / "video_final.mp4")
    (OUT / "_audio.m4a").unlink()
    print("listo:", OUT / "video_final.mp4")
