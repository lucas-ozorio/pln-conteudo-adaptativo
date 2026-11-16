"""Análise de E0, E1 e E3 -> results/ (CSV + summary.md). Todas as comparações são pareadas por item."""
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import confusion_matrix

from _common import parse
from pln.common import ROOT, read_jsonl
from pln.data import bootstrap_ci, norm, qwk
from pln.judge import TEXT_DIMS

a, cfg, out = parse(__doc__)
res = ROOT / ("results_mock" if a.mock else "results")
res.mkdir(exist_ok=True)
md = ["# Resultados iniciais" + (" (MOCK: encanamento, sem valor científico)" if a.mock else ""), ""]
items = pd.DataFrame(read_jsonl(ROOT / "data" / "processed" / "pilot_set.jsonl"))
diag_set = pd.DataFrame(read_jsonl(ROOT / "data" / "processed" / "diag_set.jsonl"))


def holm(ps):
    ps = np.asarray(ps, float)
    order = np.argsort(ps)
    adj = np.empty_like(ps)
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, (len(ps) - rank) * ps[i])
        adj[i] = min(1.0, run)
    return adj


def paired(x, y):
    """Diferença média (x-y) com IC95% bootstrap, Wilcoxon e rank-biserial (efeito)."""
    d = np.asarray(x, float) - np.asarray(y, float)
    d = d[~np.isnan(d)]
    if len(d) == 0:
        return dict(n=0, diff=np.nan, lo=np.nan, hi=np.nan, p=np.nan, r_rb=np.nan)
    m, lo, hi = bootstrap_ci(d)
    nz = d[d != 0]
    if len(nz) == 0:
        return dict(n=len(d), diff=m, lo=lo, hi=hi, p=1.0, r_rb=0.0)
    p = stats.wilcoxon(nz).pvalue
    rk = stats.rankdata(np.abs(nz))
    r_rb = (rk[nz > 0].sum() - rk[nz < 0].sum()) / rk.sum()
    return dict(n=len(d), diff=m, lo=lo, hi=hi, p=p, r_rb=r_rb)


def table(df: pd.DataFrame, floatfmt="%.3f") -> str:
    return df.to_markdown(index=False, floatfmt=".3f") if hasattr(df, "to_markdown") else df.to_string(index=False)


try:
    import tabulate  # noqa: F401
except ImportError:  # sem tabulate: formata manualmente
    def table(df, floatfmt=None):  # noqa: F811
        cols = list(df.columns)
        lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
        for i in range(len(df)):
            cells = []
            for c in cols:
                v = df[c].iloc[i]
                cells.append(f"{v:.3f}" if isinstance(v, (float, np.floating)) and not float(v).is_integer() else
                             (str(int(v)) if isinstance(v, (float, np.floating)) and float(v).is_integer() and c in ("n", "itens", "nota_ouro") else
                              (f"{v:.3f}" if isinstance(v, (float, np.floating)) else str(v))))
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines)

# =============================================================================== E0
dg = read_jsonl(out / "diagnosis.jsonl")
if dg:
    d = pd.DataFrame([{"item_id": r["item_id"], "pred": r["diag"].get("nota_estimada"), "conceitos": r["diag"].get("conceitos", [])} for r in dg])
    d = d.merge(diag_set[["item_id", "grade", "answer", "concepts"]], on="item_id").dropna(subset=["pred"])
    d["pred"] = d.pred.astype(int)
    yt, yp = d.grade.values, d.pred.values
    rho = stats.spearmanr(yt, yp)
    # proxy lexical de cobertura de conceitos (fraca: palavra-chave presente no texto do aluno)
    tp = fp = fn = 0
    for r in d.itertuples():
        ans = norm(r.answer)
        status = {norm(c.get("conceito", "")): c.get("status") for c in (r.conceitos or []) if isinstance(c, dict)}
        for c in r.concepts:
            lex = norm(c) in ans
            llm = any(norm(c) in k or k in norm(c) for k, s in status.items() if s in ("presente", "parcial") and k)
            tp += lex and llm
            fp += (not lex) and llm
            fn += lex and (not llm)
    prec = tp / max(1, tp + fp)
    rec = tp / max(1, tp + fn)
    e0 = pd.DataFrame([{"n": len(d), "QWK": qwk(yt, yp), "Spearman": rho.statistic, "MAE": np.abs(yt - yp).mean(),
                        "acc_exata": (yt == yp).mean(), "acc_binaria(>=2)": ((yt >= 2) == (yp >= 2)).mean(),
                        "concept_P(proxy)": prec, "concept_R(proxy)": rec}])
    e0.to_csv(res / "e0_diagnostico.csv", index=False)
    cm = pd.DataFrame(confusion_matrix(yt, yp, labels=[0, 1, 2, 3]), index=[f"ouro={i}" for i in range(4)], columns=[f"pred={i}" for i in range(4)])
    cm.to_csv(res / "e0_confusao.csv")
    md += ["## E0 — Diagnóstico vs nota-ouro (PT-ASAG)", table(e0), "",
           "Referência de teto: no PT-ASAG original, a concordância entre avaliadores humanos foi r=0,581 (Pearson) nas respostas duplamente avaliadas (Galhardi et al., 2018).",
           "As colunas `concept_*(proxy)` comparam o diagnóstico com presença lexical da palavra-chave: proxy fraco, não é anotação de conceito.", "",
           "Matriz de confusão:", "```", cm.to_string(), "```", ""]

