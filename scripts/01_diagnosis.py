"""E0 - Validade do diagnóstico: o diagnóstico qualitativo recupera a nota-ouro (0-3) e os conceitos-chave?"""
from _common import parse
from pln.common import JsonlAppender, pmap, read_jsonl, ROOT
from pln.llm import make_llms
from pln.pipeline import diagnose

a, cfg, out = parse(__doc__)
items = read_jsonl(ROOT / "data" / "processed" / "diag_set.jsonl")
if a.limit:
    items = items[: a.limit]
llms = make_llms(cfg, ["diagnoser"])
sink = JsonlAppender(out / "diagnosis.jsonl")
done = {r["item_id"] for r in read_jsonl(out / "diagnosis.jsonl")}
todo = [it for it in items if it["item_id"] not in done]


def run(it):
    row = {"item_id": it["item_id"], "diag": diagnose(llms["diagnoser"], it)}
    sink.add(row)
    return row


res = pmap(run, todo, cfg["runtime"]["workers"], "diagnóstico")
errs = [r for r in res if r and "_error" in r]
print(f"ok={len(todo) - len(errs)} erros={len(errs)} -> {out / 'diagnosis.jsonl'}")
if errs:
    print("exemplo de erro:", errs[0]["_error"])
