from __future__ import annotations

import hashlib
import re
import unicodedata

import numpy as np
import pandas as pd

from .common import ROOT, write_jsonl

RAW = ROOT / "data" / "raw" / "PT_ASAG_2018_v2.0"
PROC = ROOT / "data" / "processed"


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s).lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", s).split())


def item_id(qid: int, answer: str) -> str:
    return f"q{qid}_{hashlib.md5(answer.encode('utf-8')).hexdigest()[:8]}"


def load_questions() -> dict[int, dict]:
    q = pd.read_csv(RAW / "questions.csv")
    c = pd.read_csv(RAW / "concepts.csv")
    r = pd.read_csv(RAW / "reference_answers.csv")  # gabaritos escritos por professores (2 a 4 por questão)
    out = {}
    for _, row in q.iterrows():
        qid = int(row.question_id)
        out[qid] = {
            "question_id": qid,
            "question": " ".join(str(row.question_text).split()),
            "concepts": c[c.question_id == qid].concept_text.tolist(),
            "refs": r[r.question_id == qid].refans_text.tolist(),
        }
    return out


def build_samples(cfg: dict) -> tuple[list[dict], list[dict]]:
    """Retorna (diag_set, pilot_set). pilot ⊂ diag. A nota-ouro fica em 'grade' e NUNCA entra em prompts."""
    s = cfg["sample"]
    rng_seed = cfg["seed"]
    qs = load_questions()
    a = pd.read_csv(RAW / "student_answers_and_grades_v2.csv")
    a["answer_text"] = a.answer_text.astype(str).str.strip()
    a["words"] = a.answer_text.str.split().str.len()
    a = a[(a.words >= 1) & (a.words <= s["max_words"]) & a.question_id.isin(qs)]
    a["key"] = a.question_id.astype(str) + "|" + a.answer_text.map(norm)
    a = a.drop_duplicates("key")  # respostas idênticas removidas (como no paper original)

    diag, pilot = [], []
    for (qid, g), grp in a.groupby(["question_id", "grade"]):
        n = min(len(grp), s["n_diag_per_q_grade"])
        take = grp.sample(n=n, random_state=rng_seed)
        rows = [
            {**qs[int(qid)], "item_id": item_id(int(qid), r.answer_text), "answer": r.answer_text, "grade": int(g)}
            for r in take.itertuples()
        ]
        diag += rows
        if int(g) in s["pilot_grades"]:
            pilot += rows[: s["n_pilot_per_q_grade"]]
    diag.sort(key=lambda r: (r["question_id"], r["grade"], r["item_id"]))
    pilot.sort(key=lambda r: (r["question_id"], r["grade"], r["item_id"]))
    return diag, pilot


def save_samples(cfg: dict) -> tuple[list[dict], list[dict]]:
    diag, pilot = build_samples(cfg)
    write_jsonl(PROC / "diag_set.jsonl", diag)
    write_jsonl(PROC / "pilot_set.jsonl", pilot)
    return diag, pilot


def qwk(y_true, y_pred, labels=(0, 1, 2, 3)) -> float:
    from sklearn.metrics import cohen_kappa_score

    return float(cohen_kappa_score(y_true, y_pred, weights="quadratic", labels=list(labels)))


def bootstrap_ci(x, stat=np.mean, n=2000, seed=0, alpha=0.05):
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return (float("nan"), float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    bs = [stat(rng.choice(x, size=len(x), replace=True)) for _ in range(n)]
    return float(stat(x)), float(np.quantile(bs, alpha / 2)), float(np.quantile(bs, 1 - alpha / 2))
