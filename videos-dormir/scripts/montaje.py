"""Monta el vídeo final: voz + sonido ambiente + música + fondo animado.

    VIDEO=02 python3 scripts/montaje.py [horas] [voz.wav]   (por defecto 3 h y output/<vídeo>/voz.wav)

Cronología:
  0:00          fundido de entrada; la voz empieza a los VOZ_INICIO segundos
  fin de voz    la música se apaga en 3 min, el ambiente sube un poco y la imagen se oscurece
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

import proyecto

SR, LOOP = 48000, 120  # LOOP: duración del bucle de vídeo (s)
# Calidad (CRF: más alto = más compresión). HEVC: 3 h caben en ~350 MB sin pérdida visible.
CRF_CLARO, CRF_TRANSICION, CRF_OSCURO = 25, 27, 30
AUDIO_KBPS = 128
OUT = proyecto.OUT
VOZ_INICIO = 6.0
LUFS = {"voz": -19.0, "ambiente_con_voz": -30.0, "ambiente_solo": -27.0, "pad": -33.0}


def codec(crf):
    return ["-c:v", "libx265", "-preset", "medium", "-crf", str(crf), "-tag:v", "hvc1",
            "-x265-params", "log-level=error:aq-mode=3:keyint=96:open-gop=0",
            "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]


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
    amb, pad, voz = leer_wav(OUT / "ambiente_loop.wav"), leer_wav(OUT / "pad_loop.wav"), leer_wav(voz_wav)
    voz = voz * ganancia(voz, LUFS["voz"])
    g_amb = ganancia(amb[:SR * 120], LUFS["ambiente_con_voz"])
    subida = 10 ** ((LUFS["ambiente_solo"] - LUFS["ambiente_con_voz"]) / 20)
    pad = pad * ganancia(pad, LUFS["pad"])
    fin_voz = VOZ_INICIO + voz.shape[0] / SR
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                          "-c:a", "aac", "-b:a", f"{AUDIO_KBPS}k", str(salida)], stdin=subprocess.PIPE)
    trozo = SR * 30
    total = int(dur * SR)
    pico = 0.0
    for ini in range(0, total, trozo):
        n = min(trozo, total - ini)
        idx = np.arange(ini, ini + n)
        t = idx / SR
        y = amb[idx % amb.shape[0]] * (g_amb * rampa(t, fin_voz + 20, fin_voz + 140, 1, subida))[:, None]
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
    inicio = variante("inicio", "[0:v]fade=in:st=0:d=4", CRF_CLARO)
    clara = variante("clara", "[0:v]null", CRF_CLARO)
    transicion = variante("transicion", f"{negro},fade=in:st=0:d={LOOP}:alpha=1,colorchannelmixer=aa={oscuro}[n];[0:v][n]overlay", CRF_TRANSICION)
    # la parte oscura casi nadie la mira: mucha más compresión, mucho menos peso
    oscura = variante("oscura", f"{negro},colorchannelmixer=aa={oscuro}[n];[0:v][n]overlay", CRF_OSCURO)
    ultima = dur - (vueltas - 1) * LOOP
    final = variante("final", f"{negro},colorchannelmixer=aa={oscuro}[n];[0:v][n]overlay,fade=out:st={max(0, ultima - 60)}:d=60", CRF_OSCURO)
    lista = [inicio] + [clara] * (claras - 1) + [transicion] + [oscura] * (vueltas - claras - 2) + [final]
    (OUT / "_lista.txt").write_text("".join(f"file '{r.name}'\n" for r in lista))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(OUT / "_lista.txt"),
                    "-i", str(audio_m4a), "-map", "0:v", "-map", "1:a", "-c", "copy", "-tag:v", "hvc1", "-t", str(dur),
                    "-movflags", "+faststart", str(salida)], check=True)
    for r in {inicio, clara, transicion, oscura, final, OUT / "_lista.txt"}:
        r.unlink()


def capitulos(fin_voz, salida):
    datos = json.loads((OUT / "capitulos.json").read_text())
    lineas = []
    for i, (t, titulo) in enumerate(datos["capitulos"]):
        t = 0 if i == 0 else t + VOZ_INICIO
        lineas.append(f"{int(t // 60)}:{int(t % 60):02d} {titulo}")
    lineas.append(f"{int(fin_voz // 60) + 1}:00 {proyecto.CONF['capitulo_final']}")
    salida.write_text("\n".join(lineas) + "\n")
    print("capítulos:\n" + "\n".join(lineas))


def cambiar_audio(salida, audio_m4a):
    """Sustituye el sonido de un vídeo ya montado, sin volver a codificar la imagen."""
    anterior = OUT / "_video_anterior.mp4"
    salida.rename(anterior)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(anterior), "-i", str(audio_m4a), "-map", "0:v", "-map", "1:a",
                    "-c", "copy", "-tag:v", "hvc1", "-movflags", "+faststart", str(salida)], check=True)
    anterior.unlink()


if __name__ == "__main__":
    # --solo-audio: rehace el sonido y reutiliza la imagen del vídeo ya montado (mucho más rápido)
    solo_audio = "--solo-audio" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    horas = float(args[0]) if args else 3
    voz_wav = Path(args[1]) if len(args) > 1 else OUT / "voz.wav"
    dur = horas * 3600
    salida = OUT / f"{proyecto.CONF['archivo']}.mp4"
    fin_voz = audio(dur, voz_wav, OUT / "_audio.m4a")
    if (OUT / "capitulos.json").exists():
        capitulos(fin_voz, OUT / "capitulos_youtube.txt")
    if solo_audio and salida.exists():
        cambiar_audio(salida, OUT / "_audio.m4a")
    else:
        video(dur, fin_voz, OUT / "_audio.m4a", salida)
    (OUT / "_audio.m4a").unlink()
    print("listo:", salida)
