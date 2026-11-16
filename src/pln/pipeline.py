"""Pipeline adaptativo (A1), ablações (A0, A2) e linhas de base estáticas (S, S0)."""
from __future__ import annotations

import json

from . import prompts as P

BLOOM_PT = {"lembrar", "entender", "aplicar", "analisar", "avaliar", "criar"}


def _wc(t: str) -> int:
    return len(t.split())


def diagnose(llm, it: dict) -> dict:
    u = P.fill(P.DIAG_USER, PERGUNTA=it["question"], REFS=P.fmt_refs(it["refs"]),
               CONCEITOS=P.fmt_concepts(it["concepts"]), RESPOSTA=it["answer"])
    d = llm.json(P.DIAG_SYSTEM, u, task="diagnose")
    try:  # normaliza a nota estimada (sem vazar nota-ouro: ela nunca está no prompt)
        d["nota_estimada"] = max(0, min(3, int(d.get("nota_estimada"))))
    except (TypeError, ValueError):
        d["nota_estimada"] = None
    return d


def gen_support(llm, it: dict, diag: dict, cfg: dict) -> str:
    lo, hi = cfg["pipeline"]["support_words"]
    u = P.fill(P.SUPPORT_USER, PERGUNTA=it["question"], REFS=P.fmt_refs(it["refs"]), RESPOSTA=it["answer"],
               DIAG=json.dumps({k: diag.get(k) for k in ("acertos", "erros_conceituais", "lacunas_prioritarias", "conceitos")},
                               ensure_ascii=False), MIN=lo, MAX=hi)
    return llm.text(P.SUPPORT_SYSTEM, u, task="support")


def gen_questions(llm, it: dict, cfg: dict, adaptive: bool, texto: str = "", lacunas: list | None = None) -> list[dict]:
    levels = cfg["pipeline"]["bloom_levels"]
    ctx = (P.fill(P.CTX_ADAPTIVE, TEXTO=texto, LACUNAS="; ".join(lacunas or [])) if adaptive
           else P.fill(P.CTX_STATIC, CONCEITOS=P.fmt_concepts(it["concepts"])))
    u = P.fill(P.QUESTIONS_USER, PERGUNTA=it["question"], REFS=P.fmt_refs(it["refs"]), CONTEXTO=ctx,
               N=len(levels), NIVEIS=", ".join(levels), REGRA_FOCO=P.FOCO_ADAPTIVE if adaptive else P.FOCO_STATIC)
    qs = llm.json(P.QUESTIONS_SYSTEM, u, task="questions").get("questoes", [])
    return qs[: len(levels)]


# ----------------------------------------------------------------------------- condições
def cond_A1(llms, it, cfg, diag=None):
    """Proposta: diagnóstico -> texto de apoio focado -> questões adaptativas (Bloom)."""
    diag = diag or diagnose(llms["diagnoser"], it)
    texto = gen_support(llms["generator"], it, diag, cfg)
    qs = gen_questions(llms["generator"], it, cfg, True, texto, diag.get("lacunas_prioritarias"))
    return {"texto": texto, "questoes": qs, "diag": diag}


def cond_A0(llms, it, cfg):
    """Ablação: geração direta, sem etapa explícita de diagnóstico (mede o valor do diagnóstico)."""
    lo, hi = cfg["pipeline"]["support_words"]
    lv = cfg["pipeline"]["bloom_levels"]
    u = P.fill(P.DIRECT_USER, PERGUNTA=it["question"], REFS=P.fmt_refs(it["refs"]),
               CONCEITOS=P.fmt_concepts(it["concepts"]), RESPOSTA=it["answer"], MIN=lo, MAX=hi, N=len(lv),
               NIVEIS=", ".join(lv))
    o = llms["generator"].json(P.SUPPORT_SYSTEM, u, task="direct")
    return {"texto": str(o.get("texto_apoio", "")).strip(), "questoes": o.get("questoes", [])[: len(lv)]}


def verify_and_rewrite(llms, it, cfg, texto: str) -> dict:
    refs = P.fmt_refs(it["refs"])
    v = llms["verifier"].json(P.VERIFY_SYSTEM, P.fill(P.VERIFY_USER, REFS=refs, CONCEITOS=P.fmt_concepts(it["concepts"]),
                                                      TEXTO=texto), task="verify")
    claims = v.get("afirmacoes", [])
    bad = [c for c in claims if c.get("veredito") in ("nao_suportada", "incorreta")]
    out = {"texto_final": texto, "n_afirmacoes": len(claims), "n_problemas": len(bad), "reescrito": False,
           "n_incorretas": sum(c.get("veredito") == "incorreta" for c in claims), "claims": claims}
    if bad:
        lo, hi = cfg["pipeline"]["support_words"]
        probs = "\n".join(f"- {c.get('afirmacao')} ({c.get('veredito')}: {c.get('motivo', '')})" for c in bad)
        out["texto_final"] = llms["generator"].text(
            P.SUPPORT_SYSTEM, P.fill(P.REWRITE_USER, REFS=refs, TEXTO=texto, PROBLEMAS=probs, MIN=lo, MAX=hi), task="rewrite")
        out["reescrito"] = True
    return out


def cond_A2(llms, it, cfg, a1: dict | None = None):
    """Proposta + mitigação de alucinação (verificação por afirmação ancorada no gabarito + reescrita)."""
    a1 = a1 or cond_A1(llms, it, cfg)
    vr = verify_and_rewrite(llms, it, cfg, a1["texto"])
    texto = vr["texto_final"]
    lac = a1["diag"].get("lacunas_prioritarias")
    qs = a1["questoes"] if not vr["reescrito"] else gen_questions(llms["generator"], it, cfg, True, texto, lac)
    return {"texto": texto, "questoes": qs, "diag": a1["diag"],
            "verif": {k: vr[k] for k in ("n_afirmacoes", "n_problemas", "n_incorretas", "reescrito")}}


def static_for_question(llms, q: dict, cfg) -> dict:
    """S: texto de reforço + questões gerados UMA vez por pergunta (iguais para todos os alunos)."""
    lo, hi = cfg["pipeline"]["support_words"]
    u = P.fill(P.STATIC_USER, PERGUNTA=q["question"], REFS=P.fmt_refs(q["refs"]),
               CONCEITOS=P.fmt_concepts(q["concepts"]), MIN=lo, MAX=hi)
    texto = llms["generator"].text(P.SUPPORT_SYSTEM, u, task="static")
    return {"texto": texto, "questoes": gen_questions(llms["generator"], q, cfg, False)}


def s0_gabarito(q: dict) -> dict:
    """S0: o próprio gabarito do professor como 'material' (linha de base sem LLM, sem alucinação, sem personalização)."""
    return {"texto": " ".join(q["refs"]), "questoes": []}


def format_material(m: dict) -> str:
    """Formatação neutra e idêntica para todas as condições (juiz cego à condição)."""
    s = m["texto"].strip()
    qs = m.get("questoes") or []
    if qs:
        s += "\n\nQuestões:\n" + "\n".join(
            f"{i}. [{q.get('nivel_bloom', '?')}] {q.get('enunciado', '')}" for i, q in enumerate(qs, 1))
    return s


def format_questions(qs: list[dict]) -> str:
    return "\n".join(f"{i}. [rótulo: {q.get('nivel_bloom', '?')}] {q.get('enunciado', '')}\n   Resposta esperada: {q.get('resposta_esperada', '')}"
                     for i, q in enumerate(qs, 1))
