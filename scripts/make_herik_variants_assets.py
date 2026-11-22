"""Gera os artefatos LaTeX de RQ2/RQ3 (H-03 + H-04) para `paper/herik_contrib/`.

Lê exclusivamente `results/herik_variants/h03_*.csv`, `h04_*.csv` e `analise_a1_a0_s.md` (gerados por
`scripts/analyze_variants_a1_a0_s.py`). Sem API, sem `data/`, sem tocar `paper/main.tex`, `paper/tables/` ou `results/`.

Saídas:
  paper/herik_contrib/tab_rq3_length_and_strat.tex      (tabular: controle de tamanho + estratos)
  paper/herik_contrib/tab_rq3_qualitative_summary.tex   (tabular: mecanismos qualitativos com evidência numérica)
  paper/herik_contrib/rq2_rq3_draft.tex                 (blocos de texto em inglês; todos os números vêm dos CSVs)

Uso: python scripts/make_herik_variants_assets.py
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "herik_variants"
DST = ROOT / "paper" / "herik_contrib"
DST.mkdir(parents=True, exist_ok=True)

A1, A0, S = "A1_pipeline", "A0_direto", "S_estatico"
MINUS = "−"  # os CSVs usam o sinal de menos tipográfico nos rótulos de contraste


def csv(name: str) -> pd.DataFrame:
    return pd.read_csv(SRC / name)


raw = csv("h03_01_contrastes_brutos.csv")
dist = csv("h03_02_distribuicao_palavras.csv")
reg = csv("h03_03_regressao_efeito_fixo_item.csv")
pr = csv("h03_04_delta_palavras_vs_delta_nota.csv").set_index("dimensao")
bands = csv("h03_05_faixas_delta_palavras.csv")
strat = csv("h03_06_estratificacao.csv")
qtab = csv("h03_07_por_questao.csv")
dtab = csv("h03_08_erro_diagnostico.csv").set_index(["grupo_diag", "dimensao"])
cross = csv("h03_09_erro_diag_x_nota_ouro.csv")
pairs = csv("h03_10_par_a_par_por_item.csv")
psum = csv("h03_11_par_a_par_resumo.csv").set_index(["par", "resultado"])
tech = csv("h04_01_termos_tecnicos_fora_do_gabarito.csv")
vac = csv("h04_02_vacuolo.csv").set_index("condicao")
panel = csv("h04_03_painel_itens.csv").set_index("item_id")
qlen = csv("h04_04_tamanho_enunciados.csv").set_index("condicao")
lac = csv("h04_05_lacunas_por_nota_ouro.csv").set_index("grade")
cases = csv("h04_06_casos_selecionados.csv").set_index("item_id")
report = (SRC / "analise_a1_a0_s.md").read_text(encoding="utf-8")

reg["controle_log_palavras"] = reg.controle_log_palavras.astype(str).str.lower().eq("true")
regc = reg[reg.controle_log_palavras].set_index("dimensao")
regu = reg[~reg.controle_log_palavras].set_index("dimensao")


def con(x: str, y: str) -> pd.DataFrame:
    return raw[raw.contraste == f"{x} {MINUS} {y}"].set_index("dimensao")


R10, R1S, R0S = con(A1, A0), con(A1, S), con(A0, S)


# ------------------------------------------------------------------ formatação
def sg(x: float, nd: int = 2, star: bool = False) -> str:
    """Número com sinal em modo matemático: $+0.12$ / $-0.06$ (asterisco dentro do mesmo $...$, nunca '$$')."""
    s = f"{x:+.{nd}f}"
    if s in ("+0." + "0" * nd, "-0." + "0" * nd):
        s = "0." + "0" * nd
    return f"${s}" + ("^{*}" if star else "") + "$"


def nn(x: float, nd: int = 2) -> str:
    return f"{x:.{nd}f}"


def ci(lo: float, hi: float, nd: int = 2) -> str:
    return f"$[{lo:.{nd}f}, {hi:.{nd}f}]$"


def pct(x: float) -> str:
    return f"{100 * x:.0f}\\%"


def pfmt(p: float) -> str:
    """Valor de p SEM '$': o template o coloca dentro de uma expressão matemática."""
    return "<0.001" if p < 0.001 else f"{p:.3f}" if p < 0.01 else f"{p:.2f}"


DIM_EN = {"coerencia": "Coherence", "foco_na_lacuna": "Gap focus", "utilidade_pedagogica": "Usefulness",
          "adequacao_nivel": "Level adequacy", "q_relevancia": "Q.\\ gap relevance", "q_clareza": "Q.\\ clarity",
          "abs_texto": "Text mean (6 dims)"}

# ------------------------------------------------------------------ valores derivados (todos de CSV)
pa = pairs[pairs.par == f"{A1} vs {A0}"].copy()
ps_ = pairs[pairs.par == f"{A1} vs {S}"].copy()
w10, w01 = int((pa.resultado == "A1 robusta").sum()), int((pa.resultado == "A0 robusta").sum())
inc10 = int((pa.resultado == "inconsistente").sum())
w1s, ws1 = int((ps_.resultado == "A1 robusta").sum()), int((ps_.resultado == "S robusta").sum())
p10 = stats.binomtest(w10, w10 + w01, 0.5).pvalue
p1s = stats.binomtest(w1s, w1s + ws1, 0.5).pvalue
mw_len = stats.mannwhitneyu(pa[pa.resultado == "A1 robusta"]["Δpalavras"], pa[pa.resultado == "A0 robusta"]["Δpalavras"]).pvalue
pa["erro"] = pa.pred - pa.grade
dabs_sub, dabs_ok = pa[pa.erro < 0]["Δabs_texto"], pa[pa.erro == 0]["Δabs_texto"]
mw_sub = stats.mannwhitneyu(dabs_sub, dabs_ok).pvalue
q42_a0 = int(((pa.resultado == "A0 robusta") & (pa.question_id == 42)).sum())
n_items = len(pa)

d10 = dist.set_index("condicao").loc[f"Δ {A1} {MINUS} {A0}"]
frac_longer = float(d10.frac_x_mais_longo)
med_dw = float(d10.q50)
a0_below = float((panel.w_A0 < 120).mean())
n_logneg, n_logdims = int((regc.coef_log_palavras < 0).sum()), len(regc)
max_p_log = float(regc.p_log_palavras.min())
rho_max = float(pr.spearman_dpalavras_dnota.abs().max())
terc = bands[bands.faixa.str.startswith("T")].abs_texto
st = strat[strat.estrato == "nota_ouro"].assign(valor=lambda d: d.valor.astype(int)).set_index("valor")
g2ok = cross[(cross.grade == 2) & cross.grupo_diag.str.startswith("acert")].iloc[0]
lac_total = int(round((lac.frac_3_lacunas * lac.n).sum()))
lac_n = int(lac.n.sum())
SUB, OK, SUP = "subavaliou (pred<ouro)", "acertou (pred=ouro)", "superavaliou (pred>ouro)"
n_sub, n_ok, n_sup = (int(dtab.loc[(g, "abs_texto"), "n"]) for g in (SUB, OK, SUP))

tsum = tech.groupby("condicao").agg(occ=("termo", "size"), items=("item_id", "nunique"),
                                    untraced=("termo_no_diagnostico", lambda s: int((~s.astype(bool)).sum())))
sperm = tech[(tech.question_id == 42) & tech.termo.str.startswith("espermatog")].groupby("condicao").item_id.nunique()
sperm_a1, sperm_a0 = int(sperm.get(A1, 0)), int(sperm.get(A0, 0))

# ------------------------------------------------------------------ checagem cruzada com o relatório (falha se divergir)
CHECKS = [f"{w10}/180 itens vs {w01}/180", f"{lac_total}/{lac_n}", f"A0 vence par-a-par em {100 * g2ok.vit_A0:.0f}% vs A1 em {100 * g2ok.vit_A1:.0f}% (n={int(g2ok.n)})",
          f"{int(tsum.loc[A0, 'occ'])} ocorrências no A0 vs {int(tsum.loc[A1, 'occ'])} no A1",
          f"Mann-Whitney p = {mw_len:.2f}", f"MW p = {mw_sub:.2f}", f"{100 * a0_below:.0f}% dos textos A0 têm < 120 palavras",
          f"concentra {q42_a0} das {w01} vitórias robustas de A0"]
missing = [c for c in CHECKS if c not in report]
assert not missing, f"Divergência com analise_a1_a0_s.md: {missing}"

# ================================================================== Tabela 1: tamanho + estratos
L = [r"\begin{tabular}{lccccc}", r"\toprule",
     r"\multicolumn{6}{l}{\textit{(a) A1$-$A0 with and without length control}} \\",
     r"Dimension & Raw A1$-$A0 [CI] & Adj.\ A1$-$A0 (SE) & $\beta_{\log w}$ ($p$) & $\alpha_{\Delta w=0}$ (SE) & $\rho(\Delta w, \Delta s)$ \\",
     r"\midrule"]
for d in ["coerencia", "foco_na_lacuna", "utilidade_pedagogica", "adequacao_nivel", "q_relevancia", "q_clareza", "abs_texto"]:
    star = bool(R10.loc[d, "p_cluster"] < 0.05)
    L.append(f"{DIM_EN[d]} & {sg(R10.loc[d, 'diff'], star=star)} {ci(R10.loc[d, 'ic_cluster_lo'], R10.loc[d, 'ic_cluster_hi'])} & "
             f"{sg(regc.loc[d, 'A1_menos_A0'])} ({nn(regc.loc[d, 'ep_A1_A0'])}) & "
             f"{sg(regc.loc[d, 'coef_log_palavras'])} ({nn(regc.loc[d, 'p_log_palavras'])}) & "
             f"{sg(pr.loc[d, 'alfa_tamanho_igual'])} ({nn(pr.loc[d, 'ep_alfa'])}) & {sg(pr.loc[d, 'spearman_dpalavras_dnota'])} \\\\")
L += [r"\midrule",
      r"\multicolumn{6}{l}{\textit{(b) By gold grade ($n{=}60$ each): text-mean / focus / usefulness differences and robust pairwise wins}} \\",
      r"Gold & A1$-$A0 (mean / focus / useful) & Wins A1:A0 & A1$-$S (focus / useful) & Wins A1:S & $\Delta$words A1$-$A0 \\",
      r"\midrule"]
for gval in (0, 1, 2):
    r = st.loc[gval]
    L.append(f"{gval} & {sg(r.A1_A0_abs_texto)} / {sg(r.A1_A0_foco_na_lacuna)} / {sg(r.A1_A0_utilidade_pedagogica)} & "
             f"{pct(r.A1_A0_par_vitA1)}:{pct(r.A1_A0_par_vitOutro)} & {sg(r.A1_S_foco_na_lacuna)} / {sg(r.A1_S_utilidade_pedagogica)} & "
             f"{pct(r.A1_S_par_vitA1)}:{pct(r.A1_S_par_vitOutro)} & {r.Δpalavras_A1_A0:.0f} \\\\")
L += [r"\midrule",
      r"\multicolumn{6}{l}{\textit{(c) By diagnosis grade error (estimated $-$ gold)}} \\",
      r"Diagnosis & $n$ & A1$-$A0 text mean [CI] & A1$-$A0 Q.\ relevance [CI] & Wins A1:A0 & A1$-$S focus \\",
      r"\midrule"]
for lab, g in (("Under-graded", SUB), ("Correct", OK), ("Over-graded", SUP)):
    sub = pa[np.sign(pa.erro) == {SUB: -1, OK: 0, SUP: 1}[g]]
    a, q = dtab.loc[(g, "abs_texto")], dtab.loc[(g, "q_relevancia")]
    L.append(f"{lab} & {int(a.n)} & {sg(a.A1_menos_A0)} {ci(a.ic_lo, a.ic_hi)} & {sg(q.A1_menos_A0)} {ci(q.ic_lo, q.ic_hi)} & "
             f"{pct((sub.resultado == 'A1 robusta').mean())}:{pct((sub.resultado == 'A0 robusta').mean())} & "
             f"{sg(dtab.loc[(g, 'foco_na_lacuna'), 'A1_menos_S'])} \\\\")
L += [r"\bottomrule", r"\end{tabular}"]
(DST / "tab_rq3_length_and_strat.tex").write_text("\n".join(L) + "\n", encoding="utf-8")

# ================================================================== Tabela 2: mecanismos qualitativos
def cs(iid: str) -> str:
    c = cases.loc[iid]
    return f"\\texttt{{{iid.replace('_', chr(92) + '_')}}} (gold {c.ouro}, diag.\\ {c.diag})"


T = [r"\begin{tabular}{p{0.20\textwidth}p{0.47\textwidth}p{0.25\textwidth}}", r"\toprule",
     r"Mechanism & Evidence (180 items) & Example \\", r"\midrule",
     (r"Forced gaps & The diagnosis lists exactly 3 priority gaps in " f"{lac_total}/{lac_n}" r" items, also for gold-2 answers ("
      f"{pct(lac.loc[2, 'frac_3_lacunas'])}" r"). With gold 2 and a correct grade ($n{=}" f"{int(g2ok.n)}" r"$), A0 wins "
      f"{pct(g2ok.vit_A0)}" r" of robust pairwise verdicts vs.\ " f"{pct(g2ok.vit_A1)}" r" for A1. & "
      f"{cs('q45_2a7cf00f')}: peripheral gaps become peripheral questions. \\\\"),
     (r"Diagnosis errors propagate & In \texttt{q42}, a gap outside the reference (spermatogenesis) appears in "
      f"{sperm_a1}/12 A1 vs.\\ {sperm_a0}/12 A0 texts; \\texttt{{q42}} holds {q42_a0} of the {w01} robust A0 wins. & "
      f"{cs('q42_9260e885')}: A1 repeats a false terminology ``correction'' produced by the diagnosis. \\\\"),
     (r"Narrowing & Instructed to address \emph{only} the listed gaps, A1 may ignore content the student did discuss. & "
      f"{cs('q37_4f1cecfe')}: A0 and S both beat A1 in both orders. \\\\"),
     (r"Diagnosed error not used & The diagnosis contains the misconception, but the A1 text stays generic (focus "
      f"{cases.loc['q40_19368b9f', 'foco A1/A0/S'].split('/')[0]} vs.\\ {cases.loc['q40_19368b9f', 'foco A1/A0/S'].split('/')[1]} for A0). & "
      f"{cs('q40_19368b9f')}. \\\\"),
     (r"Off-reference content & Curated technical terms absent from the reference and from S: A0 "
      f"{int(tsum.loc[A0, 'occ'])} occurrences in {int(tsum.loc[A0, 'items'])} items ({int(tsum.loc[A0, 'untraced'])} not traceable to the student's answer) "
      f"vs.\\ A1 {int(tsum.loc[A1, 'occ'])} in {int(tsum.loc[A1, 'items'])} ({int(tsum.loc[A1, 'untraced'])}). ``Vacuole'' in "
      f"\\texttt{{q36}}: A0 {int(vac.loc[A0, 'q36_com_vacuolo'])}/12 (student mentioned it in {int(vac.loc[A0, 'q36_com_vacuolo_e_aluno_citou'])}), "
      f"A1 {int(vac.loc[A1, 'q36_com_vacuolo'])}/12. Judged faithfulness: A1$-$A0 {sg(R10.loc['fidelidade_gabarito', 'diff'])}. & "
      f"{cs('q36_3b0258ff')}: A0 adds vacuoles; A1 wins vs.\\ A0 and S. \\\\"),
     (r"Gap-targeted questions & A1 questions receive the gap list: relevance "
      f"{sg(R10.loc['q_relevancia', 'diff'])} vs.\\ A0, {sg(R1S.loc['q_relevancia', 'diff'])} vs.\\ S; clarity {sg(R10.loc['q_clareza', 'diff'])} vs.\\ A0 "
      f"(stems of {qlen.loc[A1, 'mean']:.1f} vs.\\ {qlen.loc[A0, 'mean']:.1f} words). & {cs('q43_da5a83a4')}: all three questions target the gaps. \\\\"),
     (r"Grade under-estimation is harmless on average & A1$-$A0 text mean: under-graded "
      f"{sg(dtab.loc[(SUB, 'abs_texto'), 'A1_menos_A0'])} ($n{{=}}{n_sub}$) vs.\\ correct {sg(dtab.loc[(OK, 'abs_texto'), 'A1_menos_A0'])} ($n{{=}}{n_ok}$); "
      f"Mann--Whitney $p{{=}}{mw_sub:.2f}$. & {cs('q39_524585dd')}: under-graded, A1 still wins vs.\\ A0 and S. \\\\"),
     r"\bottomrule", r"\end{tabular}"]
(DST / "tab_rq3_qualitative_summary.tex").write_text("\n".join(T) + "\n", encoding="utf-8")

# ================================================================== Rascunho de texto (template com marcadores <<nome>>)
V = {
    "a1s_focus": sg(R1S.loc["foco_na_lacuna", "diff"]), "a0s_focus": sg(R0S.loc["foco_na_lacuna", "diff"]),
    "a1a0_focus": sg(R10.loc["foco_na_lacuna", "diff"]),
    "a1a0_focus_ci": ci(R10.loc["foco_na_lacuna", "ic_cluster_lo"], R10.loc["foco_na_lacuna", "ic_cluster_hi"]),
    "a1a0_useful": sg(R10.loc["utilidade_pedagogica", "diff"]),
    "a1a0_useful_ci": ci(R10.loc["utilidade_pedagogica", "ic_cluster_lo"], R10.loc["utilidade_pedagogica", "ic_cluster_hi"]),
    "a1a0_coh": sg(R10.loc["coerencia", "diff"]), "a1a0_level": sg(R10.loc["adequacao_nivel", "diff"]),
    "a1a0_qrel": sg(R10.loc["q_relevancia", "diff"]),
    "a1a0_qrel_ci": ci(R10.loc["q_relevancia", "ic_cluster_lo"], R10.loc["q_relevancia", "ic_cluster_hi"]),
    "a1a0_qcla": sg(R10.loc["q_clareza", "diff"]),
    "a1a0_qcla_ci": ci(R10.loc["q_clareza", "ic_cluster_lo"], R10.loc["q_clareza", "ic_cluster_hi"]),
    "a1s_qrel": sg(R1S.loc["q_relevancia", "diff"]), "a0s_qrel": sg(R0S.loc["q_relevancia", "diff"]),
    "frac_longer": f"{100 * frac_longer:.1f}\\%", "med_dw": f"{med_dw:.0f}", "a0_below": pct(a0_below),
    "n_logneg": str(n_logneg), "n_logdims": str(n_logdims), "min_p_log": nn(max_p_log),
    "rho_max": nn(rho_max), "terc_lo": nn(terc.min()), "terc_hi": nn(terc.max()),
    "adj_useful": sg(regc.loc["utilidade_pedagogica", "A1_menos_A0"]), "adj_useful_se": nn(regc.loc["utilidade_pedagogica", "ep_A1_A0"]),
    "raw_useful_se": nn(regu.loc["utilidade_pedagogica", "ep_A1_A0"]),
    "w10": str(w10), "w01": str(w01), "inc10": str(inc10), "p10": pfmt(p10), "w1s": str(w1s), "ws1": str(ws1), "p1s": nn(p1s),
    "n_items": str(n_items),
    "abs_agree": pct(psum.loc[(f"{A1} vs {A0}", "A1 robusta"), "frac_abs_concorda"]), "mw_len": nn(mw_len),
    "dw_win_a1": f"{psum.loc[(f'{A1} vs {A0}', 'A1 robusta'), 'Δpalavras_media']:.0f}",
    "dw_win_a0": f"{psum.loc[(f'{A1} vs {A0}', 'A0 robusta'), 'Δpalavras_media']:.0f}",
    "g1_abs": sg(st.loc[1, "A1_A0_abs_texto"]), "g1_useful": sg(st.loc[1, "A1_A0_utilidade_pedagogica"]),
    "g2_w1": pct(st.loc[2, "A1_A0_par_vitA1"]), "g2_w0": pct(st.loc[2, "A1_A0_par_vitOutro"]),
    "g2_ws": pct(st.loc[2, "A1_S_par_vitOutro"]),
    "n_sub": str(n_sub), "n_ok": str(n_ok), "n_sup": str(n_sup),
    "sub_abs": sg(dtab.loc[(SUB, "abs_texto"), "A1_menos_A0"]), "ok_abs": sg(dtab.loc[(OK, "abs_texto"), "A1_menos_A0"]),
    "sup_abs": sg(dtab.loc[(SUP, "abs_texto"), "A1_menos_A0"]), "mw_sub": nn(mw_sub),
    "sub_qrel": sg(dtab.loc[(SUB, "q_relevancia"), "A1_menos_A0"]),
    "sub_qrel_ci": ci(dtab.loc[(SUB, "q_relevancia"), "ic_lo"], dtab.loc[(SUB, "q_relevancia"), "ic_hi"]),
    "g2ok_n": str(int(g2ok.n)), "g2ok_a0": pct(g2ok.vit_A0), "g2ok_a1": pct(g2ok.vit_A1),
    "lac_total": str(lac_total), "lac_n": str(lac_n), "q42_a0": str(q42_a0),
    "sperm_a1": str(sperm_a1), "sperm_a0": str(sperm_a0),
    "vac_a0": str(int(vac.loc[A0, "q36_com_vacuolo"])), "vac_a0_stud": str(int(vac.loc[A0, "q36_com_vacuolo_e_aluno_citou"])),
    "vac_a1": str(int(vac.loc[A1, "q36_com_vacuolo"])),
    "tech_a0": str(int(tsum.loc[A0, "occ"])), "tech_a1": str(int(tsum.loc[A1, "occ"])),
    "faith": sg(R10.loc["fidelidade_gabarito", "diff"]),
    "stem_a1": f"{qlen.loc[A1, 'mean']:.1f}", "stem_a0": f"{qlen.loc[A0, 'mean']:.1f}",
}

DRAFT = r"""% ==============================================================================
% Pacote de Contribuição RQ2/RQ3 (H-03 + H-04) — pronto para integrar em paper/main.tex
% GERADO por scripts/make_herik_variants_assets.py: não editar à mão; todos os números vêm de
% results/herik_variants/h03_*.csv e h04_*.csv (n = 180 itens, 15 questões).
% Não altera paper/main.tex. Instruções linha a linha em paper/herik_contrib/INTEGRACAO_RQ2_RQ3.md.
% Nenhuma resposta de aluno é reproduzida além do exemplo curto que o main.tex já contém (CC BY-NC-SA 4.0).
% ==============================================================================

