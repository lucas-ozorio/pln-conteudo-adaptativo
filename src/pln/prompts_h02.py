"""Variantes calibradas de prompt de diagnóstico para a tarefa H-02 (RQ1 / E0).

Mantém o arquivo original `src/pln/prompts.py` intacto e implementa três variantes
com o mesmo schema JSON de saída de `DIAG_USER`:
  - `v1_rubrica_calibrada`: zero-shot com rubrica corrigida (sem conceitos extras,
    regra explícita de gabaritos alternativos, 0-3 lacunas reais e omissão != erro).
  - `v2_fewshot_cross_q`: `v1_rubrica_calibrada` + 4 exemplos âncora (notas 0..3) de
    outra questão sorteados dinamicamente do holdout do PT-ASAG fora do `diag_set`.
  - `v3_fewshot_same_q`: `v1_rubrica_calibrada` + exemplos âncora da mesma questão
    (quando disponíveis no holdout fora do `diag_set`).

Guardrails:
  - A nota real do item-alvo nunca entra em nenhum prompt.
  - Exemplos de holdout são carregados dinamicamente de `data/raw/` (nunca gravados
    em texto fixo no código ou em relatórios públicos, conforme licença CC BY-NC-SA 4.0).
"""
from __future__ import annotations

import pandas as pd

from . import prompts as P
from .data import RAW, load_questions, norm

VARIANTS = ("v1_rubrica_calibrada", "v2_fewshot_cross_q", "v3_fewshot_same_q")
DEFAULT_DONOR_QID = 40
FALLBACK_DONOR_QID = 39

DIAG_SYSTEM_V1 = (
    "Você é um professor experiente de Ciências/Biologia do ensino fundamental (8º e 9º anos) no Brasil. "
    "Sua tarefa é diagnosticar, com justiça pedagógica e fidelidade ao gabarito, o que o aluno entendeu e o que ainda precisa aprender. "
    "Use apenas o gabarito e os conceitos-chave como referência, aceitando sinônimos e linguagem simples de aluno quando a ideia científica estiver correta. "
    "Responda apenas com JSON válido."
)

_DIAG_USER_BODY = """PERGUNTA: <<PERGUNTA>>

GABARITO (formulações alternativas e independentes escritas por professores):
<<REFS>>

CONCEITOS-CHAVE esperados: <<CONCEITOS>>
<<BLOCO_EXEMPLOS>>
RESPOSTA DO ALUNO A DIAGNOSTICAR: \"\"\"<<RESPOSTA>>\"\"\"

IMPORTANTE — Regras de correção e calibração:
1. Gabaritos alternativos: as respostas em GABARITO são exemplos equivalentes de professores. O aluno NÃO precisa combinar detalhes exclusivos de todas elas; atender ao núcleo de UMA formulação equivalente já é suficiente.
2. Conceitos: avalie em "conceitos" EXCLUSIVAMENTE os CONCEITOS-CHAVE esperados listados acima (não adicione conceitos extras que não estejam na lista).
3. Omissão vs. erro conceitual: "erros_conceituais" devem registrar SOMENTE concepções cientificamente erradas ou que contradigam o gabarito. Falta de informação (omissão) é marcada como "ausente" ou "parcial", NUNCA como erro conceitual. Nunca invente erro quando o aluno usar sinônimo válido ou linguagem simples correta.
4. Lacunas prioritárias: liste de 0 a 3 lacunas realmente importantes para o estudo do aluno. Se a resposta já cobrir os pontos essenciais sem lacunas relevantes, devolva lista vazia [].

Devolva JSON exatamente no formato:
{
  "conceitos": [
    {"conceito": "<exatamente um dos conceitos-chave esperados>", "status": "presente|parcial|ausente|incorreto", "evidencia": "<trecho literal da resposta do aluno ou null>"}
  ],
  "acertos": ["<o que o aluno acertou, em linguagem simples>"],
  "erros_conceituais": [{"descricao": "<concepção equivocada real, explicada em 1 frase>", "trecho": "<trecho literal do aluno>"}],
  "lacunas_prioritarias": ["<0 a 3 ideias/conceitos essenciais realmente ausentes ou errados; [] se completa>"],
  "nota_estimada": <0, 1, 2 ou 3>
}

Âncoras calibradas de "nota_estimada" (avalie a compreensão global da resposta frente a UM gabarito equivalente):
- 0 = incorreta ou irrelevante: não acerta nenhum conceito-chave essencial do núcleo da pergunta, contradiz o gabarito, apenas repete a pergunta ou traz só menção vaga sem explicação correta;
- 1 = inicial / insuficiente: apresenta alguma ideia correta isolada ou parcial, mas ainda falha no núcleo da pergunta ou comete erro conceitual importante;
- 2 = boa / parcialmente completa: responde corretamente ao núcleo da pergunta de forma compatível com um gabarito, faltando apenas um conceito específico ou maior precisão;
- 3 = completa / satisfatória: cobre as ideias essenciais de pelo menos um gabarito (mesmo de forma concisa ou em linguagem simples de 8º/9º ano), sem erros conceituais relevantes."""


