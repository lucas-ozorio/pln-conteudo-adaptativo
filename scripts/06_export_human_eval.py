"""Exporta a planilha CEGA para avaliação humana especialista + o gabarito de condições (guardar separado dos avaliadores)."""
import random

import pandas as pd

from _common import parse
from pln.common import ROOT, read_jsonl
from pln.pipeline import format_questions
from pln import prompts as P


def extra(ap):
    ap.add_argument("--n-items", type=int, default=None)


a, cfg, out = parse(__doc__, extra)
n = a.n_items or cfg["human_eval"]["n_items"]
conds = cfg["human_eval"]["conditions"]
items = {r["item_id"]: r for r in read_jsonl(ROOT / "data" / "processed" / "pilot_set.jsonl")}
mats = [m for m in read_jsonl(out / "materials.jsonl") if m["condition"] in conds]
ids = sorted({m["item_id"] for m in mats})
rng = random.Random(cfg["seed"])
# amostra estratificada por nota-ouro (balanceia 0/1/2)
by_g = {}
for i in ids:
    by_g.setdefault(items[i]["grade"], []).append(i)
chosen = []
per = max(1, n // max(1, len(by_g)))
for g, lst in sorted(by_g.items()):
    rng.shuffle(lst)
    chosen += lst[:per]
chosen = chosen[:n]

rows, key = [], []
for iid in chosen:
    it = items[iid]
    for m in [m for m in mats if m["item_id"] == iid]:
        rid = f"R{rng.randrange(10**6):06d}"
        rows.append({"id_avaliacao": rid, "pergunta": it["question"], "gabarito": " | ".join(it["refs"]), "resposta_aluno": it["answer"],
                     "texto_apoio": m["texto"], "novas_questoes": format_questions(m["questoes"]) if m["questoes"] else "",
                     **{k: "" for k in ["coerencia", "correcao_conceitual", "fidelidade_gabarito", "foco_na_lacuna",
                                        "utilidade_pedagogica", "adequacao_nivel", "afirmacoes_incorretas", "comentario"]}})
        key.append({"id_avaliacao": rid, "item_id": iid, "condicao": m["condition"], "nota_ouro": it["grade"]})
rng.shuffle(rows)  # ordem aleatória, sem pistas de condição
hd = ROOT / "human_eval"
hd.mkdir(exist_ok=True)
pd.DataFrame(rows).to_csv(hd / "planilha_avaliadores.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(key).to_csv(hd / "CHAVE_condicoes_NAO_COMPARTILHAR.csv", index=False, encoding="utf-8-sig")
(hd / "INSTRUCOES_avaliadores.md").write_text(
    "# Instruções para avaliadores (cegas à condição)\n\n"
    "Para cada linha, leia pergunta, gabarito, resposta do aluno, texto de apoio e novas questões. Dê notas de 1 a 5 "
    "(1 = muito ruim, 3 = aceitável, 5 = excelente) em:\n"
    "- coerencia: clareza e fluidez em português;\n- correcao_conceitual: sem erros científicos (1 = erro grave);\n"
    "- fidelidade_gabarito: alinhado ao gabarito, sem contradizê-lo;\n"
    "- foco_na_lacuna: trata ESPECIFICAMENTE o que ESTE aluno errou/omitiu (1 = genérico);\n"
    "- utilidade_pedagogica: ajudaria este aluno a corrigir o erro, sem entregar a resposta pronta;\n"
    "- adequacao_nivel: adequado ao 8º/9º ano.\n"
    "Em afirmacoes_incorretas, conte afirmações cientificamente erradas ou contrárias ao gabarito.\n"
    "Não preferir texto só por ser mais longo. Não tente adivinhar qual sistema gerou o material.\n"
    "Cada avaliador preenche uma CÓPIA da planilha (nome: planilha_<avaliador>.csv). Sugestão: 2 ou 3 avaliadores sobre as mesmas linhas.\n",
    encoding="utf-8")
print(f"{len(rows)} linhas ({len(chosen)} itens x {len(conds)} condições) -> {hd}")