# =============================================================================== E1
ab = read_jsonl(out / "judgments_abs.jsonl")
mats = pd.DataFrame(read_jsonl(out / "materials.jsonl"))
conds = cfg["pipeline"]["conditions"]
if ab:
    rows = []
    for r in ab:
        row = {"item_id": r["item_id"], "condition": r["condition"], "rep": r["rep"], "n_palavras": r["n_palavras"], **r["texto"]}
        q = [x for x in r["questoes"]]
        if q:
            row["q_alinhamento"] = np.nanmean([x["alinhamento_gabarito"] or np.nan for x in q])
            row["q_clareza"] = np.nanmean([x["clareza"] or np.nan for x in q])
            row["q_relevancia"] = np.nanmean([x["relevancia_lacuna"] or np.nan for x in q])
            row["q_resp_correta"] = np.mean([bool(x["resposta_esperada_correta"]) for x in q])
            row["q_bloom_match"] = np.mean([(x["bloom_pedido"] or "") == (x["bloom_percebido"] or "") for x in q])
        rows.append(row)
    J = pd.DataFrame(rows).groupby(["item_id", "condition"], as_index=False).mean(numeric_only=True)  # média das réplicas
    J = J.merge(items[["item_id", "grade", "question_id"]], on="item_id")
    J.to_csv(res / "e1_juiz_absoluto_por_item.csv", index=False)
    dims = TEXT_DIMS + ["afirmacoes_incorretas"]
    qd = [c for c in J.columns if c.startswith("q_")]

    # --- médias com IC95% por condição
    lines = []
    for c in [c for c in conds if c in J.condition.unique()]:
        s = J[J.condition == c]
        row = {"condicao": c, "n": len(s), "palavras": s.n_palavras.mean()}
        for dm in dims + qd:
            if dm in s and s[dm].notna().any():
                m, lo, hi = bootstrap_ci(s[dm])
                row[dm] = f"{m:.2f} [{lo:.2f}; {hi:.2f}]"
        lines.append(row)
    means = pd.DataFrame(lines)
    means.to_csv(res / "e1_medias_por_condicao.csv", index=False)
    md += ["## E1 — Qualidade do material (juiz LLM, 1–5; IC95% bootstrap por item)", table(means.fillna("—")), ""]

    # --- contrastes pareados (Holm sobre todas as dimensões x contrastes)
    contrasts = [tuple(p) for p in cfg["judge"]["pairs"]]
    crow = []
    wide = {dm: J.pivot(index="item_id", columns="condition", values=dm) for dm in dims + qd}
    for (x, y) in contrasts:
        for dm in dims + qd:
            w = wide[dm]
            if x in w and y in w:
                crow.append({"contraste": f"{x} − {y}", "dimensao": dm, **paired(w[x], w[y])})
    cdf = pd.DataFrame(crow)
    if len(cdf):
        cdf["p_holm"] = holm(cdf.p.fillna(1.0))
        cdf.to_csv(res / "e1_contrastes_pareados.csv", index=False)
        md += ["### Contrastes pareados (diferença média, IC95%, Wilcoxon, efeito r rank-biserial, p ajustado por Holm)",
               table(cdf[["contraste", "dimensao", "n", "diff", "lo", "hi", "r_rb", "p", "p_holm"]]), ""]

    # --- viés de verbosidade: efeito do tamanho do texto sobre a nota, controlando a condição
    vb = []
    cdum = pd.get_dummies(J.condition, drop_first=True).astype(float)
    for dm in TEXT_DIMS:
        s = J.dropna(subset=[dm])
        X = np.column_stack([np.ones(len(s)), np.log(s.n_palavras.clip(lower=1)), cdum.loc[s.index].values])
        beta = np.linalg.lstsq(X, s[dm].values, rcond=None)[0]
        rho = stats.spearmanr(s.n_palavras, s[dm]).statistic
        vb.append({"dimensao": dm, "spearman(palavras,nota)": rho, "coef_log_palavras|condicao": beta[1]})
    vbd = pd.DataFrame(vb)
    vbd.to_csv(res / "e1_vies_verbosidade.csv", index=False)
    md += ["### Viés de verbosidade do juiz (coef. ≈ 0 e Spearman baixo indicam pouca influência do tamanho)", table(vbd), ""]

    # --- por estrato de nota-ouro (quem mais se beneficia da adaptação?)
    if "A1_pipeline" in J.condition.unique() and "S_estatico" in J.condition.unique():
        st = []
        for g, sub in J.groupby("grade"):
            w = sub.pivot(index="item_id", columns="condition", values="foco_na_lacuna")
            w2 = sub.pivot(index="item_id", columns="condition", values="utilidade_pedagogica")
            st.append({"nota_ouro": g, "A1−S foco_na_lacuna": (w["A1_pipeline"] - w["S_estatico"]).mean(),
                       "A1−S utilidade": (w2["A1_pipeline"] - w2["S_estatico"]).mean(), "n": len(w)})
        md += ["### Efeito da adaptação por nota-ouro do aluno", table(pd.DataFrame(st)), ""]

    # --- verificação (A2)
    if "verif" in mats and mats.verif.notna().any():
        v = pd.DataFrame([x for x in mats.verif.dropna()])
        md += ["### A2 — verificação ancorada no gabarito",
               f"afirmações/texto: {v.n_afirmacoes.mean():.1f}; com problema (não suportada/incorreta): {v.n_problemas.mean():.2f}/texto; "
               f"textos reescritos: {v.reescrito.mean():.1%}; afirmações incorretas/texto: {v.n_incorretas.mean():.2f}", ""]

