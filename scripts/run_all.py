"""Roda E0 -> E1 (geração, juiz) -> E3 -> análise. Repassa --mock/--limit. Retomável (cache + jsonl)."""
import subprocess
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
args = sys.argv[1:]
steps = ["00_prepare_data.py", "01_diagnosis.py", "02_generate.py", "03_judge.py", "04_student_sim.py", "05_analyze.py"]
for s in steps:
    print(f"\n=== {s} ===", flush=True)
    r = subprocess.run([sys.executable, str(here / s), *args])
    if r.returncode != 0:
        sys.exit(f"falhou em {s}")
