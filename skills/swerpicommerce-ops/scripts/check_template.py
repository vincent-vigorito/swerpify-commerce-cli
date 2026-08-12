#!/usr/bin/env python3
"""
Controllo di bilanciamento dei blocchi Django in un template del tema.

Perché serve: un template con {% if %}/{% for %}/{% block %} sbilanciati non
degrada, manda in 500 TUTTE le pagine di quel tipo — e l'API accetta il PUT
senza fiatare, perché non valida la sintassi dei tag. Il 500 non dice né quale
file né quale riga.

Uso:
    python check_template.py <file.html>              # da file locale
    swc ... | python check_template.py -              # da stdin

Exit code: 0 se bilanciato, 1 se ci sono errori (utile in una catena && prima del PUT).
"""
import re
import sys

APRE = {
    "if": "endif",
    "for": "endfor",
    "block": "endblock",
    "with": "endwith",
    "comment": "endcomment",
    "spaceless": "endspaceless",
    "autoescape": "endautoescape",
    "blocktrans": "endblocktrans",
    "filter": "endfilter",
}
CHIUDE = {v: k for k, v in APRE.items()}


def controlla(testo):
    stack, errori = [], []
    for n, riga in enumerate(testo.split("\n"), 1):
        for tag in re.findall(r"\{%\s*(\w+)", riga):
            if tag in APRE:
                stack.append((tag, n))
            elif tag in CHIUDE:
                if not stack:
                    errori.append(f"riga {n}: '{tag}' senza apertura")
                elif stack[-1][0] != CHIUDE[tag]:
                    apert, riga_ap = stack[-1]
                    errori.append(f"riga {n}: '{tag}' ma il blocco aperto è '{apert}' (riga {riga_ap})")
                    stack.pop()
                else:
                    stack.pop()
    for tag, n in stack:
        errori.append(f"blocco '{tag}' aperto alla riga {n} e mai chiuso")
    return errori


def main():
    if len(sys.argv) != 2:
        print(__doc__.strip())
        return 2
    sorgente = sys.argv[1]
    testo = sys.stdin.read() if sorgente == "-" else open(sorgente, encoding="utf-8").read()

    errori = controlla(testo)
    nome = "(stdin)" if sorgente == "-" else sorgente
    print(f"Template: {nome}  —  {testo.count(chr(10)) + 1} righe")
    if not errori:
        print("  ✓ blocchi bilanciati — si può caricare")
        return 0
    for e in errori:
        print(f"  ❌ {e}")
    print(f"\n  {len(errori)} problema/i — NON caricare: il PUT passa ma le pagine di questo tipo daranno 500.")
    print("  Causa più frequente: coda di una versione precedente rimasta dopo un merge.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
