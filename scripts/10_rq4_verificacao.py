"""RQ4 (offline) - O que a verificação A2 realmente fez? Sem chamadas de LLM.

1. Liga cada resposta do verificador no cache ao seu item (recomputando a chave do cache) e conta os vereditos por afirmação.
2. Compara A2 com A1 em todos os 180 itens e só nos textos REESCRITOS (nos demais, A2 = A1 e a diferença é 0 por construção).
3. Mede a concordância entre o verificador e o juiz, e o piso de falso positivo do juiz (afirmações "incorretas" no próprio gabarito, S0).
4. Exporta uma planilha CEGA de auditoria manual de afirmações; com --auditoria <csv preenchido>, calcula a precisão do verificador.

Saídas: results/rq4_*.csv, paper/tables/tab_rq4.tex, human_eval/auditoria_afirmacoes.csv (+ chave separada; ambos gitignored).
"""
import hashlib
import json
import random
import re
import warnings

import numpy as np
import pandas as pd
from scipy import stats

from _common import parse
from pln import prompts as P
from pln.common import ROOT, read_jsonl
from pln.data import norm
from pln.judge import TEXT_DIMS
from pln.llm import extract_json
from pln.stats import cluster_boot, cluster_ci, holm, wilson


def extra(ap):
    ap.add_argument("--auditoria", default=None, help="planilha de auditoria preenchida (coluna 'rotulo')")
    ap.add_argument("--n-auditoria", type=int, default=50)


a, cfg, out = parse(__doc__, extra)
warnings.filterwarnings("ignore", category=stats.ConstantInputWarning)  # reamostras com nota constante viram NaN e são descartadas
RES = ROOT / "results"
TAB = ROOT / "paper" / "tables"
HE = ROOT / "human_eval"
VEREDITOS = ["suportada", "conhecimento_geral_correto", "nao_suportada", "incorreta"]
# rótulos da auditoria manual: nao_factual = frase sem conteúdo científico (ex.: encorajamento), que o verificador também marca
ROTULOS = ["correta", "incorreta", "duvidosa", "nao_factual"]

items = {r["item_id"]: r for r in read_jsonl(ROOT / "data" / "processed" / "pilot_set.jsonl")}
if not items:
    raise SystemExit("rode antes: python scripts/00_prepare_data.py (precisa de data/raw)")
mats = read_jsonl(out / "materials.jsonl")
A1 = {m["item_id"]: m for m in mats if m["condition"] == "A1_pipeline"}
A2 = {m["item_id"]: m for m in mats if m["condition"] == "A2_pipeline_verif"}
qmap = pd.Series({i: it["question_id"] for i, it in items.items()})

# ------------------------------------------------------------------ 1. afirmações do verificador (cache)
mv = cfg["models"]["verifier"]
kind = cfg["providers"][mv["provider"]]["kind"]
cache = {r["k"]: r["v"] for r in read_jsonl(ROOT / "cache" / f"verifier_{kind}.jsonl")}


