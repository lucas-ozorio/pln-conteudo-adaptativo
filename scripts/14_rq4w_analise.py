"""RQ4 com gerador fraco - análise offline do que o script 13 produziu (sem chamadas de LLM).

Lê outputs_rq4w/materiais.jsonl e results/rq4w_contrastes.csv e gera:
  results/rq4w_holm.csv           A2w-A1w e A2w_inc-A1w com Holm (família exploratória: 2 contrastes x 5 dimensões do juiz)
  results/rq4w_deteccao.csv       textos com erro segundo o juiz: o verificador viu? a reescrita corrigiu? criou erro novo?
  results/rq4w_orcamento.csv      tamanho de cada versão frente ao orçamento de palavras do prompt
  results/rq4w_subconjuntos.csv   A2w-A1w em todos, só nos reescritos e só onde o A1w respeitou o orçamento

--mostrar-erros imprime, para cada texto A1w com erro, a justificativa do juiz (recuperada do cache) e as frases
que o verificador marcou. As justificativas não vão para CSV, porque podem parafrasear a resposta do aluno.
"""
import hashlib
import json

import pandas as pd

from _common import parse
from pln import prompts as P
from pln.common import ROOT, read_jsonl
from pln.stats import cluster_ci, holm


def extra(ap):
    ap.add_argument("--mostrar-erros", action="store_true", help="imprime justificativas do juiz e frases marcadas")


a, cfg, _ = parse(__doc__, extra)
PASTA = ROOT / ("outputs_mock/rq4w" if a.mock else "outputs_rq4w")
RES = ROOT / ("results_mock" if a.mock else "results")
rows = read_jsonl(PASTA / "materiais.jsonl")
LO, HI = cfg["pipeline"]["support_words"]
V = ["A1w", "A2w", "A2w_inc"]
DIMS = ["afirmacoes_incorretas", "correcao_conceitual", "fidelidade_gabarito", "utilidade_pedagogica", "foco_na_lacuna"]

# ------------------------------------------------------------------ tabela larga: uma linha por item
reg = []
for r in rows:
    d = {"item_id": r["item_id"], "questao": r["question_id"], "nota": r["grade"], "verif_problemas": r["n_problemas"],
         "verif_incorretas": r["n_incorretas"], "reescrito_A2w": r["reescrito"]["A2w"],
         "reescrito_A2w_inc": r["reescrito"]["A2w_inc"]}
    for v in V:
        d[f"palavras_{v}"] = r["n_palavras"][v]
        for dm in DIMS:
            d[f"{dm}_{v}"] = r["juiz"][v][dm]
    reg.append(d)
df = pd.DataFrame(reg).set_index("item_id")
grupos = df["questao"]

# ------------------------------------------------------------------ 1. Holm na família exploratória
c = pd.read_csv(RES / "rq4w_contrastes.csv")
fam = c[c["contraste"].isin(["A2w - A1w", "A2w_inc - A1w"]) & c["dimensao"].isin(DIMS)].copy()
fam["p_holm"] = holm(fam["p_boot"].values)
fam.to_csv(RES / "rq4w_holm.csv", index=False, encoding="utf-8")

# ------------------------------------------------------------------ 2. detecção e correção dos erros vistos pelo juiz
inc = {v: df[f"afirmacoes_incorretas_{v}"] for v in V}
com_erro = df[inc["A1w"] > 0]
det = [
    ("textos A1w com erro (juiz)", len(com_erro)),
    ("afirmações incorretas no total: A1w", int(inc["A1w"].sum())),
    ("afirmações incorretas no total: A2w", int(inc["A2w"].sum())),
    ("afirmações incorretas no total: A2w_inc", int(inc["A2w_inc"].sum())),
    ("dos textos com erro: verificador marcou alguma frase", int((com_erro["verif_problemas"] > 0).sum())),
    ("dos textos com erro: verificador marcou alguma frase como incorreta", int((com_erro["verif_incorretas"] > 0).sum())),
    ("dos textos com erro: A2w ficou sem erro", int((com_erro["afirmacoes_incorretas_A2w"] == 0).sum())),
    ("dos textos com erro: A2w_inc ficou sem erro", int((com_erro["afirmacoes_incorretas_A2w_inc"] == 0).sum())),
    ("erro novo: A1w sem erro, A2w com erro", int(((inc["A1w"] == 0) & (inc["A2w"] > 0)).sum())),
    ("erro novo: A1w sem erro, A2w_inc com erro", int(((inc["A1w"] == 0) & (inc["A2w_inc"] > 0)).sum())),
    ("textos em que o verificador marcou alguma frase como incorreta", int((df["verif_incorretas"] > 0).sum())),
    ("desses: o juiz também viu erro no A1w", int(((df["verif_incorretas"] > 0) & (inc["A1w"] > 0)).sum())),
]
pd.DataFrame(det, columns=["medida", "n"]).to_csv(RES / "rq4w_deteccao.csv", index=False, encoding="utf-8")

