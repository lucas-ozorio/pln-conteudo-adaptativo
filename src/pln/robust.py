"""Biblioteca da rodada de robustez (PRE_REGISTRO.md): geração de variantes, juízes extras e trava de saldo."""
from __future__ import annotations

import json
import os
import random
import urllib.request
from pathlib import Path

from . import judge as J
from . import pipeline as PL
from . import prompts as P
from . import prompts_robust as PR
from .common import JsonlAppender, ROOT, pmap, read_jsonl
from .llm import LLM

# US$ por 1M de tokens (entrada, saída), conferidos em 2026-11-16/24 na lista de modelos do OpenRouter
PRICES = {
    "openai/gpt-4o-mini": (0.15, 0.60),
    "google/gemini-2.5-flash": (0.30, 2.50),
    "anthropic/claude-haiku-5.5": (0.10, 0.50),
    "deepseek/deepseek-v4-flash": (0.09, 0.18),
    "meta-llama/llama-3.1-8b-instruct": (0.10, 0.20),  # teto conservador
}


class RobustLLM(LLM):
    """LLM do projeto com cache e registro de uso ISOLADOS em cache_robust/ e outputs_robust/ e com 'semente' (rep_base)."""

    def __init__(self, role: str, cfg: dict, tag: str | None = None, rep_base: int = 0, mock: bool = False):
        super().__init__(role, cfg)
        self.role = tag or role
        self.rep_base = rep_base
        outdir = ROOT / ("outputs_robust_mock" if mock else "outputs_robust")
        self.cache_path = ROOT / ("cache_robust_mock" if mock else "cache_robust") / f"{self.role}_{self.kind}.jsonl"
        self.usage_path = outdir / "usage.jsonl"
        self._cache = {}
        if self.cache_path.exists():
            for line in self.cache_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    r = json.loads(line)
                    self._cache[r["k"]] = r["v"]

    def text(self, system: str, user: str, task: str, rep: int = 0) -> str:
        return super().text(system, user, task, rep + self.rep_base)

    def json(self, system: str, user: str, task: str, rep: int = 0) -> dict:
        return super().json(system, user, task, rep + self.rep_base)


# ------------------------------------------------------------------ saldo e custo
def remaining_usd() -> float | None:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return None
    req = urllib.request.Request("https://openrouter.ai/api/v1/credits", headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)["data"]
    return float(d["total_credits"]) - float(d["total_usage"])


def guard(min_left: float = 0.5, mock: bool = False) -> None:
    if mock:
        return
    r = remaining_usd()
    print(f"[saldo] US$ {r:.2f}" if r is not None else "[saldo] desconhecido")
    if r is not None and r < min_left:
        raise SystemExit(f"Saldo US$ {r:.2f} abaixo do mínimo US$ {min_left:.2f}: parando (PRE_REGISTRO.md).")


def spent_usd(path: Path) -> float:
    tot = 0.0
    if not Path(path).exists():
        return tot
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        p = PRICES.get(d.get("model"), (0.10, 0.20))
        tot += (d.get("in", 0) * p[0] + d.get("out", 0) * p[1]) / 1e6
    return tot


# ------------------------------------------------------------------ dados
def _rep(res: list, name: str) -> list:
    errs = [r for r in res if isinstance(r, dict) and "_error" in r]
    print(f"[{name}] itens={len(res)} erros={len(errs)}" + (f" | ex.: {errs[0]['_error'][:200]}" if errs else ""), flush=True)
    return res


def load_items(path: Path) -> dict[str, dict]:
    return {r["item_id"]: r for r in read_jsonl(path)}


def build_grade3(cfg: dict, per_question: int = 4) -> list[dict]:
    """60 respostas nota 3 (4 por questão) sorteadas do diag_set (disjuntas do piloto, que só tem notas 0-2)."""
    diag = [r for r in read_jsonl(ROOT / "data" / "processed" / "diag_set.jsonl") if r["grade"] == 3]
    rng = random.Random(cfg["seed"])
    out = []
    for qid in sorted({r["question_id"] for r in diag}):
        pool = sorted([r for r in diag if r["question_id"] == qid], key=lambda r: r["item_id"])
        rng.shuffle(pool)
        out += pool[:per_question]
    return out


