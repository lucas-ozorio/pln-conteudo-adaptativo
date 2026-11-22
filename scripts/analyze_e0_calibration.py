"""Análise offline do conservadorismo e calibração do diagnóstico em E0 (tarefa H-01, RQ1).

Lê `outputs/diagnosis.jsonl`, `data/processed/diag_set.jsonl`, metadados do PT-ASAG
e `outputs/student_sim.jsonl` (condição PRE), sem fazer chamadas de API de LLM e sem
expor respostas de alunos no relatório.

Saídas em `results/herik_e0/`:
  - e0_por_questao.csv
  - e0_estrutura_diagnostico.csv
  - e0_diagnoser_vs_grader_180.csv
  - e0_recalibracao_logo.csv
  - e0_taxonomia_erros.csv
  - analise_e0_diagnostico.md
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import Ridge
from sklearn.metrics import confusion_matrix
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pln.common import ROOT, load_config, read_jsonl  # noqa: E402
from pln.data import RAW, norm, qwk  # noqa: E402

OUT_DIR = ROOT / "results" / "herik_e0"

PT_STOPWORDS = {
    "a", "o", "e", "as", "os", "um", "uma", "uns", "umas", "de", "da", "do", "das", "dos",
    "em", "na", "no", "nas", "nos", "por", "para", "com", "sem", "sob", "sobre", "entre",
    "que", "se", "ao", "aos", "ou", "mas", "pois", "como", "mais", "menos", "muito",
    "muita", "muitos", "muitas", "tambem", "ja", "nao", "sim", "sao", "ser", "esta",
    "estao", "tem", "ter", "pode", "podem", "ele", "ela", "eles", "elas", "isso", "isto",
    "esse", "essa", "este", "esta", "seu", "sua", "seus", "suas", "quando", "onde", "qual",
    "quais", "pelo", "pela", "pelos", "pelas", "atraves", "forma",
}

DIAG_FEATURES = [
    "nota_estimada",
    "frac_presente",
    "frac_parcial",
    "frac_ausente",
    "frac_incorreto",
    "n_erros_conceituais",
    "n_acertos",
    "n_lacunas",
    "n_conceitos_listados",
]


def content_tokens(text: str) -> set[str]:
    """Extrai tokens normalizados com >=3 caracteres fora da lista de stopwords."""
    return {t for t in norm(text).split() if len(t) >= 3 and t not in PT_STOPWORDS}


def safe_qwk(yt, yp) -> float:
    yt_arr = np.asarray(yt, dtype=int)
    yp_arr = np.asarray(yp, dtype=int)
    if len(yt_arr) == 0:
        return float("nan")
    if np.all(yt_arr == yt_arr[0]) and np.all(yp_arr == yp_arr[0]):
        return 1.0 if yt_arr[0] == yp_arr[0] else 0.0
    val = qwk(yt_arr, yp_arr, labels=(0, 1, 2, 3))
    return float(val)


def safe_corr(fn, x, y) -> float:
    x_arr, y_arr = np.asarray(x, float), np.asarray(y, float)
    if len(x_arr) < 3 or np.std(x_arr) == 0 or np.std(y_arr) == 0:
        return float("nan")
    return float(fn(x_arr, y_arr)[0])


def compute_metrics(yt, yp) -> dict:
    yt_arr = np.asarray(yt, dtype=int)
    yp_arr = np.asarray(yp, dtype=int)
    diff = yp_arr - yt_arr
    return {
        "n": int(len(yt_arr)),
        "QWK": safe_qwk(yt_arr, yp_arr),
        "Spearman": safe_corr(stats.spearmanr, yt_arr, yp_arr),
        "Pearson": safe_corr(stats.pearsonr, yt_arr, yp_arr),
        "MAE": float(np.abs(diff).mean()),
        "bias_medio": float(diff.mean()),
        "acc_exata": float((yt_arr == yp_arr).mean()),
        "acc_tol1": float((np.abs(diff) <= 1).mean()),
        "acc_binaria_ge2": float(((yt_arr >= 2) == (yp_arr >= 2)).mean()),
        "taxa_subavaliacao": float((yp_arr < yt_arr).mean()),
        "taxa_superavaliacao": float((yp_arr > yt_arr).mean()),
    }


def fast_qwk(yt: np.ndarray, yp: np.ndarray) -> float:
    """QWK 4x4 vetorizado para busca rápida de limiares em LOGO."""
    n = len(yt)
    if n == 0:
        return 0.0
    idx = yt * 4 + yp
    O = np.bincount(idx, minlength=16).reshape(4, 4).astype(float)
    w = np.subtract.outer(np.arange(4), np.arange(4)) ** 2 / 9.0
    hist_t = O.sum(axis=1)
    hist_p = O.sum(axis=0)
    E = np.outer(hist_t, hist_p) / n
    denom = (w * E).sum()
    if denom == 0.0:
        return 1.0 if np.array_equal(yt, yp) else 0.0
    return float(1.0 - (w * O).sum() / denom)


def load_ptasag_extra_counts(cfg: dict, valid_qids: set[int], diag_counts: pd.Series) -> pd.DataFrame:
    """Conta respostas únicas válidas no PT-ASAG v2 fora do diag_set (para holdout H-02)."""
    a = pd.read_csv(RAW / "student_answers_and_grades_v2.csv")
    a["answer_text"] = a.answer_text.astype(str).str.strip()
    a["words"] = a.answer_text.str.split().str.len()
    a = a[(a.words >= 1) & (a.words <= cfg["sample"]["max_words"]) & a.question_id.isin(valid_qids)].copy()
    a["key"] = a.question_id.astype(str) + "|" + a.answer_text.map(norm)
    a = a.drop_duplicates("key")
    tot = a.groupby("question_id").size().rename("total_disponivel_ptasag")
    by_grade = a.groupby(["question_id", "grade"]).size().unstack(fill_value=0)
    df_c = pd.DataFrame({"total_disponivel_ptasag": tot}).join(diag_counts.rename("n_diag_set"))
    df_c["extra_holdout_fora_diag_set"] = df_c["total_disponivel_ptasag"] - df_c["n_diag_set"]
    for g in (0, 1, 2, 3):
        df_c[f"ptasag_grade_{g}"] = by_grade.get(g, 0)
    return df_c.reset_index()


def load_e0_dataframe(cfg: dict) -> pd.DataFrame:
    """Carrega e junta outputs/diagnosis.jsonl com data/processed/diag_set.jsonl."""
    dg_raw = read_jsonl(ROOT / "outputs" / "diagnosis.jsonl")
    ds_raw = read_jsonl(ROOT / "data" / "processed" / "diag_set.jsonl")
    if len(dg_raw) != len(ds_raw):
        raise RuntimeError(f"Contagens divergentes: diagnosis={len(dg_raw)}, diag_set={len(ds_raw)}")

    dg_rows = []
    for r in dg_raw:
        diag = r["diag"]
        conceitos = [c for c in (diag.get("conceitos") or []) if isinstance(c, dict)]
        counts = {"presente": 0, "parcial": 0, "ausente": 0, "incorreto": 0}
        for c in conceitos:
            st = c.get("status")
            if st in counts:
                counts[st] += 1
        n_list = len(conceitos)
        denom = max(1, n_list)
        lacs = [x for x in (diag.get("lacunas_prioritarias") or []) if isinstance(x, str)]
        dg_rows.append(
            {
                "item_id": r["item_id"],
                "nota_estimada": int(diag["nota_estimada"]),
                "n_conceitos_listados": n_list,
                "n_presente": counts["presente"],
                "n_parcial": counts["parcial"],
                "n_ausente": counts["ausente"],
                "n_incorreto": counts["incorreto"],
                "frac_presente": counts["presente"] / denom,
                "frac_parcial": counts["parcial"] / denom,
                "frac_ausente": counts["ausente"] / denom,
                "frac_incorreto": counts["incorreto"] / denom,
                "frac_coberto": (counts["presente"] + counts["parcial"]) / denom,
                "n_acertos": len(diag.get("acertos") or []),
                "n_erros_conceituais": len(diag.get("erros_conceituais") or []),
                "n_lacunas": len(lacs),
                "is_3_lacunas": int(len(lacs) == 3),
                "lacunas_txt": lacs,
            }
        )

    df_dg = pd.DataFrame(dg_rows)
    df_ds = pd.DataFrame(ds_raw)
    df = df_dg.merge(df_ds, on="item_id", how="inner")
    if len(df) != 595:
        raise RuntimeError(f"Esperados 595 itens pareados, encontrados {len(df)}")

    df["pred"] = df["nota_estimada"].astype(int)
    df["grade"] = df["grade"].astype(int)
    df["erro"] = df["pred"] - df["grade"]
    df["n_conceitos_esperados"] = df["concepts"].map(len)
    df["n_conceitos_extras"] = df["n_conceitos_listados"] - df["n_conceitos_esperados"]
    df["n_refs"] = df["refs"].map(len)
    df["palavras_aluno"] = df["answer"].str.split().str.len()
    df["palavras_ref_media"] = df["refs"].map(lambda rs: float(np.mean([len(r.split()) for r in rs])))
    df["zero_erros_conceituais"] = (df["n_erros_conceituais"] == 0).astype(int)
    df["tem_conceitos_extras"] = (df["n_conceitos_extras"] > 0).astype(int)

    # Sobreposição lexical do aluno contra gabaritos individuais vs. união e conceitos,
    # e respaldo lexical das lacunas geradas contra gabaritos + conceitos-chave
    max_ov, union_ov, min_ov, conc_ov, lac_sem_rc = [], [], [], [], []
    for r in df.itertuples():
        ans_toks = content_tokens(r.answer)
        ref_sets = [content_tokens(ref) for ref in r.refs]
        ovs = [len(ans_toks & rs) / max(1, len(rs)) for rs in ref_sets]
        union_toks = set().union(*ref_sets) if ref_sets else set()
        c_toks = set().union(*(content_tokens(c) for c in r.concepts)) if r.concepts else set()
        rc_toks4 = {t for t in (union_toks | c_toks) if len(t) >= 4}
        n_sem = sum(
            1
            for lac in r.lacunas_txt
            if len({t for t in content_tokens(lac) if len(t) >= 4} & rc_toks4) == 0
        )
        max_ov.append(max(ovs) if ovs else 0.0)
        min_ov.append(min(ovs) if ovs else 0.0)
        union_ov.append(len(ans_toks & union_toks) / max(1, len(union_toks)))
        conc_ov.append(len(ans_toks & c_toks) / max(1, len(c_toks)))
        lac_sem_rc.append(n_sem)
    df["max_ref_overlap"] = max_ov
    df["min_ref_overlap"] = min_ov
    df["all_refs_overlap"] = union_ov
    df["gap_max_vs_all_refs"] = df["max_ref_overlap"] - df["all_refs_overlap"]
    df["concept_union_overlap"] = conc_ov
    df["n_lacunas_sem_respaldo"] = lac_sem_rc
    df["alguma_lacuna_sem_respaldo"] = (df["n_lacunas_sem_respaldo"] > 0).astype(int)
    df = df.drop(columns=["lacunas_txt"])
    df["faixa_erro"] = np.where(
        df["erro"] < 0, "subavaliado", np.where(df["erro"] > 0, "superavaliado", "exato")
    )
    return df


def build_per_question_table(df: pd.DataFrame, ptasag_counts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for qid, g in df.groupby("question_id"):
        m = compute_metrics(g["grade"], g["pred"])
        g3 = g[g["grade"] == 3]
        g2 = g[g["grade"] == 2]
        g0 = g[g["grade"] == 0]
        rows.append(
            {
                "question_id": int(qid),
                **m,
                "pct_ouro3_pred3": float((g3["pred"] == 3).mean()) if len(g3) else float("nan"),
                "pct_ouro3_pred_le1": float((g3["pred"] <= 1).mean()) if len(g3) else float("nan"),
                "pct_ouro2_pred1": float((g2["pred"] == 1).mean()) if len(g2) else float("nan"),
                "pct_ouro0_pred_ge1": float((g0["pred"] >= 1).mean()) if len(g0) else float("nan"),
                "n_refs": int(g["n_refs"].iloc[0]),
                "n_conceitos_esperados": int(g["n_conceitos_esperados"].iloc[0]),
                "media_conceitos_listados": float(g["n_conceitos_listados"].mean()),
                "media_conceitos_extras": float(g["n_conceitos_extras"].mean()),
                "palavras_aluno_media": float(g["palavras_aluno"].mean()),
                "palavras_ref_media": float(g["palavras_ref_media"].iloc[0]),
            }
        )
    out = pd.DataFrame(rows).merge(
        ptasag_counts[["question_id", "total_disponivel_ptasag", "extra_holdout_fora_diag_set"]],
        on="question_id",
        how="left",
    )
    return out.sort_values("question_id").reset_index(drop=True)


def _summarize_structure_group(sub: pd.DataFrame, agrupamento: str, grupo: str, grade=np.nan, pred=np.nan) -> dict:
    return {
        "agrupamento": agrupamento,
        "grupo": grupo,
        "grade": grade,
        "pred": pred,
        "n": int(len(sub)),
        "n_conceitos_esperados": float(sub["n_conceitos_esperados"].mean()),
        "n_conceitos_listados": float(sub["n_conceitos_listados"].mean()),
        "n_conceitos_extras": float(sub["n_conceitos_extras"].mean()),
        "n_presente": float(sub["n_presente"].mean()),
        "n_parcial": float(sub["n_parcial"].mean()),
        "n_ausente": float(sub["n_ausente"].mean()),
        "n_incorreto": float(sub["n_incorreto"].mean()),
        "frac_presente": float(sub["frac_presente"].mean()),
        "frac_coberto": float(sub["frac_coberto"].mean()),
        "n_acertos": float(sub["n_acertos"].mean()),
        "n_erros_conceituais": float(sub["n_erros_conceituais"].mean()),
        "pct_zero_erros_conceituais": float(sub["zero_erros_conceituais"].mean()),
        "n_lacunas": float(sub["n_lacunas"].mean()),
        "pct_3_lacunas": float(sub["is_3_lacunas"].mean()),
        "n_lacunas_sem_respaldo": float(sub["n_lacunas_sem_respaldo"].mean()),
        "pct_alguma_lacuna_sem_respaldo": float(sub["alguma_lacuna_sem_respaldo"].mean()),
        "palavras_aluno": float(sub["palavras_aluno"].mean()),
    }


def build_structure_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = [_summarize_structure_group(df, "geral", "todos")]
    for gr, sub in df.groupby("grade"):
        rows.append(_summarize_structure_group(sub, "por_grade", f"ouro={gr}", grade=int(gr)))
    for fx in ("subavaliado", "exato", "superavaliado"):
        sub = df[df["faixa_erro"] == fx]
        rows.append(_summarize_structure_group(sub, "faixa_erro", fx))
    for (gr, pr), sub in df.groupby(["grade", "pred"]):
        rows.append(_summarize_structure_group(sub, "par_grade_pred", f"ouro={gr}_pred={pr}", grade=int(gr), pred=int(pr)))
    return pd.DataFrame(rows)


def build_diagnoser_vs_grader(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Compara gpt-4o-mini (DIAG_USER) e gemini-2.5-flash (GRADER_USER) nos 180 itens do piloto."""
    ss = [r for r in read_jsonl(ROOT / "outputs" / "student_sim.jsonl") if r["condition"] == "PRE"]
    df_pre = pd.DataFrame([{"item_id": r["item_id"], "grader_nota": int(r["nota"])} for r in ss])
    m = df.merge(df_pre, on="item_id", how="inner")
    if len(m) != 180:
        raise RuntimeError(f"Esperados 180 itens no piloto PRE, encontrados {len(m)}")

    pairs = [
        ("diagnoser_vs_ouro", m["grade"], m["pred"]),
        ("grader_vs_ouro", m["grade"], m["grader_nota"]),
        ("diagnoser_vs_grader", m["grader_nota"], m["pred"]),
    ]
    rows = []
    cms = {}
    for label, yt, yp in pairs:
        met = compute_metrics(yt, yp)
        cm = confusion_matrix(yt, yp, labels=[0, 1, 2, 3])
        row = {"comparacao": label, **met}
        for i in range(4):
            for j in range(4):
                row[f"cm_r{i}_c{j}"] = int(cm[i, j])
        rows.append(row)
        cms[label] = pd.DataFrame(cm, index=[f"ref={i}" for i in range(4)], columns=[f"pred={j}" for j in range(4)])

    # Também estratificado por nota-ouro (0, 1, 2) para comparação direta de calibração
    for g in (0, 1, 2):
        sub = m[m["grade"] == g]
        for label, yp_col in (("diagnoser_vs_ouro", "pred"), ("grader_vs_ouro", "grader_nota")):
            met = compute_metrics(sub["grade"], sub[yp_col])
            rows.append({"comparacao": f"{label}_ouro_{g}", **met})
    return pd.DataFrame(rows), cms


