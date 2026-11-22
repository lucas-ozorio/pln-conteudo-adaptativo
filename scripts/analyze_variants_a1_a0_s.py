"""H-03/H-04 — Análise A1 (pipeline com diagnóstico) vs A0 (direto) vs S (estático), 100% offline.

Entradas (somente leitura): results/e1_juiz_absoluto_por_item.csv, outputs/materials.jsonl,
outputs/judgments_pair.jsonl, outputs/diagnosis.jsonl.
Saídas: results/herik_variants/*.csv + results/herik_variants/analise_a1_a0_s.md

Uso: python scripts/analyze_variants_a1_a0_s.py
Nenhuma chamada de API. A nota-ouro é usada apenas para estratificar a análise (nunca entra em prompt).
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
RES = ROOT / "results"
DST = RES / "herik_variants"
DST.mkdir(parents=True, exist_ok=True)

A1, A0, S, S0 = "A1_pipeline", "A0_direto", "S_estatico", "S0_gabarito"
CONDS = [A1, A0, S]
TEXT_DIMS = ["coerencia", "correcao_conceitual", "fidelidade_gabarito", "foco_na_lacuna", "utilidade_pedagogica", "adequacao_nivel"]
Q_DIMS = ["q_alinhamento", "q_clareza", "q_relevancia"]
KEY_DIMS = ["coerencia", "foco_na_lacuna", "utilidade_pedagogica", "adequacao_nivel", "q_relevancia", "q_clareza"]
ALL_DIMS = TEXT_DIMS + ["afirmacoes_incorretas"] + Q_DIMS
B = 5000
rng = np.random.default_rng(0)


def read_jsonl(p: Path) -> list[dict]:
    with open(p, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def fmt(x, nd=3):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    if isinstance(x, (float, np.floating)):
        return f"{x:.{nd}f}"
    return str(x)


def md_table(df: pd.DataFrame, nd=3) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(fmt(r[c], nd) for c in cols) + " |")
    return "\n".join(lines)


# ----------------------------------------------------------------------------- dados
J = pd.read_csv(RES / "e1_juiz_absoluto_por_item.csv")
J = J[J.condition.isin(CONDS + [S0])].copy()
J["abs_texto"] = J[TEXT_DIMS].mean(axis=1)  # média das 6 dimensões de texto
J["logw"] = np.log(J.n_palavras)
meta = J.drop_duplicates("item_id").set_index("item_id")[["grade", "question_id"]]
qmap = meta.question_id

mats = pd.DataFrame(read_jsonl(OUT / "materials.jsonl"))
mats_i = mats.set_index(["item_id", "condition"])

# nota estimada pelo diagnóstico usado no A1 (embutido no material) — confere com diagnosis.jsonl
diag_a1 = {r["item_id"]: r["diag"] for r in mats[mats.condition == A1].to_dict("records")}
diag_e0 = {r["item_id"]: r["diag"] for r in read_jsonl(OUT / "diagnosis.jsonl")}
meta["pred"] = [diag_a1[i].get("nota_estimada") for i in meta.index]
same = [diag_e0[i].get("nota_estimada") == diag_a1[i].get("nota_estimada") for i in meta.index if i in diag_e0]
meta["erro_diag"] = meta.pred - meta.grade
meta["grupo_diag"] = np.select([meta.erro_diag < 0, meta.erro_diag > 0], ["subavaliou (pred<ouro)", "superavaliou (pred>ouro)"],
                               "acertou (pred=ouro)")
meta["n_lacunas"] = [len(diag_a1[i].get("lacunas_prioritarias") or []) for i in meta.index]
meta["n_acertos_diag"] = [len(diag_a1[i].get("acertos") or []) for i in meta.index]
meta["n_erros_diag"] = [len(diag_a1[i].get("erros_conceituais") or []) for i in meta.index]


def wide(dim: str) -> pd.DataFrame:
    return J.pivot(index="item_id", columns="condition", values=dim)


W = {d: wide(d) for d in ALL_DIMS + ["abs_texto", "n_palavras", "logw"]}


def boot_ci(d: np.ndarray):
    d = np.asarray(d, float)
    d = d[~np.isnan(d)]
    if len(d) == 0:
        return np.nan, np.nan, np.nan
    bs = rng.choice(d, size=(2000, len(d)), replace=True).mean(axis=1)
    return d.mean(), *np.quantile(bs, [0.025, 0.975])


def cluster_boot(d: pd.Series, q: pd.Series = qmap):
    """IC95% e p bilateral por bootstrap de QUESTÃO (15 clusters), como em 08_cluster_bootstrap.py."""
    d = d.dropna()
    if len(d) == 0:
        return np.nan, np.nan, np.nan, np.nan
    by = [v.values for _, v in d.groupby(q.reindex(d.index))]
    k = len(by)
    bs = np.array([np.concatenate([by[j] for j in rng.integers(0, k, k)]).mean() for _ in range(B)])
    lo, hi = np.quantile(bs, [0.025, 0.975])
    p = min(1.0, 2 * min((bs <= 0).mean(), (bs >= 0).mean()))
    return d.mean(), lo, hi, p


def wilcoxon_p(d):
    d = np.asarray(d, float)
    nz = d[(d != 0) & ~np.isnan(d)]
    return stats.wilcoxon(nz).pvalue if len(nz) else 1.0


def ols_cluster(y: np.ndarray, X: np.ndarray, groups: np.ndarray):
    """OLS com erro-padrão robusto por cluster (CR1). Retorna beta, se."""
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    e = y - X @ beta
    meat = np.zeros((X.shape[1], X.shape[1]))
    G = np.unique(groups)
    for g in G:
        m = groups == g
        s = X[m].T @ e[m]
        meat += np.outer(s, s)
    n, k = X.shape
    c = len(G) / (len(G) - 1) * (n - 1) / (n - k)
    V = c * XtX_inv @ meat @ XtX_inv
    return beta, np.sqrt(np.diag(V))


md: list[str] = []
add = md.append

# ============================================================================ 0. visão geral
base = []
for c in CONDS:
    g = J[J.condition == c]
    base.append({"condicao": c, "n": len(g), "palavras_media": g.n_palavras.mean(), "palavras_mediana": g.n_palavras.median(),
                 "p10": g.n_palavras.quantile(.1), "p90": g.n_palavras.quantile(.9), "min": g.n_palavras.min(), "max": g.n_palavras.max(),
                 **{d: g[d].mean() for d in TEXT_DIMS + Q_DIMS}})
base = pd.DataFrame(base)
base.to_csv(DST / "h03_00_visao_geral.csv", index=False)

# contrastes pareados brutos (item) + cluster por questão
CONTR = [(A1, A0), (A1, S), (A0, S)]
rows = []
for x, y in CONTR:
    for d in ALL_DIMS + ["abs_texto"]:
        dd = (W[d][x] - W[d][y])
        m, lo, hi, p = cluster_boot(dd)
        rows.append({"contraste": f"{x} − {y}", "dimensao": d, "n": int(dd.notna().sum()), "diff": m, "ic_cluster_lo": lo,
                     "ic_cluster_hi": hi, "p_cluster": p, "p_wilcoxon_item": wilcoxon_p(dd),
                     "frac_x_maior": (dd > 0).mean(), "frac_empate": (dd == 0).mean(), "frac_y_maior": (dd < 0).mean()})
raw = pd.DataFrame(rows)
raw.to_csv(DST / "h03_01_contrastes_brutos.csv", index=False)

# ============================================================================ a) controle de tamanho
dw = (W["n_palavras"][A1] - W["n_palavras"][A0])
dist = []
for c in CONDS:
    v = W["n_palavras"][c]
    dist.append({"condicao": c, **{f"q{int(q*100)}": v.quantile(q) for q in [.05, .25, .5, .75, .95]}, "dp": v.std()})
for (x, y) in CONTR:
    v = W["n_palavras"][x] - W["n_palavras"][y]
    dist.append({"condicao": f"Δ {x} − {y}", **{f"q{int(q*100)}": v.quantile(q) for q in [.05, .25, .5, .75, .95]}, "dp": v.std(),
                 "frac_x_mais_longo": (v > 0).mean()})
dist = pd.DataFrame(dist)
dist.to_csv(DST / "h03_02_distribuicao_palavras.csv", index=False)

# a.1) regressão em formato longo com efeito fixo de item (within) + log(palavras), EP cluster por questão
reg_rows = []
L = J[J.condition.isin(CONDS)].copy()
L["dA1"] = (L.condition == A1).astype(float)
L["dS"] = (L.condition == S).astype(float)  # referência = A0
for d in KEY_DIMS + ["fidelidade_gabarito", "correcao_conceitual", "abs_texto"]:
    sub = L.dropna(subset=[d])
    dm = sub.groupby("item_id")[[d, "dA1", "dS", "logw"]].transform("mean")
    yv = (sub[d] - dm[d]).values
    for ctrl in (False, True):
        cols = ["dA1", "dS"] + (["logw"] if ctrl else [])
        X = (sub[cols] - dm[cols]).values
        beta, se = ols_cluster(yv, X, sub.question_id.values)
        r = {"dimensao": d, "controle_log_palavras": ctrl,
             "A1_menos_A0": beta[0], "ep_A1_A0": se[0], "p_A1_A0": 2 * stats.t.sf(abs(beta[0] / se[0]), 14),
             "S_menos_A0": beta[1], "ep_S_A0": se[1],
             "A1_menos_S": beta[0] - beta[1]}
        if ctrl:
            r["coef_log_palavras"], r["ep_log_palavras"] = beta[2], se[2]
            r["p_log_palavras"] = 2 * stats.t.sf(abs(beta[2] / se[2]), 14)
        reg_rows.append(r)
reg = pd.DataFrame(reg_rows)
reg.to_csv(DST / "h03_03_regressao_efeito_fixo_item.csv", index=False)

# a.2) diferença pareada A1−A0: Δnota = α + β·Δlog(palavras); α = vantagem de A1 com tamanho igual
dl = (W["logw"][A1] - W["logw"][A0])
pr_rows = []
for d in KEY_DIMS + ["abs_texto"]:
    dd = (W[d][A1] - W[d][A0])
    ok = dd.notna() & dl.notna()
    X = np.column_stack([np.ones(ok.sum()), dl[ok].values])
    beta, se = ols_cluster(dd[ok].values, X, qmap.reindex(dd[ok].index).values)
    rho, prho = stats.spearmanr(dw[ok], dd[ok])
    pr_rows.append({"dimensao": d, "diff_bruta": dd.mean(), "alfa_tamanho_igual": beta[0], "ep_alfa": se[0],
                    "p_alfa": 2 * stats.t.sf(abs(beta[0] / se[0]), 14), "beta_dlog": beta[1], "ep_beta": se[1],
                    "spearman_dpalavras_dnota": rho, "p_spearman": prho})
pr = pd.DataFrame(pr_rows)
pr.to_csv(DST / "h03_04_delta_palavras_vs_delta_nota.csv", index=False)

# a.3) faixas de Δpalavras (tercis) e subconjunto de tamanho pareado (|Δ| ≤ 15% do A0)
rel = dw / W["n_palavras"][A0]
bins = pd.qcut(dw, 3, labels=["T1 (Δ menor)", "T2", "T3 (Δ maior)"])
band_rows = []
for lab, idx in list(bins.groupby(bins, observed=True).groups.items()) + [("pareado |Δ|≤15%", rel[rel.abs() <= .15].index)]:
    idx = list(idx)
    r = {"faixa": str(lab), "n": len(idx), "Δpalavras_media": dw[idx].mean(), "Δpalavras_min": dw[idx].min(), "Δpalavras_max": dw[idx].max()}
    for d in KEY_DIMS + ["abs_texto"]:
        r[d] = (W[d][A1] - W[d][A0])[idx].mean()
    band_rows.append(r)
bands = pd.DataFrame(band_rows)
bands.to_csv(DST / "h03_05_faixas_delta_palavras.csv", index=False)

# ============================================================================ par-a-par (por item)
pw = pd.DataFrame(read_jsonl(OUT / "judgments_pair.jsonl"))


def pair_outcome(x, y):
    g = pw[(pw.x == x) & (pw.y == y)]
    per = g.groupby("item_id").winner.agg(list)

    def lab(ws):
        if all(w == x for w in ws):
            return "x_robusta"
        if all(w == y for w in ws):
            return "y_robusta"
        if all(w == "empate" for w in ws):
            return "empate"
        return "inconsistente"
    return per.map(lab)


PO = {(A1, A0): pair_outcome(A1, A0), (A1, S): pair_outcome(A1, S)}

# ============================================================================ b) estratificação por nota-ouro e por questão
strat_rows = []
for key, grp in [("nota_ouro", meta.grade), ("question_id", meta.question_id), ("grupo_diag", meta.grupo_diag)]:
    for val, idx in grp.groupby(grp).groups.items():
        idx = list(idx)
        r = {"estrato": key, "valor": val, "n": len(idx),
             "Δpalavras_A1_A0": dw[idx].mean()}
        for x, y in [(A1, A0), (A1, S)]:
            tag = "A1_A0" if y == A0 else "A1_S"
            for d in ["abs_texto", "foco_na_lacuna", "utilidade_pedagogica", "coerencia", "q_relevancia", "q_clareza"]:
                r[f"{tag}_{d}"] = (W[d][x] - W[d][y])[idx].mean()
            po = PO[(x, y)].reindex(idx)
            r[f"{tag}_par_vitA1"] = (po == "x_robusta").mean()
            r[f"{tag}_par_vitOutro"] = (po == "y_robusta").mean()
        strat_rows.append(r)
strat = pd.DataFrame(strat_rows)
strat.to_csv(DST / "h03_06_estratificacao.csv", index=False)

# questão: classificação A1 abre vantagem / empata / perde vs A0 (média de abs_texto + par-a-par)
qrows = []
for q, idx in meta.groupby("question_id").groups.items():
    idx = list(idx)
    d10 = (W["abs_texto"][A1] - W["abs_texto"][A0])[idx]
    d1s = (W["abs_texto"][A1] - W["abs_texto"][S])[idx]
    po = PO[(A1, A0)].reindex(idx)
    pos = PO[(A1, S)].reindex(idx)
    net0 = (po == "x_robusta").sum() - (po == "y_robusta").sum()
    nets = (pos == "x_robusta").sum() - (pos == "y_robusta").sum()
    qrows.append({"question_id": q, "n": len(idx), "acc_diag": (meta.loc[idx, "erro_diag"] == 0).mean(),
                  "erro_diag_medio": meta.loc[idx, "erro_diag"].mean(),
                  "Δabs_A1_A0": d10.mean(), "par_saldo_A1_A0": net0, "Δabs_A1_S": d1s.mean(), "par_saldo_A1_S": nets,
                  "Δfoco_A1_S": (W["foco_na_lacuna"][A1] - W["foco_na_lacuna"][S])[idx].mean(),
                  "Δq_relev_A1_A0": (W["q_relevancia"][A1] - W["q_relevancia"][A0])[idx].mean()})
qtab = pd.DataFrame(qrows)


def qclass(r):
    """Sinal 'forte' em cada critério: |Δabs| ≥ 0,15 ou |saldo de vitórias robustas| ≥ 2 (n=12 por questão)."""
    s1 = np.sign(r.Δabs_A1_A0) if abs(r.Δabs_A1_A0) >= .15 else 0
    s2 = np.sign(r.par_saldo_A1_A0) if abs(r.par_saldo_A1_A0) >= 2 else 0
    if s1 * s2 < 0:
        return "divergente"
    if s1 + s2 > 0:
        return "A1 > A0"
    if s1 + s2 < 0:
        return "A0 > A1"
    return "empate"


qtab["classe_A1_vs_A0"] = qtab.apply(qclass, axis=1)
qtab.to_csv(DST / "h03_07_por_questao.csv", index=False)

# ============================================================================ c) erro do diagnóstico
diag_rows = []
for gname, idx in meta.groupby("grupo_diag").groups.items():
    idx = list(idx)
    for d in ["abs_texto", "foco_na_lacuna", "utilidade_pedagogica", "coerencia", "fidelidade_gabarito", "q_relevancia"]:
        dd = (W[d][A1] - W[d][A0])[idx]
        m, lo, hi = boot_ci(dd.values)
        diag_rows.append({"grupo_diag": gname, "n": len(idx), "dimensao": d, "A1_menos_A0": m, "ic_lo": lo, "ic_hi": hi,
                          "A1_menos_S": (W[d][A1] - W[d][S])[idx].mean(), "A1_nivel": W[d][A1][idx].mean(), "A0_nivel": W[d][A0][idx].mean()})
diag_tab = pd.DataFrame(diag_rows)
# grupo × nota-ouro (contagens e Δabs)
cross = meta.assign(dabs=(W["abs_texto"][A1] - W["abs_texto"][A0]), dfoco=(W["foco_na_lacuna"][A1] - W["foco_na_lacuna"][A0]),
                    par=PO[(A1, A0)]).groupby(["grade", "grupo_diag"]).agg(
    n=("dabs", "size"), Δabs_A1_A0=("dabs", "mean"), Δfoco_A1_A0=("dfoco", "mean"),
    vit_A1=("par", lambda s: (s == "x_robusta").mean()), vit_A0=("par", lambda s: (s == "y_robusta").mean())).reset_index()
# teste: Δabs A1−A0 nos itens subavaliados vs acertados (Mann-Whitney, item) — exploratório
dabs = W["abs_texto"][A1] - W["abs_texto"][A0]
mw_sub = stats.mannwhitneyu(dabs[meta.grupo_diag.str.startswith("sub")], dabs[meta.grupo_diag.str.startswith("acert")]).pvalue
rho_err, p_err = stats.spearmanr(meta.erro_diag, dabs.reindex(meta.index))
diag_tab.to_csv(DST / "h03_08_erro_diagnostico.csv", index=False)
cross.to_csv(DST / "h03_09_erro_diag_x_nota_ouro.csv", index=False)

# ============================================================================ d) par-a-par detalhado
pair_rows = []
for (x, y), po in PO.items():
    for iid, lab in po.items():
        pair_rows.append({"par": f"{x} vs {y}", "item_id": iid, "question_id": meta.question_id[iid], "grade": meta.grade[iid],
                          "pred": meta.pred[iid], "resultado": {"x_robusta": f"{x.split('_')[0]} robusta", "y_robusta": f"{y.split('_')[0]} robusta"}.get(lab, lab),
                          "Δpalavras": W["n_palavras"][x][iid] - W["n_palavras"][y][iid],
                          "Δabs_texto": W["abs_texto"][x][iid] - W["abs_texto"][y][iid],
                          "Δfoco": W["foco_na_lacuna"][x][iid] - W["foco_na_lacuna"][y][iid],
                          "Δutilidade": W["utilidade_pedagogica"][x][iid] - W["utilidade_pedagogica"][y][iid],
                          "Δq_relevancia": W["q_relevancia"][x][iid] - W["q_relevancia"][y][iid]})
pairs = pd.DataFrame(pair_rows)
pairs.to_csv(DST / "h03_10_par_a_par_por_item.csv", index=False)
pair_sum = pairs.groupby(["par", "resultado"]).agg(n=("item_id", "size"), Δpalavras_media=("Δpalavras", "mean"),
                                                   Δpalavras_mediana=("Δpalavras", "median"),
                                                   Δabs_texto=("Δabs_texto", "mean"), Δfoco=("Δfoco", "mean"),
                                                   Δutilidade=("Δutilidade", "mean"),
                                                   frac_abs_concorda=("Δabs_texto", lambda s: np.nan)).reset_index()
# concordância absoluto × par: entre vitórias robustas, o vencedor também tem maior média absoluta?
for i, r in pair_sum.iterrows():
    s = pairs[(pairs.par == r.par) & (pairs.resultado == r.resultado)].Δabs_texto
    if r.resultado.startswith("A1"):
        pair_sum.loc[i, "frac_abs_concorda"] = (s > 0).mean()
    elif "robusta" in r.resultado:
        pair_sum.loc[i, "frac_abs_concorda"] = (s < 0).mean()
pair_sum.to_csv(DST / "h03_11_par_a_par_resumo.csv", index=False)
# Logística simples: P(A1 vence robusto | decisivo) ~ Δlog palavras (vs A0)
dec = pairs[(pairs.par == f"{A1} vs {A0}") & pairs.resultado.str.contains("robusta")].copy()
dec["y"] = dec.resultado.str.startswith("A1").astype(int)
dec["dlog"] = dl.reindex(dec.item_id).values
mw_len = stats.mannwhitneyu(dec[dec.y == 1].Δpalavras, dec[dec.y == 0].Δpalavras).pvalue

# ============================================================================ H-04 apoio 1: termos técnicos fora do gabarito
def nz(t: str) -> str:
    t = unicodedata.normalize("NFKD", (t or "").lower())
    return "".join(ch for ch in t if not unicodedata.combining(ch))


# radicais de termos técnicos de Biologia escolar (lista curada; termos genéricos como "ambiente" ficam de fora)
TECH = {"vacuo": "vacúolo", "mitocon": "mitocôndria", "reticul": "retículo endoplasmático", "ribossom": "ribossomo",
        "golgi": "complexo golgiense", "lisossom": "lisossomo", "clorop": "cloroplasto", "centriol": "centríolo",
        "antigen": "antígeno", "memoria imun": "memória imunológica", "linfocit": "linfócito", "hemoglob": "hemoglobina",
        "dna": "DNA", "alveol": "alvéolo", "enzima": "enzima", "glicog": "glicogênio", "alelo": "alelo", "dominan": "dominante",
        "recessiv": "recessivo", "nefron": "néfron", "transplant": "transplante", "espermatog": "espermatogênese",
        "espermiog": "espermiogênese", "capilar": "capilar", "atp": "ATP", "glicose": "glicose", "proteina": "proteína",
        "glandul": "glândula", "cilio": "cílio", "flagel": "flagelo"}
tech_rows = []
for iid in meta.index:
    q = meta.question_id[iid]
    ref = nz(" ".join(mats[(mats.item_id.str.startswith(f"q{q}_")) & mats.condition.isin([S0, S])].texto))
    dj = nz(json.dumps(diag_a1[iid], ensure_ascii=False))  # diagnóstico (inclui trechos literais do aluno como evidência)
    for c in [A1, A0]:
        t = nz(mats_i.loc[(iid, c), "texto"])
        for k, lab in TECH.items():
            if re.search(r"\b" + re.escape(k), t) and k not in ref:
                tech_rows.append({"item_id": iid, "question_id": q, "condicao": c, "termo": lab, "termo_no_diagnostico": k in dj})
tech = pd.DataFrame(tech_rows)
tech.to_csv(DST / "h04_01_termos_tecnicos_fora_do_gabarito.csv", index=False)
tech_sum = tech.groupby("condicao").agg(ocorrencias=("termo", "size"), itens=("item_id", "nunique"),
                                        ocorr_sem_rastro_no_diag=("termo_no_diagnostico", lambda s: int((~s).sum()))).reset_index()
tech_q = tech.groupby(["question_id", "condicao"]).size().unstack(fill_value=0).reset_index()
tech_q = tech_q[(tech_q[A0] + tech_q.get(A1, 0)) >= 3]

# vacúolo (caso do apêndice do main.tex): recorrência por condição
vac = []
for c in [S0, S, A0, A1]:
    sub = mats[mats.condition == c]
    hit = sub.texto.map(nz).str.contains(r"vacuol")
    q36 = sub.item_id.str.startswith("q36_")
    stud = sub.item_id.map(lambda i: "vacu" in nz(json.dumps(diag_a1[i], ensure_ascii=False)))
    vac.append({"condicao": c, "itens_q36": int(q36.sum()), "q36_com_vacuolo": int((hit & q36).sum()),
                "q36_com_vacuolo_e_aluno_citou": int((hit & q36 & stud).sum()), "total_com_vacuolo": int(hit.sum())})
vac = pd.DataFrame(vac)
vac.to_csv(DST / "h04_02_vacuolo.csv", index=False)

# ============================================================================ H-04 apoio 2: questões e lacunas
qrows = []
for (iid, c), r in mats_i.iterrows():
    if c in CONDS and iid in meta.index:
        qs = r.questoes if isinstance(r.questoes, list) else []
        qrows.append({"item_id": iid, "condicao": c, "palavras_por_enunciado": np.mean([len(q["enunciado"].split()) for q in qs])})
qlen = pd.DataFrame(qrows).groupby("condicao").palavras_por_enunciado.agg(["mean", "median"]).reset_index()
qlen.to_csv(DST / "h04_04_tamanho_enunciados.csv", index=False)
lac = meta.groupby("grade").agg(n=("n_lacunas", "size"), lacunas_media=("n_lacunas", "mean"),
                                frac_3_lacunas=("n_lacunas", lambda s: (s == 3).mean()), acertos_diag_media=("n_acertos_diag", "mean"),
                                erros_diag_media=("n_erros_diag", "mean")).reset_index().astype({"grade": int, "n": int})
lac.to_csv(DST / "h04_05_lacunas_por_nota_ouro.csv", index=False)
a0_below = (W["n_palavras"][A0] < 120).mean()

# ============================================================================ H-04: painel por item + casos selecionados
dpos = pd.DataFrame({
    "grade": meta.grade, "pred": meta.pred, "qid": meta.question_id,
    "w_A1": W["n_palavras"][A1], "w_A0": W["n_palavras"][A0], "w_S": W["n_palavras"][S],
    "abs_A1": W["abs_texto"][A1], "abs_A0": W["abs_texto"][A0], "abs_S": W["abs_texto"][S],
    "foco_A1": W["foco_na_lacuna"][A1], "foco_A0": W["foco_na_lacuna"][A0], "foco_S": W["foco_na_lacuna"][S],
    "util_A1": W["utilidade_pedagogica"][A1], "util_A0": W["utilidade_pedagogica"][A0], "util_S": W["utilidade_pedagogica"][S],
    "fid_A1": W["fidelidade_gabarito"][A1], "fid_A0": W["fidelidade_gabarito"][A0],
    "qrel_A1": W["q_relevancia"][A1], "qrel_A0": W["q_relevancia"][A0], "qrel_S": W["q_relevancia"][S],
    "qcla_A1": W["q_clareza"][A1], "qcla_A0": W["q_clareza"][A0],
    "par_A1_A0": PO[(A1, A0)], "par_A1_S": PO[(A1, S)],
})
dpos.index.name = "item_id"
dpos.reset_index().to_csv(DST / "h04_03_painel_itens.csv", index=False)

# Casos escolhidos após inspeção dos textos (critérios na seção H-04 do relatório). Os comentários são
# leitura humana dos materiais gerados; NÃO reproduzem respostas de alunos (CC BY-NC-SA 4.0).
CASES = [
    ("q36_3b0258ff", "(i)+(iii) A1 > A0 e S; A0 sai do gabarito",
     "Caso do apêndice do `main.tex`. O diagnóstico subestimou (nota 0 vs ouro 1) e não registrou o acerto do aluno "
     "(cloroplasto), mas o A1 também recebe a resposta e abre reconhecendo esse acerto; depois cobre exatamente as 3 lacunas "
     "(formato, parede celular, celulose) com analogia. O A0 cobre o mesmo núcleo, porém acrescenta vacúolo (ausente do gabarito "
     "e não citado pelo aluno). Questões: A1 testa as 3 lacunas (q_relevância 5,0); A0 inclui uma questão sobre membrana "
     "plasmática, fora das lacunas (3,67). Subavaliação aqui NÃO gerou sobre-remediação nociva."),
    ("q39_524585dd", "(i) A1 > A0 e S com diagnóstico conservador",
     "Ouro 2, diagnóstico 1. Ambos (A1 e A0) corrigem corretamente a concepção errada (metabolismo dependente de impulsos "
     "nervosos). A1 organiza a explicação em síntese/degradação → energia → funções e fecha com analogia; A0 diz o mesmo de "
     "forma mais compacta. Notas absolutas quase iguais (Δ≈0,17); a preferência par-a-par reflete organização/estilo, não "
     "conteúdo diferente. S (genérico) não toca a concepção errada (foco 2)."),
    ("q40_19368b9f", "(ii) A0 > A1 com diagnóstico correto",
     "Ouro 0 = diagnóstico 0. O diagnóstico identificou o erro central (o aluno associa fenótipo/genótipo a partes do corpo), "
     "mas o texto A1 vira uma explicação genérica de fenótipo×genótipo e não confronta esse erro; o A0 abre exatamente por ele "
     "(foco 5 vs 2; utilidade 5 vs 3). A1 ainda generaliza que o genótipo 'define as características da espécie'. "
     "Mostra que ter o erro no diagnóstico não garante que o gerador o use."),
    ("q37_4f1cecfe", "(ii) sobre-remediação/estreitamento com diagnóstico conservador",
     "Ouro 2, diagnóstico 1. O diagnóstico tratou como 'erro' a omissão do citoplasma e reduziu as lacunas a citoplasma/núcleo. "
     "Seguindo a instrução de focar ESTRITAMENTE nas lacunas, o A1 ignora as organelas que o aluno discutiu; o A0 dialoga com tudo "
     "o que o aluno escreveu (retículo liso/rugoso, golgiense, ribossomos). A0 e S vencem A1 nas duas ordens. Observação: o A0 "
     "afirma que um termo usado pelo aluno não existe, quando parece ser grafia incorreta de um termo real (cariolinfa) — "
     "a 'correção' do A0 também é imprecisa."),
    ("q42_9260e885", "(ii)+(iii invertido) erro do diagnóstico propagado pelo A1",
     "Ouro 2 = diagnóstico 2. O diagnóstico inventa um erro: diz que 'ducto deferente' e 'vasos deferentes' são estruturas "
     "diferentes — o próprio gabarito usa 'ductos deferentes'. O A1 transmite essa correção falsa ao aluno e, por seguir a lacuna "
     "'espermatogênese/espermiogênese' (ausente do gabarito), recomenda estudá-la e cria uma questão sobre ela (q_relevância 3,33 "
     "vs 4,67). O A0 não tem nenhum dos dois problemas. Na q42, 'espermatogênese' aparece em 3/12 textos A1 e 0/12 A0 — "
     "aqui é o A1 que sai do gabarito, via diagnóstico."),
    ("q45_2a7cf00f", "(iv) questões: lacunas 'forçadas' em aluno que já acertou",
     "Ouro 2 = diagnóstico 2; o aluno já dá a resposta central (leucócitos têm núcleo; hemácias não). O diagnóstico ainda assim "
     "precisa listar 3 lacunas (o formato pede 'até 3', e na prática são 3 em 179/180 itens) e escolhe tangentes. As questões A1 "
     "derivam para transporte de oxigênio e importância genérica dos cromossomos (q_relevância 3,67); as do A0 e do S testam o "
     "raciocínio central da pergunta (5,0 e 4,0). A0 vence nas duas ordens."),
    ("q43_da5a83a4", "(iv) questões: A1 mira as lacunas",
     "Ouro 2, diagnóstico 1. As lacunas (inspiração completa, diafragma, intercostais) viram três questões diretamente sobre "
     "elas (q_relevância 5,0); o A0 inclui uma questão de aplicação sobre 'situação em que a respiração fica difícil', menos "
     "ligada à lacuna (3,67). Exemplo do mecanismo pelo qual A1 ganha em q_relevância (+0,12 em média)."),
]
case_rows = []
for iid, tipo, nota in CASES:
    r = dpos.loc[iid]
    case_rows.append({"item_id": iid, "tipo": tipo, "ouro": int(r.grade), "diag": int(r.pred),
                      "palavras A1/A0/S": f"{int(r.w_A1)}/{int(r.w_A0)}/{int(r.w_S)}",
                      "foco A1/A0/S": f"{r.foco_A1:.0f}/{r.foco_A0:.0f}/{r.foco_S:.0f}",
                      "util A1/A0/S": f"{r.util_A1:.0f}/{r.util_A0:.0f}/{r.util_S:.0f}",
                      "q_relev A1/A0/S": f"{r.qrel_A1:.2f}/{r.qrel_A0:.2f}/{r.qrel_S:.2f}",
                      "par A1×A0": {"x_robusta": "A1", "y_robusta": "A0"}.get(r.par_A1_A0, "incons."),
                      "par A1×S": {"x_robusta": "A1", "y_robusta": "S"}.get(r.par_A1_S, "incons.")})
cases = pd.DataFrame(case_rows)
cases.to_csv(DST / "h04_06_casos_selecionados.csv", index=False)

# ============================================================================ relatório
SUMMARY = dict(same_diag=np.mean(same) if same else np.nan, n_sub=int((meta.erro_diag < 0).sum()),
               n_ok=int((meta.erro_diag == 0).sum()), n_sup=int((meta.erro_diag > 0).sum()))
g = lambda df, dim, col="diff": float(df.loc[dim, col])  # noqa: E731
r10 = raw[raw.contraste == f"{A1} − {A0}"].set_index("dimensao")
r1s = raw[raw.contraste == f"{A1} − {S}"].set_index("dimensao")
r0s = raw[raw.contraste == f"{A0} − {S}"].set_index("dimensao")
regc = reg[reg.controle_log_palavras].set_index("dimensao")
regu = reg[~reg.controle_log_palavras].set_index("dimensao")
prr = pr.set_index("dimensao")
po10, po1s = PO[(A1, A0)].value_counts(), PO[(A1, S)].value_counts()
w10, w01 = int(po10.get("x_robusta", 0)), int(po10.get("y_robusta", 0))
w1s, ws1 = int(po1s.get("x_robusta", 0)), int(po1s.get("y_robusta", 0))
p10 = stats.binomtest(w10, w10 + w01, .5).pvalue
p1s = stats.binomtest(w1s, w1s + ws1, .5).pvalue
ps = pair_sum.set_index(["par", "resultado"])
q42_a0 = int(((pairs.par == f"{A1} vs {A0}") & (pairs.resultado == "A0 robusta") & (pairs.question_id == 42)).sum())
g2ok = cross[(cross.grade == 2) & cross.grupo_diag.str.startswith("acert")].iloc[0]
cls = qtab.classe_A1_vs_A0.value_counts()
ts = tech_sum.set_index("condicao")
v0 = vac.set_index("condicao")
dsub = diag_tab.set_index(["grupo_diag", "dimensao"])


def sel(df, cols, nd=3):
    return md_table(df[cols], nd)


add("# H-03 / H-04 — A1 (pipeline com diagnóstico) vs A0 (direto) vs S (estático)")
add("")
add("> Gerado por `scripts/analyze_variants_a1_a0_s.py` (100% offline, sem chamadas de API). Fontes: "
    "`results/e1_juiz_absoluto_por_item.csv`, `outputs/materials.jsonl`, `outputs/judgments_pair.jsonl`, `outputs/diagnosis.jsonl`. "
    f"n = {len(meta)} itens (15 questões × 12 respostas; nota-ouro 0/1/2 balanceada). Juiz: `gemini-2.5-flash`; gerador: `gpt-4o-mini`. "
    "Como os 180 itens vêm de 15 questões, os ICs principais são por **bootstrap de questão** (cluster, B=5000) e as regressões usam "
    "EP robusto por questão; resultados por estrato são exploratórios (n pequeno, sem correção de multiplicidade). "
    f"A nota estimada embutida no A1 coincide com `diagnosis.jsonl` em {100*SUMMARY['same_diag']:.0f}% dos itens.")
add("")
add("## Resumo executivo")
add("")
add(f"1. **Tamanho não explica a vantagem nominal de A1 sobre A0 — mas essa vantagem já é pequena.** A1 é mais longo que A0 em "
    f"{100*(dw > 0).mean():.1f}% dos itens (Δ mediano {dw.median():.0f} palavras), então condição e tamanho quase se confundem no "
    f"contraste A1×A0. Três controles apontam na mesma direção: (a) o coeficiente de log(palavras) com efeito fixo de item não é "
    f"significativo em nenhuma dimensão (e é negativo em {int((regc.coef_log_palavras < 0).sum())} de {len(regc)}); (b) Δnota(A1−A0) não varia com Δpalavras (Spearman |ρ| ≤ "
    f"{prr.spearman_dpalavras_dnota.abs().max():.2f}) e é igual nos três tercis de Δpalavras; (c) S tem o mesmo tamanho de A1 "
    f"(~159) e fica **abaixo** do A0 (~120) em foco e utilidade. Com controle, a estimativa pontual de A1−A0 não encolhe, mas o "
    f"IC alarga e nenhuma dimensão fica significativa.")
add(f"2. **O que é robusto é A1/A0 > S (adaptação), não A1 > A0 (diagnóstico explícito).** Foco na lacuna: A1−S = "
    f"{g(r1s,'foco_na_lacuna'):+.2f} e A0−S = {g(r0s,'foco_na_lacuna'):+.2f}, contra A1−A0 = {g(r10,'foco_na_lacuna'):+.2f} "
    f"(IC cluster [{g(r10,'foco_na_lacuna','ic_cluster_lo'):.2f}; {g(r10,'foco_na_lacuna','ic_cluster_hi'):.2f}]). As diferenças "
    f"A1−A0 que sobrevivem ao bootstrap por questão são em dimensões de teto/estilo: coerência {g(r10,'coerencia'):+.2f}, adequação "
    f"{g(r10,'adequacao_nivel'):+.2f}, relevância das questões {g(r10,'q_relevancia'):+.2f} — e A1 perde em clareza das questões "
    f"({g(r10,'q_clareza'):+.2f}; enunciados mais longos).")
add(f"3. **Par-a-par:** A1 vence A0 de forma robusta em {w10}/180 itens vs {w01}/180 (p sinal = {p10:.3f}); {int(po10.get('inconsistente',0))} "
    f"são inconsistentes entre ordens. As vitórias robustas de A1 quase nunca aparecem na nota absoluta (só "
    f"{100*ps.loc[(f'{A1} vs {A0}','A1 robusta'),'frac_abs_concorda']:.0f}% têm média absoluta maior) — o juiz absoluto está no teto; "
    f"a preferência pareada capta organização/estilo. Δpalavras não distingue vitórias de A1 e de A0 (Mann-Whitney p = {mw_len:.2f}).")
add(f"4. **Erro do diagnóstico não prejudica A1 em média.** Nos {SUMMARY['n_sub']} itens subavaliados, A1−A0 (média do texto) = "
    f"{dsub.loc[('subavaliou (pred<ouro)','abs_texto'),'A1_menos_A0']:+.2f}; nos {SUMMARY['n_ok']} acertados = "
    f"{dsub.loc[('acertou (pred=ouro)','abs_texto'),'A1_menos_A0']:+.2f}; nos {SUMMARY['n_sup']} superavaliados = "
    f"{dsub.loc[('superavaliou (pred>ouro)','abs_texto'),'A1_menos_A0']:+.2f} (sub vs acerto: MW p = {mw_sub:.2f}; "
    f"ρ(erro, Δ) = {rho_err:.2f}). O ponto fraco é outro: **alunos com nota 2 e diagnóstico correto** — A0 vence par-a-par em "
    f"{100*g2ok.vit_A0:.0f}% vs A1 em {100*g2ok.vit_A1:.0f}% (n={int(g2ok.n)}).")
add(f"5. **Mecanismo qualitativo (H-04):** o diagnóstico sempre devolve 3 lacunas (179/180), inclusive para quem já acertou; "
    f"com a instrução de focar ESTRITAMENTE nelas, A1 (i) acerta quando as lacunas são reais, mas (ii) estreita ou deriva quando são "
    f"forçadas e (iii) propaga erros do próprio diagnóstico (q42). O 'A0 sai do gabarito' existe mas é modesto e localizado "
    f"(vacúolo em {int(v0.loc[A0,'q36_com_vacuolo'])}/12 itens da q36 vs {int(v0.loc[A1,'q36_com_vacuolo'])}/12 no A1; termos técnicos fora "
    f"do gabarito: {int(ts.loc[A0,'ocorrencias'])} ocorrências no A0 vs {int(ts.loc[A1,'ocorrencias'])} no A1).")
add("")

add("## 0. Visão geral (médias por condição)")
add("")
add(sel(base, ["condicao", "n", "palavras_media", "palavras_mediana", "p10", "p90"] + TEXT_DIMS + Q_DIMS, 2))
add("")
add("Contrastes pareados (média de diferenças por item; IC95% e p por bootstrap de questão; p Wilcoxon por item só como referência):")
add("")
add(sel(raw[raw.dimensao.isin(TEXT_DIMS + Q_DIMS + ["abs_texto"])],
        ["contraste", "dimensao", "diff", "ic_cluster_lo", "ic_cluster_hi", "p_cluster", "p_wilcoxon_item", "frac_x_maior", "frac_empate", "frac_y_maior"]))
add("")
add("`abs_texto` = média das 6 dimensões de texto. A grande fração de empates (60–90%) reflete o teto do juiz (notas 4,6–5,0).")
add("")

add("## H-03 a) Controle de tamanho")
add("")
add(f"Todas as condições tinham o mesmo orçamento (120–180 palavras, `config.yaml`). Mesmo assim A0 fica no piso: "
    f"{100*a0_below:.0f}% dos textos A0 têm < 120 palavras (A0 gera texto + questões num único JSON).")
add("")
add(md_table(dist, 1))
add("")
add("**a.1 Regressão com efeito fixo de item** (formato longo A1/A0/S, dentro do item; referência = A0; EP cluster por questão, gl=14):")
add("")
add(sel(reg, ["dimensao", "controle_log_palavras", "A1_menos_A0", "ep_A1_A0", "p_A1_A0", "S_menos_A0", "A1_menos_S", "coef_log_palavras", "ep_log_palavras", "p_log_palavras"]))
add("")
add("Leitura: o coeficiente de log(palavras) nunca é significativo e é majoritariamente negativo (positivo só em questões); ao controlar o tamanho, A1−A0 **não cai** "
    "(ex.: utilidade " f"{regu.loc['utilidade_pedagogica','A1_menos_A0']:+.2f} → {regc.loc['utilidade_pedagogica','A1_menos_A0']:+.2f}), "
    "mas o EP triplica porque A1 e A0 quase não se sobrepõem em tamanho — o dado não permite separar bem as duas coisas só pelo "
    "contraste A1×A0. A âncora mais informativa é S: mesmo tamanho de A1, notas menores que A0 em foco e utilidade.")
add("")
add("**a.2 Diferença pareada A1−A0: Δnota = α + β·Δlog(palavras)** (α = vantagem de A1 a tamanho igual; EP cluster):")
add("")
add(md_table(pr))
add("")
add("**a.3 Faixas de Δpalavras (tercis) e subconjunto pareado (|Δ| ≤ 15% do A0):**")
add("")
add(md_table(bands))
add("")
add(f"Conclusão a): A1−A0 é praticamente constante entre faixas de Δpalavras; não há indício de que a vantagem nominal de A1 seja "
    f"efeito de verbosidade do juiz. Em contrapartida, essa vantagem já é pequena e só é estatisticamente distinguível em "
    f"coerência, adequação ao nível e relevância das questões (bruto, cluster), e nenhuma delas resiste ao controle de tamanho "
    f"por falta de sobreposição. O resultado pareado `mais_longo_vence = 0,56` do `summary.md` é coerente com isso.")
add("")

add("## H-03 b) Estratificação por nota-ouro e por questão")
add("")
s_cols = ["estrato", "valor", "n", "Δpalavras_A1_A0", "A1_A0_abs_texto", "A1_A0_foco_na_lacuna", "A1_A0_utilidade_pedagogica",
          "A1_A0_q_relevancia", "A1_A0_par_vitA1", "A1_A0_par_vitOutro", "A1_S_foco_na_lacuna", "A1_S_utilidade_pedagogica",
          "A1_S_par_vitA1", "A1_S_par_vitOutro"]
add(sel(strat[strat.estrato == "nota_ouro"], s_cols, 2))
add("")
add("`par_vitA1` / `par_vitOutro` = fração de itens com vitória robusta (mesmo vencedor nas duas ordens).")
add("")
st = strat[strat.estrato == "nota_ouro"].set_index("valor")
add(f"- A vantagem de A1 sobre A0 é maior na nota 1 (Δabs {st.loc[1,'A1_A0_abs_texto']:+.2f}; utilidade "
    f"{st.loc[1,'A1_A0_utilidade_pedagogica']:+.2f}) e desaparece na nota 2: no par-a-par, A0 vence {100*st.loc[2,'A1_A0_par_vitOutro']:.0f}% "
    f"vs A1 {100*st.loc[2,'A1_A0_par_vitA1']:.0f}%. Contra S, a nota 2 também é onde S mais vence A1 ({100*st.loc[2,'A1_S_par_vitOutro']:.0f}%).")
add("- Padrão consistente com o mecanismo do H-04: para quem já sabe quase tudo, o diagnóstico precisa 'achar' lacunas e o A1 "
    "foca nelas, enquanto A0/S cobrem o núcleo da pergunta.")
add("")
add("**Por questão** (n=12 cada; classe: sinal concordante entre |Δabs| ≥ 0,15 e |saldo de vitórias robustas| ≥ 2):")
add("")
add(md_table(qtab, 2))
add("")
add(f"Contagem: {', '.join(f'{k}: {v}' for k, v in cls.items())}. A q42 (aparelho reprodutor masculino) concentra {q42_a0} das "
    f"{w01} vitórias robustas de A0; A1 abre vantagem mais clara em q37, q47, q49 e q50 no par-a-par e em q36/q45 na nota absoluta. "
    f"A acurácia do diagnóstico por questão não prediz essa classe (q44 tem a pior acurácia, 25%, e A1 ainda vence). "
    f"Cautela: com n=12, limiares baixos e muitos sinais 'A1 > A0' vindo de um único critério (ex.: q36 e q45 só pela nota absoluta; "
    f"q45 tem saldo par-a-par negativo), a contagem superestima a consistência; o sinal mais firme é o A0 > A1 na q42.")
add("")

add("## H-03 c) Cruzamento com o erro do diagnóstico (nota_estimada − ouro)")
add("")
add(sel(diag_tab, ["grupo_diag", "n", "dimensao", "A1_menos_A0", "ic_lo", "ic_hi", "A1_menos_S", "A1_nivel", "A0_nivel"]))
add("")
add("IC por bootstrap de item (exploratório). Cruzamento com a nota-ouro:")
add("")
add(md_table(cross))
add("")
add(f"- Subavaliação (conservadorismo, n={SUMMARY['n_sub']}, quase toda em ouro=2) **não** derruba A1 frente a A0 na média "
    f"(Δabs ≈ 0) e até melhora a relevância das questões (+{dsub.loc[('subavaliou (pred<ouro)','q_relevancia'),'A1_menos_A0']:.2f}, IC exclui 0): "
    "mais lacunas declaradas → questões mais 'mirando' algo.")
add(f"- A célula problemática é **ouro=2 com diagnóstico correto** (n={int(g2ok.n)}): A0 vence par-a-par {100*g2ok.vit_A0:.0f}% vs A1 "
    f"{100*g2ok.vit_A1:.0f}%. Ou seja, o risco não é o diagnóstico errar a nota, e sim as lacunas listadas para alunos fortes serem "
    "periféricas ou incorretas (ver q42, q45).")
add("- Superavaliação (n=36) tende a favorecer A1 (Δabs +0,17, utilidade +0,22), mas o IC inclui 0.")
add("")

add("## H-03 d) Par-a-par detalhado")
add("")
add(md_table(pair_sum, 2))
add("")
add(f"- A1×A0: {w10} vitórias robustas de A1, {w01} de A0 (p = {p10:.3f}). A1×S: {w1s} vs {ws1} (p = {p1s:.3f}).")
add(f"- Δpalavras médio nas vitórias de A1 ({ps.loc[(f'{A1} vs {A0}','A1 robusta'),'Δpalavras_media']:.0f}) é próximo do das vitórias "
    f"de A0 ({ps.loc[(f'{A1} vs {A0}','A0 robusta'),'Δpalavras_media']:.0f}) e dos inconsistentes; MW p = {mw_len:.2f}. A1 é mais longo "
    "em praticamente todos os pares, inclusive nos que perde.")
add("- Concordância absoluto×par baixa: nas vitórias robustas de A1 sobre A0, só "
    f"{100*ps.loc[(f'{A1} vs {A0}','A1 robusta'),'frac_abs_concorda']:.0f}% têm média absoluta maior (o resto é empate no teto). Contra S, "
    f"{100*ps.loc[(f'{A1} vs {S}','A1 robusta'),'frac_abs_concorda']:.0f}% — aí a diferença é de conteúdo (foco +"
    f"{ps.loc[(f'{A1} vs {S}','A1 robusta'),'Δfoco']:.1f}).")
add("- Lista completa por item: `h03_10_par_a_par_por_item.csv`.")
add("")

add("## H-04 — Análise qualitativa pareada")
add("")
add("Seleção: a partir de `h04_03_painel_itens.csv`, foram filtrados (i) vitórias robustas de A1 sobre A0 **e** S, (ii) vitórias "
    "robustas de A0 sobre A1, (iii) itens com termos fora do gabarito, (iv) maiores |Δ q_relevância|; dentro de cada grupo, "
    "escolhidos itens com diagnóstico certo e errado e de questões diferentes. Os textos foram lidos integralmente; abaixo só há "
    "resumos (nenhuma resposta de aluno é reproduzida).")
add("")
add(md_table(cases))
add("")
for iid, tipo, nota in CASES:
    add(f"- **`{iid}` — {tipo}.** {nota}")
add("")
add("### (iii) A0 introduz conteúdo fora do gabarito? (checagem de recorrência)")
add("")
add("Termos técnicos de uma lista curada que aparecem no texto mas não no gabarito nem no S da questão; "
    "`sem_rastro_no_diag` = o termo também não aparece no diagnóstico (que inclui trechos literais do aluno), "
    "ou seja, provável acréscimo do gerador e não resposta ao que o aluno escreveu.")
add("")
add(md_table(tech_sum))
add("")
add(md_table(tech_q))
add("")
add(md_table(vac))
add("")
add(f"- O padrão existe, mas é **modesto e localizado** nas questões de citologia (q36/q37) e em 'DNA' (q40/q45). Parte relevante "
    f"dos termos do A0 responde ao que o aluno escreveu (só {int(ts.loc[A0,'ocorr_sem_rastro_no_diag'])}/{int(ts.loc[A0,'ocorrencias'])} sem rastro "
    f"no diagnóstico vs {int(ts.loc[A1,'ocorr_sem_rastro_no_diag'])}/{int(ts.loc[A1,'ocorrencias'])} no A1). A fidelidade ao gabarito medida "
    f"pelo juiz é igual (A1−A0 = {g(r10,'fidelidade_gabarito'):+.2f}).")
add(f"- O vacúolo do apêndice é recorrente na q36 ({int(v0.loc[A0,'q36_com_vacuolo'])}/12 no A0), mas em "
    f"{int(v0.loc[A0,'q36_com_vacuolo_e_aluno_citou'])} desses itens o aluno citou vacúolos (o A0 respondeu ao aluno); só os demais, "
    "como o `q36_3b0258ff` do apêndice, são acréscimo do gerador. Recomenda-se descrever no artigo como 'ocasional', não como padrão sistemático do A0.")
add("- Simetricamente, o A1 também sai do gabarito quando o **diagnóstico** sai (espermatogênese na q42; correção falsa "
    "'ducto ≠ vasos deferentes'). O vocabulário extra do A1 é sobretudo de **analogias** (receita, alarme de fumaça, detergente, "
    "soldados), que o prompt do A1 pede e o do A0 não.")
add("")
add("### (iv) Questões geradas")
add("")
add(md_table(qlen, 1))
add("")
add(f"- A1 ganha em relevância das questões ({g(r10,'q_relevancia'):+.2f} vs A0; {g(r1s,'q_relevancia'):+.2f} vs S) porque as questões "
    f"recebem explicitamente a lista de lacunas (q43). Perde em clareza ({g(r10,'q_clareza'):+.2f}) com enunciados mais longos/compostos "
    "('Compare X e discorra sobre Y').")
add("- Quando as lacunas são forçadas (aluno forte), a mesma ligação direta transforma lacunas periféricas em questões periféricas (q45, q42).")
add("")
add(md_table(lac, 2))
add("")

add("## Implicações para RQ2/RQ3 (papel real da etapa explícita de diagnóstico)")
add("")
add("1. **RQ2 (adaptação ajuda?)** — Sim, e de forma robusta: A1 e A0 superam S em foco na lacuna (~+0,8) e utilidade (+0,4/+0,5), "
    "com tamanho igual entre A1 e S. A vantagem vem de **condicionar na resposta do aluno**, presente em ambas.")
add("2. **RQ3 (diagnóstico explícito agrega?)** — Pouco, e não por causa de tamanho. A1 > A0 aparece em coerência, adequação e "
    "relevância das questões e na preferência par-a-par (34×14), mas não em foco/utilidade/fidelidade. Sugestão de redação: "
    "'o diagnóstico explícito estrutura e direciona o material (sobretudo as questões), mas não aumenta de forma mensurável o "
    "foco nas lacunas em relação à geração direta condicionada na resposta'.")
add("3. **O diagnóstico é um ponto de falha também, não só de ganho.** Ele sempre produz 3 lacunas, e o A1 segue-as estritamente: "
    "ajuda alunos de nota 1, mas para alunos de nota 2 estreita o texto (q37), gera questões periféricas (q45) e pode propagar "
    "erros do próprio diagnóstico (q42). Isso é mais relevante que o conservadorismo de nota (RQ1): errar a nota não piorou A1 em média.")
add("4. **Ressalva de desenho (importante para o texto do artigo):** A1 e A0 não diferem só no diagnóstico. O prompt do A1 pede "
    "analogia do cotidiano e tom encorajador e gera texto e questões em chamadas separadas (questões recebem as lacunas); "
    "o A0 gera tudo num único JSON e recebe os conceitos-chave. Parte da vantagem de estilo do A1 (coerência, analogias, "
    "preferência par-a-par) pode vir dessas diferenças de prompt, não do diagnóstico em si.")
add("5. **Sugestões acionáveis:** (a) permitir 0–3 lacunas no diagnóstico (\"nenhuma lacuna relevante\" para respostas completas) "
    "— conecta com H-02; (b) verificar as lacunas/erros do diagnóstico contra o gabarito antes da geração (o A2 já faz isso no "
    "texto, mas não no diagnóstico); (c) para uma ablação limpa de RQ3, usar o prompt do A1 com o diagnóstico vazio/omitido.")
add("6. **Limitações:** juiz único no teto (empates de 60–90%), n=12 por questão, estratos sem correção de multiplicidade; "
    "a checagem de termos técnicos é um proxy lexical curado, não anotação humana.")
add("")
add("## Arquivos gerados (`results/herik_variants/`)")
add("")
for f in sorted(DST.glob("*.csv")):
    add(f"- `{f.name}`")
(DST / "analise_a1_a0_s.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print(f"OK: {DST / 'analise_a1_a0_s.md'} ({len(md)} linhas) + {len(list(DST.glob('*.csv')))} CSVs")
