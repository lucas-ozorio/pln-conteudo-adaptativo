"""Estima nº de chamadas por etapa (e tokens aproximados) a partir da config e das amostras. Não chama nenhum LLM."""
from _common import parse
from pln.common import ROOT, read_jsonl

a, cfg, out = parse(__doc__)
diag = len(read_jsonl(ROOT / "data" / "processed" / "diag_set.jsonl"))
n = len(read_jsonl(ROOT / "data" / "processed" / "pilot_set.jsonl"))
if not (diag and n):
    raise SystemExit("rode primeiro: python scripts/00_prepare_data.py")
c = cfg["pipeline"]["conditions"]
reps = cfg["judge"].get("n_reps", 1)
nq = len({r["question_id"] for r in read_jsonl(ROOT / "data" / "processed" / "pilot_set.jsonl")})
calls = {"E0 diagnóstico": diag}
g = 0
g += nq * 2 if "S_estatico" in c else 0                      # texto + questões estáticos
g += n * 2 if "A1_pipeline" in c or "A2_pipeline_verif" in c else 0   # apoio + questões (diagnóstico vem do E0)
g += n * 1 if "A0_direto" in c else 0
g += n * 2.5 if "A2_pipeline_verif" in c else 0              # verificação + (≈50%) reescrita + questões
calls["E1 geração"] = int(g)
withq = len([x for x in c if x != "S0_gabarito"])
calls["E1 juiz absoluto"] = int(n * reps * (len(c) + withq))
calls["E1 juiz par-a-par"] = int(n * len(cfg["judge"]["pairs"]) * 2 * reps)
calls["E3 aluno simulado + corretor"] = int(n * (1 + len(cfg["student_sim"]["conditions"])) * 2 - n)
tot = sum(calls.values())
for k, v in calls.items():
    print(f"{k:34s} {v:7d}")
print(f"{'TOTAL':34s} {tot:7d}  (~{tot * 1100 / 1e6:.1f}M tokens de entrada, ~{tot * 350 / 1e6:.1f}M de saída, estimativa grosseira)")
print("Custo = tokens x preço do seu modelo/provedor; confira a tabela de preços antes de rodar.")
