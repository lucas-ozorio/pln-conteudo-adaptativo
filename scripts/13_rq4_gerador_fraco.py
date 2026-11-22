"""RQ4 com gerador mais fraco (USA API, barato): a verificação A2 ajuda quando o gerador erra mais?

Cenário: o Llama 3.1 8B gera o texto de apoio A1 e faz a reescrita; o verificador (GPT-4o mini) e o juiz
(Gemini 2.5 Flash) são os MESMOS do artigo. Usa os prompts de src/pln/prompts.py sem alteração e reaproveita o
diagnóstico de outputs/diagnosis.jsonl (nenhuma chamada de diagnóstico). Não gera questões: o juiz de texto só lê o texto.

Três versões por item:
  A1w      texto do gerador fraco
  A2w      política do artigo: reescreve se houver afirmação nao_suportada OU incorreta
  A2w_inc  política "sem encurtar": reescreve só se houver afirmação incorreta, e só essas (mesmo prompt de reescrita)

Gasto: as chamadas param quando o gasto estimado pelos tokens passa de --teto-usd; o gasto real da chave
(GET /api/v1/key, que não consome tokens) é mostrado no fim. Saídas e cache em outputs_rq4w/ (outputs_mock/rq4w
com --mock); resumo em results/rq4w_*.csv. Nunca escreve em outputs/ nem em cache/.

Uso:  python scripts/13_rq4_gerador_fraco.py --mock --n-por-questao 12   (encanamento, sem custo)
      python scripts/13_rq4_gerador_fraco.py --n-por-questao 1           (piloto: 15 itens)
      python scripts/13_rq4_gerador_fraco.py --n-por-questao 12          (180 itens; retoma o que já foi feito)
"""
import copy
import json
import os
import threading
import time
import urllib.request
from collections import Counter

import pandas as pd

from _common import parse
from pln import judge as J
from pln import pipeline as PL
from pln import prompts as P
from pln.common import JsonlAppender, ROOT, pmap, read_jsonl
from pln.llm import LLM
from pln.stats import cluster_ci


def extra(ap):
    ap.add_argument("--n-por-questao", type=int, default=1, help="itens por questão (1 = piloto de 15; 12 = os 180)")
    ap.add_argument("--gerador", default="meta-llama/llama-3.1-8b-instruct", help="modelo do gerador fraco (OpenRouter)")
    ap.add_argument("--teto-usd", type=float, default=1.0, help="para as chamadas quando o gasto estimado passa disso")


a, cfg, _ = parse(__doc__, extra)
PASTA = ROOT / ("outputs_mock/rq4w" if a.mock else "outputs_rq4w")
RES = ROOT / ("results_mock" if a.mock else "results")
PASTA.mkdir(parents=True, exist_ok=True)
RES.mkdir(exist_ok=True)

# ------------------------------------------------------------------ cliente isolado com teto de gasto
# US$ por 1M tokens (entrada, saída), conferidos em 2026-11-22; o padrão (Llama 8B) é um teto conservador
PRECO = {"openai/gpt-4o-mini": (0.15, 0.60), "google/gemini-2.5-flash": (0.30, 2.50)}
PRECO_PADRAO = (0.10, 0.20)
GASTO = {"usd": 0.0, "chamadas": 0}
TRAVA = threading.Lock()


class LLMIsolado(LLM):
    """O LLM do projeto, mas com cache e registro de uso em PASTA (nunca em cache/ ou outputs/) e teto de gasto."""

    def __init__(self, role: str, cfg: dict):
        super().__init__(role, cfg)  # lê o cache original só para descartar em seguida (leitura apenas)
        self.cache_path = PASTA / "cache" / f"{role}_{self.kind}.jsonl"
        self.usage_path = PASTA / "uso.jsonl"
        self._cache = {r["k"]: r["v"] for r in read_jsonl(self.cache_path)}

    def _raw(self, system, user, task, want_json):
        with TRAVA:
            if GASTO["usd"] >= a.teto_usd:
                raise RuntimeError(f"teto de gasto atingido (US$ {GASTO['usd']:.3f} >= {a.teto_usd})")
        return super()._raw(system, user, task, want_json)

    def _log_usage(self, task, usage):
        super()._log_usage(task, usage)
        if usage is None:
            return
        pi, po = PRECO.get(self.name, PRECO_PADRAO)
        with TRAVA:
            GASTO["usd"] += (getattr(usage, "prompt_tokens", 0) * pi + getattr(usage, "completion_tokens", 0) * po) / 1e6
            GASTO["chamadas"] += 1


