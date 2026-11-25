"""Tabelas LaTeX da seção de robustez (paper/tables/tab_rb_*.tex), geradas dos CSVs de results_robust/. Sem números digitados à mão."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results_robust"
T = ROOT / "paper" / "tables"
T.mkdir(parents=True, exist_ok=True)
rd = lambda n: pd.read_csv(R / f"{n}.csv")  # noqa: E731


def ci(e, lo, hi, star=False):
    return f"${e:+.2f}$ [{lo:.2f}, {hi:.2f}]" + ("*" if star else "")


def write(name, lines):
    (T / f"tab_rb_{name}.tex").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------- H1: replicação A1 - S
h1 = rd("h1_replicacao_A1_menos_S")
LAB = {"piloto, J1 (original)": "Main pilot, judge 1", "piloto, J2": "Main pilot, judge 2", "semente 1, J1": "Seed 1, judge 1",
       "semente 2, J1": "Seed 2, judge 1", "gerador 2 (DeepSeek), J1": "DeepSeek generator, judge 1",
       "gerador 2 (DeepSeek), J2": "DeepSeek generator, judge 2", "diagnóstico v2, J1": "Calibrated diagnosis (v2), judge 1",
       "diagnóstico v2, J2": "Calibrated diagnosis (v2), judge 2"}
L = [r"\begin{tabular}{lcc}", r"\toprule", r"Replication & Gap focus A1$-$S [CI] & Usefulness A1$-$S [CI] \\", r"\midrule"]
for k, name in LAB.items():
    a = h1[(h1.replica == k) & (h1.dim == "foco_na_lacuna")].iloc[0]
    b = h1[(h1.replica == k) & (h1.dim == "utilidade_pedagogica")].iloc[0]
    L.append(f"{name} & {ci(a['A1-S'], a.lo, a.hi)} & {ci(b['A1-S'], b.lo, b.hi)} \\\\")
L += [r"\bottomrule", r"\end{tabular}"]
write("h1", L)

# ---------------------------------------------------------------- H2/H3/H4: A1 vs A0, A1 sem diagnóstico, v2
h2, h3, h4 = rd("h2_A1_vs_A0"), rd("h3_ablacao_sem_diagnostico"), rd("h4_diagnostico_v2")
L = [r"\begin{tabular}{llcc}", r"\toprule", r"Contrast & Judge / run & Gap focus [CI] & Usefulness [CI] \\", r"\midrule"]
for lab, key in (("main pilot, judge 1", "piloto, J1"), ("main pilot, judge 2", "piloto, J2"), ("seed 1, judge 1", "semente 1, J1"),
                 ("seed 2, judge 1", "semente 2, J1"), ("DeepSeek, judge 1", "gerador 2, J1"), ("DeepSeek, judge 2", "gerador 2, J2")):
    a = h2[(h2.replica == key) & (h2.dim == "foco_na_lacuna")].iloc[0]
    b = h2[(h2.replica == key) & (h2.dim == "utilidade_pedagogica")].iloc[0]
    L.append(f"A1$-$A0 (explicit diagnosis vs.\\ direct) & {lab} & {ci(a['A1-A0'], a.lo, a.hi)} & {ci(b['A1-A0'], b.lo, b.hi)} \\\\")
L.append(r"\midrule")
for jd in ("J1", "J2"):
    a = h3[(h3.juiz == jd) & (h3.contraste.str.startswith("A1ø (sem")) & (h3.dim == "foco_na_lacuna")].iloc[0]
    b = h3[(h3.juiz == jd) & (h3.contraste.str.startswith("A1ø (sem")) & (h3.dim == "utilidade_pedagogica")].iloc[0]
    L.append(f"A1$\\varnothing-$A1 (empty diagnosis vs.\\ diagnosis) & judge {jd[-1]} & {ci(a.est, a.lo, a.hi)} & {ci(b.est, b.lo, b.hi)} \\\\")
L.append(r"\midrule")
for jd in ("J1", "J2"):
    a = h4[(h4.juiz == jd) & (h4.dim == "foco_na_lacuna")].iloc[0]
    b = h4[(h4.juiz == jd) & (h4.dim == "utilidade_pedagogica")].iloc[0]
    L.append(f"A1(v2)$-$A1(v0) (calibrated vs.\\ original diagnosis) & judge {jd[-1]} & {ci(a['A1v2-A1v0'], a.lo, a.hi)} & {ci(b['A1v2-A1v0'], b.lo, b.hi)} \\\\")
L += [r"\bottomrule", r"\end{tabular}"]
write("abl", L)

# ---------------------------------------------------------------- H5: juiz cego (A1 - S)
h5 = rd("h5_juiz_cego")
DIM5 = {"coerencia": "Coherence", "correcao_conceitual": "Conceptual correctness", "fidelidade_gabarito": "Faithfulness", "completude": "Completeness",
        "adequacao_nivel": "Level adequacy", "qualidade_geral": "Overall quality"}
L = [r"\begin{tabular}{lcc}", r"\toprule", r"Dimension (judge blind to the student's answer) & Judge 1 A1$-$S [CI] & Judge 2 A1$-$S [CI] \\", r"\midrule"]
for k, name in DIM5.items():
    r1 = h5[(h5.juiz == "J1") & (h5.contraste == "A1 − S") & (h5.dim == k)].iloc[0]
    r2 = h5[(h5.juiz == "J2") & (h5.contraste == "A1 − S") & (h5.dim == k)].iloc[0]
    L.append(f"{name} & {ci(r1.est, r1.lo, r1.hi)} & {ci(r2.est, r2.lo, r2.hi)} \\\\")
L += [r"\bottomrule", r"\end{tabular}"]
write("blind", L)

# ---------------------------------------------------------------- H6: nota 3
h6 = rd("h6_nota3_sobre_remediacao")
DIM6 = {"sobre_remediacao": "Over-remediation (1 none -- 5 severe)", "reconhece_acertos": "Acknowledges correct parts (1--5)",
        "utilidade_pedagogica": "Usefulness (1--5)", "coerencia": "Coherence", "correcao_conceitual": "Conceptual correctness"}
L = [r"\begin{tabular}{lcc}", r"\toprule", r"Gold-3 answers ($n{=}60$): A1$-$S & Judge 1 [CI] & Judge 2 [CI] \\", r"\midrule"]
for k, name in DIM6.items():
    r1 = h6[(h6.juiz == "J1") & (h6.contraste == "A1 − S") & (h6.dim == k)].iloc[0]
    r2 = h6[(h6.juiz == "J2") & (h6.contraste == "A1 − S") & (h6.dim == k)].iloc[0]
    L.append(f"{name} & {ci(r1.est, r1.lo, r1.hi)} & {ci(r2.est, r2.lo, r2.hi)} \\\\")
for k, name in (("foco_na_lacuna", "Gap focus (standard rubric)"), ("utilidade_pedagogica", "Usefulness (standard rubric)")):
    r1 = h6[(h6.juiz == "J1") & (h6.contraste.str.contains("padrão")) & (h6.dim == k)].iloc[0]
    r2 = h6[(h6.juiz == "J2") & (h6.contraste.str.contains("padrão")) & (h6.dim == k)].iloc[0]
    L.append(f"{name} & {ci(r1.est, r1.lo, r1.hi)} & {ci(r2.est, r2.lo, r2.hi)} \\\\")
L += [r"\bottomrule", r"\end{tabular}"]
write("nota3", L)

# ---------------------------------------------------------------- H7: transferência
m, c = rd("h7_transferencia_medias"), rd("h7_transferencia_contrastes")
NM = {"N_sem_material": "No material", "S0_gabarito": "Reference answers (S0)", "S_estatico": "Static reinforcement (S)", "A0_direto": "Direct generation (A0)",
      "A1_pipeline": "Diagnose-then-generate (A1)", "A2_pipeline_verif": "A1 + verification (A2)"}
L = [r"\begin{tabular}{lcc}", r"\toprule", r"Material read before the transfer test & $n$ & Mean score (0--3) [CI] \\", r"\midrule"]
for k, name in NM.items():
    r = m[m["condição"] == k].iloc[0]
    L.append(f"{name} & {int(r.n)} & {r['nota média (0-3) no pós-teste']:.2f} [{r.lo:.2f}, {r.hi:.2f}] \\\\")
L.append(r"\midrule")
for key, name in (("S_estatico − N_sem_material", "S $-$ none"), ("A1_pipeline − N_sem_material", "A1 $-$ none"), ("A1_pipeline − S_estatico", "A1 $-$ S"),
                  ("A1_pipeline − A0_direto", "A1 $-$ A0"), ("A2_pipeline_verif − A1_pipeline", "A2 $-$ A1")):
    r = c[c.contraste == key].iloc[0]
    L.append(f"\\emph{{{name}}} & {int(r.n)} & {ci(r.est, r.lo, r.hi, star=r.p_holm < 0.05)} \\\\")
L += [r"\bottomrule", r"\end{tabular}"]
write("transfer", L)

# ---------------------------------------------------------------- concordância entre juízes
ag = rd("juizes_concordancia")
DIM = {"coerencia": "Coherence", "correcao_conceitual": "Conceptual correctness", "fidelidade_gabarito": "Faithfulness", "foco_na_lacuna": "Gap focus",
       "utilidade_pedagogica": "Usefulness", "adequacao_nivel": "Level adequacy"}
L = [r"\begin{tabular}{lccccc}", r"\toprule", r"Dimension & Spearman & QWK & Mean J1 / J2 & \% of 5s J1 / J2 \\", r"\midrule"]
for k, name in DIM.items():
    r = ag[ag.dim == k].iloc[0]
    L.append(f"{name} & {r.spearman:.2f} & {r.QWK:.2f} & {r['J1 média']:.2f} / {r['J2 média']:.2f} & {r['J1 % nota 5'] * 100:.0f} / {r['J2 % nota 5'] * 100:.0f} \\\\")
L += [r"\bottomrule", r"\end{tabular}"]
write("agree", L)

# ---------------------------------------------------------------- modelo misto
mm = rd("h10_modelo_misto")
L = [r"\begin{tabular}{llccc}", r"\toprule", r"Judge, dimension & Contrast & Mixed model [CI] & Cluster bootstrap [CI] & $\hat\tau_{q}$ \\", r"\midrule"]
for _, r in mm[mm.contraste.isin(["A1_pipeline − S_estatico", "A1_pipeline − A0_direto"])].iterrows():
    d = "focus" if r.dim == "foco_na_lacuna" else "usefulness"
    con = "A1$-$S" if r.contraste.endswith("S_estatico") else "A1$-$A0"
    L.append(f"J{r.juiz[-1]}, {d} & {con} & {ci(r.est_misto, r.lo_misto, r.hi_misto)} & {ci(r.est_bootstrap, r.lo_boot, r.hi_boot)} & {r.tau_questao:.2f} \\\\")
L += [r"\bottomrule", r"\end{tabular}"]
write("mixed", L)

# ---------------------------------------------------------------- por tópico
tp = rd("por_topico")
TN = {"células e metabolismo": "Cells and metabolism", "genética": "Genetics", "sistemas do corpo humano": "Human body systems"}
L = [r"\begin{tabular}{lcccc}", r"\toprule", r"Topic & Questions & Gap focus A1$-$S (J1) [CI] & Gap focus A1$-$S (J2) & Usefulness A1$-$S (J1 / J2) \\", r"\midrule"]
for t, name in TN.items():
    a = tp[(tp["tópico"] == t) & (tp.dim == "foco_na_lacuna")].iloc[0]
    b = tp[(tp["tópico"] == t) & (tp.dim == "utilidade_pedagogica")].iloc[0]
    L.append(f"{name} & {int(a['questões'])} & {ci(a['J1 A1−S'], a['J1 lo'], a['J1 hi'])} & ${a['J2 A1−S']:+.2f}$ & ${b['J1 A1−S']:+.2f}$ / ${b['J2 A1−S']:+.2f}$ \\\\")
L += [r"\bottomrule", r"\end{tabular}"]
write("topic", L)
print("ok:", sorted(p.name for p in T.glob("tab_rb_*.tex")))
