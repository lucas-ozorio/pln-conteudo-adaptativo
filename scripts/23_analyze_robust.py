"""Análise da rodada de robustez (PRE_REGISTRO.md). Lê outputs/ e outputs_robust/; escreve results_robust/*.csv e RESULTADOS_ROBUSTEZ.md.
Os veredictos (replica / equivalente / não pior / inconclusivo) seguem EXATAMENTE os critérios do pré-registro.
Tolera dados ausentes: pode ser executado com a rodada incompleta."""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

from _common import parse
from pln.common import ROOT, read_jsonl
from pln.stats import cluster_ci, holm

warnings.filterwarnings("ignore")
a, cfg, _ = parse(__doc__)
OUT = ROOT / ("outputs_robust_mock" if a.mock else "outputs_robust")
RES = ROOT / ("results_robust_mock" if a.mock else "results_robust")
RES.mkdir(exist_ok=True)
MARGIN = 0.25  # margem de equivalência (PRE_REGISTRO.md)
PRIM = ["foco_na_lacuna", "utilidade_pedagogica"]
TEXT = ["coerencia", "correcao_conceitual", "fidelidade_gabarito", "foco_na_lacuna", "utilidade_pedagogica", "adequacao_nivel"]
md = ["# Resultados da rodada de robustez" + (" (MOCK)" if a.mock else ""),
      "", "Critérios, hipóteses e margens: ver `PRE_REGISTRO.md` (commit anterior às rodadas). Todos os IC são bootstrap por questão (15 clusters).", ""]

# ------------------------------------------------------------------ dados
proc = ROOT / "data" / "processed"
pilot = pd.DataFrame(read_jsonl(proc / "pilot_set.jsonl"))
g3 = pd.DataFrame(read_jsonl(proc / "grade3_set.jsonl")) if (proc / "grade3_set.jsonl").exists() else pd.DataFrame(columns=pilot.columns)
ITEMS = pd.concat([pilot, g3]).drop_duplicates("item_id").set_index("item_id")
QMAP = ITEMS.question_id
TOPIC = {q: ("células e metabolismo" if q <= 39 else "genética" if q <= 41 else "sistemas do corpo humano") for q in ITEMS.question_id.unique()}


def flat(r, judge, mode):
    row = {"judge": judge, "mode": mode, "item_id": r["item_id"], "condition": r["condition"]}
    row.update({k: v for k, v in (r.get("texto") or {}).items()})
    qs = r.get("questoes") or []
    if qs:
        for src, dst in (("relevancia_lacuna", "q_relevancia"), ("alinhamento_gabarito", "q_alinhamento"), ("clareza", "q_clareza")):
            v = [x[src] for x in qs if x.get(src) is not None]
            row[dst] = float(np.mean(v)) if v else np.nan
    return row


rows = [flat(r, "J1", "abs") for r in read_jsonl(ROOT / "outputs" / "judgments_abs.jsonl") if r.get("rep", 0) == 0]
rows += [flat(r, r["judge"], r["mode"]) for r in read_jsonl(OUT / "judgments_abs.jsonl")]
D = pd.DataFrame(rows)
D = D.groupby(["judge", "mode", "item_id", "condition"], as_index=False).mean(numeric_only=True) if len(D) else D
pairs_rows = [{**r, "judge": "J1"} for r in read_jsonl(ROOT / "outputs" / "judgments_pair.jsonl")] + read_jsonl(OUT / "judgments_pair.jsonl")
PW = pd.DataFrame(pairs_rows)
print("julgamentos:", D.groupby(["judge", "mode"]).size().to_dict() if len(D) else "nenhum")


def wide(judge, mode, dim, conds, items=None):
    s = D[(D.judge == judge) & (D["mode"] == mode) & D.condition.isin(conds)]
    if items is not None:
        s = s[s.item_id.isin(items)]
    if dim not in s or s.empty:
        return pd.DataFrame()
    return s.pivot(index="item_id", columns="condition", values=dim)