def diag_map(path: Path) -> dict[str, dict]:
    return {r["item_id"]: r["diag"] for r in read_jsonl(path)}


# ------------------------------------------------------------------ geração de variantes
def make_material(it: dict, cond: str, m: dict) -> dict:
    return {"item_id": it["item_id"], "condition": cond, "texto": m["texto"], "questoes": m.get("questoes", []),
            "n_palavras": len(m["texto"].split()), "diag": m.get("diag")}


def gen_nodiag(llms, it, cfg) -> dict:
    """A1ø: mesmos prompts de texto e de questões do A1; o diagnóstico vira um aviso vazio."""
    lo, hi = cfg["pipeline"]["support_words"]
    u = P.fill(P.SUPPORT_USER, PERGUNTA=it["question"], REFS=P.fmt_refs(it["refs"]), RESPOSTA=it["answer"],
               DIAG=PR.NODIAG_DIAG, MIN=lo, MAX=hi)
    texto = llms["generator"].text(P.SUPPORT_SYSTEM, u, task="support")
    qs = PL.gen_questions(llms["generator"], it, cfg, True, texto, [PR.NODIAG_LACUNAS])
    return {"texto": texto, "questoes": qs}


def generate(items: list[dict], cfg: dict, out_path: Path, llms: dict, conds: list[str], tag: str, diags: dict | None,
             static_src: dict | None = None, workers: int = 6, desc: str = "") -> list[dict]:
    """Gera os materiais das condições 'conds' (A1_pipeline, A0_direto, S_estatico, A1_nodiag) com sufixo @tag.

    static_src: {question_id: material} para reaproveitar o S existente (itens nota 3). Retomável por (item_id, condition).
    """
    from .data import load_questions

    sink = JsonlAppender(out_path)
    done = {(r["item_id"], r["condition"]) for r in read_jsonl(out_path)}
    name = lambda c: c if not tag else f"{c}@{tag}"  # noqa: E731
    qs = load_questions()
    static = dict(static_src or {})
    if "S_estatico" in conds and not static_src:
        for qid in sorted({it["question_id"] for it in items}):
            if (f"static_q{qid}", name("S_estatico")) not in done:
                static[qid] = PL.static_for_question(llms, qs[qid], cfg)
                sink.add({"item_id": f"static_q{qid}", "condition": name("S_estatico"), **static[qid],
                          "n_palavras": len(static[qid]["texto"].split())})
            else:
                r = next(x for x in read_jsonl(out_path) if x["item_id"] == f"static_q{qid}" and x["condition"] == name("S_estatico"))
                static[qid] = {"texto": r["texto"], "questoes": r["questoes"]}

    def run(it):
        a1 = None
        rows = []
        for c in conds:
            if (it["item_id"], name(c)) in done:
                continue
            if c == "S_estatico":
                m = static[it["question_id"]]
            elif c == "A0_direto":
                m = PL.cond_A0(llms, it, cfg)
            elif c == "A1_pipeline":
                a1 = a1 or PL.cond_A1(llms, it, cfg, (diags or {}).get(it["item_id"]))
                m = a1
            elif c == "A1_nodiag":
                m = gen_nodiag(llms, it, cfg)
            else:
                raise ValueError(c)
            row = make_material(it, name(c), m)
            sink.add(row)
            rows.append(row)
        return rows

    return _rep(pmap(run, items, workers, desc or f"gerar {tag}"), desc or f"gerar {tag}")


# ------------------------------------------------------------------ juízes
def all_materials(*paths: Path) -> dict[tuple[str, str], dict]:
    mats = {}
    for p in paths:
        for r in read_jsonl(p):
            mats[(r["item_id"], r["condition"])] = r
    return mats


