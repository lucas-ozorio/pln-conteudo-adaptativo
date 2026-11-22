"""Harness da tarefa H-02: calibração do diagnóstico em E0 (RQ1).

Permite rodar variantes calibradas do prompt de diagnóstico (`prompts_h02.py`) de
forma totalmente isolada do piloto original:
  - Saídas reais em `outputs/h02/` e `results/herik_h02/`
  - Saídas `--mock` em `outputs_mock/h02/` e `results_mock/h02/`
  - Suporta `--provider openrouter` (padrão) ou `--provider openai`, além de `.env`
  - Compara cada variante de forma pareada contra `v0_baseline` (`outputs/diagnosis.jsonl`)

Uso típico:
  python scripts/run_h02_calibration.py --dry-run --subset pilot60
  python scripts/run_h02_calibration.py --mock --subset pilot60
  python scripts/run_h02_calibration.py --subset pilot60
  python scripts/run_h02_calibration.py --subset full595
"""
from __future__ import annotations

import argparse
import copy
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
for p in (str(ROOT_DIR / "src"), str(SCRIPT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from analyze_e0_calibration import _df_to_md, compute_metrics, content_tokens, safe_qwk  # noqa: E402
from pln.common import JsonlAppender, ROOT, load_config, pmap, read_jsonl  # noqa: E402
from pln.data import load_questions  # noqa: E402
from pln.llm import LLM  # noqa: E402
from pln.prompts_h02 import VARIANTS, build_diag_prompt, load_holdout_pool  # noqa: E402

# Preço de referência gpt-4o-mini (USD por 1M tokens) para estimativa no --dry-run
PRICE_IN_PER_1M = 0.15
PRICE_OUT_PER_1M = 0.60
EST_AVG_OUT_TOKENS = 260


def load_dotenv_silent(env_path: Path) -> None:
    """Carrega variáveis de `.env` local se não estiverem definidas no ambiente (sem imprimir valores)."""
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and v:
            os.environ.setdefault(k, v)


def configure_provider(cfg: dict, provider: str, mock: bool) -> tuple[dict, str]:
    """Retorna cópia de `cfg` ajustada para `openrouter` ou `openai` sem alterar `config.yaml`."""
    c = copy.deepcopy(cfg)
    if mock:
        for m in c["models"].values():
            m["provider"] = "mock"
        return c, "MOCK"
    if provider == "openai":
        c["providers"]["main"]["base_url"] = "https://api.openai.com/v1"
        c["providers"]["main"]["api_key_env"] = "OPENAI_API_KEY"
        c["models"]["diagnoser"]["name"] = "gpt-4o-mini"
    return c, c["providers"]["main"]["api_key_env"]


def build_isolated_llm(cfg: dict, provider: str, out_dir: Path, mock: bool) -> LLM:
    """Instancia `LLM('diagnoser')` com cache e log de uso isolados em `out_dir`."""
    llm = LLM("diagnoser", cfg)
    tag = "mock" if mock else provider
    cache_path = out_dir / f"cache_{tag}.jsonl"
    llm.cache_path = cache_path
    llm.usage_path = out_dir / f"usage_{tag}.jsonl"
    llm._cache = {}
    if cache_path.exists():
        import json

        for line in cache_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                llm._cache[rec["k"]] = rec["v"]
    return llm


def select_subset(diag_items: list[dict], subset: str, limit: int = 0, seed: int = 42) -> list[dict]:
    """Seleciona `pilot60` (1 por questão x nota = 60) ou `full595`, preservando ordem determinística."""
    if subset == "full595":
        chosen = list(diag_items)
    elif subset == "pilot60":
        rng = np.random.default_rng(seed)
        df = pd.DataFrame([{"idx": i, "question_id": r["question_id"], "grade": r["grade"]} for i, r in enumerate(diag_items)])
        picks = []
        for (_, _), grp in df.groupby(["question_id", "grade"]):
            idxs = sorted(grp["idx"].tolist())
            picks.append(int(rng.choice(idxs)))
        picks.sort()
        chosen = [diag_items[i] for i in picks]
    else:
        raise ValueError(f"Subset inválido: {subset}")
    return chosen[:limit] if limit and limit > 0 else chosen


def run_dry_run(
    items: list[dict],
    variants: list[str],
    holdout_df: pd.DataFrame,
    qmap: dict[int, dict],
    out_dir: Path,
    cfg: dict,
    api_key_env: str,
    mock: bool,
) -> None:
    """Valida prompts/holdout e imprime estimativa de chamadas, tokens e custo sem chamar API."""
    key_status = "N/A (--mock)" if mock else ("DEFINIDA" if os.environ.get(api_key_env) else "AUSENTE")
    model_name = cfg["models"]["diagnoser"]["name"]
    print(f"[H-02 dry-run] modelo={model_name} | env={api_key_env} ({key_status}) | itens={len(items)} | holdout={len(holdout_df)}")

    tot_calls, tot_in_tok, tot_out_tok = 0, 0, 0
    for var in variants:
        done = {r["item_id"] for r in read_jsonl(out_dir / f"diagnosis_{var}.jsonl")}
        todo = [it for it in items if it["item_id"] not in done]
        chars = 0
        for it in todo:
            sys_p, usr_p = build_diag_prompt(var, it, holdout_df=holdout_df, qmap=qmap)
            chars += len(sys_p) + len(usr_p)
        est_in = int(round(chars / 3.6))
        est_out = len(todo) * EST_AVG_OUT_TOKENS
        tot_calls += len(todo)
        tot_in_tok += est_in
        tot_out_tok += est_out
        print(f"  - {var:22s}: pendentes={len(todo):3d}/{len(items):3d} | ~in={est_in:7d} tok | ~out={est_out:6d} tok")

    est_cost = (tot_in_tok / 1e6) * PRICE_IN_PER_1M + (tot_out_tok / 1e6) * PRICE_OUT_PER_1M
    print(f"TOTAL pendente: {tot_calls} chamadas | ~{tot_in_tok:,} in + ~{tot_out_tok:,} out tokens | custo ref gpt-4o-mini ≈ US$ {est_cost:.4f}")


def execute_variant(
    variant: str,
    items: list[dict],
    holdout_df: pd.DataFrame,
    qmap: dict[int, dict],
    llm: LLM,
    out_dir: Path,
    workers: int,
) -> Path:
    """Executa chamadas retomáveis para uma variante e grava JSONL em `out_dir`."""
    path = out_dir / f"diagnosis_{variant}.jsonl"
    sink = JsonlAppender(path)
    done = {r["item_id"] for r in read_jsonl(path)}
    todo = [it for it in items if it["item_id"] not in done]
    if not todo:
        print(f"[{variant}] já completo ({len(items)} itens em {path})")
        return path

    def run_one(it: dict) -> dict:
        sys_p, usr_p = build_diag_prompt(variant, it, holdout_df=holdout_df, qmap=qmap)
        d = llm.json(sys_p, usr_p, task="diagnose")
        try:
            d["nota_estimada"] = max(0, min(3, int(d.get("nota_estimada"))))
        except (TypeError, ValueError):
            d["nota_estimada"] = None
        row = {"item_id": it["item_id"], "variant": variant, "diag": d}
        sink.add(row)
        return row

    res = pmap(run_one, todo, workers, f"H-02 {variant}")
    errs = [r for r in res if r and "_error" in r]
    print(f"[{variant}] ok={len(todo) - len(errs)} erros={len(errs)} -> {path}")
    if errs:
        raise RuntimeError(f"Falha em {len(errs)} chamadas de {variant}. Exemplo: {errs[0]['_error']}")
    return path


def _cluster_bootstrap_qwk_and_delta(
    yt: np.ndarray,
    yp: np.ndarray,
    yv0: np.ndarray,
    qids: np.ndarray,
    n_boot: int = 5000,
    seed: int = 0,
) -> tuple[float, float, float, float, float]:
    """IC95% bootstrap por cluster de questão para QWK e para diferença pareada (QWK - QWK_v0)."""
    df_tmp = pd.DataFrame({"qid": qids, "yt": yt, "yp": yp, "yv0": yv0})
    by = {k: g for k, g in df_tmp.groupby("qid")}
    ks = np.array(sorted(by))
    if len(ks) < 2:
        q_val = safe_qwk(yt, yp)
        d_val = q_val - safe_qwk(yt, yv0)
        return q_val, float("nan"), float("nan"), d_val, float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    bs_q, bs_d = [], []
    for _ in range(n_boot):
        pick = rng.choice(ks, size=len(ks), replace=True)
        samp = pd.concat([by[k] for k in pick], ignore_index=True)
        qv = safe_qwk(samp["yt"], samp["yp"])
        q0 = safe_qwk(samp["yt"], samp["yv0"])
        bs_q.append(qv)
        bs_d.append(qv - q0)
    q_obs = safe_qwk(yt, yp)
    d_obs = q_obs - safe_qwk(yt, yv0)
    return (
        q_obs,
        float(np.quantile(bs_q, 0.025)),
        float(np.quantile(bs_q, 0.975)),
        d_obs,
        float(np.quantile(bs_d, 0.025)),
        float(np.quantile(bs_d, 0.975)),
    )


def _records_to_eval_df(records: list[dict], item_map: dict[str, dict]) -> pd.DataFrame:
    """Converte registros JSONL de diagnóstico em DataFrame pareado com `item_map`."""
    rows = []
    for r in records:
        iid = r["item_id"]
        if iid not in item_map:
            continue
        it = item_map[iid]
        d = r.get("diag") or {}
        pred = d.get("nota_estimada")
        if pred is None:
            continue
        conceitos = [c for c in (d.get("conceitos") or []) if isinstance(c, dict)]
        lacs = [x for x in (d.get("lacunas_prioritarias") or []) if isinstance(x, str)]
        errs = d.get("erros_conceituais") or []
        rc_toks4 = {
            t
            for t in set().union(
                *(content_tokens(x) for x in it["refs"]),
                *(content_tokens(x) for x in it["concepts"]),
            )
            if len(t) >= 4
        }
        n_sem = sum(1 for lac in lacs if len({t for t in content_tokens(lac) if len(t) >= 4} & rc_toks4) == 0)
        rows.append(
            {
                "item_id": iid,
                "question_id": int(it["question_id"]),
                "grade": int(it["grade"]),
                "pred": int(pred),
                "n_conceitos_esperados": len(it["concepts"]),
                "n_conceitos_listados": len(conceitos),
                "n_conceitos_extras": len(conceitos) - len(it["concepts"]),
                "n_erros_conceituais": len(errs),
                "n_lacunas": len(lacs),
                "is_3_lacunas": int(len(lacs) == 3),
                "alguma_lacuna_sem_respaldo": int(n_sem > 0),
            }
        )
    return pd.DataFrame(rows).drop_duplicates("item_id", keep="last").sort_values(["question_id", "grade", "item_id"])


def evaluate_results(
    items: list[dict],
    variants: list[str],
    out_dir: Path,
    res_dir: Path,
    mock: bool,
) -> None:
    """Compara todas as variantes executadas de forma pareada com `v0_baseline` e salva CSVs + MD."""
    item_map = {it["item_id"]: it for it in items}
    v0_raw = read_jsonl(ROOT / "outputs" / "diagnosis.jsonl")
    v0_df = _records_to_eval_df(v0_raw, item_map)

    loaded: dict[str, pd.DataFrame] = {"v0_baseline": v0_df}
    for var in variants:
        p = out_dir / f"diagnosis_{var}.jsonl"
        if p.exists():
            df_v = _records_to_eval_df(read_jsonl(p), item_map)
            if not df_v.empty:
                loaded[var] = df_v

    if len(loaded) <= 1:
        print("Nenhuma saída H-02 encontrada para avaliar.")
        return

    # Mantém interseção pareada exata com os itens comuns entre todas as variantes carregadas e v0
    common_ids = set.intersection(*(set(d["item_id"]) for d in loaded.values()))
    if not common_ids:
        raise RuntimeError("Sem interseção de item_ids entre v0_baseline e as saídas de H-02.")

    v0_common = loaded["v0_baseline"]
    v0_common = v0_common[v0_common["item_id"].isin(common_ids)].sort_values("item_id").reset_index(drop=True)

    comp_rows, q_rows, cm_rows = [], [], []
    cms_text = {}

    for name, df_var in loaded.items():
        d = df_var[df_var["item_id"].isin(common_ids)].sort_values("item_id").reset_index(drop=True)
        assert list(d["item_id"]) == list(v0_common["item_id"])
        m = compute_metrics(d["grade"], d["pred"])
        q_obs, q_lo, q_hi, d_obs, d_lo, d_hi = _cluster_bootstrap_qwk_and_delta(
            d["grade"].values, d["pred"].values, v0_common["pred"].values, d["question_id"].values
        )
        g3 = d[d["grade"] == 3]
        g2 = d[d["grade"] == 2]
        g0 = d[d["grade"] == 0]
        comp_rows.append(
            {
                "variante": name,
                **m,
                "QWK_ic_lo": q_lo,
                "QWK_ic_hi": q_hi,
                "delta_QWK_vs_v0": 0.0 if name == "v0_baseline" else d_obs,
                "delta_QWK_ic_lo": 0.0 if name == "v0_baseline" else d_lo,
                "delta_QWK_ic_hi": 0.0 if name == "v0_baseline" else d_hi,
                "pct_pred_1": float((d["pred"] == 1).mean()),
                "pct_ouro3_pred3": float((g3["pred"] == 3).mean()) if len(g3) else float("nan"),
                "pct_ouro3_pred_le1": float((g3["pred"] <= 1).mean()) if len(g3) else float("nan"),
                "pct_ouro2_pred1": float((g2["pred"] == 1).mean()) if len(g2) else float("nan"),
                "pct_ouro0_pred_ge1": float((g0["pred"] >= 1).mean()) if len(g0) else float("nan"),
                "media_conceitos_extras": float(d["n_conceitos_extras"].mean()),
                "pct_3_lacunas": float(d["is_3_lacunas"].mean()),
                "pct_ouro3_3_lacunas": float(g3["is_3_lacunas"].mean()) if len(g3) else float("nan"),
                "pct_ouro3_com_erro_conceitual": float((g3["n_erros_conceituais"] > 0).mean()) if len(g3) else float("nan"),
                "pct_alguma_lacuna_sem_respaldo": float(d["alguma_lacuna_sem_respaldo"].mean()),
            }
        )

        cm = confusion_matrix(d["grade"], d["pred"], labels=[0, 1, 2, 3])
        cms_text[name] = pd.DataFrame(cm, index=[f"ouro={i}" for i in range(4)], columns=[f"pred={j}" for j in range(4)])
        for i in range(4):
            cm_rows.append(
                {
                    "variante": name,
                    "ouro": i,
                    "pred_0": int(cm[i, 0]),
                    "pred_1": int(cm[i, 1]),
                    "pred_2": int(cm[i, 2]),
                    "pred_3": int(cm[i, 3]),
                    "total": int(cm[i].sum()),
                }
            )

        for qid, sub in d.groupby("question_id"):
            sub_v0 = v0_common[v0_common["question_id"] == qid]
            qm = compute_metrics(sub["grade"], sub["pred"])
            q0 = safe_qwk(sub_v0["grade"], sub_v0["pred"])
            qg3 = sub[sub["grade"] == 3]
            qg2 = sub[sub["grade"] == 2]
            qg0 = sub[sub["grade"] == 0]
            q_rows.append(
                {
                    "variante": name,
                    "question_id": int(qid),
                    **qm,
                    "delta_QWK_vs_v0": 0.0 if name == "v0_baseline" else qm["QWK"] - q0,
                    "pct_ouro3_pred_le1": float((qg3["pred"] <= 1).mean()) if len(qg3) else float("nan"),
                    "pct_ouro2_pred1": float((qg2["pred"] == 1).mean()) if len(qg2) else float("nan"),
                    "pct_ouro0_pred_ge1": float((qg0["pred"] >= 1).mean()) if len(qg0) else float("nan"),
                }
            )

    comp_df = pd.DataFrame(comp_rows)
    q_df = pd.DataFrame(q_rows).sort_values(["question_id", "variante"]).reset_index(drop=True)
    cm_df = pd.DataFrame(cm_rows)

    res_dir.mkdir(parents=True, exist_ok=True)
    comp_df.to_csv(res_dir / "h02_comparacao_variantes.csv", index=False)
    q_df.to_csv(res_dir / "h02_por_questao.csv", index=False)
    cm_df.to_csv(res_dir / "h02_matrizes_confusao.csv", index=False)

    q_pivot = q_df.pivot(index="question_id", columns="variante", values="QWK").reset_index()
    cols_view = [
        "variante", "n", "QWK", "QWK_ic_lo", "QWK_ic_hi", "delta_QWK_vs_v0",
        "Spearman", "MAE", "bias_medio", "acc_exata", "pct_pred_1",
        "pct_ouro3_pred_le1", "pct_ouro2_pred1", "pct_ouro0_pred_ge1",
        "media_conceitos_extras", "pct_ouro3_3_lacunas", "pct_ouro3_com_erro_conceitual",
    ]
    md = [
        "# Relatório H-02 — Calibração do Diagnóstico (`RQ1` / E0)",
        "",
    ]
    if mock:
        md += [
            "> **AVISO:** Execução em modo `--mock` apenas para validar o encanamento sem chave de API. **Sem valor científico.**",
            "",
        ]
    md += [
        f"Comparação estritamente pareada sobre **`n = {len(common_ids)}` itens** de `data/processed/diag_set.jsonl` contra `v0_baseline` (`outputs/diagnosis.jsonl`).",
        "",
        "## 1. Comparação Global das Variantes",
        "",
        _df_to_md(
            comp_df[cols_view],
            {
                "QWK": ".3f", "QWK_ic_lo": ".3f", "QWK_ic_hi": ".3f", "delta_QWK_vs_v0": "+.3f",
                "Spearman": ".3f", "MAE": ".3f", "bias_medio": "+.3f", "acc_exata": ".3f",
                "pct_pred_1": ".3f", "pct_ouro3_pred_le1": ".3f", "pct_ouro2_pred1": ".3f",
                "pct_ouro0_pred_ge1": ".3f", "media_conceitos_extras": "+.2f",
                "pct_ouro3_3_lacunas": ".3f", "pct_ouro3_com_erro_conceitual": ".3f",
            },
        ),
        "",
        "## 2. Matrizes de Confusão",
        "",
    ]
    for name, cm_t in cms_text.items():
        md += [f"### `{name}`", "```", cm_t.to_string(), "```", ""]
    md += [
        "## 3. QWK por Questão",
        "",
        _df_to_md(q_pivot),
        "",
    ]
    (res_dir / "h02_relatorio.md").write_text("\n".join(md), encoding="utf-8")
    print(f"ok -> {res_dir}")


def main() -> None:
    load_dotenv_silent(ROOT / ".env")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--provider", choices=("openrouter", "openai"), default="openrouter")
    ap.add_argument("--mock", action="store_true", help="roda com LLM sintético em outputs_mock/h02 e results_mock/h02")
    ap.add_argument("--subset", choices=("pilot60", "full595"), default="pilot60")
    ap.add_argument("--variants", nargs="+", choices=VARIANTS, default=["v1_rubrica_calibrada", "v2_fewshot_cross_q"])
    ap.add_argument("--limit", type=int, default=0, help="limita aos primeiros N itens do subset")
    ap.add_argument("--dry-run", action="store_true", help="valida prompts/holdout e estima custo sem chamar API")
    ap.add_argument("--analyze-only", action="store_true", help="gera métricas a partir das saídas já gravadas")
    ap.add_argument("--config", default=None)
    args = ap.parse_args()

    cfg_base = load_config(args.config, mock=args.mock)
    cfg, api_key_env = configure_provider(cfg_base, args.provider, args.mock)

    out_dir = ROOT / ("outputs_mock" if args.mock else "outputs") / "h02"
    res_dir = ROOT / ("results_mock" if args.mock else "results") / ("h02" if args.mock else "herik_h02")
    out_dir.mkdir(parents=True, exist_ok=True)

    diag_items = read_jsonl(ROOT / "data" / "processed" / "diag_set.jsonl")
    if not diag_items:
        raise RuntimeError("diag_set.jsonl ausente. Rode: python scripts/00_prepare_data.py")

    items = select_subset(diag_items, args.subset, limit=args.limit, seed=int(cfg["seed"]))
    holdout_df = load_holdout_pool(cfg, diag_items)
    qmap = load_questions()

    if args.dry_run:
        run_dry_run(items, args.variants, holdout_df, qmap, out_dir, cfg, api_key_env, args.mock)
        return

    if not args.analyze_only:
        llm = build_isolated_llm(cfg, args.provider, out_dir, args.mock)
        workers = int(cfg["runtime"]["workers"])
        for var in args.variants:
            execute_variant(var, items, holdout_df, qmap, llm, out_dir, workers)

    evaluate_results(items, args.variants, out_dir, res_dir, args.mock)


if __name__ == "__main__":
    main()