def contrast(judge, mode, dim, x, y, items=None, **kw):
    w = wide(judge, mode, dim, [x, y], items)
    if w.empty or x not in w or y not in w:
        return None
    d = (w[x] - w[y]).dropna()
    if len(d) < 10:
        return None
    r = cluster_ci(d, QMAP.reindex(d.index), **kw)
    return {"judge": judge, "mode": mode, "dim": dim, "x": x, "y": y, **r}


def verdict_equiv(r):
    if r is None:
        return "sem dados"
    if r["lo"] > -MARGIN and r["hi"] < MARGIN:
        return "equivalente (IC dentro de ±0,25)"
    if r["lo"] > 0:
        return "x melhor"
    if r["hi"] < 0:
        return "y melhor"
    return "inconclusivo"


PILOT_IDS = list(pilot.item_id)
G3_IDS = list(g3.item_id)

# ================================================================== H1: replicação do efeito principal A1 - S
H1 = []
reps = [("piloto, J1 (original)", "J1", "A1_pipeline", "S_estatico"), ("piloto, J2", "J2", "A1_pipeline", "S_estatico"),
        ("semente 1, J1", "J1", "A1_pipeline@s1", "S_estatico@s1"), ("semente 2, J1", "J1", "A1_pipeline@s2", "S_estatico@s2"),
        ("gerador 2 (DeepSeek), J1", "J1", "A1_pipeline@g2", "S_estatico@g2"), ("gerador 2 (DeepSeek), J2", "J2", "A1_pipeline@g2", "S_estatico@g2"),
        ("diagnóstico v2, J1", "J1", "A1_pipeline@v2", "S_estatico"), ("diagnóstico v2, J2", "J2", "A1_pipeline@v2", "S_estatico")]
for lab, jd, x, y in reps:
    rs = [contrast(jd, "abs", d, x, y, items=PILOT_IDS) for d in PRIM]
    if any(r is None for r in rs):
        continue
    ph = holm([r["p_boot"] for r in rs])
    for r, p in zip(rs, ph):
        H1.append({"replica": lab, "dim": r["dim"], "A1-S": r["est"], "lo": r["lo"], "hi": r["hi"], "p_holm": p,
                   "replica_criterio": "sim" if (r["est"] > 0 and r["lo"] > 0) else "não"})
H1 = pd.DataFrame(H1)
if len(H1):
    H1.to_csv(RES / "h1_replicacao_A1_menos_S.csv", index=False)
    md += ["## H1. O efeito A1 > S replica? (foco na lacuna e utilidade; 1–5)", H1.round(3).to_markdown(index=False), "",
           f"**Critério do pré-registro** (diferença positiva e IC95% sem zero nas duas dimensões): replicou em "
           f"{int((H1.groupby('replica').replica_criterio.apply(lambda s: (s == 'sim').all())).sum())} de {H1.replica.nunique()} réplicas.", ""]

# ================================================================== H2: A1 vs A0 (equivalência)
H2 = []
for lab, jd, x, y in [("piloto, J1", "J1", "A1_pipeline", "A0_direto"), ("piloto, J2", "J2", "A1_pipeline", "A0_direto"),
                      ("semente 1, J1", "J1", "A1_pipeline@s1", "A0_direto@s1"), ("semente 2, J1", "J1", "A1_pipeline@s2", "A0_direto@s2"),
                      ("gerador 2, J1", "J1", "A1_pipeline@g2", "A0_direto@g2"), ("gerador 2, J2", "J2", "A1_pipeline@g2", "A0_direto@g2")]:
    for d in PRIM:
        r = contrast(jd, "abs", d, x, y, items=PILOT_IDS)
        if r:
            H2.append({"replica": lab, "dim": d, "A1-A0": r["est"], "lo": r["lo"], "hi": r["hi"], "veredito": verdict_equiv(r)})
H2 = pd.DataFrame(H2)
if len(H2):
    H2.to_csv(RES / "h2_A1_vs_A0.csv", index=False)
    md += ["## H2. Diagnóstico explícito (A1) vs geração direta (A0)", H2.round(3).to_markdown(index=False), ""]

