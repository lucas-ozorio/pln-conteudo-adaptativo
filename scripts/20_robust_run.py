"""Rodada de robustez (PRE_REGISTRO.md). Etapas retomáveis; cada uma checa o saldo antes de gastar.

Etapas de geração:  gen_nodiag | gen_v2 | gen_s1 | gen_s2 | gen_g2 | gen_g3
Etapas de juízes:   judge2_pilot | blind_pilot | judge_new | judge_seeds | judge_g3
Ex.: python scripts/20_robust_run.py --stage gen_nodiag,gen_v2 --mock --limit 6
"""
from _common import parse
from pln import robust as R
from pln.common import ROOT, read_jsonl, write_jsonl

STAGES = ["gen_nodiag", "gen_v2", "gen_s1", "gen_s2", "gen_g2", "gen_g3",
          "judge2_pilot", "blind_pilot", "judge_new", "judge_seeds", "judge_g3"]


def extra(ap):
    ap.add_argument("--stage", required=True, help="lista separada por vírgula: " + ", ".join(STAGES))
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--min-saldo", type=float, default=0.5)


a, cfg, _ = parse(__doc__, extra)
MOCK = a.mock
OUT = ROOT / ("outputs_robust_mock" if MOCK else "outputs_robust")
OUT.mkdir(exist_ok=True)
W = a.workers or cfg["runtime"]["workers"]
PROC = ROOT / "data" / "processed"
pilot = read_jsonl(PROC / "pilot_set.jsonl")
if a.limit:
    pilot = pilot[: a.limit]
g3path = PROC / "grade3_set.jsonl"
if not g3path.exists():
    write_jsonl(g3path, R.build_grade3(cfg))
grade3 = read_jsonl(g3path)
if a.limit:
    grade3 = grade3[: a.limit]
items_all = {**{r["item_id"]: r for r in read_jsonl(PROC / "pilot_set.jsonl")}, **{r["item_id"]: r for r in read_jsonl(g3path)}}
V0 = R.diag_map(ROOT / "outputs" / "diagnosis.jsonl") if not MOCK else R.diag_map(ROOT / "outputs_mock" / "diagnosis.jsonl")
V2 = R.diag_map(ROOT / "outputs" / "h02" / "diagnosis_v2_fewshot_cross_q.jsonl")
MATS_PILOT = ROOT / "outputs" / "materials.jsonl"
MATS_NEW = OUT / "materials.jsonl"
MATS_G3 = OUT / "materials_grade3.jsonl"
JOUT = OUT / "judgments_abs.jsonl"
POUT = OUT / "judgments_pair.jsonl"
CONDS5 = cfg["pipeline"]["conditions"]


def llm(role, tag=None, rep=0):
    return R.RobustLLM(role, cfg, tag=tag, rep_base=rep, mock=MOCK)


def judges():
    return {"J1": llm("judge", "judge1"), "J2": llm("judge2", "judge2")}


for st in [s.strip() for s in a.stage.split(",") if s.strip()]:
    assert st in STAGES, st
    R.guard(a.min_saldo, MOCK)
    print(f"\n=== {st} ===", flush=True)
    if st == "gen_nodiag":
        R.generate(pilot, cfg, MATS_NEW, {"generator": llm("generator", "generator_nodiag")}, ["A1_nodiag"], "", None, workers=W, desc=st)
    elif st == "gen_v2":
        R.generate(pilot, cfg, MATS_NEW, {"generator": llm("generator", "generator_v2")}, ["A1_pipeline"], "v2", V2, workers=W, desc=st)
    elif st in ("gen_s1", "gen_s2"):
        rep = int(st[-1])
        R.generate(pilot, cfg, MATS_NEW, {"generator": llm("generator", f"generator_s{rep}", rep)},
                   ["S_estatico", "A0_direto", "A1_pipeline"], f"s{rep}", V0, workers=W, desc=st)
    elif st == "gen_g2":
        R.generate(pilot, cfg, MATS_NEW, {"generator": llm("generator2", "generator2")},
                   ["S_estatico", "A0_direto", "A1_pipeline"], "g2", V0, workers=W, desc=st)
    elif st == "gen_g3":
        pm = R.all_materials(MATS_PILOT)
        static_src = {}
        for it in read_jsonl(PROC / "pilot_set.jsonl"):
            m = pm.get((it["item_id"], "S_estatico"))
            if m:
                static_src[it["question_id"]] = {"texto": m["texto"], "questoes": m["questoes"]}
        R.generate(grade3, cfg, MATS_G3, {"generator": llm("generator", "generator_g3")}, ["S_estatico", "A0_direto", "A1_pipeline"],
                   "", V0, static_src=static_src, workers=W, desc=st)
    elif st == "judge2_pilot":
        mats = R.all_materials(MATS_PILOT)
        keys = [(it["item_id"], c) for it in pilot for c in CONDS5]
        j2 = judges()["J2"]
        R.run_abs(j2, "J2", items_all, mats, keys, JOUT, True, W)
        R.run_pairs(j2, "J2", items_all, mats, [tuple(p) for p in cfg["judge"]["pairs"][:2]], [it["item_id"] for it in pilot], POUT, W)
    elif st == "blind_pilot":
        mats = R.all_materials(MATS_PILOT)
        keys = [(it["item_id"], c) for it in pilot for c in CONDS5]
        for jt, j in judges().items():
            R.run_abs(j, jt, items_all, mats, keys, JOUT, False, W, mode="blind")
    elif st == "judge_new":
        mats = R.all_materials(MATS_PILOT, MATS_NEW)
        ids = [it["item_id"] for it in pilot]
        keys = [(i, c) for i in ids for c in ("A1_nodiag", "A1_pipeline@v2")]
        pairs = [("A1_nodiag", "A1_pipeline"), ("A1_pipeline@v2", "A1_pipeline")]
        for jt, j in judges().items():
            R.run_abs(j, jt, items_all, mats, keys, JOUT, True, W)
            R.run_pairs(j, jt, items_all, mats, pairs, ids, POUT, W)
    elif st == "judge_seeds":
        mats = R.all_materials(MATS_NEW)
        ids = [it["item_id"] for it in pilot]
        conds = [f"{c}@{t}" for t in ("s1", "s2", "g2") for c in ("S_estatico", "A0_direto", "A1_pipeline")]
        keys = [(i, c) for i in ids for c in conds]
        J = judges()
        R.run_abs(J["J1"], "J1", items_all, mats, keys, JOUT, False, W)  # sementes e G2: juiz principal
        R.run_abs(J["J2"], "J2", items_all, mats, [k for k in keys if k[1].endswith("@g2")], JOUT, False, W)  # G2 tambem no juiz 2 (custo)
    elif st == "judge_g3":
        mats = R.all_materials(MATS_G3)
        keys = [(it["item_id"], c) for it in grade3 for c in ("S_estatico", "A0_direto", "A1_pipeline")]
        for jt, j in judges().items():
            R.run_abs(j, jt, items_all, mats, keys, JOUT, True, W)
            R.run_abs(j, jt, items_all, mats, keys, JOUT, False, W, mode="overrem")
    print(f"gasto acumulado (estimado, esta rodada): US$ {R.spent_usd(OUT / 'usage.jsonl'):.3f}")
