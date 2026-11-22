"""Gera paper/tables/tab_rq4w.tex (RQ4 com gerador fraco) a partir de results/rq4w_condicoes.csv. Offline, sem API."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
d = pd.read_csv(ROOT / "results" / "rq4w_condicoes.csv").set_index("versao")
NAME = {
    "A1_artigo": "A1, GPT-4o mini (main pilot)",
    "A2_artigo": "A2, GPT-4o mini (main pilot)",
    "A1w": "A1-weak (Llama 3.1 8B)",
    "A2w": "A2-weak: rewrite if unsupported or incorrect",
    "A2w_inc": "A2-weak-inc: rewrite only if incorrect",
}
lines = [r"\begin{tabular}{lcccccccc}", r"\toprule",
         r"Version & Incorr./text & Texts w/ error & Rewritten & Corr. & Faith. & Useful & Focus & Words \\", r"\midrule"]
for k, name in NAME.items():
    r = d.loc[k]
    rew = "--" if pd.isna(r.frac_reescrito) or k in ("A1_artigo", "A2_artigo", "A1w") else f"{r.frac_reescrito * 100:.0f}\\%"
    if k == "A2_artigo":
        rew = "74\\%"  # 133/180 textos reescritos (results/rq4_resumo.csv)
    lines.append(f"{name} & {r.incorretas:.2f} & {r.frac_com_incorreta * 100:.1f}\\% & {rew} & {r.correcao:.2f} & {r.fidelidade:.2f} & "
                 f"{r.utilidade:.2f} & {r.foco:.2f} & {r.palavras:.0f} \\\\")
    if k == "A2_artigo":
        lines.append(r"\midrule")
lines += [r"\bottomrule", r"\end{tabular}"]
out = ROOT / "paper" / "tables" / "tab_rq4w.tex"
out.write_text("\n".join(lines), encoding="utf-8")
print("ok ->", out)