# ================================================================== H3: ablação limpa; H4: diagnóstico v2
H3 = []
for jd in ("J1", "J2"):
    for d in PRIM + ["coerencia", "correcao_conceitual", "fidelidade_gabarito", "adequacao_nivel", "q_relevancia"]:
        for lab, x, y in (("A1ø (sem diagnóstico) − A1", "A1_nodiag", "A1_pipeline"), ("A1ø − A0", "A1_nodiag", "A0_direto"),
                          ("A1ø − S", "A1_nodiag", "S_estatico")):
            r = contrast(jd, "abs", d, x, y, items=PILOT_IDS)
            if r:
                H3.append({"juiz": jd, "contraste": lab, "dim": d, "est": r["est"], "lo": r["lo"], "hi": r["hi"], "veredito": verdict_equiv(r)})
H3 = pd.DataFrame(H3)
if len(H3):
    H3.to_csv(RES / "h3_ablacao_sem_diagnostico.csv", index=False)
    md += ["## H3. Ablação limpa: A1 com diagnóstico vazio (A1ø)", H3[H3.dim.isin(PRIM)].round(3).to_markdown(index=False), ""]
H4 = []
for jd in ("J1", "J2"):
    for d in PRIM + ["coerencia", "correcao_conceitual", "fidelidade_gabarito", "adequacao_nivel", "q_relevancia"]:
        r = contrast(jd, "abs", d, "A1_pipeline@v2", "A1_pipeline", items=PILOT_IDS)
        if r:
            H4.append({"juiz": jd, "dim": d, "A1v2-A1v0": r["est"], "lo": r["lo"], "hi": r["hi"],
                       "nao_pior(lo>-0,25)": "sim" if r["lo"] > -MARGIN else "não", "melhor(lo>0)": "sim" if r["lo"] > 0 else "não"})
H4 = pd.DataFrame(H4)
if len(H4):
    H4.to_csv(RES / "h4_diagnostico_v2.csv", index=False)
    md += ["## H4. Diagnóstico calibrado (v2) não é pior que o original (v0)?", H4.round(3).to_markdown(index=False), ""]

# ================================================================== H5: juiz cego à resposta do aluno
H5 = []
BL = ["coerencia", "correcao_conceitual", "fidelidade_gabarito", "completude", "adequacao_nivel", "qualidade_geral"]
for jd in ("J1", "J2"):
    for d in BL:
        for lab, x, y in (("A1 − S", "A1_pipeline", "S_estatico"), ("A0 − S", "A0_direto", "S_estatico"), ("A2 − S", "A2_pipeline_verif", "S_estatico")):
            r = contrast(jd, "blind", d, x, y, items=PILOT_IDS)
            if r:
                H5.append({"juiz": jd, "contraste": lab, "dim": d, "est": r["est"], "lo": r["lo"], "hi": r["hi"],
                           "não_pior(lo>-0,25)": "sim" if r["lo"] > -MARGIN else "não"})
H5 = pd.DataFrame(H5)
if len(H5):
    H5.to_csv(RES / "h5_juiz_cego.csv", index=False)
    md += ["## H5. Qualidade como material de estudo SEM ver a resposta do aluno (A1 vs S)", H5[H5.contraste == "A1 − S"].round(3).to_markdown(index=False), ""]

