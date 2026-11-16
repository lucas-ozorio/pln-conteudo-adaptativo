"""Testes rápidos, sem rede: python tests/test_basic.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pln import prompts as P  # noqa: E402
from pln.common import load_config  # noqa: E402
from pln.data import build_samples, norm  # noqa: E402
from pln.llm import extract_json  # noqa: E402


def test_extract_json():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Claro! {"a": {"b": 2}} fim')["a"]["b"] == 2


def test_fill_keeps_json_braces():
    out = P.fill('{"x": "<<K>>"}', K="v")
    assert out == '{"x": "v"}'
    assert "<<" not in P.fill(P.DIAG_USER, PERGUNTA="p", REFS="r", CONCEITOS="c", RESPOSTA="a")


def test_samples_no_leak_and_nesting():
    cfg = load_config()
    diag, pilot = build_samples(cfg)
    ids = {r["item_id"] for r in diag}
    assert all(r["item_id"] in ids for r in pilot)  # piloto ⊂ E0
    assert len(ids) == len(diag)  # sem item duplicado
    assert {r["grade"] for r in pilot} <= set(cfg["sample"]["pilot_grades"])
    # a nota-ouro não aparece em nenhum prompt de entrada do pipeline
    r = pilot[0]
    u = P.fill(P.DIAG_USER, PERGUNTA=r["question"], REFS=P.fmt_refs(r["refs"]), CONCEITOS=P.fmt_concepts(r["concepts"]), RESPOSTA=r["answer"])
    assert "grade" not in u.lower() and "nota-ouro" not in u.lower()


def test_norm():
    assert norm("Célula, Vegetal!") == "celula vegetal"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
