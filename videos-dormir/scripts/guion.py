"""Lee guion.txt y lo convierte en una lista de eventos: capítulos, frases y pausas."""
import re
from pathlib import Path

import proyecto

ROOT = proyecto.ROOT
GUION = proyecto.DIR / "guion.txt"
PAUSA_POR_DEFECTO = 1.2  # segundos entre dos frases seguidas sin [n]


def leer(path=None):
    eventos = []  # ("capitulo", titulo) | ("frase", texto) | ("pausa", segundos)
    for linea in Path(path or GUION).read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or (linea.startswith("#") and not linea.startswith("##")):
            continue
        if linea.startswith("##"):
            eventos.append(("capitulo", linea.lstrip("#").strip()))
        elif m := re.fullmatch(r"\[(\d+(?:\.\d+)?)\]", linea):
            eventos.append(("pausa", float(m.group(1))))
        else:
            if eventos and eventos[-1][0] == "frase":
                eventos.append(("pausa", PAUSA_POR_DEFECTO))
            eventos.append(("frase", linea))
    return eventos


def frases(eventos):
    return [texto for tipo, texto in eventos if tipo == "frase"]


if __name__ == "__main__":
    ev = leer()
    fr = frases(ev)
    palabras = sum(len(f.split()) for f in fr)
    caracteres = sum(len(f) for f in fr)
    pausas = sum(v for t, v in ev if t == "pausa")
    habla = palabras / 1.6  # voz lenta de meditación ≈ 95 palabras/min
    print(f"frases: {len(fr)}  palabras: {palabras}  caracteres: {caracteres}")
    print(f"pausas: {pausas/60:.1f} min  voz estimada: {habla/60:.1f} min  total ≈ {(pausas+habla)/60:.1f} min")