# ================================================================== concordância entre juízes (piloto, abs)
AG = []
if len(D):
    j1 = D[(D.judge == "J1") & (D["mode"] == "abs") & D.item_id.isin(PILOT_IDS) & D.condition.isin(["S0_gabarito", "S_estatico", "A0_direto", "A1_pipeline", "A2_pipeline_verif"])]
    j2 = D[(D.judge == "J2") & (D["mode"] == "abs") & D.item_id.isin(PILOT_IDS) & D.condition.isin(["S0_gabarito", "S_estatico", "A0_direto", "A1_pipeline", "A2_pipeline_verif"])]
    m = j1.merge(j2, on=["item_id", "condition"], suffixes=("_1", "_2"))
    for d in TEXT:
        if f"{d}_1" in m and f"{d}_2" in m and m[[f"{d}_1", f"{d}_2"]].dropna().shape[0] > 20:
            s = m[[f"{d}_1", f"{d}_2"]].dropna()
            from sklearn.metrics import cohen_kappa_score
            AG.append({"dim": d, "n": len(s), "spearman": stats.spearmanr(s.iloc[:, 0], s.iloc[:, 1]).statistic,
                       "QWK": cohen_kappa_score(s.iloc[:, 0].round().astype(int), s.iloc[:, 1].round().astype(int), weights="quadratic"),
                       "J1 média": s.iloc[:, 0].mean(), "J2 média": s.iloc[:, 1].mean(),
                       "J1 % nota 5": (s.iloc[:, 0] == 5).mean(), "J2 % nota 5": (s.iloc[:, 1] == 5).mean()})
AG = pd.DataFrame(AG)
if len(AG):
    AG.to_csv(RES / "juizes_concordancia.csv", index=False)
    md += ["## Concordância entre os dois juízes (piloto, notas absolutas, 5 condições × 180 itens)", AG.round(3).to_markdown(index=False), ""]
    # mesmas direções nos contrastes principais do piloto?
    dr = []
    for x, y in (("A1_pipeline", "S_estatico"), ("A0_direto", "S_estatico"), ("A1_pipeline", "A0_direto"), ("A2_pipeline_verif", "A1_pipeline")):
        for d in TEXT:
            r1, r2 = contrast("J1", "abs", d, x, y, items=PILOT_IDS), contrast("J2", "abs", d, x, y, items=PILOT_IDS)
            if r1 and r2:
                dr.append({"contraste": f"{x} − {y}", "dim": d, "J1": r1["est"], "J2": r2["est"], "J1_ic_sem_zero": r1["lo"] > 0 or r1["hi"] < 0,
                           "J2_ic_sem_zero": r2["lo"] > 0 or r2["hi"] < 0, "mesmo_sinal": np.sign(r1["est"]) == np.sign(r2["est"])})
    dr = pd.DataFrame(dr)
    if len(dr):
        dr.to_csv(RES / "juizes_contrastes_J1_J2.csv", index=False)
        md += [f"Os dois juízes têm o **mesmo sinal** em {int(dr.mesmo_sinal.sum())} de {len(dr)} contrastes do piloto; "
               f"ICs sem zero: J1 em {int(dr.J1_ic_sem_zero.sum())}, J2 em {int(dr.J2_ic_sem_zero.sum())}.", "", dr.round(3).to_markdown(index=False), ""]

# viés de posição do J2
if len(PW):
    P2 = PW[PW.judge == "J2"]
    if len(P2):
        rows2 = []
        for (x, y), g in P2.groupby(["x", "y"]):
            nt = g[g.winner != "empate"]
            per = g.groupby("item_id").winner.agg(list)
            rows2.append({"par": f"{x} vs {y}", "itens": len(per), "1º vence": nt.pos_first_won.mean() if len(nt) else np.nan,
                          "mesmo veredito nas 2 ordens": per.map(lambda w: len(set(w)) == 1).mean(),
                          "x vence nas 2": per.map(lambda w: all(v == x for v in w)).mean(), "y vence nas 2": per.map(lambda w: all(v == y for v in w)).mean()})
        pd.DataFrame(rows2).to_csv(RES / "j2_pareado.csv", index=False)
        md += ["## Juiz 2 par-a-par (duas ordens)", pd.DataFrame(rows2).round(3).to_markdown(index=False), ""]

