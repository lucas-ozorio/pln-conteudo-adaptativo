"""Bootstrap por QUESTÃO (cluster): os 180 itens vêm de só 15 perguntas, logo não são independentes.
Reamostra perguntas com reposição e recalcula as diferenças pareadas. Gera results/cluster_*.csv."""
import numpy as np
import pandas as pd

from _common import parse
from pln.common import ROOT, read_jsonl
from pln.data import qwk

a, cfg, out = parse(__doc__)
res = ROOT / "results"
B = 5000
rng = np.random.default_rng(0)

J = pd.read_csv(res / "e1_juiz_absoluto_por_item.csv")
qids = np.array(sorted(J.question_id.unique()))


def cluster_ci(wide: pd.DataFrame, qcol: pd.Series, x: str, y: str):
    d = (wide[x] - wide[y]).dropna()
    q = qcol.reindex(d.index)
    by = {k: v.values for k, v in d.groupby(q)}
    ks = np.array(list(by))
    stat = d.mean()
    bs = []
    for _ in range(B):
        pick = rng.choice(ks, size=len(ks), replace=True)
        bs.append(np.concatenate([by[k] for k in pick]).mean())
    lo, hi = np.quantile(bs, [0.025, 0.975])
    # p bilateral bootstrap (centrado): proporção de reamostras do outro lado do zero
    p = 2 * min((np.array(bs) <= 0).mean(), (np.array(bs) >= 0).mean())
    return stat, lo, hi, min(1.0, p), len(ks)


rows = []
qmap = J.drop_duplicates("item_id").set_index("item_id").question_id
dims = ["coerencia", "correcao_conceitual", "fidelidade_gabarito", "foco_na_lacuna", "utilidade_pedagogica", "adequacao_nivel",
        "q_alinhamento", "q_clareza", "q_relevancia"]
contrasts = [("A1_pipeline", "S_estatico"), ("A1_pipeline", "A0_direto"), ("A2_pipeline_verif", "A1_pipeline"), ("A0_direto", "S_estatico")]
for dm in dims:
    w = J.pivot(index="item_id", columns="condition", values=dm)
    for x, y in contrasts:
        s, lo, hi, p, k = cluster_ci(w, qmap, x, y)
        rows.append({"dimensao": dm, "contraste": f"{x} - {y}", "diff": s, "ic_lo": lo, "ic_hi": hi, "p_boot": p, "n_questoes": k})
C = pd.DataFrame(rows)
# Holm sobre as 6 dimensões de texto x contrastes principais (mesma família do artigo)
fam = C[C.dimensao.isin(dims[:6])].copy()
order = fam.p_boot.argsort().values
m = len(fam)
adj = np.empty(m)
run = 0.0
for rank, i in enumerate(order):
    run = max(run, (m - rank) * fam.p_boot.values[i])
    adj[i] = min(1.0, run)
C.loc[fam.index, "p_holm"] = adj
C.to_csv(res / "cluster_e1_contrastes.csv", index=False)

# E3: ganho do aluno simulado
ss = pd.DataFrame(read_jsonl(out / "student_sim.jsonl")).pivot_table(index="item_id", columns="condition", values="nota", aggfunc="first")
G = ss.drop(columns="PRE").sub(ss["PRE"], axis=0)
rows = []
for x, y in [("A1_pipeline", "S_estatico"), ("A1_pipeline", "A0_direto"), ("A2_pipeline_verif", "A1_pipeline"), ("A1_pipeline", "N_sem_material"), ("S_estatico", "N_sem_material")]:
    s, lo, hi, p, k = cluster_ci(G, qmap, x, y)
    rows.append({"contraste": f"{x} - {y}", "diff": s, "ic_lo": lo, "ic_hi": hi, "p_boot": p})
pd.DataFrame(rows).to_csv(res / "cluster_e3_contrastes.csv", index=False)
mean_rows = []
for c in G.columns:
    d = G[c].dropna()
    by = {k: v.values for k, v in d.groupby(qmap.reindex(d.index))}
    ks = np.array(list(by))
    bs = [np.concatenate([by[k] for k in rng.choice(ks, len(ks), True)]).mean() for _ in range(B)]
    mean_rows.append({"condicao": c, "ganho": d.mean(), "ic_lo": np.quantile(bs, .025), "ic_hi": np.quantile(bs, .975)})
pd.DataFrame(mean_rows).to_csv(res / "cluster_e3_ganho.csv", index=False)

# médias por condição com IC por questão (para o gráfico)
mrows = []
for c in J.condition.unique():
    for dm in dims:
        d = J[J.condition == c].set_index("item_id")[dm].dropna()
        if d.empty:
            continue
        by = {k: v.values for k, v in d.groupby(qmap.reindex(d.index))}
        ks = np.array(list(by))
        bs = [np.concatenate([by[k] for k in rng.choice(ks, len(ks), True)]).mean() for _ in range(B)]
        mrows.append({"condicao": c, "dimensao": dm, "media": d.mean(), "ic_lo": np.quantile(bs, .025), "ic_hi": np.quantile(bs, .975)})
pd.DataFrame(mrows).to_csv(res / "cluster_e1_medias.csv", index=False)

# E0: QWK com IC por questão
dg = pd.DataFrame([{"item_id": r["item_id"], "pred": r["diag"].get("nota_estimada")} for r in read_jsonl(out / "diagnosis.jsonl")])
dset = pd.DataFrame(read_jsonl(ROOT / "data" / "processed" / "diag_set.jsonl"))
d = dg.merge(dset[["item_id", "grade", "question_id"]], on="item_id").dropna(subset=["pred"])
d["pred"] = d.pred.astype(int)
by = {k: g for k, g in d.groupby("question_id")}
ks = np.array(list(by))
bs = []
for _ in range(B):
    g = pd.concat([by[k] for k in rng.choice(ks, len(ks), True)])
    bs.append(qwk(g.grade, g.pred))
pd.DataFrame([{"n": len(d), "QWK": qwk(d.grade, d.pred), "ic_lo": np.quantile(bs, .025), "ic_hi": np.quantile(bs, .975),
               "QWK_por_questao_min": min(qwk(g.grade, g.pred) for g in by.values()),
               "QWK_por_questao_max": max(qwk(g.grade, g.pred) for g in by.values())}]).to_csv(res / "cluster_e0_qwk.csv", index=False)
print("ok ->", sorted(p.name for p in res.glob("cluster_*.csv")))
