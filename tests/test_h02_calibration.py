"""Testes rápidos (sem rede/sem API) para H-02: python tests/test_h02_calibration.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT / "src"), str(ROOT / "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from pln.common import load_config, read_jsonl  # noqa: E402
from pln.data import load_questions, norm  # noqa: E402
from pln.prompts_h02 import (  # noqa: E402
    DEFAULT_DONOR_QID,
    FALLBACK_DONOR_QID,
    VARIANTS,
    build_diag_prompt,
    load_holdout_pool,
)
from run_h02_calibration import select_subset  # noqa: E402


def test_holdout_zero_leakage():
    cfg = load_config()
    diag = read_jsonl(ROOT / "data" / "processed" / "diag_set.jsonl")
    pilot = read_jsonl(ROOT / "data" / "processed" / "pilot_set.jsonl")
    holdout = load_holdout_pool(cfg, diag, extra_exclude=pilot)
    assert len(holdout) == 6501, f"esperado 6501 no holdout, obtido {len(holdout)}"
    diag_keys = {(int(r["question_id"]), norm(r["answer"])) for r in diag}
    pilot_keys = {(int(r["question_id"]), norm(r["answer"])) for r in pilot}
    hold_keys = set(holdout["nkey"])
    assert not (hold_keys & diag_keys)
    assert not (hold_keys & pilot_keys)


def test_prompt_rendering_and_anti_leakage():
    cfg = load_config()
    diag = read_jsonl(ROOT / "data" / "processed" / "diag_set.jsonl")
    holdout = load_holdout_pool(cfg, diag)
    qmap = load_questions()

    # Garante cobertura de uma questão padrão, da doadora (q40 -> fallback q39) e de q42 (sem nota 3 no holdout próprio)
    by_q = {int(r["question_id"]): r for r in diag}
    for qid in sorted(by_q):
        it = by_q[qid]
        for var in VARIANTS:
            sys_p, usr_p = build_diag_prompt(var, it, holdout_df=holdout, qmap=qmap)
            assert sys_p.strip()
            for tag in ("<<PERGUNTA>>", "<<REFS>>", "<<CONCEITOS>>", "<<BLOCO_EXEMPLOS>>", "<<RESPOSTA>>"):
                assert tag not in usr_p
            for key in ('"conceitos"', '"acertos"', '"erros_conceituais"', '"lacunas_prioritarias"', '"nota_estimada"'):
                assert key in usr_p
            assert "nota-ouro" not in usr_p.lower()
            assert "grade" not in usr_p.lower()

        # Checagem específica de cross-question (v2)
        _, usr_v2 = build_diag_prompt("v2_fewshot_cross_q", it, holdout_df=holdout, qmap=qmap)
        expected_donor = FALLBACK_DONOR_QID if qid == DEFAULT_DONOR_QID else DEFAULT_DONOR_QID
        assert f"Pergunta do exemplo: {qmap[expected_donor]['question']}" in usr_v2
        for g in (0, 1, 2, 3):
            assert f"nota_estimada esperada = {g}" in usr_v2

    # Na q42, v3_fewshot_same_q deve lidar graciosamente com ausência de grade 3 no holdout próprio
    _, usr_v3_q42 = build_diag_prompt("v3_fewshot_same_q", by_q[42], holdout_df=holdout, qmap=qmap)
    assert "nota_estimada esperada = 2" in usr_v3_q42
    assert "nota_estimada esperada = 3" not in usr_v3_q42


def test_pilot60_determinism():
    diag = read_jsonl(ROOT / "data" / "processed" / "diag_set.jsonl")
    s1 = select_subset(diag, "pilot60", seed=42)
    s2 = select_subset(diag, "pilot60", seed=42)
    assert [r["item_id"] for r in s1] == [r["item_id"] for r in s2]
    assert len(s1) == 60
    assert len({(r["question_id"], r["grade"]) for r in s1}) == 60
    diag_ids = {r["item_id"] for r in diag}
    assert all(r["item_id"] in diag_ids for r in s1)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
