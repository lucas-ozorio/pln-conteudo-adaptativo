"""Gera figuras (PDF) e tabelas (.tex) do artigo a partir de results/*.csv. Nenhum número é digitado à mão."""
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from _common import parse  # noqa: E402
from pln.common import ROOT, read_jsonl  # noqa: E402

a, cfg, out = parse(__doc__)
R = ROOT / "results"
PAPER = ROOT / "paper"
(PAPER / "tables").mkdir(parents=True, exist_ok=True)
(PAPER / "figures").mkdir(parents=True, exist_ok=True)

NAME = {"S0_gabarito": "Reference answers (S0)", "S_estatico": "Static reinforcement (S)", "A0_direto": "Direct generation (A0)",
        "A1_pipeline": "Diagnose-then-generate (A1)", "A2_pipeline_verif": "A1 + verification (A2)", "N_sem_material": "No material"}
SHORT = {"S0_gabarito": "S0", "S_estatico": "S", "A0_direto": "A0", "A1_pipeline": "A1", "A2_pipeline_verif": "A2", "N_sem_material": "None"}
DIM = {"coerencia": "Coherence", "correcao_conceitual": "Conceptual correctness", "fidelidade_gabarito": "Faithfulness to reference",
       "foco_na_lacuna": "Gap focus", "utilidade_pedagogica": "Pedagogical usefulness", "adequacao_nivel": "Level adequacy"}
TEXT_DIMS = list(DIM)
ORDER = ["S0_gabarito", "S_estatico", "A0_direto", "A1_pipeline", "A2_pipeline_verif"]

M = pd.read_csv(R / "cluster_e1_medias.csv")
C = pd.read_csv(R / "cluster_e1_contrastes.csv")
J = pd.read_csv(R / "e1_juiz_absoluto_por_item.csv")
G = pd.read_csv(R / "cluster_e3_ganho.csv")
E3C = pd.read_csv(R / "cluster_e3_contrastes.csv")
E0 = pd.read_csv(R / "e0_diagnostico.csv").iloc[0]
E0C = pd.read_csv(R / "cluster_e0_qwk.csv").iloc[0]
CM = pd.read_csv(R / "e0_confusao.csv", index_col=0)


def mean_of(c, d):
    r = M[(M.condicao == c) & (M.dimensao == d)]
    return r.media.iloc[0] if len(r) else np.nan


# ------------------------------------------------------------------ Tabela principal (médias do juiz)
words = J.groupby("condition").n_palavras.mean()
inc = J.groupby("condition").afirmacoes_incorretas.mean()
lines = [r"\begin{tabular}{lrccccccc}", r"\toprule",
         r"Condition & Words & Coh. & Corr. & Faith. & Focus & Useful & Level & Incorr. \\", r"\midrule"]
best = {d: max(mean_of(c, d) for c in ORDER[1:]) for d in TEXT_DIMS}
for c in ORDER:
    cells = []
    for d in TEXT_DIMS:
        v = mean_of(c, d)
        s = f"{v:.2f}"
        cells.append(r"\textbf{" + s + "}" if (c != "S0_gabarito" and abs(v - best[d]) < 1e-9) else s)
    lines.append(f"{NAME[c]} & {words[c]:.0f} & " + " & ".join(cells) + f" & {inc[c]:.2f} \\\\")
    if c == "S0_gabarito":
        lines.append(r"\midrule")
lines += [r"\bottomrule", r"\end{tabular}"]
(PAPER / "tables" / "tab_main.tex").write_text("\n".join(lines), encoding="utf-8")

# ------------------------------------------------------------------ Tabela de contrastes (diff [IC], estrelas = Holm)
pairs = [("A1_pipeline - S_estatico", r"A1$-$S"), ("A0_direto - S_estatico", r"A0$-$S"), ("A1_pipeline - A0_direto", r"A1$-$A0"),
         ("A2_pipeline_verif - A1_pipeline", r"A2$-$A1")]
lines = [r"\begin{tabular}{l" + "c" * len(pairs) + "}", r"\toprule", "Dimension & " + " & ".join(p[1] for p in pairs) + r" \\", r"\midrule"]
for d in TEXT_DIMS:
    cells = []
    for key, _ in pairs:
        r = C[(C.dimensao == d) & (C.contraste == key)].iloc[0]
        star = "*" if r.p_holm < 0.05 else ""
        cells.append(f"${r['diff']:+.2f}$ [{r.ic_lo:.2f}, {r.ic_hi:.2f}]{star}")
    lines.append(f"{DIM[d]} & " + " & ".join(cells) + r" \\")
lines += [r"\bottomrule", r"\end{tabular}"]
(PAPER / "tables" / "tab_contrasts.tex").write_text("\n".join(lines), encoding="utf-8")

# ------------------------------------------------------------------ Tabela das questões geradas (apêndice)
qd = {"q_alinhamento": "Alignment", "q_clareza": "Clarity", "q_relevancia": "Gap relevance"}
bm = J.groupby("condition").q_bloom_match.mean()
lines = [r"\begin{tabular}{lcccc}", r"\toprule", r"Condition & Alignment & Clarity & Gap relevance & Bloom match \\", r"\midrule"]
for c in ORDER[1:]:
    lines.append(f"{NAME[c]} & " + " & ".join(f"{mean_of(c, k):.2f}" for k in qd) + f" & {bm[c]:.2f} \\\\")
lines += [r"\bottomrule", r"\end{tabular}"]
(PAPER / "tables" / "tab_questions.tex").write_text("\n".join(lines), encoding="utf-8")

