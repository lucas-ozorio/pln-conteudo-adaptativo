"""Item 8: aluno simulado com pós-teste de TRANSFERÊNCIA (sem acesso ao material no momento da resposta).

Para cada item x condição: o aluno simulado lê o material e escreve anotações curtas (gargalo de informação); em seguida
responde a 3 questões NOVAS e independentes de qualquer condição, usando só as anotações. Um corretor com gabarito
atribui 0-3 a cada resposta. 'N_sem_material' controla o conhecimento prévio do LLM. Exploratório (PRE_REGISTRO.md H7).
"""
import json

from _common import parse
from pln import prompts as P
from pln import prompts_robust as PR
from pln import robust as R
from pln.common import JsonlAppender, ROOT, pmap, read_jsonl
from pln.data import load_questions

a, cfg, _ = parse(__doc__, lambda ap: ap.add_argument("--so-reparo", action="store_true", help="só relê notas do cache e sai (sem chamadas novas)"))
MOCK = a.mock
OUT = ROOT / ("outputs_robust_mock" if MOCK else "outputs_robust")
OUT.mkdir(exist_ok=True)
R.guard(0.5, MOCK)
items = read_jsonl(ROOT / "data" / "processed" / "pilot_set.jsonl")
if a.limit:
    items = items[: a.limit]
mats = R.all_materials(ROOT / "outputs" / "materials.jsonl")
CONDS = ["N_sem_material", "S0_gabarito", "S_estatico", "A0_direto", "A1_pipeline", "A2_pipeline_verif"]


def llm(role, tag):
    return R.RobustLLM(role, cfg, tag=tag, mock=MOCK)


gen, student, grader = llm("generator", "posttest_gen"), llm("student_sim2", "student_post"), llm("grader", "grader_post")

# ------------------------------------------------------------------ 1. pós-teste neutro (1 vez por pergunta)
qpath = OUT / "posttest_questions.json"
qs = load_questions()
post = json.loads(qpath.read_text(encoding="utf-8")) if qpath.exists() else {}
for qid in sorted({it["question_id"] for it in items}):
    if str(qid) in post:
        continue
    q = qs[qid]
    u = P.fill(PR.POSTTEST_USER, PERGUNTA=q["question"], REFS=P.fmt_refs(q["refs"]), CONCEITOS=P.fmt_concepts(q["concepts"]))
    post[str(qid)] = gen.json(PR.POSTTEST_SYSTEM, u, task="posttest").get("questoes", [])[:3]
qpath.write_text(json.dumps(post, ensure_ascii=False, indent=1), encoding="utf-8")
print("pós-teste:", {k: len(v) for k, v in post.items()})

def parse_notas(g: dict) -> list:
    """Aceita {"notas": [2, 3, 3]} e também {"notas": [{"questao": 1, "nota": 2, ...}, ...]} (formato visto em ~40% das respostas)."""
    out = []
    for x in (g.get("notas") or [])[:3]:
        if isinstance(x, dict):
            x = x.get("nota", x.get("notas"))
        try:
            out.append(max(0, min(3, int(x))))
        except (TypeError, ValueError):
            out.append(None)
    return out + [None] * (3 - len(out))


def corrige(it, pq, resp):
    itens = "\n".join(f"Questão {i}: {q['enunciado']}\nResposta esperada: {q['resposta_esperada']}\nResposta do aluno: {r or '(em branco)'}\n"
                      for i, (q, r) in enumerate(zip(pq, resp), 1))
    return grader.json(P.GRADER_SYSTEM, P.fill(PR.POSTGRADER_USER, REFS=P.fmt_refs(it["refs"]), ITENS=itens), task="postgrade")


# ------------------------------------------------------------------ 1b. reparo: linhas antigas sem nota (formato de resposta do corretor)
_tp = OUT / "transfer.jsonl"
_rows = read_jsonl(_tp)
_by = {it["item_id"]: it for it in items}
_fix = 0
for r in _rows:
    if r["media"] is None and r["item_id"] in _by:
        it = _by[r["item_id"]]
        nt = parse_notas(corrige(it, post[str(it["question_id"])], r["respostas"]))  # resposta já está no cache: sem custo
        v = [n for n in nt if n is not None]
        if v:
            r["notas"], r["media"] = nt, sum(v) / len(v)
            _fix += 1
if _fix:
    from pln.common import write_jsonl

    write_jsonl(_tp, _rows)
print(f"reparo: {_fix} linhas recuperadas do cache")
if a.so_reparo:
    raise SystemExit(0)

# ------------------------------------------------------------------ 2. alunos
sink = JsonlAppender(OUT / "transfer.jsonl")
done = {(r["item_id"], r["condition"]) for r in read_jsonl(OUT / "transfer.jsonl")}
jobs = [(it, c) for it in items for c in CONDS if (it["item_id"], c) not in done and (c == "N_sem_material" or (it["item_id"], c) in mats)]


def run(job):
    it, c = job
    pq = post[str(it["question_id"])]
    if c == "N_sem_material":
        u = P.fill(PR.NOTES_NONE_USER, PERGUNTA=it["question"], RESPOSTA=it["answer"])
    else:
        u = P.fill(PR.NOTES_MATERIAL_USER, PERGUNTA=it["question"], RESPOSTA=it["answer"], MATERIAL=mats[(it["item_id"], c)]["texto"])
    notes = student.text(P.SIM_SYSTEM, u, task="notes")
    qtxt = "\n".join(f"{i}. {q['enunciado']}" for i, q in enumerate(pq, 1))
    ans = student.json(P.SIM_SYSTEM, P.fill(PR.ANSWERS_USER, PERGUNTA=it["question"], RESPOSTA=it["answer"], NOTAS=notes, QUESTOES=qtxt), task="answers")
    resp = [str(x) for x in (ans.get("respostas") or [])][:3]
    resp += [""] * (3 - len(resp))
    itens = "\n".join(f"Questão {i}: {q['enunciado']}\nResposta esperada: {q['resposta_esperada']}\nResposta do aluno: {r or '(em branco)'}\n"
                      for i, (q, r) in enumerate(zip(pq, resp), 1))
    g = grader.json(P.GRADER_SYSTEM, P.fill(PR.POSTGRADER_USER, REFS=P.fmt_refs(it["refs"]), ITENS=itens), task="postgrade")
    notas = parse_notas(g)
    valid = [n for n in notas if n is not None]
    row = {"item_id": it["item_id"], "condition": c, "notas": notas, "media": sum(valid) / len(valid) if valid else None,
           "anotacoes": notes, "respostas": resp}
    sink.add(row)
    return row


res = pmap(run, jobs, cfg["runtime"]["workers"], "transferência")
R._rep(res, "transferencia")
print(f"gasto desta rodada (estimado): US$ {R.spent_usd(OUT / 'usage.jsonl'):.3f}")
