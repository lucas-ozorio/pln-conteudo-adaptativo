import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pln.common import ROOT, load_config  # noqa: E402


def parse(desc: str, extra=None):
    ap = argparse.ArgumentParser(description=desc)
    ap.add_argument("--mock", action="store_true", help="usa LLM sintético (testa o encanamento, sem chave, sem custo)")
    ap.add_argument("--limit", type=int, default=0, help="usa só N itens (smoke test)")
    ap.add_argument("--config", default=None)
    if extra:
        extra(ap)
    a = ap.parse_args()
    cfg = load_config(a.config, mock=a.mock)
    out = ROOT / ("outputs_mock" if a.mock else "outputs")
    out.mkdir(exist_ok=True)
    return a, cfg, out