# ================================================================== H10: modelo misto sobre as DIFERENÇAS por item
# d_i = nota(x) - nota(y) do item i; d_i = mu + u_questao + e_i, com u_questao ~ N(0, tau2): inclui a heterogeneidade do EFEITO entre
# questões (um modelo só com intercepto aleatório de questão sobre as notas dá ICs estreitos demais, pois ignora isso).
MM = []
try:
    import statsmodels.formula.api as smf

    for jd in ("J1", "J2"):
        for d in PRIM:
            for x, y in (("A1_pipeline", "S_estatico"), ("A1_pipeline", "A0_direto"), ("A1_nodiag", "A1_pipeline"), ("A1_pipeline@v2", "A1_pipeline")):
                w = wide(jd, "abs", d, [x, y], PILOT_IDS)
                if w.empty or x not in w or y not in w:
                    continue
                dd = (w[x] - w[y]).dropna()
                df = pd.DataFrame({"d": dd.values, "q": QMAP.reindex(dd.index).values})
                m_ = smf.mixedlm("d ~ 1", df, groups=df["q"]).fit(reml=True)
                ci = m_.conf_int().loc["Intercept"]
                bt = cluster_ci(dd, QMAP.reindex(dd.index))
                MM.append({"juiz": jd, "dim": d, "contraste": f"{x} − {y}", "est_misto": m_.params["Intercept"], "lo_misto": ci[0], "hi_misto": ci[1],
                           "p_misto": m_.pvalues["Intercept"], "tau_questao": float(np.sqrt(max(m_.cov_re.iloc[0, 0], 0))),
                           "est_bootstrap": bt["est"], "lo_boot": bt["lo"], "hi_boot": bt["hi"]})
except Exception as e:  # noqa: BLE001
    md += [f"(modelo misto não executado: {type(e).__name__}: {e})", ""]
MM = pd.DataFrame(MM)
if len(MM):
    MM.to_csv(RES / "h10_modelo_misto.csv", index=False)
    md += ["## Robustez: modelo linear misto sobre as diferenças por item (efeito aleatório de questão) vs. bootstrap por questão",
           MM.round(3).to_markdown(index=False), ""]

# ================================================================== por tópico
TP = []
for d in PRIM:
    for tp in sorted(set(TOPIC.values())):
        its = [i for i in PILOT_IDS if TOPIC[QMAP[i]] == tp]
        r = contrast("J1", "abs", d, "A1_pipeline", "S_estatico", items=its)
        r2 = contrast("J2", "abs", d, "A1_pipeline", "S_estatico", items=its)
        if r:
            TP.append({"tópico": tp, "questões": len({QMAP[i] for i in its}), "dim": d, "J1 A1−S": r["est"], "J1 lo": r["lo"], "J1 hi": r["hi"],
                       "J2 A1−S": r2["est"] if r2 else np.nan})
TP = pd.DataFrame(TP)
if len(TP):
    TP.to_csv(RES / "por_topico.csv", index=False)
    md += ["## Consistência entre tópicos (substituto parcial de um 2º conjunto de dados; IC com poucas questões por tópico)", TP.round(3).to_markdown(index=False), ""]

# ================================================================== H6: nota 3 (sobre-remediação)
G3R = []
for jd in ("J1", "J2"):
    for d in ["sobre_remediacao", "reconhece_acertos", "utilidade_pedagogica", "coerencia", "correcao_conceitual", "fidelidade_gabarito"]:
        for lab, x, y in (("A1 − S", "A1_pipeline", "S_estatico"), ("A0 − S", "A0_direto", "S_estatico"), ("A1 − A0", "A1_pipeline", "A0_direto")):
            r = contrast(jd, "overrem", d, x, y, items=G3_IDS)
            if r:
                G3R.append({"juiz": jd, "contraste": lab, "dim": d, "est": r["est"], "lo": r["lo"], "hi": r["hi"]})
    for d in ["foco_na_lacuna", "utilidade_pedagogica"]:
        r = contrast(jd, "abs", d, "A1_pipeline", "S_estatico", items=G3_IDS)
        if r:
            G3R.append({"juiz": jd, "contraste": "A1 − S (juiz padrão, nota 3)", "dim": d, "est": r["est"], "lo": r["lo"], "hi": r["hi"]})
