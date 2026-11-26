"""Concordância entre dois anotadores da auditoria do verificador (RQ4): kappa de Cohen.

Uso: python scripts/24_kappa_auditoria.py <planilha_anotador1.csv> <planilha_anotador2.csv>
Cada planilha tem as colunas id_auditoria e rotulo (correta | incorreta | duvidosa | nao_factual).
Gera results/rq4_auditoria_kappa.csv.  As planilhas e a chave ficam em human_eval/ (gitignored).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ROT = ["correta", "incorreta", "duvidosa", "nao_factual"]


def kappa(a, b, labels):
    a, b = np.asarray(a), np.asarray(b)
    po = (a == b).mean()
    pe = sum(((a == l).mean()) * ((b == l).mean()) for l in labels)
    return (po - pe) / (1 - pe) if pe < 1 else np.nan, po


def load(p):
    d = pd.read_csv(p, sep=None, engine="python", encoding="utf-8-sig", dtype=str)
    d["rotulo"] = d["rotulo"].str.strip().str.lower()
    return d[["id_auditoria", "rotulo"]]


if len(sys.argv) != 3:
    raise SystemExit(__doc__)
A, B = load(sys.argv[1]), load(sys.argv[2])
M = A.merge(B, on="id_auditoria", suffixes=("_1", "_2"))
ok = M.rotulo_1.isin(ROT) & M.rotulo_2.isin(ROT)
if (~ok).any():
    print(f"ATENÇÃO: {(~ok).sum()} linha(s) com rótulo ausente/inválido foram ignoradas.")
M = M[ok]
k4, po4 = kappa(M.rotulo_1, M.rotulo_2, ROT)
b1, b2 = (M.rotulo_1 == "incorreta"), (M.rotulo_2 == "incorreta")
kb, pob = kappa(b1.map({True: "i", False: "n"}), b2.map({True: "i", False: "n"}), ["i", "n"])
rows = [{"medida": "kappa de Cohen, 4 rótulos", "valor": k4, "concordancia_bruta": po4, "n": len(M)},
        {"medida": "kappa de Cohen, incorreta vs. não incorreta", "valor": kb, "concordancia_bruta": pob, "n": len(M)}]
out = pd.DataFrame(rows)
out.to_csv(ROOT / "results" / "rq4_auditoria_kappa.csv", index=False)
print(out.to_string(index=False))
print("\nMatriz de confusão (linhas: anotador 1; colunas: anotador 2):")
print(pd.crosstab(M.rotulo_1, M.rotulo_2).reindex(index=ROT, columns=ROT, fill_value=0).to_string())
print("\nInterpretação usual (Landis e Koch, 1977): <0,2 fraca; 0,2-0,4 razoável; 0,4-0,6 moderada; 0,6-0,8 substancial; >0,8 quase perfeita.")
