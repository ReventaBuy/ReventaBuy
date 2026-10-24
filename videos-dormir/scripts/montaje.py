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
from scipy import signal
from scipy.io import wavfile

import proyecto

SR, LOOP = 48000, 120  # LOOP: duración del bucle de vídeo (s)
# Calidad (CRF: más alto = más compresión). HEVC: 3 h caben en ~350 MB sin pérdida visible.
# Cada vídeo puede ajustarlos en proyecto.py si su escena pesa más (p. ej. con nieve cayendo).
CRF_CLARO = proyecto.CONF.get("crf_claro", 25)
CRF_TRANSICION, CRF_OSCURO = 27, 30
AUDIO_KBPS = proyecto.CONF.get("audio_kbps", 128)
OUT = proyecto.OUT
VOZ_INICIO = 6.0
LUFS = {"voz": -20.0, "ambiente_con_voz": -23.0, "ambiente_solo": -25.0, "pad": -27.0}
DUCKING_DB = 3.0      # cuánto baja el fondo mientras habla la voz
HUECO_FIJO_DB = 4.0   # el fondo siempre deja algo de sitio en 1–4 kHz (no se nota: no hay con qué comparar)
HUECO_DB = 8.0        # y mientras habla la voz, ese hueco se hace más hondo
DECRESCENDO_DB = 3.0  # la voz baja un poco a lo largo del último capítulo


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


def procesar_voz(voz_wav):
    """Cadena de estudio para la voz: sin retumbe, menos 'caja', algo de presencia, eses suaves y compresión ligera."""
    filtro = ("highpass=f=70:poles=2,"
              "equalizer=f=250:t=q:w=1.0:g=-1.5,"
              "equalizer=f=3500:t=q:w=1.2:g=1.0,"
              "deesser=i=0.35:m=0.5:f=0.5,"
              "acompressor=threshold=0.063:ratio=2.5:attack=8:release=200:knee=6:makeup=1")
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(voz_wav), "-af", filtro, "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(pcm, np.float32).copy()