# ------------------------------------------------------------------ E3
lines = [r"\begin{tabular}{lc}", r"\toprule", r"Material given to simulated student & Gain [95\% CI] \\", r"\midrule"]
for c in ["N_sem_material", "S0_gabarito", "S_estatico", "A0_direto", "A1_pipeline", "A2_pipeline_verif"]:
    r = G[G.condicao == c].iloc[0]
    lines.append(f"{NAME[c]} & ${r.ganho:+.2f}$ [{r.ic_lo:.2f}, {r.ic_hi:.2f}] \\\\")
lines += [r"\bottomrule", r"\end{tabular}"]
(PAPER / "tables" / "tab_e3.tex").write_text("\n".join(lines), encoding="utf-8")

# ------------------------------------------------------------------ E0: matriz de confusão
lines = [r"\begin{tabular}{lcccc}", r"\toprule", r"Gold $\backslash$ Predicted & 0 & 1 & 2 & 3 \\", r"\midrule"]
for i in range(4):
    lines.append(f"{i} & " + " & ".join(str(int(x)) for x in CM.iloc[i].values) + r" \\")
lines += [r"\bottomrule", r"\end{tabular}"]
(PAPER / "tables" / "tab_confusion.tex").write_text("\n".join(lines), encoding="utf-8")

# ------------------------------------------------------------------ Pairwise (apêndice)
P = pd.read_csv(R / "e1_pareado.csv")
lines = [r"\begin{tabular}{lcccc}", r"\toprule", r"Pair ($x$ vs $y$) & $x$ wins both & $y$ wins both & Order-inconsistent/tie & 1st-position wins \\", r"\midrule"]
for _, r in P.iterrows():
    x, y = [s.strip() for s in r["par"].split(" vs ")]
    lines.append(f"{SHORT[x]} vs {SHORT[y]} & {r['vitória robusta x'] * 100:.1f}\\% & {r['vitória robusta y'] * 100:.1f}\\% & {r['inconsistente/empate'] * 100:.1f}\\% & {r['viés_posição(1º vence)'] * 100:.1f}\\% \\\\")
lines += [r"\bottomrule", r"\end{tabular}"]
(PAPER / "tables" / "tab_pairwise.tex").write_text("\n".join(lines), encoding="utf-8")

# ------------------------------------------------------------------ Números soltos para o texto
nums = {
    "e0_qwk": E0["QWK"], "e0_qwk_lo": E0C.ic_lo, "e0_qwk_hi": E0C.ic_hi, "e0_spear": E0["Spearman"], "e0_mae": E0["MAE"],
    "e0_acc": E0["acc_exata"], "e0_bin": E0["acc_binaria(>=2)"], "e0_qwk_qmin": E0C.QWK_por_questao_min, "e0_qwk_qmax": E0C.QWK_por_questao_max,
}
pd.Series(nums).to_csv(PAPER / "tables" / "numbers.csv", header=False)

# ------------------------------------------------------------------ Figura de resultados (2 painéis)
plt.rcParams.update({"font.size": 8, "font.family": "serif", "pdf.fonttype": 42})
fig, ax = plt.subplots(1, 2, figsize=(6.3, 2.5), gridspec_kw={"width_ratios": [2.3, 1]})
conds = ORDER[1:]
mk = {"S_estatico": ("s", "#555555"), "A0_direto": ("^", "#2b83ba"), "A1_pipeline": ("o", "#d7191c"), "A2_pipeline_verif": ("D", "#fdae61")}
dims_plot = ["coerencia", "correcao_conceitual", "fidelidade_gabarito", "adequacao_nivel", "foco_na_lacuna", "utilidade_pedagogica"]
xs = np.arange(len(dims_plot))
for k, c in enumerate(conds):
    off = (k - 1.5) * 0.15
    ys = [mean_of(c, d) for d in dims_plot]
    lo = [M[(M.condicao == c) & (M.dimensao == d)].ic_lo.iloc[0] for d in dims_plot]
    hi = [M[(M.condicao == c) & (M.dimensao == d)].ic_hi.iloc[0] for d in dims_plot]
    ax[0].errorbar(xs + off, ys, yerr=[np.array(ys) - lo, np.array(hi) - ys], fmt=mk[c][0], color=mk[c][1], ms=4, capsize=1.5, lw=0.8, label=SHORT[c])
ax[0].set_xticks(xs)
ax[0].set_xticklabels(["Coher.", "Correct.", "Faithful.", "Level", "Gap\nfocus", "Useful."], fontsize=7)
ax[0].set_ylim(3.4, 5.05)
ax[0].set_ylabel("Judge score (1–5)")
ax[0].set_title("(a) LLM-judge quality", fontsize=8)
ax[0].axvspan(3.5, 5.5, color="0.93", zorder=0)
ax[0].legend(ncol=4, fontsize=6.5, loc="lower left", frameon=False, handletextpad=0.2, columnspacing=0.8)
order3 = ["N_sem_material", "S_estatico", "A0_direto", "A1_pipeline", "A2_pipeline_verif"]
for i, c in enumerate(order3):
    r = G[G.condicao == c].iloc[0]
    col, m_ = (mk[c][1], mk[c][0]) if c in mk else ("0.2", "x")
    ax[1].errorbar(r.ganho, i, xerr=[[r.ganho - r.ic_lo], [r.ic_hi - r.ganho]], fmt=m_, color=col, ms=4, capsize=1.5, lw=0.8)
ax[1].set_yticks(range(len(order3)))
ax[1].set_yticklabels([SHORT[c] for c in order3])
ax[1].invert_yaxis()
ax[1].set_xlabel("Gain (0–3 scale)")
ax[1].set_title("(b) Simulated student", fontsize=8)
ax[1].set_xlim(0, 2)
plt.tight_layout()
plt.savefig(PAPER / "figures" / "results.pdf", bbox_inches="tight")
print("ok:", sorted(p.name for p in (PAPER / "tables").iterdir()), "figures/results.pdf")