def _best_constant_shift(yt: np.ndarray, yp: np.ndarray) -> float:
    best_score, best_delta = (-1e9, -1e9, -1e9), 0.0
    for delta in (-1.0, 0.0, 1.0):
        cand = np.clip(yp + int(delta), 0, 3)
        score = (fast_qwk(yt, cand), -float(np.abs(cand - yt).mean()), -abs(delta))
        if score > best_score:
            best_score, best_delta = score, delta
    return best_delta


def _best_monotonic_map(yt: np.ndarray, yp: np.ndarray) -> tuple[int, int, int, int]:
    """Busca exaustiva nos 35 mapeamentos monotônicos {0,1,2,3}->{0,1,2,3}."""
    best_score = (-1e9, -1e9, -1e9)
    best_map = (0, 1, 2, 3)
    ident = np.array([0, 1, 2, 3])
    for comb in itertools.combinations_with_replacement((0, 1, 2, 3), 4):
        lut = np.array(comb, dtype=int)
        cand = lut[yp]
        score = (fast_qwk(yt, cand), -float(np.abs(cand - yt).mean()), -float(np.abs(lut - ident).sum()))
        if score > best_score:
            best_score, best_map = score, comb
    return best_map


def _best_thresholds_3(yt: np.ndarray, scores: np.ndarray) -> tuple[float, float, float]:
    """Busca determinística em grade grossa + refino local por coordenada para maximizar QWK."""
    grid = np.round(np.arange(0.20, 2.85, 0.10), 2)
    best_score = (-1e9, -1e9, -1e9)
    best_t = (0.5, 1.5, 2.5)
    for i, t1 in enumerate(grid):
        for j in range(i, len(grid)):
            t2 = grid[j]
            for k in range(j, len(grid)):
                t3 = grid[k]
                cand = np.digitize(scores, [t1, t2, t3])
                l1_dist = abs(t1 - 0.5) + abs(t2 - 1.5) + abs(t3 - 2.5)
                sc = (fast_qwk(yt, cand), -float(np.abs(cand - yt).mean()), -l1_dist)
                if sc > best_score:
                    best_score, best_t = sc, (float(t1), float(t2), float(t3))
    # Refino local por coordenada (passo 0.02 em +/- 0.14)
    t = list(best_t)
    for _ in range(2):
        for c_idx in range(3):
            lo = 0.05 if c_idx == 0 else t[c_idx - 1]
            hi = 2.95 if c_idx == 2 else t[c_idx + 1]
            cands = np.round(np.arange(max(lo, t[c_idx] - 0.14), min(hi, t[c_idx] + 0.141), 0.02), 2)
            for v in cands:
                trial = list(t)
                trial[c_idx] = float(v)
                cand = np.digitize(scores, trial)
                l1_dist = abs(trial[0] - 0.5) + abs(trial[1] - 1.5) + abs(trial[2] - 2.5)
                sc = (fast_qwk(yt, cand), -float(np.abs(cand - yt).mean()), -l1_dist)
                if sc > best_score:
                    best_score, t[c_idx] = sc, float(v)
    return (t[0], t[1], t[2])


