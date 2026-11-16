"""Baixa o PT-ASAG 2018 v2.0 (Kaggle: lucasbgalhardi/pt-asag-2018, CC BY-NC-SA 4.0) para data/raw/.
O dataset NÃO é redistribuído neste repositório (licença NC-SA e respostas de menores de idade)."""
import io
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "https://www.kaggle.com/api/v1/datasets/download/lucasbgalhardi/pt-asag-2018"
dest = ROOT / "data" / "raw"
dest.mkdir(parents=True, exist_ok=True)
with urllib.request.urlopen(URL, timeout=120) as r:
    z = zipfile.ZipFile(io.BytesIO(r.read()))
inner = "PT_ASAG_2018_v2.0/PT_ASAG_2018_v2.0/"
for n in z.namelist():
    if n.startswith(inner) and n.endswith(".csv"):
        out = dest / "PT_ASAG_2018_v2.0" / Path(n).name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(z.read(n))
if "LICENSE.txt" in z.namelist():
    (dest / "LICENSE_PT-ASAG.txt").write_bytes(z.read("LICENSE.txt"))
print("ok ->", dest / "PT_ASAG_2018_v2.0", sorted(p.name for p in (dest / "PT_ASAG_2018_v2.0").iterdir()))