% ------------------------------------------------------------------------------
% BLOCO 1 (§5.2): substituir o parágrafo \paragraph{Does the explicit diagnosis help?} (main.tex L166)
% ------------------------------------------------------------------------------
\paragraph{Does the explicit diagnosis help?} Largely no. Direct generation (A0), which also conditions on the student's answer but has no explicit diagnosis, obtains almost the same focus gain over S as A1 (<<a0s_focus>> vs.\ <<a1s_focus>>). Comparing A1 with A0 directly, gap focus differs by <<a1a0_focus>> and usefulness by <<a1a0_useful>>, with intervals spanning zero (Table~\ref{tab:contrasts}); coherence (<<a1a0_coh>>) and level adequacy (<<a1a0_level>>) are nominally positive but do not survive Holm correction. In order-swapped pairwise judgments, A1 beats A0 in both orders on <<w10>> of <<n_items>> items and A0 beats A1 on <<w01>> (sign test $p{=}<<p10>>$, ignoring clustering; <<inc10>> items are order-inconsistent), but only <<abs_agree>> of A1's robust wins also show a higher absolute mean: the preference reflects organization and style rather than different content.

\emph{Is A1's small edge a length artifact?} A0 lands at the lower edge of the shared budget (<<a0_below>> of A0 texts have fewer than 120 words), and A1 is longer than A0 for <<frac_longer>> of the items (median difference <<med_dw>> words), so length and condition are almost collinear in this contrast. Three checks (Table~\ref{tab:rq3_length}a) indicate that length does not drive the difference. (i)~In a within-item regression over A1, A0 and S with question-clustered standard errors, the coefficient of $\log(\text{words})$ is not significant for any dimension ($p\ge <<min_p_log>>$; negative in <<n_logneg>> of <<n_logdims>>), and adding it does not shrink A1$-$A0 (usefulness <<a1a0_useful>> $\to$ <<adj_useful>>), although the standard error grows (<<raw_useful_se>> $\to$ <<adj_useful_se>>) because A1 and A0 barely overlap in length. (ii)~The item-level difference in scores is unrelated to the difference in words (Spearman $|\rho|\le <<rho_max>>$), and the text-mean gap is flat across terciles of the length difference (<<terc_lo>>--<<terc_hi>>). (iii)~S has the same length as A1 and still scores below the shorter A0 on focus and usefulness. Robust pairwise wins of A1 and of A0 do not differ in length difference (<<dw_win_a1>> vs.\ <<dw_win_a0>> words; Mann--Whitney $p{=}<<mw_len>>$). The conclusion is therefore not that length explains A1's advantage, but that the advantage is small to begin with.

\emph{Where does the diagnosis help or hurt?} A1's edge over A0 is largest for gold-1 answers (text mean <<g1_abs>>, usefulness <<g1_useful>>) and vanishes for gold-2 answers, where A0 wins <<g2_w0>> of robust pairwise verdicts vs.\ <<g2_w1>> for A1 and S also wins most often against A1 (<<g2_ws>>; Table~\ref{tab:rq3_length}b). Errors in the estimated grade do not explain this: A1$-$A0 is <<sub_abs>> for under-graded answers ($n{=}<<n_sub>>$), <<ok_abs>> when the grade is correct ($n{=}<<n_ok>>$) and <<sup_abs>> when over-graded ($n{=}<<n_sup>>$; under- vs.\ correctly graded, Mann--Whitney $p{=}<<mw_sub>>$; Table~\ref{tab:rq3_length}c). The weak spot is instead gold-2 answers graded \emph{correctly} ($n{=}<<g2ok_n>>$), where A0 wins <<g2ok_a0>> vs.\ <<g2ok_a1>>. Reading the paired materials (Table~\ref{tab:rq3_qual}) points to the gap list rather than the grade: the diagnosis fills all three priority-gap slots in <<lac_total>> of <<lac_n>> items, and A1, instructed to address only those gaps, follows them even when they are peripheral or wrong. In \texttt{q42}, which holds <<q42_a0>> of the <<w01>> robust A0 wins, a gap outside the reference (spermatogenesis) reaches <<sperm_a1>> of 12 A1 texts and none of A0's, and in one item A1 repeats a terminology ``correction'' that the diagnosis invented.

\begin{table*}[t]
\centering\footnotesize
\input{herik_contrib/tab_rq3_length_and_strat.tex}
\caption{A1 vs.\ A0 (and S) beyond the averages. (a) Raw paired difference with 95\% question-clustered bootstrap CI ($^{*}$: CI excludes~0, uncorrected); CIs are recomputed from item-level scores ($5{,}000$ resamples, own seed) and may differ from Table~\ref{tab:contrasts} in the second decimal. \emph{Adj.}: A1$-$A0 in a within-item regression on A1, A0 and S adding $\log(\text{words})$, with question-clustered SE; $\beta_{\log w}$: its coefficient; $\alpha_{\Delta w=0}$: intercept of the item-level regression of the A1$-$A0 score difference on the $\log$-length difference (A1's advantage at equal length); $\rho$: Spearman between word and score differences. (b) Stratified by gold grade; \emph{Wins}: share of items won in both orders. (c) Stratified by the diagnosis's grade error; CIs resample items (exploratory). Source: \texttt{results/herik\_variants/}.}
\label{tab:rq3_length}
\end{table*}

% ------------------------------------------------------------------------------
% BLOCO 2 (§5.3 Questions): substituir a 2ª frase do parágrafo (main.tex L169, "Gap relevance is higher ...")
% ------------------------------------------------------------------------------
Gap relevance is higher for adaptive conditions (A1$-$S <<a1s_qrel>>, A0$-$S <<a0s_qrel>>; not in the Holm family), and A1's questions, which receive the diagnosis's gap list, are also more gap-relevant than A0's (<<a1a0_qrel>>, question-clustered CI <<a1a0_qrel_ci>>), including for under-graded answers (<<sub_qrel>>, item-level CI <<sub_qrel_ci>>). The price is slightly lower clarity (<<a1a0_qcla>>, <<a1a0_qcla_ci>>; both uncorrected): A1 stems are longer (<<stem_a1>> vs.\ <<stem_a0>> words) and more often compound (``compare X and discuss Y''). When the listed gaps are peripheral, the same link turns them into peripheral questions (Table~\ref{tab:rq3_qual}).

% ------------------------------------------------------------------------------
% BLOCO 3 (Discussion): substituir o item (i) de \paragraph{What it does not support.} (main.tex L185)
% ------------------------------------------------------------------------------
(i)~That an explicit diagnosis stage is needed: a single-call baseline matches it on the dimensions that matter, and its small edge in coherence, level adequacy and question relevance does not appear to be a length artifact but may stem from prompt differences rather than from the diagnosis itself. A1 and A0 differ in more than the diagnosis: A1's support-text prompt asks for an everyday analogy and an encouraging tone and its questions are generated in a separate call that receives the gap list, whereas A0 produces text and questions in one JSON call that also receives the key concepts. A clean ablation would run A1's prompts with an empty diagnosis. The diagnosis is also a point of failure: with a fixed three-gap list, it helps partly correct answers but narrows or misdirects material for nearly correct ones and can propagate its own errors. It may still be valuable as an interpretable artifact for teachers (its QWK is moderate and conservative), which we did not evaluate.

% ------------------------------------------------------------------------------
% BLOCO 4 (Limitations): substituir \textbf{Scope.} (L194) e \textbf{Generation.} (L197)
% ------------------------------------------------------------------------------
\textbf{Scope.} One domain (school biology), one level (grades 8--9), 15 questions, 180 generated items; the pilot excludes gold-3 answers, but already for gold-2 answers A1 loses its edge over A0 and the paired reading suggests over-remediation (Tables~\ref{tab:rq3_length}b and~\ref{tab:rq3_qual}), so the risk may be larger for fully correct answers. Statistics resample questions, but 15 clusters give wide intervals, and per-grade or per-question analyses ($n{=}60$ or $12$) are exploratory and uncorrected.

\textbf{Generation.} A single generation run per item (temperature 0.4); no repeated seeds. A0 lands at the lower edge of the word budget (mean 120 words; <<a0_below>> below 120), so A1 and A0 barely overlap in length; we rely on S (same length as A1) and within-item length controls rather than on length-matched A1--A0 pairs. The off-reference check in Table~\ref{tab:rq3_qual} is a curated lexical proxy, not human annotation.

% ------------------------------------------------------------------------------
% BLOCO 5 (Apêndice): incluir em \subsection{Additional tables} (após L238) e substituir a última
% frase do \subsection{Qualitative example} (L241: "A0 also acknowledges chloroplasts, but adds ...")
% ------------------------------------------------------------------------------
\begin{table*}[h]
\centering\footnotesize
\input{herik_contrib/tab_rq3_qualitative_summary.tex}
\caption{Mechanisms behind A1 vs.\ A0, from reading paired materials and counting their recurrence over the 180 pilot items (no student answers reproduced). Item IDs refer to the released outputs; ``diag.'': grade estimated by the diagnosis. Off-reference terms come from a curated list of school-biology terms absent from both the reference answers and the static text S of the question; ``not traceable'' means the term does not occur in the diagnosis either, which quotes the student's answer.}
\label{tab:rq3_qual}
\end{table*}

A0 also acknowledges chloroplasts, but adds content not in the reference answers (vacuoles). This is occasional rather than systematic: vacuoles appear in <<vac_a0>> of the 12 A0 texts for this question (in <<vac_a0_stud>> of them the student had mentioned vacuoles) and in <<vac_a1>> A1 text; over all items, curated off-reference technical terms occur <<tech_a0>> times in A0 and <<tech_a1>> times in A1, and judged faithfulness is equal (A1$-$A0 <<faith>>). Symmetrically, A1 leaves the reference when its diagnosis does (Table~\ref{tab:rq3_qual}).
"""


def fill(t: str) -> str:
    out = re.sub(r"<<(\w+)>>", lambda m: V[m.group(1)], t)
    assert "<<" not in out, "marcador não preenchido"
    return out


(DST / "rq2_rq3_draft.tex").write_text(fill(DRAFT), encoding="utf-8")
print("OK:", ", ".join(p.name for p in [DST / "tab_rq3_length_and_strat.tex", DST / "tab_rq3_qualitative_summary.tex", DST / "rq2_rq3_draft.tex"]))