# ------------------------------------------------------------------ 3. tamanho e orçamento de palavras
orc = pd.DataFrame([{"versao": v, "palavras_media": df[f"palavras_{v}"].mean(),
                     "frac_acima_de_" + str(HI): (df[f"palavras_{v}"] > HI).mean(),
                     "frac_abaixo_de_" + str(LO): (df[f"palavras_{v}"] < LO).mean()} for v in V])
orc.to_csv(RES / "rq4w_orcamento.csv", index=False, encoding="utf-8")

subs = {"todos": df.index, "so_reescritos_A2w": df.index[df["reescrito_A2w"]],
        f"A1w_ate_{HI}_palavras": df.index[df["palavras_A1w"] <= HI]}
sub = []
for nome, idx in subs.items():
    s = df.loc[idx]
    for dm in DIMS + ["palavras"]:
        r = cluster_ci(s[f"{dm}_A2w"] - s[f"{dm}_A1w"], grupos)
        sub.append({"subconjunto": nome, "dimensao": dm, "diff_A2w_menos_A1w": r["est"], "ic_lo": r["lo"], "ic_hi": r["hi"],
                    "p_boot": r["p_boot"], "n": r["n"], "n_questoes": r["n_questoes"]})
sub = pd.DataFrame(sub)
sub.to_csv(RES / "rq4w_subconjuntos.csv", index=False, encoding="utf-8")

with pd.option_context("display.width", 200, "display.max_columns", 20, "display.precision", 3):
    print("== Holm (familia exploratoria de 10 testes)\n", fam[["contraste", "dimensao", "diff", "ic_lo", "ic_hi", "p_boot", "p_holm"]])
    print("\n== deteccao e correcao\n", pd.DataFrame(det, columns=["medida", "n"]).to_string(index=False))
    print("\n== orcamento de palavras\n", orc)
    print("\n== A2w - A1w por subconjunto\n", sub)

# ------------------------------------------------------------------ 4. leitura qualitativa (só na tela)
if a.mostrar_erros:
    itens = {it["item_id"]: it for it in read_jsonl(ROOT / "data" / "processed" / "pilot_set.jsonl")}
    jm = cfg["models"]["judge"]
    kind = "mock" if a.mock else cfg["providers"][jm["provider"]]["kind"]
    cache = {r["k"]: r["v"] for r in read_jsonl(PASTA / "cache" / f"judge_{kind}.jsonl")}

    def justificativa(it, texto):
        u = P.fill(P.JUDGE_TEXT_USER, PERGUNTA=it["question"], REFS=P.fmt_refs(it["refs"]), RESPOSTA=it["answer"], TEXTO=texto)
        k = hashlib.sha256(json.dumps([kind, jm["name"], jm.get("temperature", 0.0), P.JUDGE_SYSTEM, u, 0],
                                      ensure_ascii=False).encode("utf-8")).hexdigest()
        v = cache.get(k, "")
        try:
            return json.loads(v[v.find("{"): v.rfind("}") + 1]).get("justificativa", "")
        except ValueError:
            return "(não encontrada no cache)"

    for r in rows:
        if r["juiz"]["A1w"]["afirmacoes_incorretas"] > 0:
            it = itens[r["item_id"]]
            print("=" * 110)
            print(r["item_id"], "| nota", r["grade"], "| incorretas", {v: r["juiz"][v]["afirmacoes_incorretas"] for v in V},
                  "| reescrito", r["reescrito"], "| palavras", r["n_palavras"])
            print("JUIZ (A1w):", justificativa(it, r["textos"]["A1w"]))
            for cl in r["claims"]:
                if cl.get("veredito") in ("nao_suportada", "incorreta"):
                    print(f"  VERIF [{cl['veredito']}] {cl.get('afirmacao')} | {cl.get('motivo', '')}")
