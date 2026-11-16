"""E1 (avaliação) - LLM-as-a-Judge cego à condição: notas absolutas (texto e questões) + comparações par-a-par nas duas ordens."""
from _common import parse
from pln import judge as J
from pln.common import JsonlAppender, pmap, read_jsonl, ROOT
from pln.llm import make_llms

a, cfg, out = parse(__doc__)
items = {r["item_id"]: r for r in read_jsonl(ROOT / "data" / "processed" / "pilot_set.jsonl")}
mats = read_jsonl(out / "materials.jsonl")
if a.limit:
    keep = {m["item_id"] for m in mats}
    keep = set(list(sorted(keep))[: a.limit])
    mats = [m for m in mats if m["item_id"] in keep]
by_item = {}
for m in mats:
    by_item.setdefault(m["item_id"], {})[m["condition"]] = m
llms = make_llms(cfg, ["judge"])
reps = cfg["judge"].get("n_reps", 1)

# ---- notas absolutas
abs_sink = JsonlAppender(out / "judgments_abs.jsonl")
abs_done = {(r["item_id"], r["condition"], r["rep"]) for r in read_jsonl(out / "judgments_abs.jsonl")}
jobs = [(m, rep) for m in mats for rep in range(reps) if (m["item_id"], m["condition"], rep) not in abs_done]


def run_abs(job):
    m, rep = job
    it = items[m["item_id"]]
    row = {"item_id": m["item_id"], "condition": m["condition"], "rep": rep, "n_palavras": m["n_palavras"],
           "texto": J.judge_text(llms["judge"], it, m["texto"], rep)}
    row["questoes"] = J.judge_questions(llms["judge"], it, m["questoes"], rep) if m["questoes"] else []
    abs_sink.add(row)
    return row


r1 = pmap(run_abs, jobs, cfg["runtime"]["workers"], "juiz absoluto")

# ---- par-a-par (as duas ordens: mede viés de posição)
pair_sink = JsonlAppender(out / "judgments_pair.jsonl")
pair_done = {(r["item_id"], r["x"], r["y"], r["order"], r["rep"]) for r in read_jsonl(out / "judgments_pair.jsonl")}
pjobs = []
for iid, cm in by_item.items():
    for x, y in cfg["judge"]["pairs"]:
        if x in cm and y in cm:
            for order in ("xy", "yx"):
                for rep in range(reps):
                    if (iid, x, y, order, rep) not in pair_done:
                        pjobs.append((iid, x, y, order, rep))


def run_pair(job):
    iid, x, y, order, rep = job
    first, second = by_item[iid][x], by_item[iid][y]
    if order == "yx":
        first, second = second, first
    v = J.judge_pair(llms["judge"], items[iid], first, second, rep)
    winner = "empate" if v == "empate" else ((x if v == "A" else y) if order == "xy" else (y if v == "A" else x))
    row = {"item_id": iid, "x": x, "y": y, "order": order, "rep": rep, "raw": v, "winner": winner,
           "pos_first_won": v == "A"}
    pair_sink.add(row)
    return row


r2 = pmap(run_pair, pjobs, cfg["runtime"]["workers"], "juiz par-a-par")
errs = [r for r in (r1 + r2) if isinstance(r, dict) and "_error" in r]
print(f"abs={len(jobs)} pares={len(pjobs)} erros={len(errs)}")
if errs:
    print("exemplo de erro:", errs[0]["_error"])
