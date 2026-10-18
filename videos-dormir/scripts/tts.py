"""Convierte el guion en voz con ElevenLabs y monta la pista de voz con sus pausas.

La clave se lee de la variable de entorno ELEVENLABS_API_KEY.
Cada frase se guarda en output/tts_cache/, así que repetir no gasta créditos.

    python3 scripts/tts.py muestras            -> una muestra corta por cada voz candidata
    python3 scripts/tts.py completo VOICE_ID   -> output/voz.wav con todo el guion
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import requests
from scipy.io import wavfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guion  # noqa: E402

SR = 48000
OUT = guion.ROOT / "output"
CACHE = OUT / "tts_cache"
API = "https://api.elevenlabs.io/v1"
MODELO = "eleven_multilingual_v2"
AJUSTES = {"stability": 0.65, "similarity_boost": 0.75, "style": 0.0, "use_speaker_boost": True, "speed": 0.85}

CANDIDATAS = {
    "sara_es": "Ir1QNHvhaJXbAGhT50w3",      # Sara Martin — España, mujer, íntima y tierna
    "martin_es": "W5JElH3dK1UYYAiHH7uh",    # Martin Osborne — España, hombre, íntimo y cálido
    "jhenny_latam": "D9MdulIxfrCUUJcGNQon", # Jhenny — latina, mujer, suave y meditativa
    "mauricio_latam": "94zOad0g7T7K4oa7zhDq",  # Mauricio — latino, hombre, calmado
}


def _cabeceras():
    clave = os.environ.get("ELEVENLABS_API_KEY")
    if not clave:
        sys.exit("Falta la variable de entorno ELEVENLABS_API_KEY")
    return {"xi-api-key": clave, "Content-Type": "application/json"}


def sintetizar(texto, voz, anterior=None, siguiente=None):
    """Devuelve la ruta de un mp3 con la frase; usa la caché si ya existe."""
    datos = {"text": texto, "model_id": MODELO, "voice_settings": AJUSTES}
    if anterior:
        datos["previous_text"] = anterior
    if siguiente:
        datos["next_text"] = siguiente
    clave = hashlib.sha1(json.dumps([voz, datos], sort_keys=True).encode()).hexdigest()[:16]
    ruta = CACHE / voz / f"{clave}.mp3"
    if ruta.exists():
        return ruta
    ruta.parent.mkdir(parents=True, exist_ok=True)
    r = requests.post(f"{API}/text-to-speech/{voz}?output_format=mp3_44100_128",
                      headers=_cabeceras(), json=datos, timeout=120)
    if r.status_code != 200:
        sys.exit(f"ElevenLabs respondió {r.status_code}: {r.text[:300]}")
    ruta.write_bytes(r.content)
    return ruta


def cargar(ruta):
    """Decodifica a mono float32 a 48 kHz y recorta silencios de los extremos."""
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(ruta), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(pcm, np.float32)
    voz = np.flatnonzero(np.abs(x) > 0.01)
    if voz.size == 0:
        return x[:0]
    a, b = max(0, voz[0] - int(0.02 * SR)), min(x.size, voz[-1] + int(0.15 * SR))
    return x[a:b]


def pista(eventos, voz, salida):
    """Monta la voz con sus pausas. Devuelve (capitulos [(segundo, titulo)], duración)."""
    frases = guion.frases(eventos)
    trozos, capitulos, t, i = [], [], 0.0, 0
    for tipo, valor in eventos:
        if tipo == "capitulo":
            capitulos.append((t, valor))
        elif tipo == "pausa":
            trozos.append(np.zeros(int(valor * SR), np.float32))
            t += valor
        else:
            anterior = frases[i - 1] if i > 0 else None
            siguiente = frases[i + 1] if i + 1 < len(frases) else None
            print(f"  [{i + 1}/{len(frases)}] {valor[:60]}")
            x = cargar(sintetizar(valor, voz, anterior, siguiente))
            trozos.append(x)
            t += x.size / SR
            i += 1
    y = np.concatenate(trozos)
    wavfile.write(salida, SR, y)
    return capitulos, y.size / SR


def eventos_muestra(n_frases=9):
    """Primeras frases del guion (con sus pausas) para comparar voces."""
    ev, cuenta = [], 0
    for e in guion.leer():
        ev.append(e)
        cuenta += e[0] == "frase"
        if cuenta == n_frases:
            break
    return ev


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    modo = sys.argv[1] if len(sys.argv) > 1 else "muestras"
    if modo == "muestras":
        for nombre, voz in CANDIDATAS.items():
            print(nombre)
            _, dur = pista(eventos_muestra(), voz, OUT / f"muestra_voz_{nombre}.wav")
            print(f"  -> {dur:.0f} s")
    elif modo == "completo":
        voz = sys.argv[2]
        caps, dur = pista(guion.leer(), voz, OUT / "voz.wav")
        (OUT / "capitulos.json").write_text(json.dumps({"duracion": dur, "capitulos": caps}, ensure_ascii=False, indent=1))
        print(f"voz completa: {dur / 60:.1f} min")