G3R = pd.DataFrame(G3R)
if len(G3R):
    G3R.to_csv(RES / "h6_nota3_sobre_remediacao.csv", index=False)
    g3m = []
    for jd in ("J1", "J2"):
        s = D[(D.judge == jd) & (D["mode"] == "overrem") & D.item_id.isin(G3_IDS)]
        if len(s):
            g = s.groupby("condition")[["sobre_remediacao", "reconhece_acertos"]].mean().reset_index()
            g.insert(0, "juiz", jd)
            g3m.append(g)
    if g3m:
        md += ["## H6. Respostas nota 3 (60 itens): sobre-remediação (1 = nenhuma, 5 = severa) e reconhecimento dos acertos",
               pd.concat(g3m).round(3).to_markdown(index=False), "", G3R.round(3).to_markdown(index=False), ""]

# ================================================================== H7: pós-teste de transferência
TR = pd.DataFrame(read_jsonl(OUT / "transfer.jsonl"))
if len(TR):
    W = TR.pivot(index="item_id", columns="condition", values="media")
    rows7 = []
    for c in [c for c in W.columns]:
        d = W[c].dropna()
        r = cluster_ci(d, QMAP.reindex(d.index))
        rows7.append({"condição": c, "n": r["n"], "nota média (0-3) no pós-teste": r["est"], "lo": r["lo"], "hi": r["hi"]})
    t1 = pd.DataFrame(rows7)
    t1.to_csv(RES / "h7_transferencia_medias.csv", index=False)
    rows7 = []
    for x, y in (("S_estatico", "N_sem_material"), ("A0_direto", "N_sem_material"), ("A1_pipeline", "N_sem_material"), ("A2_pipeline_verif", "N_sem_material"),
                 ("S0_gabarito", "N_sem_material"), ("A1_pipeline", "S_estatico"), ("A1_pipeline", "A0_direto"), ("A2_pipeline_verif", "A1_pipeline")):
        if x in W and y in W:
            d = (W[x] - W[y]).dropna()
            r = cluster_ci(d, QMAP.reindex(d.index))
            rows7.append({"contraste": f"{x} − {y}", "est": r["est"], "lo": r["lo"], "hi": r["hi"], "p_boot": r["p_boot"], "n": r["n"]})
    t2 = pd.DataFrame(rows7)
    t2["p_holm"] = holm(t2.p_boot) if len(t2) else np.nan
    t2.to_csv(RES / "h7_transferencia_contrastes.csv", index=False)
    # gargalo de informação: quanto das anotações do aluno é cópia literal do material?
    def tri(t):
        w = str(t).lower().split()
        return {tuple(w[i:i + 3]) for i in range(len(w) - 2)}
    MT = R_mats = {(r["item_id"], r["condition"]): r["texto"] for r in read_jsonl(ROOT / "outputs" / "materials.jsonl")}
    cp = []
    for _, r in TR.iterrows():
        mt = MT.get((r.item_id, r.condition))
        if mt and tri(r.anotacoes):
            cp.append({"condição": r.condition, "copia_3g": len(tri(r.anotacoes) & tri(mt)) / len(tri(r.anotacoes))})
    cpd = pd.DataFrame(cp).groupby("condição").copia_3g.mean().reset_index() if cp else pd.DataFrame()
    md += ["## H7 (exploratório). Pós-teste de transferência: o aluno simulado perde acesso ao material e responde a 3 questões novas",
           t1.round(3).to_markdown(index=False), "", t2.round(3).to_markdown(index=False), ""]
    if len(cpd):
        cpd.to_csv(RES / "h7_copia_nas_anotacoes.csv", index=False)
        md += ["Cópia literal (trigramas) das anotações do aluno em relação ao material lido:", cpd.round(3).to_markdown(index=False), ""]

# ================================================================== custo
from pln.robust import spent_usd
md += ["## Custo desta rodada (estimado pelos tokens e preços de lista)", f"US$ {spent_usd(OUT / 'usage.jsonl'):.2f}", ""]
(ROOT / ("RESULTADOS_ROBUSTEZ_MOCK.md" if a.mock else "RESULTADOS_ROBUSTEZ.md")).write_text("\n".join(md), encoding="utf-8")
print("escrito RESULTADOS_ROBUSTEZ.md;", {p.name for p in RES.glob('*.csv')})
