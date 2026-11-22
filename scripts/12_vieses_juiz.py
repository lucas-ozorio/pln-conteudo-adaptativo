"""Vieses e confiabilidade do juiz LLM (offline, sem chamadas de LLM).

1. Saturação: fração de notas 5 (e >=4) por dimensão e condição.
2. Mesmo texto, notas diferentes? S_estatico e S0_gabarito entregam o MESMO texto a todos os alunos de uma questão;
   coerência, correção, fidelidade e nível não deveriam variar entre esses itens. Variação = ruído ou contaminação pela
   resposta do aluno (o juiz vê a resposta). Testa também se essas notas acompanham a nota-ouro do aluno.
3. Verbosidade: Spearman(palavras, nota) DENTRO de cada condição gerada e regressão com IC por questão.
4. Par-a-par: viés de posição, "mais longo vence", consistência entre ordens, pares idênticos e concordância com o juiz absoluto.

Saídas: results/vies_*.csv, paper/tables/tab_bias.tex.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

from _common import parse
from pln.common import ROOT, read_jsonl
from pln.judge import TEXT_DIMS
from pln.stats import cluster_boot

a, cfg, out = parse(__doc__)
warnings.filterwarnings("ignore", category=stats.ConstantInputWarning)
RES = ROOT / "results"
TAB = ROOT / "paper" / "tables"
J = pd.read_csv(RES / "e1_juiz_absoluto_por_item.csv")
CONDS = cfg["pipeline"]["conditions"]
INDEP = ["coerencia", "correcao_conceitual", "fidelidade_gabarito", "adequacao_nivel"]  # não dependem do aluno
DEP = ["foco_na_lacuna", "utilidade_pedagogica"]  # dependem do aluno por definição

# ------------------------------------------------------------------ 1. saturação
sat = []
for c in CONDS:
    s = J[J.condition == c]
    for d in TEXT_DIMS:
        sat.append({"condicao": c, "dimensao": d, "media": s[d].mean(), "frac_5": (s[d] == 5).mean(), "frac_ge4": (s[d] >= 4).mean()})
SAT = pd.DataFrame(sat)
SAT.to_csv(RES / "vies_saturacao.csv", index=False)

# ------------------------------------------------------------------ 2. mesmo texto -> mesma nota?
mats = pd.DataFrame(read_jsonl(out / "materials.jsonl"))
mt = []
for c in ("S_estatico", "S0_gabarito"):
    m = mats[mats.condition == c].merge(J[["item_id", "question_id"]].drop_duplicates(), on="item_id")
    n_textos = m.groupby("question_id").texto.nunique()
    assert (n_textos == 1).all(), f"{c}: esperado 1 texto por questão"
    s = J[J.condition == c]
    for d in INDEP + DEP + ["afirmacoes_incorretas"]:
        g = s.groupby("question_id")[d]
        r = cluster_boot(s, "question_id", lambda x, d=d: stats.spearmanr(x.grade, x[d]).statistic)
        mt.append({"condicao": c, "dimensao": d, "tipo": "independe do aluno" if d in INDEP + ["afirmacoes_incorretas"] else "depende do aluno",
                   "frac_questoes_nota_constante": (g.nunique() == 1).mean(), "dp_intra_questao_medio": g.std(ddof=0).mean(),
                   "amplitude_intra_questao_media": (g.max() - g.min()).mean(),
                   "spearman(nota_ouro, nota_juiz)": r["est"], "ic_lo": r["lo"], "ic_hi": r["hi"]})
MT = pd.DataFrame(mt)
MT.to_csv(RES / "vies_mesmo_texto.csv", index=False)

# ------------------------------------------------------------------ 3. verbosidade dentro da condição + regressão com IC por questão
vb = []
for c in ("A0_direto", "A1_pipeline", "A2_pipeline_verif"):
    s = J[J.condition == c]
    for d in TEXT_DIMS:
        r = cluster_boot(s, "question_id", lambda x, d=d: stats.spearmanr(x.n_palavras, x[d]).statistic)
        vb.append({"escopo": c, "dimensao": d, "estatistica": "spearman(palavras, nota)", "est": r["est"], "ic_lo": r["lo"], "ic_hi": r["hi"]})
G = J[J.condition != "S0_gabarito"].copy()
outras = [c for c in CONDS if c not in ("S0_gabarito", "S_estatico")]


def coef_len(x: pd.DataFrame, d: str) -> float:  # nota ~ condição + log(palavras); devolve o coef. de log(palavras)
    X = np.column_stack([np.ones(len(x))] + [(x.condition == c).astype(float).values for c in outras] + [np.log(x.n_palavras.clip(lower=1))])
    return np.linalg.lstsq(X, x[d].values, rcond=None)[0][-1]


for d in TEXT_DIMS:
    r = cluster_boot(G, "question_id", lambda x, d=d: coef_len(x, d))
    vb.append({"escopo": "S+A0+A1+A2 (controla condição)", "dimensao": d, "estatistica": "coef log(palavras)", "est": r["est"], "ic_lo": r["lo"], "ic_hi": r["hi"]})
VB = pd.DataFrame(vb)
VB.to_csv(RES / "vies_verbosidade_cluster.csv", index=False)

# ------------------------------------------------------------------ 4. par-a-par
pw = pd.DataFrame(read_jsonl(out / "judgments_pair.jsonl"))
Lw = mats.set_index(["item_id", "condition"]).n_palavras.to_dict()
ident = {(r.item_id) for r in mats[mats.condition == "A2_pipeline_verif"].itertuples()
         if not r.verif["reescrito"]}
pr = []
for (x, y), g in pw.groupby(["x", "y"], sort=False):
    if (x, y) == ("A2_pipeline_verif", "A1_pipeline"):
        g = g[~g.item_id.isin(ident)]  # pares idênticos (não reescritos) são analisados à parte
    per = g.groupby("item_id").winner.agg(list)
    robust = per.map(lambda ws: ws[0] if len(set(ws)) == 1 and ws[0] != "empate" else None).dropna()
    nt = g[g.winner != "empate"]
    longer = [w == (x if Lw[(i, x)] > Lw[(i, y)] else y) for i, w in zip(g.item_id, g.winner)
              if w != "empate" and Lw[(i, x)] != Lw[(i, y)]]
    # concordância com o juiz absoluto: sinal da diferença absoluta x o vencedor robusto
    ag = {}
    for d in ("utilidade_pedagogica", "media_6"):
        w = J.assign(media_6=J[TEXT_DIMS].mean(axis=1)).pivot(index="item_id", columns="condition", values=d)
        diff = (w[x] - w[y]).reindex(robust.index)
        ok = diff != 0
        ag[d] = ((diff[ok] > 0) == (robust[ok] == x)).mean() if ok.any() else np.nan
        ag[f"n_{d}"] = int(ok.sum())
    pr.append({"par": f"{x} vs {y}", "itens": len(per), "primeiro_vence(nao_empates)": nt.pos_first_won.mean(),
               "mais_longo_vence": np.mean(longer) if longer else np.nan, "consistencia_ordem": per.map(lambda ws: len(set(ws)) == 1).mean(),
               "n_vitorias_robustas": len(robust), "concorda_abs_utilidade": ag["utilidade_pedagogica"],
               "n_abs_utilidade": ag["n_utilidade_pedagogica"], "concorda_abs_media6": ag["media_6"], "n_abs_media6": ag["n_media_6"]})
gi = pw[(pw.x == "A2_pipeline_verif") & (pw.y == "A1_pipeline") & pw.item_id.isin(ident)]
pr.append({"par": "A2 vs A1, materiais IDENTICOS", "itens": gi.item_id.nunique(), "primeiro_vence(nao_empates)": np.nan,
           "mais_longo_vence": np.nan, "consistencia_ordem": gi.groupby("item_id").winner.agg(lambda w: len(set(w)) == 1).mean(),
           "n_vitorias_robustas": 0, "frac_empate": (gi.winner == "empate").mean()})
PR = pd.DataFrame(pr)
PR.to_csv(RES / "vies_pareado.csv", index=False)

# ------------------------------------------------------------------ tabelas do artigo
SH = {"S0_gabarito": "S0", "S_estatico": "S", "A0_direto": "A0", "A1_pipeline": "A1", "A2_pipeline_verif": "A2"}
DIM = {"coerencia": "Coherence", "correcao_conceitual": "Correctness", "fidelidade_gabarito": "Faithfulness",
       "foco_na_lacuna": "Gap focus", "utilidade_pedagogica": "Usefulness", "adequacao_nivel": "Level"}
L = [r"\begin{tabular}{lcccc}", r"\toprule",
     r"Dimension & \% of 5s (A1) & \% of 5s (S) & Same-text questions & $\rho$(gold, score) \\",
     r" & & & with constant score (S) & on identical S text \\", r"\midrule"]
for d in TEXT_DIMS:
    f1 = SAT[(SAT.condicao == "A1_pipeline") & (SAT.dimensao == d)].frac_5.iloc[0]
    fs = SAT[(SAT.condicao == "S_estatico") & (SAT.dimensao == d)].frac_5.iloc[0]
    r = MT[(MT.condicao == "S_estatico") & (MT.dimensao == d)].iloc[0]
    L.append(f"{DIM[d]} & {100 * f1:.0f}\\% & {100 * fs:.0f}\\% & {100 * r.frac_questoes_nota_constante:.0f}\\% & "
             f"${r['spearman(nota_ouro, nota_juiz)']:+.2f}$ [{r.ic_lo:.2f}, {r.ic_hi:.2f}] \\\\")
L += [r"\bottomrule", r"\end{tabular}"]
(TAB / "tab_bias.tex").write_text("\n".join(L), encoding="utf-8")

L = [r"\begin{tabular}{lcccc}", r"\toprule",
     r"Pair ($x$ vs $y$) & 1st wins & Longer wins & Same verdict & Agrees w/ absolute \\", r"\midrule"]
for _, r in PR[PR.n_vitorias_robustas > 0].iterrows():
    x, y = [s.strip() for s in r.par.split(" vs ")]
    rot = f"{SH[x]} vs {SH[y]}" + ("$^\\dagger$" if x == "A2_pipeline_verif" else "")  # A2 vs A1: só textos reescritos
    L.append(f"{rot} & {100 * r['primeiro_vence(nao_empates)']:.0f}\\% & {100 * r.mais_longo_vence:.0f}\\% & "
             f"{100 * r.consistencia_ordem:.0f}\\% & {100 * r.concorda_abs_utilidade:.0f}\\% ($n{{=}}{int(r.n_abs_utilidade)}$) \\\\")
L += [r"\bottomrule", r"\end{tabular}"]
(TAB / "tab_bias_pairwise.tex").write_text("\n".join(L), encoding="utf-8")

pd.set_option("display.width", 220)
print(SAT.pivot(index="dimensao", columns="condicao", values="frac_5").round(2).to_string())
print(MT.round(3).to_string(index=False))
print(VB.round(3).to_string(index=False))
print(PR.round(3).to_string(index=False))
