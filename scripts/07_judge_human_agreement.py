"""Concordância humano x juiz LLM e humano x humano, por dimensão. Lê human_eval/planilha_*.csv preenchidas."""
import glob

import numpy as np
import pandas as pd
from scipy import stats

from _common import parse
from pln.common import ROOT
from pln.data import qwk
from pln.judge import TEXT_DIMS

a, cfg, out = parse(__doc__)
hd = ROOT / "human_eval"
key = pd.read_csv(hd / "CHAVE_condicoes_NAO_COMPARTILHAR.csv")
files = [f for f in glob.glob(str(hd / "planilha_*.csv")) if "avaliadores" not in f]
if not files:
    raise SystemExit("Nenhuma planilha preenchida encontrada (human_eval/planilha_<avaliador>.csv).")
H = []
for f in files:
    d = pd.read_csv(f)
    d["avaliador"] = f.split("planilha_")[-1].removesuffix(".csv")
    H.append(d)
H = pd.concat(H).merge(key, on="id_avaliacao")
jud = pd.read_json(out / "judgments_abs.jsonl", lines=True)
jt = pd.json_normalize(jud.to_dict("records"))
jt = jt.rename(columns={f"texto.{d}": d for d in TEXT_DIMS}).groupby(["item_id", "condition"], as_index=False).mean(numeric_only=True)
M = H.merge(jt, left_on=["item_id", "condicao"], right_on=["item_id", "condition"], suffixes=("_h", "_j"))
rows = []
for d in TEXT_DIMS:
    h = M.groupby(["item_id", "condicao"])[f"{d}_h"].mean()
    j = M.groupby(["item_id", "condicao"])[f"{d}_j"].mean()
    rows.append({"dimensao": d, "n": len(h), "Spearman(humano médio, juiz)": stats.spearmanr(h, j).statistic,
                 "QWK(humano arred., juiz arred.)": qwk(h.round().astype(int), j.round().astype(int), labels=(1, 2, 3, 4, 5))})
res = pd.DataFrame(rows)
print(res.to_string(index=False))
if H.avaliador.nunique() > 1:  # concordância humano-humano (teto de referência para o juiz)
    ks = []
    ev = sorted(H.avaliador.unique())
    for d in TEXT_DIMS:
        w = H.pivot_table(index="id_avaliacao", columns="avaliador", values=d)
        for i in range(len(ev)):
            for k in range(i + 1, len(ev)):
                s = w[[ev[i], ev[k]]].dropna()
                if len(s) > 2:
                    ks.append({"dimensao": d, "par": f"{ev[i]}~{ev[k]}", "n": len(s), "QWK": qwk(s.iloc[:, 0].astype(int), s.iloc[:, 1].astype(int), labels=(1, 2, 3, 4, 5))})
    print("\nHumano x humano:\n", pd.DataFrame(ks).to_string(index=False))
(ROOT / "results").mkdir(exist_ok=True)
res.to_csv(ROOT / "results" / "e1_concordancia_humano_juiz.csv", index=False)