def run_abs(llm, jtag: str, items: dict, mats: dict, keys: list[tuple[str, str]], out_path: Path, with_questions: bool,
            workers: int, mode: str = "abs") -> list:
    """Juiz absoluto padrão (vê a resposta do aluno) ou 'blind' (não vê) sobre os (item, condição) pedidos."""
    sink = JsonlAppender(out_path)
    done = {(r["judge"], r["mode"], r["item_id"], r["condition"]) for r in read_jsonl(out_path)}
    todo = [k for k in keys if (jtag, mode, k[0], k[1]) not in done and k in mats]

    def run(k):
        iid, cond = k
        it, m = items[iid], mats[k]
        row = {"judge": jtag, "mode": mode, "item_id": iid, "condition": cond}
        if mode == "abs":
            row["texto"] = J.judge_text(llm, it, m["texto"])
            row["questoes"] = J.judge_questions(llm, it, m["questoes"]) if (with_questions and m["questoes"]) else []
        elif mode == "blind":
            u = P.fill(PR.JUDGE_BLIND_USER, PERGUNTA=it["question"], REFS=P.fmt_refs(it["refs"]), TEXTO=m["texto"])
            r = llm.json(PR.JUDGE_SYSTEM, u, task="judge_blind")
            row["texto"] = {d: _clip(r.get(d)) for d in ("coerencia", "correcao_conceitual", "fidelidade_gabarito", "completude",
                                                          "adequacao_nivel", "qualidade_geral")}
            row["texto"]["afirmacoes_incorretas"] = _nonneg(r.get("afirmacoes_incorretas"))
        elif mode == "overrem":
            u = P.fill(PR.JUDGE_OVERREM_USER, PERGUNTA=it["question"], REFS=P.fmt_refs(it["refs"]), RESPOSTA=it["answer"], TEXTO=m["texto"])
            r = llm.json(PR.JUDGE_SYSTEM, u, task="judge_overrem")
            row["texto"] = {d: _clip(r.get(d)) for d in ("reconhece_acertos", "sobre_remediacao", "coerencia", "correcao_conceitual",
                                                          "fidelidade_gabarito", "utilidade_pedagogica")}
        else:
            raise ValueError(mode)
        sink.add(row)
        return row

    return _rep(pmap(run, todo, workers, f"{jtag}:{mode}"), f"{jtag}:{mode}")


def run_pairs(llm, jtag: str, items: dict, mats: dict, pairs: list[tuple[str, str]], item_ids: list[str], out_path: Path,
              workers: int) -> list:
    sink = JsonlAppender(out_path)
    done = {(r["judge"], r["item_id"], r["x"], r["y"], r["order"]) for r in read_jsonl(out_path)}
    todo = [(i, x, y, o) for i in item_ids for (x, y) in pairs for o in ("xy", "yx")
            if (jtag, i, x, y, o) not in done and (i, x) in mats and (i, y) in mats]

    def run(job):
        iid, x, y, order = job
        first, second = (mats[(iid, x)], mats[(iid, y)]) if order == "xy" else (mats[(iid, y)], mats[(iid, x)])
        v = J.judge_pair(llm, items[iid], first, second)
        win = "empate" if v == "empate" else ((x if v == "A" else y) if order == "xy" else (y if v == "A" else x))
        row = {"judge": jtag, "item_id": iid, "x": x, "y": y, "order": order, "raw": v, "winner": win, "pos_first_won": v == "A"}
        sink.add(row)
        return row

    return _rep(pmap(run, todo, workers, f"{jtag}:pares"), f"{jtag}:pares")


def _clip(x, lo=1, hi=5):
    try:
        return max(lo, min(hi, int(x)))
    except (TypeError, ValueError):
        return None


def _nonneg(x):
    try:
        return max(0, int(x))
    except (TypeError, ValueError):
        return None
