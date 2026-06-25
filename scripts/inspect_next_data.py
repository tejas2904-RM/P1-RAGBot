import json
import re
import sys
from pathlib import Path

scheme = sys.argv[1] if len(sys.argv) > 1 else "hdfc-mid-cap"
html = Path(f"corpus/raw/{scheme}.html").read_text(encoding="utf-8")
match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
if not match:
    raise SystemExit("no __NEXT_DATA__")

data = json.loads(match.group(1))
mf = data["props"]["pageProps"]["mfServerSideData"]
for key in sorted(mf):
    if "lump" in key.lower():
        print(key, "=", mf.get(key))
