"""Casting de voces: el mismo fragmento del guion con varias voces, y medidas para compararlas.

    VIDEO=05 python3 scripts/casting.py "Relajar la cara" ID1 ID2 ...
    -> output/<vídeo>/casting/<voz>.wav y una tabla con las medidas

Qué se mide (lo que hace que una voz relaje):
  ritmo     caracteres por segundo hablado (más bajo = más pausada)
  tono      tono medio en Hz y su variación en semitonos (más estable = más sosegada)
  calidez   centroide espectral en Hz (más bajo = más cálida) y energía de las eses (>5 kHz)
  regular   desviación del nivel entre frases (más bajo = más regular)
  fallos    muestras saturadas y saltos bruscos de nivel dentro de una frase
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guion  # noqa: E402
import tts  # noqa: E402

SR = tts.SR


def fragmento(capitulo):
    """Eventos de un capítulo del guion."""
    ev, dentro = [], False
    for e in guion.leer():
        if e[0] == "capitulo":
            dentro = e[1] == capitulo
        elif dentro:
            ev.append(e)
    return ev


def tono(x):
    """Tono fundamental por autocorrelación en tramos de 40 ms con voz (Hz)."""
    w, f0 = int(0.04 * SR), []
    for i in range(0, x.size - w, w // 2):
        t = x[i:i + w] - x[i:i + w].mean()
        if np.sqrt(np.mean(t ** 2)) < 0.02:
            continue
        ac = np.correlate(t, t, "full")[w - 1:]
        lo, hi = SR // 400, SR // 70
        k = lo + np.argmax(ac[lo:hi])
        if ac[k] > 0.45 * ac[0]:
            f0.append(SR / k)
    return np.array(f0)


def medir(frases, total_caracteres):
    x = np.concatenate(frases)
    hablado = sum(f.size for f in frases) / SR
    f0 = tono(x)
    espectro = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(x.size, 1 / SR)
    voz = (f > 80) & (f < 12000)
    centroide = (f[voz] * espectro[voz]).sum() / espectro[voz].sum()
    eses = 10 * np.log10(espectro[(f > 5000) & (f < 12000)].sum() / espectro[voz].sum())
    niveles = np.array([tts.nivel_voz(fr) for fr in frases if fr.size > SR * 0.3])
    w = int(0.02 * SR)
    saltos = 0
    for fr in frases:
        db = 20 * np.log10(np.sqrt((fr[:fr.size // w * w].reshape(-1, w) ** 2).mean(1)) + 1e-9)
        saltos += int(np.sum(np.diff(db) > 18))
    return dict(ritmo=total_caracteres / hablado, tono=np.median(f0), variacion=np.std(12 * np.log2(f0 / np.median(f0))),
                centroide=centroide, eses=eses, regular=niveles.std(), saturadas=int(np.sum(np.abs(x) > 0.98)), saltos=saltos)


if __name__ == "__main__":
    capitulo, voces = sys.argv[1], sys.argv[2:]
    ev = fragmento(capitulo)
    textos = guion.frases(ev)
    salida = tts.OUT / "casting"
    salida.mkdir(parents=True, exist_ok=True)
    print(f"{'voz':22} {'ritmo':>6} {'tono':>6} {'var.st':>6} {'centr.':>7} {'eses':>6} {'regul.':>6} {'satur.':>6} {'saltos':>6}")
    for voz in voces:
        frases = [tts.cargar(tts.sintetizar(t, voz, textos[i - 1] if i else None, textos[i + 1] if i + 1 < len(textos) else None))
                  for i, t in enumerate(textos)]
        tts.pista(ev, voz, salida / f"{voz}.wav")
        m = medir(frases, sum(len(t) for t in textos))
        print(f"{voz:22} {m['ritmo']:6.1f} {m['tono']:6.0f} {m['variacion']:6.2f} {m['centroide']:7.0f} {m['eses']:6.1f} "
              f"{m['regular']:6.2f} {m['saturadas']:6d} {m['saltos']:6d}")
