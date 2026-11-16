from __future__ import annotations

from . import prompts as P
from .pipeline import format_material, format_questions

TEXT_DIMS = ["coerencia", "correcao_conceitual", "fidelidade_gabarito", "foco_na_lacuna", "utilidade_pedagogica", "adequacao_nivel"]


def _clip(x, lo=1, hi=5):
    try:
        return max(lo, min(hi, int(x)))
    except (TypeError, ValueError):
        return None


def judge_text(llm, it: dict, texto: str, rep: int = 0) -> dict:
    u = P.fill(P.JUDGE_TEXT_USER, PERGUNTA=it["question"], REFS=P.fmt_refs(it["refs"]), RESPOSTA=it["answer"], TEXTO=texto)
    r = llm.json(P.JUDGE_SYSTEM, u, task="judge_text", rep=rep)
    out = {d: _clip(r.get(d)) for d in TEXT_DIMS}
    try:
        out["afirmacoes_incorretas"] = max(0, int(r.get("afirmacoes_incorretas", 0)))
    except (TypeError, ValueError):
        out["afirmacoes_incorretas"] = None
    return out


def judge_questions(llm, it: dict, qs: list[dict], rep: int = 0) -> list[dict]:
    u = P.fill(P.JUDGE_Q_USER, PERGUNTA=it["question"], REFS=P.fmt_refs(it["refs"]), RESPOSTA=it["answer"], QUESTOES=format_questions(qs))
    r = llm.json(P.JUDGE_SYSTEM, u, task="judge_questions", rep=rep).get("questoes", [])
    res = []
    for i, q in enumerate(qs):
        j = r[i] if i < len(r) else {}
        res.append({"bloom_pedido": q.get("nivel_bloom"), "bloom_percebido": str(j.get("nivel_bloom_percebido", "")).lower() or None,
                    "alinhamento_gabarito": _clip(j.get("alinhamento_gabarito")), "clareza": _clip(j.get("clareza")),
                    "relevancia_lacuna": _clip(j.get("relevancia_lacuna")), "resposta_esperada_correta": j.get("resposta_esperada_correta")})
    return res


def judge_pair(llm, it: dict, mat_a: dict, mat_b: dict, rep: int = 0) -> str:
    """Compara dois materiais; se um deles não tem questões (S0), compara só o texto. Retorna 'A'|'B'|'empate'."""
    text_only = not (mat_a.get("questoes") and mat_b.get("questoes"))
    fa = mat_a["texto"] if text_only else format_material(mat_a)
    fb = mat_b["texto"] if text_only else format_material(mat_b)
    u = P.fill(P.JUDGE_PAIR_USER, PERGUNTA=it["question"], REFS=P.fmt_refs(it["refs"]), RESPOSTA=it["answer"], A=fa, B=fb)
    v = str(llm.json(P.JUDGE_SYSTEM, u, task="judge_pair", rep=rep).get("vencedor", "")).strip().lower()
    return {"a": "A", "b": "B"}.get(v, "empate")
