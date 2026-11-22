"""RQ5 (offline) - Quanto do "ganho" do aluno simulado é cópia do material? Sem chamadas de LLM.

Mede a sobreposição de n-gramas entre a resposta pós-material e (i) o material lido e (ii) o gabarito, e verifica se
as diferenças entre condições sobrevivem quando se controla a cópia. Também: ganho por nota-ouro e fração que chega a 3.

Saídas: results/rq5_*.csv, paper/tables/tab_rq5.tex.
"""
import numpy as np
import pandas as pd
from scipy import stats

from _common import parse
from pln.common import ROOT, read_jsonl
from pln.data import norm
from pln.stats import cluster_boot, cluster_ci

a, cfg, out = parse(__doc__)
RES = ROOT / "results"
TAB = ROOT / "paper" / "tables"
MAT_CONDS = [c for c in cfg["student_sim"]["conditions"] if c != "N_sem_material"]
ALL_CONDS = ["N_sem_material"] + MAT_CONDS

# palavras funcionais: excluídas só na sobreposição de unigramas (vocabulário de conteúdo)
STOP = set("""a o e é de do da dos das em no na nos nas um uma uns umas que se por para com como ao aos à às ou mas mais
muito pois porque quando onde ele ela eles elas isso isto esse essa este esta ser ter tem são está estão foi era há
seu sua seus suas lhe nao não sim também já ainda só eu você nós the""".split())

items = {r["item_id"]: r for r in read_jsonl(ROOT / "data" / "processed" / "pilot_set.jsonl")}
if not items:
    raise SystemExit("rode antes: python scripts/00_prepare_data.py (precisa de data/raw)")
mats = {(m["item_id"], m["condition"]): m["texto"] for m in read_jsonl(out / "materials.jsonl")}
ss = pd.DataFrame(read_jsonl(out / "student_sim.jsonl"))
qmap = pd.Series({i: it["question_id"] for i, it in items.items()})


def toks(s: str) -> list[str]:
    return norm(s).split()


def ngr(t: list[str], n: int) -> set:
    return {tuple(t[i:i + n]) for i in range(len(t) - n + 1)}


def contem(resp: str, fonte: str, n: int, sem_stop: bool = False) -> float:
    """Fração dos n-gramas DISTINTOS da resposta que aparecem na fonte (containment)."""
    tr, tf = toks(resp), toks(fonte)
    if sem_stop:
        tr, tf = [w for w in tr if w not in STOP], [w for w in tf if w not in STOP]
    r = ngr(tr, n)
    return len(r & ngr(tf, n)) / len(r) if r else np.nan


pre = ss[ss.condition == "PRE"].set_index("item_id").nota
rows = []
for r in ss.itertuples():
    it = items[r.item_id]
    gab = " ".join(it["refs"])
    mat = mats.get((r.item_id, r.condition))
    rows.append({"item_id": r.item_id, "question_id": it["question_id"], "nota_ouro": it["grade"], "condicao": r.condition,
                 "nota": r.nota, "ganho": r.nota - pre.get(r.item_id) if r.condition != "PRE" else np.nan,
                 "palavras_resp": len(toks(r.resposta)),
                 "copia_material_3g": contem(r.resposta, mat, 3) if mat else np.nan,
                 "sobrep_gabarito_3g": contem(r.resposta, gab, 3),
                 "sobrep_gabarito_1g": contem(r.resposta, gab, 1, sem_stop=True)})
X = pd.DataFrame(rows)
X.to_csv(RES / "rq5_por_resposta.csv", index=False)

# ------------------------------------------------------------------ resumo por condição (IC por questão)
srows = []
for c in ["PRE"] + ALL_CONDS:
    s = X[X.condicao == c].set_index("item_id")
    row = {"condicao": c, "n": len(s), "palavras_resp": s.palavras_resp.mean(), "frac_nota3": (s.nota == 3).mean()}
    for col in ("ganho", "copia_material_3g", "sobrep_gabarito_3g", "sobrep_gabarito_1g"):
        if s[col].notna().any():
            r = cluster_ci(s[col], qmap)
            row.update({col: r["est"], f"{col}_lo": r["lo"], f"{col}_hi": r["hi"]})
    srows.append(row)
S = pd.DataFrame(srows)
S.to_csv(RES / "rq5_resumo_condicoes.csv", index=False)

# ------------------------------------------------------------------ ganho x cópia (dentro de cada condição)
M = X[X.condicao.isin(MAT_CONDS)].copy()
crow = []
for c in MAT_CONDS:
    s = M[M.condicao == c]
    r = cluster_boot(s, "question_id", lambda d: stats.spearmanr(d.copia_material_3g, d.ganho).statistic)
    crow.append({"condicao": c, "spearman(copia_3g, ganho)": r["est"], "ic_lo": r["lo"], "ic_hi": r["hi"], "n": r["n"]})
pd.DataFrame(crow).to_csv(RES / "rq5_ganho_vs_copia.csv", index=False)