def gasto_real():
    """Gasto acumulado da chave em US$ (GET /api/v1/key, não consome tokens). None no mock ou se falhar."""
    if a.mock:
        return None
    chave = os.environ.get(cfg["providers"]["main"]["api_key_env"], "")
    req = urllib.request.Request("https://openrouter.ai/api/v1/key", headers={"Authorization": f"Bearer {chave}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return float(json.load(r)["data"]["usage"])
    except Exception:  # noqa: BLE001
        return None


cfg = copy.deepcopy(cfg)
cfg["models"]["generator"]["name"] = a.gerador
llms = {r: LLMIsolado(r, cfg) for r in ("generator", "verifier", "judge")}

# ------------------------------------------------------------------ itens
todos = read_jsonl(ROOT / "data" / "processed" / "pilot_set.jsonl")
diag = {r["item_id"]: r["diag"] for r in read_jsonl(ROOT / "outputs" / "diagnosis.jsonl")}  # leitura apenas


def selecionar(itens, k):
    """k itens por questão, alternando as notas (0, 1, 2) e começando por uma nota diferente em cada questão."""
    por_q = {}
    for it in sorted(itens, key=lambda x: (x["question_id"], x["grade"], x["item_id"])):
        por_q.setdefault(it["question_id"], []).append(it)
    sel = []
    for i, (_, lst) in enumerate(sorted(por_q.items())):
        notas = sorted({x["grade"] for x in lst})
        filas = {g: [x for x in lst if x["grade"] == g] for g in notas}
        ordem = notas[i % len(notas):] + notas[: i % len(notas)]
        fila = []
        while any(filas.values()):
            for g in ordem:
                if filas[g]:
                    fila.append(filas[g].pop(0))
        sel += fila[:k]
    return sel


itens = selecionar(todos, a.n_por_questao)
if a.limit:
    itens = itens[: a.limit]
faltam = [it["item_id"] for it in itens if it["item_id"] not in diag]
if faltam:
    raise SystemExit(f"itens sem diagnóstico em outputs/diagnosis.jsonl: {faltam[:5]}")
QUESTAO = {it["item_id"]: it["question_id"] for it in itens}

# ------------------------------------------------------------------ geração, verificação, reescrita e juiz
sink = JsonlAppender(PASTA / "materiais.jsonl")
feitos = {r["item_id"] for r in read_jsonl(PASTA / "materiais.jsonl")}


def reescrita_so_incorretas(it, texto, claims):
    """Igual à reescrita do A2 (pipeline.verify_and_rewrite), mas só com as afirmações 'incorreta'."""
    inc = [c for c in claims if c.get("veredito") == "incorreta"]
    if not inc:
        return texto, False
    lo, hi = cfg["pipeline"]["support_words"]
    probs = "\n".join(f"- {c.get('afirmacao')} ({c.get('veredito')}: {c.get('motivo', '')})" for c in inc)
    novo = llms["generator"].text(
        P.SUPPORT_SYSTEM, P.fill(P.REWRITE_USER, REFS=P.fmt_refs(it["refs"]), TEXTO=texto, PROBLEMAS=probs, MIN=lo, MAX=hi),
        task="rewrite")
    return novo, True


def rodar(it):
    a1 = PL.gen_support(llms["generator"], it, diag[it["item_id"]], cfg)
    vr = PL.verify_and_rewrite(llms, it, cfg, a1)
    a2i, reescr_inc = reescrita_so_incorretas(it, a1, vr["claims"])
    textos = {"A1w": a1, "A2w": vr["texto_final"], "A2w_inc": a2i}
    juiz = {v: J.judge_text(llms["judge"], it, t) for v, t in textos.items()}  # textos idênticos caem no cache
    row = {"item_id": it["item_id"], "question_id": it["question_id"], "grade": it["grade"], "gerador": a.gerador,
           "textos": textos, "n_palavras": {v: len(t.split()) for v, t in textos.items()},
           "claims": vr["claims"], "n_afirmacoes": vr["n_afirmacoes"], "n_problemas": vr["n_problemas"],
           "n_incorretas": vr["n_incorretas"], "reescrito": {"A2w": vr["reescrito"], "A2w_inc": reescr_inc}, "juiz": juiz}
    sink.add(row)
    return row


pendentes = [it for it in itens if it["item_id"] not in feitos]
print(f"gerador={a.gerador} itens={len(itens)} ja_feitos={len(itens) - len(pendentes)} pendentes={len(pendentes)} "
      f"teto=US$ {a.teto_usd:.2f} pasta={PASTA.relative_to(ROOT)}")
antes = gasto_real()
res = pmap(rodar, pendentes, cfg["runtime"]["workers"], "rq4 gerador fraco") if pendentes else []
erros = [r for r in res if isinstance(r, dict) and "_error" in r]
if erros:
    print(f"erros={len(erros)}; exemplo: {erros[0]['_error']}  (rode de novo para retomar; o cache evita gastar duas vezes)")

# ------------------------------------------------------------------ resumo
VERS = ["A1_artigo", "A2_artigo", "A1w", "A2w", "A2w_inc"]
DIMS = ["afirmacoes_incorretas", "correcao_conceitual", "fidelidade_gabarito", "utilidade_pedagogica", "foco_na_lacuna",
        "palavras"]
rows = [r for r in read_jsonl(PASTA / "materiais.jsonl") if r["item_id"] in QUESTAO]
if not rows:
    raise SystemExit("nenhum item concluído")

reg = [{"item_id": r["item_id"], "versao": v, "palavras": r["n_palavras"][v], "reescrito": r["reescrito"].get(v, False),
        **r["juiz"][v]} for r in rows for v in ("A1w", "A2w", "A2w_inc")]
ids = {r["item_id"] for r in rows}
NOME = {"A1_pipeline": "A1_artigo", "A2_pipeline_verif": "A2_artigo"}
reg += [{"item_id": j["item_id"], "versao": NOME[j["condition"]], "palavras": j["n_palavras"], **j["texto"]}
        for j in read_jsonl(ROOT / "outputs" / "judgments_abs.jsonl")
        if j["rep"] == 0 and j["condition"] in NOME and j["item_id"] in ids]
df = pd.DataFrame(reg)

tab = df.groupby("versao").agg(
    n=("item_id", "size"), incorretas=("afirmacoes_incorretas", "mean"),
    frac_com_incorreta=("afirmacoes_incorretas", lambda s: (s > 0).mean()),
    correcao=("correcao_conceitual", "mean"), fidelidade=("fidelidade_gabarito", "mean"),
    utilidade=("utilidade_pedagogica", "mean"), foco=("foco_na_lacuna", "mean"), palavras=("palavras", "mean"),
    frac_reescrito=("reescrito", "mean")).reindex(VERS)

cont = Counter(c.get("veredito") for r in rows for c in r["claims"])
tot = max(1, sum(cont.values()))
ver = pd.DataFrame([{"veredito": k, "n": n, "prop": n / tot, "por_texto": n / len(rows)} for k, n in cont.most_common()])

piv = df.pivot_table(index="item_id", columns="versao", values=DIMS)
grupos = pd.Series(QUESTAO)
contr = []
for x, y in [("A2w", "A1w"), ("A2w_inc", "A1w"), ("A1w", "A1_artigo")]:
    for dm in DIMS:
        if (dm, x) not in piv or (dm, y) not in piv:
            continue
        c = cluster_ci(piv[(dm, x)] - piv[(dm, y)], grupos)
        contr.append({"contraste": f"{x} - {y}", "dimensao": dm, "diff": c["est"], "ic_lo": c["lo"], "ic_hi": c["hi"],
                      "p_boot": c["p_boot"], "n": c["n"], "n_questoes": c["n_questoes"]})
contr = pd.DataFrame(contr)

tab.to_csv(RES / "rq4w_condicoes.csv", encoding="utf-8")
ver.to_csv(RES / "rq4w_vereditos.csv", index=False, encoding="utf-8")
contr.to_csv(RES / "rq4w_contrastes.csv", index=False, encoding="utf-8")

with pd.option_context("display.width", 200, "display.max_columns", 20, "display.precision", 3):
    print(f"\n== {len(rows)} itens concluidos; medias por versao (juiz Gemini; *_artigo = GPT-4o mini nos mesmos itens)")
    print(tab)
    print("\n== vereditos do verificador nos textos A1w (artigo: 46% sup / 39% cg / 14% nao_sup / 0,13% inc)")
    print(ver)
    print("\n== contrastes pareados, IC por bootstrap de questao")
    print(contr)

if not a.mock:
    time.sleep(5)  # o painel do OpenRouter demora alguns segundos para contabilizar
    depois = gasto_real()
    real = f"US$ {depois - antes:.4f}" if (antes is not None and depois is not None) else "indisponivel"
    print(f"\ngasto estimado nesta execucao: US$ {GASTO['usd']:.4f} em {GASTO['chamadas']} chamadas | gasto real da chave: {real}")
