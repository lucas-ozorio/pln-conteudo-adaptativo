"""E1 (geração) - produz o material de cada condição para cada item do piloto."""
from _common import parse
from pln import pipeline as PL
from pln.common import JsonlAppender, pmap, read_jsonl, ROOT
from pln.data import load_questions
from pln.llm import make_llms

a, cfg, out = parse(__doc__)
items = read_jsonl(ROOT / "data" / "processed" / "pilot_set.jsonl")
if a.limit:
    items = items[: a.limit]
conds = cfg["pipeline"]["conditions"]
llms = make_llms(cfg, ["diagnoser", "generator", "verifier"])
sink = JsonlAppender(out / "materials.jsonl")
done = {(r["item_id"], r["condition"]) for r in read_jsonl(out / "materials.jsonl")}
diag_cache = {r["item_id"]: r["diag"] for r in read_jsonl(out / "diagnosis.jsonl")}  # reaproveita o E0

# Materiais estáticos: UM por pergunta, idêntico para todos os alunos daquela pergunta
qs = load_questions()
static = {}
for qid in sorted({it["question_id"] for it in items}):
    if "S_estatico" in conds:
        static[qid] = PL.static_for_question(llms, qs[qid], cfg)

STATIC_ONLY = {"S0_gabarito", "S_estatico"}


def run(it):
    rows = []
    a1 = None
    for c in conds:
        if (it["item_id"], c) in done:
            continue
        if c == "S0_gabarito":
            m = PL.s0_gabarito(it)
        elif c == "S_estatico":
            m = static[it["question_id"]]
        elif c == "A0_direto":
            m = PL.cond_A0(llms, it, cfg)
        elif c == "A1_pipeline":
            a1 = a1 or PL.cond_A1(llms, it, cfg, diag_cache.get(it["item_id"]))
            m = a1
        elif c == "A2_pipeline_verif":
            a1 = a1 or PL.cond_A1(llms, it, cfg, diag_cache.get(it["item_id"]))
            m = PL.cond_A2(llms, it, cfg, a1)
        else:
            raise ValueError(f"condição desconhecida: {c}")
        row = {"item_id": it["item_id"], "condition": c, "texto": m["texto"], "questoes": m.get("questoes", []),
               "n_palavras": len(m["texto"].split()), "diag": m.get("diag"), "verif": m.get("verif")}
        sink.add(row)
        rows.append(row)
    return rows


res = pmap(run, items, cfg["runtime"]["workers"], "geração")
errs = [r for r in res if isinstance(r, dict) and "_error" in r]
print(f"itens={len(items)} erros={len(errs)} -> {out / 'materials.jsonl'}")
if errs:
    print("exemplo de erro:", errs[0]["_error"])