# ------------------------------------------------------------------ contrastes ajustados pela cópia
# ganho ~ condição (referência S_estatico) + copia_material_3g; coeficientes com bootstrap por questão
ref = "S_estatico"
outras = [c for c in MAT_CONDS if c != ref]


def coefs(d: pd.DataFrame, ajusta: bool) -> np.ndarray:
    cols = [np.ones(len(d))] + [(d.condicao == c).astype(float).values for c in outras]
    if ajusta:
        cols.append(d.copia_material_3g.values)
    beta = np.linalg.lstsq(np.column_stack(cols), d.ganho.values, rcond=None)[0]
    return beta


M2 = M.dropna(subset=["ganho", "copia_material_3g"])
arows = []
contrastes = [("A1_pipeline", "S_estatico"), ("A1_pipeline", "A0_direto"), ("A2_pipeline_verif", "A1_pipeline"), ("S_estatico", "S0_gabarito")]
for ajusta in (False, True):
    for x, y in contrastes:
        def fn(d, x=x, y=y, aj=ajusta):
            b = coefs(d, aj)
            bx = 0.0 if x == ref else b[1 + outras.index(x)]
            by = 0.0 if y == ref else b[1 + outras.index(y)]
            return bx - by
        r = cluster_boot(M2, "question_id", fn)
        arows.append({"contraste": f"{x} - {y}", "ajustado_por_copia": ajusta, "diff": r["est"], "ic_lo": r["lo"], "ic_hi": r["hi"], "p_boot": r["p_boot"]})
    if ajusta:
        r = cluster_boot(M2, "question_id", lambda d: coefs(d, True)[-1])
        arows.append({"contraste": "coef. copia_material_3g (ganho por +1,0 de cópia)", "ajustado_por_copia": True,
                      "diff": r["est"], "ic_lo": r["lo"], "ic_hi": r["hi"], "p_boot": r["p_boot"]})
A = pd.DataFrame(arows)
A.to_csv(RES / "rq5_contrastes_ajustados.csv", index=False)

# ------------------------------------------------------------------ sensibilidade: só respostas que copiam pouco
lim = M.copia_material_3g.median()
brows = []
for c in MAT_CONDS:
    s = M[(M.condicao == c) & (M.copia_material_3g <= lim)].set_index("item_id")
    r = cluster_ci(s.ganho, qmap)
    brows.append({"condicao": c, "limite_copia_3g(mediana)": lim, "n": r["n"], "ganho": r["est"], "ic_lo": r["lo"], "ic_hi": r["hi"]})
pd.DataFrame(brows).to_csv(RES / "rq5_ganho_pouca_copia.csv", index=False)

# ------------------------------------------------------------------ ganho por nota-ouro
grows = []
for c in ALL_CONDS:
    for g in sorted(X.nota_ouro.unique()):
        s = X[(X.condicao == c) & (X.nota_ouro == g)].set_index("item_id")
        r = cluster_ci(s.ganho, qmap)
        grows.append({"condicao": c, "nota_ouro": g, "n": r["n"], "ganho": r["est"], "ic_lo": r["lo"], "ic_hi": r["hi"],
                      "nota_pre_media": pre.reindex(s.index).mean(), "frac_nota3": (s.nota == 3).mean()})
pd.DataFrame(grows).to_csv(RES / "rq5_ganho_por_nota.csv", index=False)

# ------------------------------------------------------------------ tabela do artigo
NAME = {"PRE": "Original answer (human)", "N_sem_material": "No material", "S0_gabarito": "Reference answers (S0)",
        "S_estatico": "Static reinforcement (S)", "A0_direto": "Direct generation (A0)", "A1_pipeline": "Diagnose-then-generate (A1)",
        "A2_pipeline_verif": "A1 + verification (A2)"}
L = [r"\begin{tabular}{lcccc}", r"\toprule",
     r"Material & Copied 3-grams & 3-gram overlap w/ ref. & Gain [95\% CI] & Reaches 3 \\", r"\midrule"]
for _, r in S.iterrows():
    cp = "--" if pd.isna(r.get("copia_material_3g")) else f"{100 * r.copia_material_3g:.0f}\\%"
    gn = "--" if pd.isna(r.get("ganho")) else f"${r.ganho:+.2f}$ [{r.ganho_lo:.2f}, {r.ganho_hi:.2f}]"
    L.append(f"{NAME[r.condicao]} & {cp} & {100 * r.sobrep_gabarito_3g:.0f}\\% & {gn} & {100 * r.frac_nota3:.0f}\\% \\\\")
L += [r"\bottomrule", r"\end{tabular}"]
(TAB / "tab_rq5.tex").write_text("\n".join(L), encoding="utf-8")

pd.set_option("display.width", 200)
print(S[["condicao", "n", "palavras_resp", "copia_material_3g", "sobrep_gabarito_3g", "sobrep_gabarito_1g", "ganho", "ganho_lo", "ganho_hi", "frac_nota3"]].round(3).to_string(index=False))
print(pd.DataFrame(crow).round(3).to_string(index=False))
print(A.round(3).to_string(index=False))
print(pd.DataFrame(brows).round(3).to_string(index=False))