def cache_key(user: str) -> str:  # idêntico a LLM._key (src/pln/llm.py), sem instanciar o cliente
    raw = json.dumps([kind, mv["name"], mv.get("temperature", 0.0), P.VERIFY_SYSTEM, user, 0], ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


claims, faltando = [], []
for iid, m in A1.items():
    it = items[iid]
    u = P.fill(P.VERIFY_USER, REFS=P.fmt_refs(it["refs"]), CONCEITOS=P.fmt_concepts(it["concepts"]), TEXTO=m["texto"])
    k = cache_key(u)
    if k not in cache:
        faltando.append(iid)
        continue
    for j, c in enumerate(extract_json(cache[k]).get("afirmacoes", [])):
        claims.append({"item_id": iid, "question_id": it["question_id"], "j": j, "afirmacao": c.get("afirmacao", ""),
                       "veredito": c.get("veredito", ""), "motivo": c.get("motivo", "")})
C = pd.DataFrame(claims)
print(f"cache do verificador: {len(A1) - len(faltando)}/{len(A1)} itens casados; {len(C)} afirmações")

# contagem por texto (zeros incluídos) e IC por questão
cnt = C.pivot_table(index="item_id", columns="veredito", values="j", aggfunc="count").reindex(list(A1)).fillna(0)
for v in VEREDITOS:
    if v not in cnt:
        cnt[v] = 0.0
cnt["total"] = cnt[VEREDITOS].sum(axis=1)
cnt["problemas"] = cnt["nao_suportada"] + cnt["incorreta"]
vrows = []
for v in VEREDITOS + ["problemas", "total"]:
    r = cluster_ci(cnt[v], qmap)
    vrows.append({"veredito": v, "n_total": int(cnt[v].sum()), "prop_das_afirmacoes": cnt[v].sum() / cnt["total"].sum(),
                  "media_por_texto": r["est"], "ic_lo": r["lo"], "ic_hi": r["hi"],
                  "textos_com_ao_menos_1": (cnt[v] > 0).mean()})
V = pd.DataFrame(vrows)
V.to_csv(RES / "rq4_vereditos.csv", index=False)

# ------------------------------------------------------------------ 2. A2 vs A1 (todos x só reescritos)
J = pd.read_csv(RES / "e1_juiz_absoluto_por_item.csv")
reesc = pd.Series({i: bool(A2[i]["verif"]["reescrito"]) for i in A2})
identico = pd.Series({i: A2[i]["texto"] == A1[i]["texto"] and A2[i]["questoes"] == A1[i]["questoes"] for i in A2})
assert (identico == ~reesc).all(), "esperado: A2 idêntico a A1 exatamente quando não reescrito"
dims = TEXT_DIMS + ["afirmacoes_incorretas", "n_palavras"]
rows = []
for sub, ids in (("todos", list(A2)), ("reescritos", list(reesc[reesc].index))):
    for dm in dims:
        w = J.pivot(index="item_id", columns="condition", values=dm).reindex(ids)
        r = cluster_ci(w["A2_pipeline_verif"] - w["A1_pipeline"], qmap)
        rows.append({"subconjunto": sub, "dimensao": dm, "A1": w["A1_pipeline"].mean(), "A2": w["A2_pipeline_verif"].mean(),
                     "diff": r["est"], "ic_lo": r["lo"], "ic_hi": r["hi"], "p_boot": r["p_boot"], "n": r["n"], "n_questoes": r["n_questoes"]})
D = pd.DataFrame(rows)
fam = (D.subconjunto == "reescritos") & D.dimensao.isin(TEXT_DIMS)  # família exploratória da RQ4 (6 dimensões)
D.loc[fam, "p_holm"] = holm(D.loc[fam, "p_boot"].values)
D.to_csv(RES / "rq4_a2_vs_a1.csv", index=False)

# ------------------------------------------------------------------ par-a-par A2 x A1: reescritos x idênticos
pw = pd.DataFrame(read_jsonl(out / "judgments_pair.jsonl"))
pw = pw[(pw.x == "A2_pipeline_verif") & (pw.y == "A1_pipeline")]
prow = []
for sub, ids in (("reescritos", set(reesc[reesc].index)), ("identicos (nao reescritos)", set(reesc[~reesc].index))):
    g = pw[pw.item_id.isin(ids)]
    per = g.groupby("item_id").winner.agg(list)
    xw = per.map(lambda ws: all(w == "A2_pipeline_verif" for w in ws)).sum()
    yw = per.map(lambda ws: all(w == "A1_pipeline" for w in ws)).sum()
    nt = g[g.winner != "empate"]
    prow.append({"subconjunto": sub, "itens": len(per), "A2_vence_nas_duas": xw / len(per), "A1_vence_nas_duas": yw / len(per),
                 "inconsistente_ou_empate": 1 - (xw + yw) / len(per), "empate_julgamentos": (g.winner == "empate").mean(),
                 "primeiro_vence(nao_empates)": nt.pos_first_won.mean() if len(nt) else np.nan,
                 "p_sinal_robustas": stats.binomtest(int(xw), int(xw + yw), 0.5).pvalue if xw + yw else np.nan})
PW = pd.DataFrame(prow)
PW.to_csv(RES / "rq4_pareado_reescritos.csv", index=False)

# ------------------------------------------------------------------ 3. verificador x juiz (textos A1) e piso do S0
ja1 = J[J.condition == "A1_pipeline"].set_index("item_id")
VJ = cnt.join(ja1[["correcao_conceitual", "fidelidade_gabarito", "afirmacoes_incorretas", "question_id"]])
crow = []
for vcol in ("problemas", "nao_suportada"):
    for jcol in ("correcao_conceitual", "fidelidade_gabarito"):  # incorretas do juiz em A1: só 1 texto > 0, correlação indefinida
        r = cluster_boot(VJ, "question_id", lambda s, v=vcol, j=jcol: stats.spearmanr(s[v], s[j]).statistic)
        crow.append({"verificador": vcol, "juiz": jcol, "spearman": r["est"], "ic_lo": r["lo"], "ic_hi": r["hi"], "n": r["n"]})
pd.DataFrame(crow).to_csv(RES / "rq4_verificador_vs_juiz.csv", index=False)

s0 = J[J.condition == "S0_gabarito"].set_index("item_id")
r_s0 = cluster_ci(s0.afirmacoes_incorretas, qmap)
s0_q = s0.groupby("question_id").afirmacoes_incorretas.mean()  # S0 é o MESMO texto para todos os itens da questão
juiz_inc_a1 = ja1[ja1.afirmacoes_incorretas > 0].index
resumo = {
    "afirmacoes_por_texto": cnt.total.mean(), "problemas_por_texto": cnt.problemas.mean(),
    "frac_reescritos": reesc.mean(), "n_reescritos": int(reesc.sum()),
    "palavras_A1_reescritos": J[(J.condition == "A1_pipeline") & J.item_id.isin(reesc[reesc].index)].n_palavras.mean(),
    "palavras_A2_reescritos": J[(J.condition == "A2_pipeline_verif") & J.item_id.isin(reesc[reesc].index)].n_palavras.mean(),
    "verif_incorretas_total": int(cnt.incorreta.sum()),
    "juiz_incorretas_A1_total": float(ja1.afirmacoes_incorretas.sum()),
    "juiz_incorretas_A1_itens_com_>=1": int(len(juiz_inc_a1)),
    "desses_verificador_marcou_algum_problema": int((cnt.loc[juiz_inc_a1, "problemas"] > 0).sum()),
    "S0_incorretas_por_texto": r_s0["est"], "S0_ic_lo": r_s0["lo"], "S0_ic_hi": r_s0["hi"],
    "S0_frac_itens_com_>=1": (s0.afirmacoes_incorretas > 0).mean(),
    "S0_questoes_com_alguma_marcacao": int((s0_q > 0).sum()),
    "S0_correcao_conceitual_media": s0.correcao_conceitual.mean(),
}
pd.Series(resumo).to_csv(RES / "rq4_resumo.csv", header=["valor"])

# ------------------------------------------------------------------ 4. auditoria manual (cega ao veredito)
rng = random.Random(cfg["seed"])
n_flag = round(a.n_auditoria * 0.6)
n_rest = a.n_auditoria - n_flag
pool_flag = C[C.veredito.isin(["nao_suportada", "incorreta"])]
pool_cg = C[C.veredito == "conhecimento_geral_correto"]
pool_sup = C[C.veredito == "suportada"]


def amostra(df, n):  # espalha pelas questões: round-robin entre questões embaralhadas
    by = {q: list(g.index) for q, g in df.groupby("question_id")}
    for v in by.values():
        rng.shuffle(v)
    qs = sorted(by)
    rng.shuffle(qs)
    out_ = []
    while len(out_) < n and any(by.values()):
        for q in qs:
            if by[q] and len(out_) < n:
                out_.append(by[q].pop())
    return out_


def contexto(afirmacao: str, texto: str) -> str:
    """Texto A1 inteiro com a frase de origem da afirmação marcada entre >>> <<< (resolve pronomes como "eles")."""
    frases = re.split(r"(?<=[.!?])\s+", texto.strip())
    alvo = set(norm(afirmacao).split())
    i = max(range(len(frases)), key=lambda k: (norm(afirmacao) in norm(frases[k]), len(alvo & set(norm(frases[k]).split()))))
    frases[i] = f">>> {frases[i]} <<<"
    return " ".join(frases)


inc = list(pool_flag[pool_flag.veredito == "incorreta"].index)  # todas as "incorretas" entram
sel = inc + amostra(pool_flag.drop(inc), n_flag - len(inc)) + amostra(pool_cg, n_rest // 2) + amostra(pool_sup, n_rest - n_rest // 2)
S = C.loc[sel].copy()
S["id_auditoria"] = [f"F{rng.randrange(10**5):05d}" for _ in range(len(S))]
S = S.sample(frac=1, random_state=cfg["seed"])
HE.mkdir(exist_ok=True)
plan = HE / "auditoria_afirmacoes.csv"
if not plan.exists():  # nunca sobrescreve uma planilha que pode já estar sendo preenchida
    pd.DataFrame({"id_auditoria": S.id_auditoria, "pergunta": [items[i]["question"] for i in S.item_id],
                  "gabarito": [" | ".join(items[i]["refs"]) for i in S.item_id], "afirmacao": S.afirmacao,
                  "rotulo": "", "comentario": "",
                  "texto_original": [contexto(f, A1[i]["texto"]) for f, i in zip(S.afirmacao, S.item_id)]}
                 ).to_csv(plan, index=False, encoding="utf-8-sig")
    S[["id_auditoria", "item_id", "question_id", "veredito", "motivo"]].to_csv(HE / "CHAVE_auditoria_NAO_ABRIR.csv", index=False, encoding="utf-8-sig")
    print(f"planilha de auditoria: {plan} ({len(S)} afirmações; rótulos: {' | '.join(ROTULOS)})")

if a.auditoria:
    # sep=None detecta "," ou ";" (o Excel em português salva CSV com ";")
    H = pd.read_csv(a.auditoria, sep=None, engine="python", encoding="utf-8-sig", dtype=str)
    H = H.merge(pd.read_csv(HE / "CHAVE_auditoria_NAO_ABRIR.csv", encoding="utf-8-sig"), on="id_auditoria")
    H["rotulo"] = H.rotulo.fillna("").map(lambda s: norm(s).replace(" ", "_"))  # "Não factual" -> "nao_factual"
    invalidos = H[~H.rotulo.isin(ROTULOS)]
    if len(invalidos):
        print(f"ATENÇÃO: {len(invalidos)} linha(s) sem rótulo válido (ignoradas):", invalidos.id_auditoria.tolist())
    H = H[H.rotulo.isin(ROTULOS)]
    H["grupo"] = np.where(H.veredito.isin(["nao_suportada", "incorreta"]), "marcada (nao_suportada/incorreta)", "aceita (" + H.veredito + ")")
    arows = []
    for g, s in H.groupby("grupo"):
        for rot in ROTULOS:
            p, lo, hi = wilson(int((s.rotulo == rot).sum()), len(s))
            arows.append({"grupo_verificador": g, "rotulo_humano": rot, "n": len(s), "prop": p, "ic_lo": lo, "ic_hi": hi})
    pd.DataFrame(arows).to_csv(RES / "rq4_auditoria.csv", index=False)
    print(pd.DataFrame(arows).to_string(index=False))

# ------------------------------------------------------------------ tabela do artigo
DIM = {"coerencia": "Coherence", "correcao_conceitual": "Conceptual correctness", "fidelidade_gabarito": "Faithfulness to reference",
       "foco_na_lacuna": "Gap focus", "utilidade_pedagogica": "Pedagogical usefulness", "adequacao_nivel": "Level adequacy",
       "afirmacoes_incorretas": "Incorrect claims (judge)", "n_palavras": "Words"}


def cell(sub, dm):
    r = D[(D.subconjunto == sub) & (D.dimensao == dm)].iloc[0]
    star = "*" if r.get("p_holm", 1) == r.get("p_holm", 1) and r.get("p_holm", 1) < 0.05 else ""
    f = "{:+.1f}" if dm == "n_palavras" else "{:+.2f}"
    g = "{:.1f}" if dm == "n_palavras" else "{:.2f}"
    return f"${f.format(r['diff'])}$ [{g.format(r.ic_lo)}, {g.format(r.ic_hi)}]{star}"


nr = int(reesc.sum())
lines = [r"\begin{tabular}{lcc}", r"\toprule", rf"A2$-$A1 & All items ($n{{=}}{len(A2)}$) & Rewritten only ($n{{=}}{nr}$) \\", r"\midrule"]
for dm in dims:
    lines.append(f"{DIM[dm]} & {cell('todos', dm)} & {cell('reescritos', dm)} \\\\")
lines += [r"\bottomrule", r"\end{tabular}"]
(TAB / "tab_rq4.tex").write_text("\n".join(lines), encoding="utf-8")

print(V[["veredito", "n_total", "prop_das_afirmacoes", "media_por_texto"]].to_string(index=False))
print(D[D.subconjunto == "reescritos"][["dimensao", "A1", "A2", "diff", "ic_lo", "ic_hi", "p_holm"]].to_string(index=False))
print(PW.to_string(index=False))
print(pd.Series(resumo).to_string())
