"""Monta as amostras estratificadas (questão x nota) a partir do PT-ASAG. Sem LLM."""
from _common import parse
from pln.data import save_samples

a, cfg, out = parse(__doc__)
diag, pilot = save_samples(cfg)
import pandas as pd  # noqa: E402

for name, rows in (("diag_set (E0)", diag), ("pilot_set (E1/E3)", pilot)):
    df = pd.DataFrame(rows)
    print(f"\n{name}: {len(df)} respostas; palavras médias = {df.answer.str.split().str.len().mean():.1f}")
    print(pd.crosstab(df.question_id, df.grade, margins=True).to_string())