def actividad_voz(v, anticipo=0.12, ataque=0.12, caida=0.9):
    """De 0 a 1, 100 veces por segundo: 1 mientras habla la voz (empieza un poco antes y se suelta despacio)."""
    w = SR // 100
    db = 20 * np.log10(np.sqrt((v[:v.size // w * w].reshape(-1, w) ** 2).mean(1) + 1e-12))
    habla = (db > np.percentile(db[db > -80], 95) - 30).astype(np.float32)
    k = int(anticipo * 100)
    habla = np.maximum(habla, np.concatenate([habla[k:], np.zeros(k, np.float32)]))
    sube, baja = 1 - np.exp(-1 / (ataque * 100)), 1 - np.exp(-1 / (caida * 100))
    env, e = np.zeros_like(habla), 0.0
    for i, h in enumerate(habla):
        e += (sube if h > e else baja) * (h - e)
        env[i] = e
    return env


def ecualizador_pico(f0, q, ganancia_db):
    """Filtro de pico (RBJ) en formato SOS."""
    A, w0 = 10 ** (ganancia_db / 40), 2 * np.pi * f0 / SR
    alfa = np.sin(w0) / (2 * q)
    return signal.tf2sos([1 + alfa * A, -2 * np.cos(w0), 1 - alfa * A], [1 + alfa / A, -2 * np.cos(w0), 1 - alfa / A])


def audio(dur, voz_wav, salida):
    """Mezcla final.

    - La voz pasa por procesar_voz() y se normaliza; en el último capítulo baja DECRESCENDO_DB.
    - Mientras habla, el fondo (ambiente + música) baja DUCKING_DB y deja un hueco de HUECO_DB entre 1 y 4 kHz,
      donde se entienden las palabras. En las pausas vuelve a su nivel: la voz no tapa el fondo ni al revés.
    - Limitador final para que no haya picos.
    Devuelve el segundo en que acaba la voz y escribe output/<vídeo>/informe_mezcla.txt.
    """
    amb, pad = leer_wav(OUT / "ambiente_loop.wav"), leer_wav(OUT / "pad_loop.wav")
    voz = procesar_voz(voz_wav)
    voz *= ganancia(voz, LUFS["voz"])
    caps = json.loads((OUT / "capitulos.json").read_text())["capitulos"] if (OUT / "capitulos.json").exists() else []
    if caps:
        tv = np.arange(voz.size) / SR
        voz *= rampa(tv, caps[-1][0], voz.size / SR, 1, 10 ** (-DECRESCENDO_DB / 20)).astype(np.float32)
    act = actividad_voz(voz)
    fin_voz = VOZ_INICIO + voz.size / SR
    g_amb = ganancia(amb[:SR * 120], LUFS["ambiente_con_voz"])
    subida = 10 ** ((LUFS["ambiente_solo"] - LUFS["ambiente_con_voz"]) / 20)
    pad = pad * ganancia(pad, LUFS["pad"])
    duck = 1 - 10 ** (-DUCKING_DB / 20)
    hueco_fijo = ecualizador_pico(2000, 0.6, -HUECO_FIJO_DB)  # Q bajo: cubre de ~0,9 a ~4,5 kHz
    hueco = ecualizador_pico(2000, 0.55, -HUECO_DB)
    estado = [np.zeros((hueco.shape[0], 2)) for _ in range(2)]
    estado_fijo = [np.zeros((hueco_fijo.shape[0], 2)) for _ in range(2)]
    banda = signal.butter(4, [1000, 4000], btype="band", fs=SR, output="sos")
    medidas = []  # por bloque de 400 ms con voz: (voz, fondo, voz 1-4 kHz, fondo 1-4 kHz, actividad)

    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                          "-af", "alimiter=limit=0.8:attack=5:release=80:latency=1:level=0",
                          "-c:a", "aac", "-b:a", f"{AUDIO_KBPS}k", str(salida)], stdin=subprocess.PIPE)
    trozo, total, pico = SR * 30, int(dur * SR), 0.0
    for ini in range(0, total, trozo):
        n = min(trozo, total - ini)
        idx = np.arange(ini, ini + n)
        t = idx / SR
        a = np.interp((t - VOZ_INICIO) * 100, np.arange(act.size), act, left=0, right=0).astype(np.float32)
        fondo = amb[idx % amb.shape[0]] * (g_amb * rampa(t, fin_voz + 20, fin_voz + 140, 1, subida))[:, None]
        con_hueco = np.empty_like(fondo)
        for c in range(2):
            fondo[:, c], estado_fijo[c] = signal.sosfilt(hueco_fijo, fondo[:, c], zi=estado_fijo[c])
            con_hueco[:, c], estado[c] = signal.sosfilt(hueco, fondo[:, c], zi=estado[c])
        fondo = fondo + (con_hueco - fondo) * a[:, None]
        fondo += pad[idx % pad.shape[0]] * (rampa(t, 0, 15, 0, 1) * rampa(t, fin_voz, fin_voz + 180, 1, 0))[:, None]
        fondo *= (1 - duck * a)[:, None]
        v = np.zeros(n, np.float32)
        iv = idx - int(VOZ_INICIO * SR)
        ok = (iv >= 0) & (iv < voz.size)
        v[ok] = voz[iv[ok]]
        if ok.any():
            vk, f_m = ponderacion_k(v), ponderacion_k(fondo.mean(1))
            vb, fb = signal.sosfilt(banda, vk), signal.sosfilt(banda, f_m)
            b = int(0.4 * SR)
            for k in range(0, n - b + 1, b):
                sl = slice(k, k + b)
                medidas.append([np.mean(vk[sl] ** 2), np.mean(f_m[sl] ** 2), np.mean(vb[sl] ** 2), np.mean(fb[sl] ** 2), a[sl].mean()])
        y = (fondo + v[:, None]) * (rampa(t, 0, 5, 0, 1) * rampa(t, dur - 60, dur, 1, 0))[:, None]
        pico = max(pico, float(np.abs(y).max()))
        p.stdin.write(np.clip(y, -1, 1).astype(np.float32).tobytes())
    p.stdin.close()
    p.wait()
    informe_mezcla(np.array(medidas), voz)
    print(f"audio: {dur / 3600:.2f} h, pico antes del limitador {20 * math.log10(pico):.1f} dBFS, "
          f"fin de la voz {fin_voz / 60:.1f} min")
    return fin_voz


def ponderacion_k(x):
    """Filtro de ponderación K (ITU-R BS.1770, 48 kHz): pesa las frecuencias como el oído al medir sonoridad."""
    x = signal.lfilter([1.53512485958697, -2.69169618940638, 1.19839281085285], [1, -1.69065929318241, 0.73248077421585], x)
    return signal.lfilter([1.0, -2.0, 1.0], [1, -1.99004745483398, 0.99007225036621], x)


def informe_mezcla(m, voz):
    """Comprueba con números (sonoridad ponderada K) que la voz se entiende sin tapar el fondo."""
    db = lambda x: 10 * np.log10(np.maximum(x, 1e-12))
    habla = (m[:, 4] > 0.9) & (db(m[:, 0]) > db(m[:, 0]).max() - 30)
    pausa = (m[:, 4] < 0.05) & (db(m[:, 0]) < db(m[:, 0]).max() - 50)
    snr = db(m[habla, 0]) - db(m[habla, 1])
    snr_b = db(m[habla, 2]) - db(m[habla, 3])
    voz_hablando = np.median(db(m[habla, 0]))
    fondo_pausas = np.median(db(m[pausa, 1])) - voz_hablando
    # nivel de cada frase (tramos con voz separados por silencios de más de 0,5 s)
    from tts import nivel_voz
    w = SR // 100
    sonando = np.sqrt((voz[:voz.size // w * w].reshape(-1, w) ** 2).mean(1)) > 10 ** (-50 / 20)
    frases, ini, hueco = [], None, 0
    for i, s_ in enumerate(sonando):
        if s_:
            ini, hueco = (i if ini is None else ini), 0
        elif ini is not None:
            hueco += 1
            if hueco > 50:
                frases.append(voz[ini * w:(i - hueco) * w])
                ini, hueco = None, 0
    niveles = np.array([nivel_voz(f) for f in frases if f.size > SR * 0.3])
    lineas = [
        "INFORME DE MEZCLA (parte con voz, sonoridad ponderada K)",
        f"Voz sobre el fondo mientras habla:   mediana {np.median(snr):5.1f} dB   (peor 10 %: {np.percentile(snr, 10):5.1f} dB)",
        f"  … en 1–4 kHz (inteligibilidad):    mediana {np.median(snr_b):5.1f} dB   (peor 10 %: {np.percentile(snr_b, 10):5.1f} dB)",
        f"Fondo en las pausas:                 {fondo_pausas:5.1f} dB respecto a la voz",
        f"Frases: {niveles.size}, nivel igualado con desviación {niveles.std():.1f} dB (rango {np.ptp(niveles):.1f} dB)",
        "Objetivo: voz 10–14 dB sobre el fondo (peor 10 % > 7 dB); en las pausas el fondo entre −6 y −10 dB.",
    ]
    (OUT / "informe_mezcla.txt").write_text("\n".join(lineas) + "\n")
    print("\n".join(lineas))


def variante(nombre, filtro, crf=20, bucle="fondo_loop.mp4"):
    """Re-codifica un bucle aplicando un filtro (oscurecer, fundidos) con los mismos parámetros."""
    ruta = OUT / f"_fondo_{nombre}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(OUT / bucle), "-filter_complex", filtro,
                    *codec(crf), "-an", str(ruta)], check=True)
    return ruta


def video(dur, fin_voz, audio_m4a, salida):
    vueltas = math.ceil(dur / LOOP)
    oscurecer = min(fin_voz + 60, proyecto.CONF.get("oscurecer_min", 1e9) * 60)  # cuándo empieza a oscurecerse
    claras = max(1, math.ceil(oscurecer / LOOP))
    oscuro = 0.6  # opacidad del negro encima de la imagen después de la voz
    negro = f"color=black:s=1920x1080:r=24:d={LOOP},format=rgba"
    inicio = variante("inicio", "[0:v]fade=in:st=0:d=4", CRF_CLARO)
    clara = variante("clara", "[0:v]null", CRF_CLARO)
    # una escena puede tener bucles propios para el final (p. ej. deja de nevar y luego no nieva)
    b_transicion = proyecto.CONF.get("bucle_transicion", "fondo_loop.mp4")
    b_oscuro = proyecto.CONF.get("bucle_oscuro", "fondo_loop.mp4")
    transicion = variante("transicion", f"{negro},fade=in:st=0:d={LOOP}:alpha=1,colorchannelmixer=aa={oscuro}[n];[0:v][n]overlay",
                          CRF_TRANSICION, b_transicion)
    # la parte oscura casi nadie la mira: mucha más compresión, mucho menos peso
    oscura = variante("oscura", f"{negro},colorchannelmixer=aa={oscuro}[n];[0:v][n]overlay", CRF_OSCURO, b_oscuro)
    ultima = dur - (vueltas - 1) * LOOP
    final = variante("final", f"{negro},colorchannelmixer=aa={oscuro}[n];[0:v][n]overlay,fade=out:st={max(0, ultima - 60)}:d=60",
                     CRF_OSCURO, b_oscuro)
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