# --- par-a-par
pw = pd.DataFrame(read_jsonl(out / "judgments_pair.jsonl"))
if len(pw):
    L = mats.set_index(["item_id", "condition"]).n_palavras.to_dict()
    rows = []
    for (x, y), g in pw.groupby(["x", "y"]):
        nt = g[g.winner != "empate"]
        pos = nt.pos_first_won.mean() if len(nt) else np.nan  # 0,5 = sem viés de posição
        per = g.groupby("item_id").winner.agg(list)
        cons = per.map(lambda ws: len(set(ws)) == 1).mean()  # concorda nas duas ordens
        # vitória "robusta": x vence nas duas ordens vs y vence nas duas; resto = inconsistente/empate
        xw = per.map(lambda ws: all(w == x for w in ws)).sum()
        yw = per.map(lambda ws: all(w == y for w in ws)).sum()
        n = len(per)
        pval = stats.binomtest(int(xw), int(xw + yw), 0.5).pvalue if xw + yw > 0 else np.nan
        longer = []
        for iid, ws in per.items():
            lx, ly = L.get((iid, x), 0), L.get((iid, y), 0)
            if lx != ly:
                for w in ws:
                    if w != "empate":
                        longer.append(w == (x if lx > ly else y))
        rows.append({"par": f"{x} vs {y}", "itens": n, f"vitória robusta x": xw / n, "vitória robusta y": yw / n,
                     "inconsistente/empate": 1 - (xw + yw) / n, "p(sinal, robustas)": pval,
                     "viés_posição(1º vence)": pos, "consistência_ordem": cons, "mais_longo_vence": np.mean(longer) if longer else np.nan})
    pwd = pd.DataFrame(rows)
    pwd.to_csv(res / "e1_pareado.csv", index=False)
    md += ["### Comparação par-a-par (duas ordens; 'robusta' = mesmo vencedor nas duas ordens)",
           "x é o 1º item do par. `viés_posição`=0,5 e `mais_longo_vence`=0,5 indicam ausência de viés de posição e de verbosidade.",
           table(pwd), ""]

# =============================================================================== E3
ss = pd.DataFrame(read_jsonl(out / "student_sim.jsonl"))
if len(ss):
    P_ = ss.pivot_table(index="item_id", columns="condition", values="nota", aggfunc="first")
    gold = items.set_index("item_id").grade
    if "PRE" in P_:
        pre = P_["PRE"].dropna()
        g = gold.reindex(pre.index)
        md += ["## E3 (exploratório) — Ganho com aluno simulado",
               f"Sanidade do corretor: QWK(nota do corretor na resposta original, nota-ouro) = {qwk(g.values, pre.values.astype(int)):.3f} (n={len(pre)})", ""]
        rows = []
        gains = {}
        for c in [c for c in P_.columns if c != "PRE"]:
            gains[c] = (P_[c] - P_["PRE"])
            m, lo, hi = bootstrap_ci(gains[c])
            rows.append({"condicao": c, "n": int(gains[c].notna().sum()), "ganho_medio": m, "ic_lo": lo, "ic_hi": hi})
        gdf = pd.DataFrame(rows)
        gdf.to_csv(res / "e3_ganho.csv", index=False)
        md += [table(gdf), ""]
        crow = []
        if "N_sem_material" in gains:
            for c in gains:
                if c != "N_sem_material":
                    crow.append({"contraste": f"{c} − N_sem_material", **paired(gains[c], gains["N_sem_material"])})
        for (x, y) in cfg["judge"]["pairs"]:
            if x in gains and y in gains:
                crow.append({"contraste": f"{x} − {y}", **paired(gains[x], gains[y])})
        if crow:
            cd = pd.DataFrame(crow)
            cd["p_holm"] = holm(cd.p.fillna(1.0))
            cd.to_csv(res / "e3_contrastes.csv", index=False)
            md += ["Contrastes de ganho (pareados por item):", table(cd[["contraste", "n", "diff", "lo", "hi", "r_rb", "p", "p_holm"]]), "",
                   "Atenção: LLM simulando aluno tende a 'aprender' mais do que alunos reais e já conhece a matéria; "
                   "interprete apenas o ganho RELATIVO a N_sem_material e as diferenças entre condições."]

(res / "summary.md").write_text("\n".join(md), encoding="utf-8")
print(f"escrito {res / 'summary.md'}")
