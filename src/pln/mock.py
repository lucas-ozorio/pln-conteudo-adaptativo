"""Respostas sintéticas para testar o ENCANAMENTO sem chave de API. NÃO produzem resultado científico."""
from __future__ import annotations

import hashlib
import json


def _h(s: str, mod: int) -> int:
    return int(hashlib.md5(s.encode("utf-8")).hexdigest(), 16) % mod


def mock_reply(task: str, user: str) -> str:
    if task == "diagnose":
        return json.dumps({"conceitos": [{"conceito": "c1", "status": ["presente", "parcial", "ausente", "incorreto"][_h(user, 4)], "evidencia": None}],
                           "acertos": ["a"], "erros_conceituais": [{"descricao": "d", "trecho": "t"}],
                           "lacunas_prioritarias": ["lacuna 1", "lacuna 2"], "nota_estimada": _h(user, 4)})
    if task in ("support", "static", "rewrite"):
        return "Texto de apoio simulado. " + " ".join(["palavra"] * (130 + _h(user, 40)))
    if task == "questions":
        return json.dumps({"questoes": [{"nivel_bloom": n, "enunciado": f"Questão {n}?", "resposta_esperada": "r"}
                                        for n in ("entender", "aplicar", "analisar")]})
    if task == "direct":
        return json.dumps({"texto_apoio": "Texto direto simulado. " + " ".join(["palavra"] * (130 + _h(user, 40))),
                           "questoes": [{"nivel_bloom": n, "enunciado": f"Questão {n}?", "resposta_esperada": "r"}
                                        for n in ("entender", "aplicar", "analisar")]})
    if task == "verify":
        return json.dumps({"afirmacoes": [{"afirmacao": "x", "veredito": ["suportada", "nao_suportada", "conhecimento_geral_correto", "incorreta"][_h(user, 4)], "motivo": "m"}]})
    if task == "judge_text":
        r = lambda k: 1 + _h(user + k, 5)  # noqa: E731
        return json.dumps({"justificativa": "j", "coerencia": r("a"), "correcao_conceitual": r("b"), "fidelidade_gabarito": r("c"),
                           "foco_na_lacuna": r("d"), "utilidade_pedagogica": r("e"), "adequacao_nivel": r("f"), "afirmacoes_incorretas": _h(user, 2)})
    if task == "judge_questions":
        return json.dumps({"questoes": [{"nivel_bloom_percebido": "entender", "alinhamento_gabarito": 1 + _h(user + str(i), 5), "clareza": 4,
                                         "relevancia_lacuna": 1 + _h(user + "r" + str(i), 5), "resposta_esperada_correta": bool(_h(user, 2))} for i in range(3)]})
    if task == "judge_pair":
        return json.dumps({"justificativa": "j", "vencedor": ["A", "B", "empate"][_h(user, 3)]})
    if task == "student_sim":
        return "Resposta simulada do aluno " + str(_h(user, 100))
    if task == "grade":
        return json.dumps({"nota": _h(user, 4)})
    if task == "judge_blind":
        r = lambda k: 1 + _h(user + k, 5)  # noqa: E731
        return json.dumps({"justificativa": "j", "coerencia": r("a"), "correcao_conceitual": r("b"), "fidelidade_gabarito": r("c"),
                           "completude": r("d"), "adequacao_nivel": r("e"), "qualidade_geral": r("f"), "afirmacoes_incorretas": _h(user, 2)})
    if task == "judge_overrem":
        r = lambda k: 1 + _h(user + k, 5)  # noqa: E731
        return json.dumps({"justificativa": "j", "reconhece_acertos": r("a"), "sobre_remediacao": r("b"), "coerencia": r("c"),
                           "correcao_conceitual": r("d"), "fidelidade_gabarito": r("e"), "utilidade_pedagogica": r("f")})
    if task == "posttest":
        return json.dumps({"questoes": [{"enunciado": f"Pergunta nova {i}?", "resposta_esperada": "r"} for i in range(3)]})
    if task == "notes":
        return "Anotacao simulada " + str(_h(user, 100))
    if task == "answers":
        return json.dumps({"respostas": ["resp a", "resp b", "resp c"]})
    if task == "postgrade":
        return json.dumps({"notas": [_h(user + "1", 4), _h(user + "2", 4), _h(user + "3", 4)]})
    raise ValueError(f"mock: tarefa desconhecida {task}")