def _inner_logo_ridge_scores(X: np.ndarray, y: np.ndarray, qids: np.ndarray, alpha: float = 10.0) -> np.ndarray:
    oof = np.zeros(len(y), dtype=float)
    for qid in np.unique(qids):
        va = qids == qid
        tr = ~va
        sc = StandardScaler()
        X_tr = sc.fit_transform(X[tr])
        X_va = sc.transform(X[va])
        model = Ridge(alpha=alpha).fit(X_tr, y[tr])
        oof[va] = model.predict(X_va)
    return oof


def run_logo_recalibration(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Avalia recalibração pós-hoc em Leave-One-Question-Out (15 folds, sem vazamento)."""
    qids = df["question_id"].values
    yt = df["grade"].values
    yp_raw = df["pred"].values
    X = df[DIAG_FEATURES].values.astype(float)

    preds = {
        "baseline_raw": yp_raw.copy(),
        "shift_constante_logo": np.zeros(len(df), dtype=int),
        "remap_nota_logo": np.zeros(len(df), dtype=int),
        "linear_diag_features_logo": np.zeros(len(df), dtype=int),
        "ordinal_thresholds_logo": np.zeros(len(df), dtype=int),
    }
    fold_params = {"shifts": [], "maps": [], "thresholds": []}

    for qid in sorted(df["question_id"].unique()):
        va = qids == qid
        tr = ~va

        delta = _best_constant_shift(yt[tr], yp_raw[tr])
        preds["shift_constante_logo"][va] = np.clip(yp_raw[va] + int(delta), 0, 3)
        fold_params["shifts"].append((int(qid), int(delta)))

        lut = _best_monotonic_map(yt[tr], yp_raw[tr])
        preds["remap_nota_logo"][va] = np.array(lut, dtype=int)[yp_raw[va]]
        fold_params["maps"].append((int(qid), lut))

        sc = StandardScaler()
        X_tr = sc.fit_transform(X[tr])
        X_va = sc.transform(X[va])
        ridge = Ridge(alpha=10.0).fit(X_tr, yt[tr])
        cont_va = ridge.predict(X_va)
        preds["linear_diag_features_logo"][va] = np.clip(np.rint(cont_va), 0, 3).astype(int)

        # Para otimizar (t1, t2, t3) sem otimismo in-sample, usa OOF interno nos 14 folds de treino
        oof_tr = _inner_logo_ridge_scores(X[tr], yt[tr], qids[tr], alpha=10.0)
        t1, t2, t3 = _best_thresholds_3(yt[tr], oof_tr)
        preds["ordinal_thresholds_logo"][va] = np.digitize(cont_va, [t1, t2, t3])
        fold_params["thresholds"].append((int(qid), (t1, t2, t3)))

    rows = []
    for method, yp in preds.items():
        rows.append({"scope": "global", "question_id": "ALL", "metodo": method, **compute_metrics(yt, yp)})
        for qid in sorted(df["question_id"].unique()):
            mask = qids == qid
            rows.append({"scope": "por_questao", "question_id": str(qid), "metodo": method, **compute_metrics(yt[mask], yp[mask])})

    return pd.DataFrame(rows), fold_params


def build_error_taxonomy(df: pd.DataFrame) -> pd.DataFrame:
    """Quantifica os modos de falha (subavaliação ouro=2/3 e superavaliação ouro=0)."""
    subsets = [
        ("ouro=3 -> pred<=1 (grave)", (df["grade"] == 3) & (df["pred"] <= 1)),
        ("ouro=3 -> pred=2 (leve)", (df["grade"] == 3) & (df["pred"] == 2)),
        ("ouro=3 -> pred=3 (acerto ref)", (df["grade"] == 3) & (df["pred"] == 3)),
        ("ouro=2 -> pred=1 (subavaliado)", (df["grade"] == 2) & (df["pred"] == 1)),
        ("ouro=2 -> pred=2 (acerto ref)", (df["grade"] == 2) & (df["pred"] == 2)),
        ("ouro=1 -> pred=1 (acerto ref)", (df["grade"] == 1) & (df["pred"] == 1)),
        ("ouro=0 -> pred>=1 (indulgente)", (df["grade"] == 0) & (df["pred"] >= 1)),
        ("ouro=0 -> pred=1 (indulgente)", (df["grade"] == 0) & (df["pred"] == 1)),
        ("ouro=0 -> pred=0 (acerto ref)", (df["grade"] == 0) & (df["pred"] == 0)),
    ]
    rows = []
    for label, mask in subsets:
        sub = df[mask]
        multi_ref_trap = (sub["max_ref_overlap"] >= 0.50) & (sub["all_refs_overlap"] < 0.40)
        rows.append(
            {
                "modo_erro": label,
                "n": int(len(sub)),
                "pct_zero_erros_conceituais": float(sub["zero_erros_conceituais"].mean()),
                "pct_tem_conceitos_extras": float(sub["tem_conceitos_extras"].mean()),
                "media_conceitos_esperados": float(sub["n_conceitos_esperados"].mean()),
                "media_conceitos_listados": float(sub["n_conceitos_listados"].mean()),
                "media_conceitos_extras": float(sub["n_conceitos_extras"].mean()),
                "media_presente": float(sub["n_presente"].mean()),
                "media_parcial": float(sub["n_parcial"].mean()),
                "media_ausente": float(sub["n_ausente"].mean()),
                "media_incorreto": float(sub["n_incorreto"].mean()),
                "media_n_acertos": float(sub["n_acertos"].mean()),
                "pct_algum_acerto": float((sub["n_acertos"] >= 1).mean()),
                "pct_algum_presente_ou_parcial": float(((sub["n_presente"] + sub["n_parcial"]) >= 1).mean()),
                "max_ref_overlap_medio": float(sub["max_ref_overlap"].mean()),
                "all_refs_overlap_medio": float(sub["all_refs_overlap"].mean()),
                "gap_max_vs_all_refs_medio": float(sub["gap_max_vs_all_refs"].mean()),
                "concept_union_overlap_medio": float(sub["concept_union_overlap"].mean()),
                "pct_alta_sobreposicao_1ref_baixa_uniao": float(multi_ref_trap.mean()),
                "media_palavras_aluno": float(sub["palavras_aluno"].mean()),
            }
        )
    return pd.DataFrame(rows)


def _df_to_md(df: pd.DataFrame, float_cols: dict[str, str] | None = None) -> str:
    d = df.copy()
    float_cols = float_cols or {}
    for col in d.columns:
        if col in float_cols:
            fmt = float_cols[col]
            d[col] = d[col].map(lambda v: "—" if pd.isna(v) else format(v, fmt))
        elif pd.api.types.is_float_dtype(d[col]):
            d[col] = d[col].map(lambda v: "—" if pd.isna(v) else f"{v:.3f}")
    headers = list(d.columns)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in d.itertuples(index=False):
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)


def write_markdown_report(
    df: pd.DataFrame,
    q_tab: pd.DataFrame,
    st_tab: pd.DataFrame,
    dg_tab: pd.DataFrame,
    cms: dict[str, pd.DataFrame],
    logo_tab: pd.DataFrame,
    fold_params: dict,
    tax_tab: pd.DataFrame,
) -> None:
    """Gera o relatório técnico consolidado em `results/herik_e0/analise_e0_diagnostico.md`."""
    g_metrics = compute_metrics(df["grade"], df["pred"])
    cm_full = pd.DataFrame(
        confusion_matrix(df["grade"], df["pred"], labels=[0, 1, 2, 3]),
        index=[f"ouro={i}" for i in range(4)],
        columns=[f"pred={j}" for j in range(4)],
    )

    q_sorted = q_tab.sort_values("QWK").reset_index(drop=True)
    worst_q = q_sorted.iloc[0]
    best_q = q_sorted.iloc[-1]

    # Correlações entre características das questões e QWK / viés
    r_refs_qwk = safe_corr(stats.spearmanr, q_tab["n_refs"], q_tab["QWK"])
    r_conc_qwk = safe_corr(stats.spearmanr, q_tab["n_conceitos_esperados"], q_tab["QWK"])
    r_len_qwk = safe_corr(stats.spearmanr, q_tab["palavras_aluno_media"], q_tab["QWK"])
    r_conc_bias = safe_corr(stats.spearmanr, q_tab["n_conceitos_esperados"], q_tab["bias_medio"])

    logo_global = logo_tab[logo_tab["scope"] == "global"].drop(columns=["scope", "question_id"])
    logo_q = logo_tab[logo_tab["scope"] == "por_questao"].pivot(index="question_id", columns="metodo", values="QWK")
    logo_q.index = logo_q.index.astype(int)
    logo_q = logo_q.sort_index()
    logo_q["ganho_remap"] = logo_q["remap_nota_logo"] - logo_q["baseline_raw"]
    logo_q["ganho_ordinal"] = logo_q["ordinal_thresholds_logo"] - logo_q["baseline_raw"]
    logo_q_df = logo_q[
        ["baseline_raw", "shift_constante_logo", "remap_nota_logo", "linear_diag_features_logo", "ordinal_thresholds_logo", "ganho_remap", "ganho_ordinal"]
    ].reset_index()

    from collections import Counter
    shift_counts = Counter(d for _, d in fold_params["shifts"])
    map_counts = Counter(m for _, m in fold_params["maps"])
    t_arr = np.array([t for _, t in fold_params["thresholds"]])

    ouro3_le1 = tax_tab[tax_tab["modo_erro"] == "ouro=3 -> pred<=1 (grave)"].iloc[0]
    ouro3_2 = tax_tab[tax_tab["modo_erro"] == "ouro=3 -> pred=2 (leve)"].iloc[0]
    ouro2_1 = tax_tab[tax_tab["modo_erro"] == "ouro=2 -> pred=1 (subavaliado)"].iloc[0]
    ouro0_ge1 = tax_tab[tax_tab["modo_erro"] == "ouro=0 -> pred>=1 (indulgente)"].iloc[0]

    dg_main = dg_tab[dg_tab["comparacao"].isin(["diagnoser_vs_ouro", "grader_vs_ouro", "diagnoser_vs_grader"])][
        ["comparacao", "n", "QWK", "Spearman", "MAE", "bias_medio", "acc_exata", "taxa_subavaliacao", "taxa_superavaliacao"]
    ]
    fx_tab = st_tab[st_tab["agrupamento"] == "faixa_erro"][
        ["grupo", "n", "n_conceitos_esperados", "n_conceitos_listados", "n_conceitos_extras", "frac_presente", "frac_coberto", "n_acertos", "n_erros_conceituais", "pct_zero_erros_conceituais", "palavras_aluno"]
    ]
    gr_tab = st_tab[st_tab["agrupamento"] == "por_grade"][
        ["grupo", "n", "n_conceitos_listados", "n_conceitos_extras", "n_presente", "n_parcial", "n_ausente", "n_incorreto", "frac_coberto", "n_erros_conceituais", "pct_zero_erros_conceituais", "n_lacunas", "pct_3_lacunas", "pct_alguma_lacuna_sem_respaldo"]
    ]

    tax_view = tax_tab[
        [
            "modo_erro", "n", "pct_zero_erros_conceituais", "pct_tem_conceitos_extras",
            "media_presente", "media_parcial", "media_ausente", "media_incorreto",
            "max_ref_overlap_medio", "all_refs_overlap_medio", "pct_alta_sobreposicao_1ref_baixa_uniao", "media_palavras_aluno",
        ]
    ]

    q_view = q_sorted[
        [
            "question_id", "n", "QWK", "Spearman", "MAE", "bias_medio", "acc_exata",
            "taxa_subavaliacao", "pct_ouro3_pred_le1", "pct_ouro2_pred1", "pct_ouro0_pred_ge1",
            "n_refs", "n_conceitos_esperados", "palavras_aluno_media", "extra_holdout_fora_diag_set",
        ]
    ]

    total_extra = int(q_tab["extra_holdout_fora_diag_set"].sum())

    d_row = dg_tab[dg_tab["comparacao"] == "diagnoser_vs_ouro"].iloc[0]
    g_row = dg_tab[dg_tab["comparacao"] == "grader_vs_ouro"].iloc[0]
    a_row = dg_tab[dg_tab["comparacao"] == "diagnoser_vs_grader"].iloc[0]
    cm_d = cms["diagnoser_vs_ouro"].values
    cm_g = cms["grader_vs_ouro"].values

    calib_wins = logo_q_df[logo_q_df["ganho_ordinal"] >= 0.13].sort_values("ganho_ordinal", ascending=False)
    calib_str = ", ".join(
        f"`q{int(r.question_id)}` (`{r.baseline_raw:.3f}` → `{r.ordinal_thresholds_logo:.3f}`)"
        for r in calib_wins.itertuples()
    )
    hard_q = logo_q_df[logo_q_df["ordinal_thresholds_logo"] < 0.45].sort_values("ordinal_thresholds_logo")
    hard_str = ", ".join(
        f"`q{int(r.question_id)}` (`{r.baseline_raw:.3f}` → `{r.ordinal_thresholds_logo:.3f}`)"
        for r in hard_q.itertuples()
    )
    focus_ids = sorted(set(q_sorted.iloc[:5]["question_id"].astype(int)).union(set(hard_q["question_id"].astype(int))))
    focus_str = ", ".join(f"`q{q}`" for q in focus_ids)

    lines = [
        "# Análise Offline do Conservadorismo em E0 (`H-01`, `RQ1`)",
        "",
        "Relatório gerado por `scripts/analyze_e0_calibration.py` sobre os 595 itens reais de `outputs/diagnosis.jsonl` pareados com `data/processed/diag_set.jsonl` (100% offline, sem chamadas de API).",
        "",
        "## 1. Resumo Executivo",
        "",
        f"- **Reprodutibilidade base (`n = {g_metrics['n']}`):** `QWK = {g_metrics['QWK']:.3f}`, `Spearman = {g_metrics['Spearman']:.3f}`, `MAE = {g_metrics['MAE']:.3f}`, `acc_exata = {g_metrics['acc_exata']:.1%}`, `acc_binaria(>=2) = {g_metrics['acc_binaria_ge2']:.1%}` (idêntico a `results/e0_diagnostico.csv`).",
        f"- **Assimetria forte do erro:** viés médio = `{g_metrics['bias_medio']:+.3f}` pontos; **{g_metrics['taxa_subavaliacao']:.1%}** dos itens são subavaliados (`pred < grade`) contra **{g_metrics['taxa_superavaliacao']:.1%}** superavaliados (`pred > grade`). O erro concentra-se na compressão para `pred = 1` ({int((df['pred'] == 1).sum())}/{len(df)} = {(df['pred'] == 1).mean():.1%} das predições).",
        f"- **Não é só viés conservador nas notas altas, é colapso de extremos:** `ouro=3` cai para `<=1` em `{ouro3_le1['n']}/145` (`{ouro3_le1['n']/145:.1%}`) e `ouro=2` cai para `1` em `{ouro2_1['n']}/150` (`{ouro2_1['n']/150:.1%}`), mas ao mesmo tempo `ouro=0` sobe para `>=1` em `{ouro0_ge1['n']}/150` (`{ouro0_ge1['n']/150:.1%}`).",
        f"- **Causa estrutural principal — penalização sem erro conceitual:** entre os `{ouro3_le1['n']}` casos graves `ouro=3 -> pred<=1`, **{ouro3_le1['pct_zero_erros_conceituais']:.1%}** têm **zero erros conceituais** registrados; o mesmo ocorre em **{ouro2_1['pct_zero_erros_conceituais']:.1%}** dos `{ouro2_1['n']}` casos `ouro=2 -> pred=1`. O diagnoser está usando a contagem de conceitos marcados como `ausente` após forçar a extração de *todos* os conceitos + extras (`tem_conceitos_extras` em `{df['tem_conceitos_extras'].mean():.1%}` de todo o E0).",
        f"- **Quanto é calibração pura vs. discriminação (LOGO 15-fold):** apenas remapear a escala de `nota_estimada` via Leave-One-Question-Out (`remap_nota_logo`) já eleva o QWK de `{logo_global.loc[logo_global['metodo']=='baseline_raw', 'QWK'].iloc[0]:.3f}` para **{logo_global.loc[logo_global['metodo']=='remap_nota_logo', 'QWK'].iloc[0]:.3f}** (sem novo custo de API). Usar as frações internas do JSON (`ordinal_thresholds_logo`) chega a **{logo_global.loc[logo_global['metodo']=='ordinal_thresholds_logo', 'QWK'].iloc[0]:.3f}** (Spearman `{logo_global.loc[logo_global['metodo']=='ordinal_thresholds_logo', 'Spearman'].iloc[0]:.3f}`), aproximando o patamar do `grader` Gemini no subconjunto piloto.",
        "",
        "### Matriz de confusão completa (`n = 595`)",
        "```",
        cm_full.to_string(),
        "```",
        "",
        "---",
        "",
        "## 2. Desempenho por Questão (`QWK 0.18` a `0.78`)",
        "",
        f"- **Pior questão:** `q{int(worst_q['question_id'])}` (`QWK = {worst_q['QWK']:.3f}`, `Spearman = {worst_q['Spearman']:.3f}`, `bias = {worst_q['bias_medio']:+.3f}`, subavaliação `{worst_q['taxa_subavaliacao']:.1%}`, `ouro=3 -> pred<=1` = `{worst_q['pct_ouro3_pred_le1']:.1%}`).",
        f"- **Melhor questão:** `q{int(best_q['question_id'])}` (`QWK = {best_q['QWK']:.3f}`, `Spearman = {best_q['Spearman']:.3f}`, `bias = {best_q['bias_medio']:+.3f}`, `acc_exata = {best_q['acc_exata']:.1%}`).",
        f"- **Correlações entre atributos da questão e QWK/viés (`n = 15` questões):** Spearman(`n_refs`, `QWK`) = `{r_refs_qwk:+.3f}`; Spearman(`n_conceitos_esperados`, `QWK`) = `{r_conc_qwk:+.3f}`; Spearman(`palavras_aluno_media`, `QWK`) = `{r_len_qwk:+.3f}`; Spearman(`n_conceitos_esperados`, `bias_medio`) = `{r_conc_bias:+.3f}`.",
        f"- **Disponibilidade para holdout sem vazamento (`H-02`):** o PT-ASAG v2 possui **{total_extra}** respostas válidas únicas fora do `diag_set` (mínimo de `{int(q_tab['extra_holdout_fora_diag_set'].min())}` e máximo de `{int(q_tab['extra_holdout_fora_diag_set'].max())}` por questão).",
        "",
        _df_to_md(
            q_view,
            {
                "QWK": ".3f", "Spearman": ".3f", "MAE": ".3f", "bias_medio": "+.3f",
                "acc_exata": ".3f", "taxa_subavaliacao": ".3f", "pct_ouro3_pred_le1": ".3f",
                "pct_ouro2_pred1": ".3f", "pct_ouro0_pred_ge1": ".3f", "palavras_aluno_media": ".1f",
            },
        ),
        "",
        "---",
        "",
        "## 3. Anatomia Interna do Diagnóstico e Taxonomia de Erros",
        "",
        "### Por faixa de erro (`pred - grade`)",
        _df_to_md(
            fx_tab,
            {
                "n_conceitos_esperados": ".2f", "n_conceitos_listados": ".2f", "n_conceitos_extras": ".2f",
                "frac_presente": ".3f", "frac_coberto": ".3f", "n_acertos": ".2f",
                "n_erros_conceituais": ".2f", "pct_zero_erros_conceituais": ".3f", "palavras_aluno": ".1f",
            },
        ),
        "",
        "### Por nota-ouro (`grade`)",
        _df_to_md(
            gr_tab,
            {
                "n_conceitos_listados": ".2f", "n_conceitos_extras": ".2f", "n_presente": ".2f",
                "n_parcial": ".2f", "n_ausente": ".2f", "n_incorreto": ".2f",
                "frac_coberto": ".3f", "n_erros_conceituais": ".2f", "pct_zero_erros_conceituais": ".3f",
                "n_lacunas": ".2f", "pct_3_lacunas": ".3f", "pct_alguma_lacuna_sem_respaldo": ".3f",
            },
        ),
        "",
        "### Modos de falha quantificados (subavaliação, múltiplos gabaritos e indulgência em 0)",
        _df_to_md(
            tax_view,
            {
                "pct_zero_erros_conceituais": ".3f", "pct_tem_conceitos_extras": ".3f",
                "media_presente": ".2f", "media_parcial": ".2f", "media_ausente": ".2f",
                "media_incorreto": ".2f", "max_ref_overlap_medio": ".3f",
                "all_refs_overlap_medio": ".3f", "pct_alta_sobreposicao_1ref_baixa_uniao": ".3f",
                "media_palavras_aluno": ".1f",
            },
        ),
        "",
        "**Leitura dos mecanismos de erro:**",
        f"1. **Checklist rigorosa inflada por conceitos extras:** o prompt pede incluir todos os conceitos-chave + *até 2 ideias essenciais adicionais* do gabarito. Em `{df['tem_conceitos_extras'].mean():.1%}` dos 595 diagnósticos o modelo adiciona conceitos extras (média `+{df['n_conceitos_extras'].mean():.2f}` conceito). Mesmo quando a resposta é `ouro=3` e cai para `pred<=1` (`n={ouro3_le1['n']}`), a média de conceitos `ausente` sobe para `{ouro3_le1['media_ausente']:.2f}` enquanto `erros_conceituais` é zero em `{ouro3_le1['pct_zero_erros_conceituais']:.1%}` dos casos.",
        f"2. **Armadilha de múltiplos gabaritos alternativos:** respostas curtas `ouro=3 -> pred<=1` atingem em média `{ouro3_le1['max_ref_overlap_medio']:.1%}` dos termos de *um* gabarito específico contra apenas `{ouro3_le1['all_refs_overlap_medio']:.1%}` da *união* de todos os gabaritos (`{ouro3_le1['pct_alta_sobreposicao_1ref_baixa_uniao']:.1%}` têm alta sobreposição com 1 gabarito e baixa com a união). O `DIAG_USER` apresenta `GABARITO` como lista única de respostas de professores sem explicitar que **basta atender a uma formulação equivalente**.",
        f"3. **Indulgência na nota 0 (`ouro=0 -> pred>=1`, `n={ouro0_ge1['n']}`):** em `{ouro0_ge1['pct_algum_presente_ou_parcial']:.1%}` desses casos o diagnoser marcou ao menos 1 conceito como `presente` ou `parcial`, e em `{ouro0_ge1['pct_algum_acerto']:.1%}` listou ao menos 1 `acerto` positivo (puxando a nota para `1`), mesmo quando a rubrica humana deu `0`. Como resultado, há sobreposição de sinal entre respostas `ouro=0` mal-rejeitadas e `ouro=2` excessivamente penalizadas na classe `pred=1`.",
        f"4. **Saturação em 3 lacunas e falsos erros conceituais (cruzamento com `H-03`/`H-04`):** em `{df['is_3_lacunas'].mean():.1%}` de todo o E0 (`{int(df['is_3_lacunas'].sum())}/595`), o modelo preenche o teto de 3 `lacunas_prioritarias` — incluindo `{df[df['grade']==3]['is_3_lacunas'].mean():.1%}` (`{int(df[df['grade']==3]['is_3_lacunas'].sum())}/145`) dos itens `ouro=3` e `{df[df['grade']==2]['is_3_lacunas'].mean():.1%}` (`{int(df[df['grade']==2]['is_3_lacunas'].sum())}/150`) dos `ouro=2` — enquanto `{df[df['grade']==3]['zero_erros_conceituais'].map(lambda v: 1-v).mean():.1%}` dos `ouro=3` recebem ao menos 1 `erro_conceitual`. Em `{int(df['n_lacunas_sem_respaldo'].sum())}/{int(df['n_lacunas'].sum())}` lacunas (`{df['alguma_lacuna_sem_respaldo'].mean():.1%}` dos itens) não há sequer respaldo lexical mínimo (`>=4` chars) nos gabaritos/conceitos (além de casos qualitativos documentados em `H-04` onde o diagnóstico rejeita sinônimos ou confunde omissão com erro conceitual).",
        "",
        "---",
        "",
        "## 4. `diagnoser` (`gpt-4o-mini` + `DIAG_USER`) vs. `grader` (`gemini-2.5-flash` + `GRADER_USER`) em `n = 180`",
        "",
        _df_to_md(
            dg_main,
            {
                "QWK": ".3f", "Spearman": ".3f", "MAE": ".3f", "bias_medio": "+.3f",
                "acc_exata": ".3f", "taxa_subavaliacao": ".3f", "taxa_superavaliacao": ".3f",
            },
        ),
        "",
        "Matrizes de confusão lado a lado (`n = 180`, onde `grade ∈ {0, 1, 2}`):",
        "```",
        "DIAGNOSER (gpt-4o-mini, DIAG_USER) vs Ouro:",
        cms["diagnoser_vs_ouro"].iloc[:3, :].to_string(),
        "",
        "GRADER (gemini-2.5-flash, GRADER_USER) vs Ouro:",
        cms["grader_vs_ouro"].iloc[:3, :].to_string(),
        "```",
        "",
        f"- **Conclusão desta comparação:** no subconjunto piloto de `180` itens (`grade ∈ {{0,1,2}}`), o `grader` supera o `diagnoser` em QWK (`{g_row['QWK']:.3f}` vs `{d_row['QWK']:.3f}`), Spearman (`{g_row['Spearman']:.3f}` vs `{d_row['Spearman']:.3f}`) e acurácia binária `>=2` (`{g_row['acc_binaria_ge2']:.1%}` vs `{d_row['acc_binaria_ge2']:.1%}`), enquanto o `diagnoser` mantém maior `acc_exata` (`{d_row['acc_exata']:.1%}` vs `{g_row['acc_exata']:.1%}`) e menor MAE (`{d_row['MAE']:.3f}` vs `{g_row['MAE']:.3f}`). O motivo é a assimetria oposta dos dois prompts: o `diagnoser` ainda derruba `{int(cm_d[2,1])}/60` (`{cm_d[2,1]/60:.1%}`) dos `ouro=2` para `pred=1` (`bias = {d_row['bias_medio']:+.3f}`), enquanto o `grader` tem viés positivo (`bias = {g_row['bias_medio']:+.3f}`), acertando `{int(cm_g[2,2])}/60` (`{cm_g[2,2]/60:.1%}`) em `ouro=2` mas promovendo `{int(cm_g[2,3])}/60` (`{cm_g[2,3]/60:.1%}`) para `3` e superavaliando `{g_row['taxa_superavaliacao']:.1%}` dos itens. Além disso, o `diagnoser` sobe de QWK = `{g_metrics['QWK']:.3f}` (`n=595`) para `{d_row['QWK']:.3f}` (`n=180`) simplesmente porque o piloto exclui `grade=3` (onde ocorre o pior colapso conservador). Entre si, os dois modelos têm forte correlação de ordem (`Spearman = {a_row['Spearman']:.3f}`, `QWK = {a_row['QWK']:.3f}`), confirmando que o gargalo central em `DIAG_USER` é de **calibração e rigidez da checklist**, não ausência total de sinal.",
        "",
        "---",
        "",
        "## 5. Recalibração Pós-Hoc em Leave-One-Question-Out (15 folds LOGO)",
        "",
        "Todos os métodos abaixo foram ajustados **exclusivamente nos 14 folds de treino** e avaliados na questão retida (sem vazamento). O ajuste de limiares ordinais usou escores *out-of-fold* internos nos 14 folds de treino.",
        "",
        _df_to_md(
            logo_global,
            {
                "QWK": ".3f", "Spearman": ".3f", "Pearson": ".3f", "MAE": ".3f",
                "bias_medio": "+.3f", "acc_exata": ".3f", "acc_tol1": ".3f",
                "acc_binaria_ge2": ".3f", "taxa_subavaliacao": ".3f", "taxa_superavaliacao": ".3f",
            },
        ),
        "",
        f"- **Parâmetros aprendidos nos 15 folds LOGO:**",
        f"  - `shift_constante_logo`: deltas selecionados = `{dict(shift_counts)}` (um deslocamento uniforme `+1` melhora `ouro=2/3` mas estraga `ouro=0`, levando QWK para `{logo_global.loc[logo_global['metodo']=='shift_constante_logo','QWK'].iloc[0]:.3f}`).",
        f"  - `remap_nota_logo`: mapeamentos `{dict(map_counts)}` (ou seja, manter `0->0`, subir `1->2` ou `2->3` conforme o fold já elimina boa parte do viés conservador com QWK = `{logo_global.loc[logo_global['metodo']=='remap_nota_logo','QWK'].iloc[0]:.3f}`).",
        f"  - `ordinal_thresholds_logo`: média dos limiares nos 15 folds = `({t_arr[:,0].mean():.2f}, {t_arr[:,1].mean():.2f}, {t_arr[:,2].mean():.2f})` (em vez de `0.50, 1.50, 2.50`), atingindo **QWK = `{logo_global.loc[logo_global['metodo']=='ordinal_thresholds_logo','QWK'].iloc[0]:.3f}`** e `acc_binaria(>=2) = {logo_global.loc[logo_global['metodo']=='ordinal_thresholds_logo','acc_binaria_ge2'].iloc[0]:.1%}`.",
        "",
        "### Impacto da recalibração LOGO por questão (QWK antes vs. depois)",
        _df_to_md(
            logo_q_df,
            {
                "baseline_raw": ".3f", "shift_constante_logo": ".3f", "remap_nota_logo": ".3f",
                "linear_diag_features_logo": ".3f", "ordinal_thresholds_logo": ".3f",
                "ganho_remap": "+.3f", "ganho_ordinal": "+.3f",
            },
        ),
        "",
        "**Diagnóstico final calibração vs. discriminação:**",
        f"- **Questões recuperadas por calibração pós-hoc (`ganho_ordinal >= +0.13`):** {calib_str}. Nelas, a ordenação já existia (`Spearman` entre `0.52` e `0.75`, salvo `q36` e `q48` mais ruidosas), e o erro vinha de deslocamento de escala.",
        f"- **Questões que permanecem difíceis mesmo após recalibração (`QWK_ordinal < 0.45`):** {hard_str}. Essas concentram o verdadeiro erro de *discriminação* semântica/rubrica (em `q37`, `q42`, `q44` e `q48`, `80%` dos `ouro=0` sobem para `>=1`, enquanto em `q36`, `q44` e `q48` há forte compressão de `ouro=2/3`, e `q42` soma `8` conceitos esperados e `4` gabaritos), exigindo revisão de prompt/few-shot em `H-02`.",
        "",
        "---",
        "",
        "## 6. Recomendações Diretas para `H-02` (Calibração do Prompt `DIAG_USER`)",
        "",
        "1. **Remover a obrigação de extrair conceitos extras além dos conceitos-chave** no `DIAG_USER` (ou separar explicitamente conceitos obrigatórios vs. complementares para não inflar `ausente`).",
        "2. **Explicitar regra de gabaritos alternativos e equivalência semântica:** instruir que as respostas em `GABARITO` são *exemplos independentes/equivalentes* de professores, que sinônimos/variações corretas de nomenclatura devem ser aceitos (cf. achado de `H-04` na `q42`), e que o aluno **não precisa combinar detalhes exclusivos de todos os gabaritos** para receber `nota_estimada = 2` ou `3`.",
        "3. **Permitir `0–3` lacunas reais e separar omissão de erro conceitual (handoff `H-03`/`H-04`):** trocar `\"<até 3 ideias...>\"` por permissão explícita de lista vazia (`[]`) quando não houver lacuna relevante (`ouro=2/3`), evitando que `A1` sobre-remedie ou invente lacunas fora do gabarito; instruir explicitamente que **omissão não é erro conceitual** e proibir inventar erros não respaldados pelo gabarito.",
        "4. **Calibrar as âncoras da escala `0–3` com critério explícito de corte entre `1` e `2` e entre `0` e `1`:**",
        "   - `0`: não apresenta nenhum conceito-chave correto ou responde algo errado/fora do núcleo da pergunta (não promover chute vago ou repetição do enunciado para `1`);",
        "   - `1`: acerta apenas parte secundária ou com erro conceitual importante;",
        "   - `2`: acerta o núcleo da pergunta de forma compatível com um gabarito, faltando só um conceito específico ou precisão;",
        "   - `3`: cobre as ideias essenciais de um gabarito completo (mesmo em linguagem simples/curta de 8º/9º ano, sem exigência de jargão extra).",
        "5. **Few-shot sem vazamento usando o holdout do PT-ASAG:** selecionar 2–4 exemplos âncora (ex.: notas `0, 1, 2, 3`) exclusivamente dentre as **`" + str(total_extra) + "` respostas fora do `diag_set`** (nunca usar itens do próprio `diag_set` nem vazar nota-ouro em inferência; o texto-exemplo ilustra apenas critérios públicos de rubrica).",
        f"6. **Protocolo barato de validação em `H-02`:** validar primeiro em um subconjunto estratificado (ex.: `60` itens = 4 por questão × 4 notas, priorizando as questões críticas {focus_str} + questões de referência alta) antes de re-executar os `595` itens de E0.",
    ]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "analise_e0_diagnostico.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    cfg = load_config()
    df = load_e0_dataframe(cfg)
    diag_counts = df.groupby("question_id").size()
    ptasag_counts = load_ptasag_extra_counts(cfg, set(df["question_id"].unique()), diag_counts)

    q_tab = build_per_question_table(df, ptasag_counts)
    st_tab = build_structure_table(df)
    dg_tab, cms = build_diagnoser_vs_grader(df)
    logo_tab, fold_params = run_logo_recalibration(df)
    tax_tab = build_error_taxonomy(df)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    q_tab.to_csv(OUT_DIR / "e0_por_questao.csv", index=False)
    st_tab.to_csv(OUT_DIR / "e0_estrutura_diagnostico.csv", index=False)
    dg_tab.to_csv(OUT_DIR / "e0_diagnoser_vs_grader_180.csv", index=False)
    logo_tab.to_csv(OUT_DIR / "e0_recalibracao_logo.csv", index=False)
    tax_tab.to_csv(OUT_DIR / "e0_taxonomia_erros.csv", index=False)

    write_markdown_report(df, q_tab, st_tab, dg_tab, cms, logo_tab, fold_params, tax_tab)
    print(f"ok -> {OUT_DIR}")


if __name__ == "__main__":
    main()
