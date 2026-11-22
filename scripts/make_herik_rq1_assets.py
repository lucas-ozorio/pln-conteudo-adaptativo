"""Gera os artefatos LaTeX (.tex) e figura (.pdf) de RQ1 (H-01 + H-02) para `paper/herik_contrib/`.

Lê exclusivamente CSVs já commitados em `results/herik_h02/` e `results/herik_e0/`,
sem depender de `data/raw/` nem alterar `paper/tables/` ou `paper/figures/`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pln.common import ROOT  # noqa: E402

CONTRIB_DIR = ROOT / "paper" / "herik_contrib"
H02_DIR = ROOT / "results" / "herik_h02"
E0_DIR = ROOT / "results" / "herik_e0"

VARIANT_LABELS = {
    "v0_baseline": "Original prompt (v0)",
    "v1_rubrica_calibrada": "Calibrated rubric, zero-shot (v1)",
    "v2_fewshot_cross_q": "v1 + cross-question anchors (v2)",
}
ORDER = ["v0_baseline", "v1_rubrica_calibrada", "v2_fewshot_cross_q"]


def _fmt_bold(text: str, is_best: bool) -> str:
    return rf"\textbf{{{text}}}" if is_best else text


def make_calibration_table(comp: pd.DataFrame, logo_row: pd.Series) -> str:
    rows = {r["variante"]: r for _, r in comp.iterrows()}
    best_qwk = max(rows[v]["QWK"] for v in ORDER)
    best_spear = max(rows[v]["Spearman"] for v in ORDER)
    best_mae = min(rows[v]["MAE"] for v in ORDER)
    best_abs_bias = min(abs(rows[v]["bias_medio"]) for v in ORDER)
    best_gap3 = min(rows[v]["pct_ouro3_3_lacunas"] for v in ORDER)
    best_err3 = min(rows[v]["pct_ouro3_com_erro_conceitual"] for v in ORDER)

    lines = [
        r"\begin{tabular}{lccccccc}",
        r"\toprule",
        r"Variant & QWK [95\% CI] & $\Delta$QWK & Spearman & MAE & Bias & 3-gap ($g{=}3$) & Err ($g{=}3$) \\",
        r"\midrule",
    ]
    for v in ORDER:
        r = rows[v]
        qwk_s = _fmt_bold(f"{r['QWK']:.3f}", abs(r["QWK"] - best_qwk) < 1e-9)
        qwk_cell = f"{qwk_s} [{r['QWK_ic_lo']:.3f}, {r['QWK_ic_hi']:.3f}]"
        if v == "v0_baseline":
            delta_cell = "--"
        else:
            star = "*" if r["delta_QWK_ic_lo"] > 0 else ""
            delta_cell = f"${r['delta_QWK_vs_v0']:+.3f}${star}"
        sp_cell = _fmt_bold(f"{r['Spearman']:.3f}", abs(r["Spearman"] - best_spear) < 1e-9)
        mae_cell = _fmt_bold(f"{r['MAE']:.3f}", abs(r["MAE"] - best_mae) < 1e-9)
        bias_cell = _fmt_bold(f"${r['bias_medio']:+.3f}$", abs(abs(r["bias_medio"]) - best_abs_bias) < 1e-9)
        g3_cell = _fmt_bold(f"{r['pct_ouro3_3_lacunas'] * 100:.1f}\\%", abs(r["pct_ouro3_3_lacunas"] - best_gap3) < 1e-9)
        e3_cell = _fmt_bold(
            f"{r['pct_ouro3_com_erro_conceitual'] * 100:.1f}\\%",
            abs(r["pct_ouro3_com_erro_conceitual"] - best_err3) < 1e-9,
        )
        lines.append(
            f"{VARIANT_LABELS[v]} & {qwk_cell} & {delta_cell} & {sp_cell} & {mae_cell} & {bias_cell} & {g3_cell} & {e3_cell} \\\\"
        )

    logo_delta = float(logo_row["QWK"] - rows["v0_baseline"]["QWK"])
    lines += [
        r"\midrule",
        (
            rf"\emph{{Post-hoc LOGO calibration (v0)}} & \emph{{{logo_row['QWK']:.3f}}} & "
            rf"\emph{{${logo_delta:+.3f}$}} & \emph{{{logo_row['Spearman']:.3f}}} & "
            rf"\emph{{{logo_row['MAE']:.3f}}} & \emph{{${logo_row['bias_medio']:+.3f}$}} & -- & -- \\"
        ),
        r"\bottomrule",
        r"\end{tabular}",
    ]
    return "\n".join(lines) + "\n"


def make_confusion_table(cm_df: pd.DataFrame, variant: str = "v2_fewshot_cross_q") -> str:
    sub = cm_df[cm_df["variante"] == variant].sort_values("ouro")
    lines = [
        r"\begin{tabular}{lcccc}",
        r"\toprule",
        r"Gold $\backslash$ Predicted & 0 & 1 & 2 & 3 \\",
        r"\midrule",
    ]
    for _, r in sub.iterrows():
        lines.append(
            f"{int(r['ouro'])} & {int(r['pred_0'])} & {int(r['pred_1'])} & {int(r['pred_2'])} & {int(r['pred_3'])} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines) + "\n"


def make_per_question_figure(q_df: pd.DataFrame, out_pdf: Path) -> None:
    piv = q_df.pivot(index="question_id", columns="variante", values="QWK")
    piv = piv.sort_values("v0_baseline", ascending=True)
    qids = [f"q{int(q)}" for q in piv.index]
    xs = np.arange(len(qids))

    plt.rcParams.update({"font.size": 8, "font.family": "serif", "pdf.fonttype": 42})
    fig, ax = plt.subplots(figsize=(6.3, 2.5))

    for i, q in enumerate(piv.index):
        vals = [piv.loc[q, "v0_baseline"], piv.loc[q, "v1_rubrica_calibrada"], piv.loc[q, "v2_fewshot_cross_q"]]
        ax.plot([i, i], [min(vals), max(vals)], color="0.80", lw=1.2, zorder=1)

    styles = [
        ("v0_baseline", "s", "#555555", "v0 (original)"),
        ("v1_rubrica_calibrada", "^", "#2b83ba", "v1 (calibrated rubric)"),
        ("v2_fewshot_cross_q", "o", "#d7191c", "v2 (v1 + cross-q anchors)"),
    ]
    for col, marker, color, label in styles:
        ax.scatter(xs, piv[col].values, marker=marker, color=color, s=26, zorder=3, label=label)

    ax.set_xticks(xs)
    ax.set_xticklabels(qids, fontsize=7)
    ax.set_ylim(0.10, 0.96)
    ax.set_ylabel("QWK per question")
    ax.set_xlabel("PT-ASAG question (sorted by v0 baseline QWK)")
    ax.grid(axis="y", linestyle=":", alpha=0.5, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(ncol=3, fontsize=7, loc="upper left", frameon=False, handletextpad=0.3, columnspacing=1.0)
    plt.tight_layout()
    plt.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    CONTRIB_DIR.mkdir(parents=True, exist_ok=True)
    comp = pd.read_csv(H02_DIR / "h02_comparacao_variantes.csv")
    cm = pd.read_csv(H02_DIR / "h02_matrizes_confusao.csv")
    q_df = pd.read_csv(H02_DIR / "h02_por_questao.csv")
    logo = pd.read_csv(E0_DIR / "e0_recalibracao_logo.csv")
    logo_row = logo[(logo["scope"] == "global") & (logo["metodo"] == "ordinal_thresholds_logo")].iloc[0]

    (CONTRIB_DIR / "tab_rq1_calibration.tex").write_text(make_calibration_table(comp, logo_row), encoding="utf-8")
    (CONTRIB_DIR / "tab_rq1_confusion_v2.tex").write_text(make_confusion_table(cm), encoding="utf-8")
    make_per_question_figure(q_df, CONTRIB_DIR / "fig_rq1_per_question.pdf")
    print("ok ->", sorted(p.name for p in CONTRIB_DIR.iterdir()))


if __name__ == "__main__":
    main()
