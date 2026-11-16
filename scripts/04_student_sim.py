"""E3 (EXPLORATÓRIO) - Proxy de redução da lacuna com aluno simulado.

Para cada item: o aluno simulado relê a pergunta, lê (ou não) o material e responde de novo; um corretor com
gabarito atribui nota 0-3. Ganho = nota_pos - nota_pre (ambas pelo MESMO corretor). A condição N_sem_material
controla o conhecimento prévio do LLM simulado (sem ela, o 'ganho' seria só o modelo já saber a matéria).
LIMITAÇÃO: aluno simulado não substitui estudo com estudantes reais; use para triagem, não como evidência final.
"""
from _common import parse
from pln import prompts as P
from pln.common import JsonlAppender, pmap, read_jsonl, ROOT
from pln.llm import make_llms
from pln.pipeline import format_material

a, cfg, out = parse(__doc__)
items = {r["item_id"]: r for r in read_jsonl(ROOT / "data" / "processed" / "pilot_set.jsonl")}
mats = read_jsonl(out / "materials.jsonl")
by = {(m["item_id"], m["condition"]): m for m in mats}
ids = sorted({m["item_id"] for m in mats})
if a.limit:
    ids = ids[: a.limit]
llms = make_llms(cfg, ["student_sim", "grader"])
sink = JsonlAppender(out / "student_sim.jsonl")
done = {(r["item_id"], r["condition"]) for r in read_jsonl(out / "student_sim.jsonl")}
conds = ["PRE"] + cfg["student_sim"]["conditions"]
jobs = [(i, c) for i in ids for c in conds if (i, c) not in done and (c in ("PRE", "N_sem_material") or (i, c) in by)]


def grade(it, text):
    u = P.fill(P.GRADER_USER, PERGUNTA=it["question"], REFS=P.fmt_refs(it["refs"]), CONCEITOS=P.fmt_concepts(it["concepts"]), RESPOSTA=text)
    try:
        return max(0, min(3, int(llms["grader"].json(P.GRADER_SYSTEM, u, task="grade").get("nota"))))
    except (TypeError, ValueError):
        return None


def run(job):
    iid, c = job
    it = items[iid]
    if c == "PRE":
        resp = it["answer"]
    elif c == "N_sem_material":
        resp = llms["student_sim"].text(P.SIM_SYSTEM, P.fill(P.SIM_USER_NONE, PERGUNTA=it["question"], RESPOSTA=it["answer"]), task="student_sim")
    else:
        mat = by[(iid, c)]["texto"]  # só o texto de apoio: as questões novas não entram no reaprendizado
        resp = llms["student_sim"].text(P.SIM_SYSTEM, P.fill(P.SIM_USER_MATERIAL, PERGUNTA=it["question"], RESPOSTA=it["answer"], MATERIAL=mat), task="student_sim")
    row = {"item_id": iid, "condition": c, "resposta": resp, "nota": grade(it, resp)}
    sink.add(row)
    return row


res = pmap(run, jobs, cfg["runtime"]["workers"], "aluno simulado")
errs = [r for r in res if isinstance(r, dict) and "_error" in r]
print(f"jobs={len(jobs)} erros={len(errs)} -> {out / 'student_sim.jsonl'}")
if errs:
    print("exemplo de erro:", errs[0]["_error"])