def load_holdout_pool(cfg: dict, diag_items: list[dict], extra_exclude: list[dict] | None = None) -> pd.DataFrame:
    """Carrega respostas únicas válidas do PT-ASAG v2 estritamente fora de `diag_items`."""
    valid_qids = {int(r["question_id"]) for r in diag_items}
    excluded = {(int(r["question_id"]), norm(r["answer"])) for r in diag_items}
    if extra_exclude:
        excluded |= {(int(r["question_id"]), norm(r["answer"])) for r in extra_exclude}

    a = pd.read_csv(RAW / "student_answers_and_grades_v2.csv")
    a["answer_text"] = a["answer_text"].astype(str).str.strip()
    a["words"] = a["answer_text"].str.split().str.len()
    a = a[(a["words"] >= 1) & (a["words"] <= int(cfg["sample"]["max_words"])) & a["question_id"].isin(valid_qids)].copy()
    a["norm_answer"] = a["answer_text"].map(norm)
    a["nkey"] = list(zip(a["question_id"].astype(int), a["norm_answer"]))
    a = a.drop_duplicates("nkey")

    holdout = a[~a["nkey"].isin(excluded)].copy()
    assert not (set(holdout["nkey"]) & excluded), "Vazamento detectado: item de diag_set presente no holdout!"
    return holdout.sort_values(["question_id", "grade", "words", "norm_answer"]).reset_index(drop=True)


def pick_anchor_examples(holdout_df: pd.DataFrame, donor_qid: int) -> list[dict]:
    """Seleciona deterministicamente 1 resposta âncora (mediana de tamanho) por nota disponível (0..3)."""
    sub_q = holdout_df[holdout_df["question_id"] == int(donor_qid)]
    picked = []
    for grade in (0, 1, 2, 3):
        sub_g = sub_q[sub_q["grade"] == grade].copy()
        if sub_g.empty:
            continue
        mid = sub_g[(sub_g["words"] >= 5) & (sub_g["words"] <= 45)]
        pool = mid if not mid.empty else sub_g
        med = float(pool["words"].median())
        pool = pool.assign(_dist=(pool["words"] - med).abs()).sort_values(["_dist", "words", "norm_answer"])
        chosen = pool.iloc[0]
        picked.append({"grade": int(grade), "answer": str(chosen["answer_text"])})
    return picked


def format_fewshot_block(
    qmap: dict[int, dict],
    holdout_df: pd.DataFrame,
    donor_qid: int,
    cross_question: bool,
) -> str:
    """Formata bloco curto de calibração sem usar palavras proibidas e sem vazar alvo."""
    examples = pick_anchor_examples(holdout_df, donor_qid)
    if not examples:
        return ""
    lines = ["", "EXEMPLOS DE CALIBRAÇÃO DA ESCALA (apenas referência de critério):"]
    if cross_question:
        dq = qmap[int(donor_qid)]
        lines.append(f"Pergunta do exemplo: {dq['question']}")
        lines.append(f"Gabarito resumido do exemplo: {' / '.join(dq['refs'][:2])}")
        lines.append(f"Conceitos-chave do exemplo: {P.fmt_concepts(dq['concepts'])}")
    for ex in examples:
        lines.append(f"- Resposta (nota_estimada esperada = {ex['grade']}): \"\"\"{ex['answer']}\"\"\"")
    lines.append("")
    return "\n".join(lines)


def build_diag_prompt(
    variant: str,
    item: dict,
    holdout_df: pd.DataFrame | None = None,
    qmap: dict[int, dict] | None = None,
) -> tuple[str, str]:
    """Retorna `(system, user)` pronto para chamada do `diagnoser` em `H-02`."""
    if variant not in VARIANTS:
        raise ValueError(f"Variante desconhecida: {variant}. Opções: {VARIANTS}")

    bloco = ""
    if variant in ("v2_fewshot_cross_q", "v3_fewshot_same_q"):
        if holdout_df is None:
            raise ValueError(f"Variante '{variant}' exige `holdout_df`.")
        qmap = qmap or load_questions()
        target_qid = int(item["question_id"])
        if variant == "v2_fewshot_cross_q":
            donor_qid = FALLBACK_DONOR_QID if target_qid == DEFAULT_DONOR_QID else DEFAULT_DONOR_QID
            assert donor_qid != target_qid
            bloco = format_fewshot_block(qmap, holdout_df, donor_qid, cross_question=True)
        else:
            bloco = format_fewshot_block(qmap, holdout_df, target_qid, cross_question=False)

    user = P.fill(
        _DIAG_USER_BODY,
        PERGUNTA=item["question"],
        REFS=P.fmt_refs(item["refs"]),
        CONCEITOS=P.fmt_concepts(item["concepts"]),
        BLOCO_EXEMPLOS=bloco,
        RESPOSTA=item["answer"],
    )
    for tag in ("<<PERGUNTA>>", "<<REFS>>", "<<CONCEITOS>>", "<<BLOCO_EXEMPLOS>>", "<<RESPOSTA>>"):
        assert tag not in user, f"Marcador {tag} não preenchido no prompt H-02!"
    return DIAG_SYSTEM_V1, user
