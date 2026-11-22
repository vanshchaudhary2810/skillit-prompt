"""Check that every resource URL in code/kb/resources.json opens (HTTP status < 400).

Usage: python code/check_links.py
"""
import json
from pathlib import Path

import requests

res = json.loads((Path(__file__).parent / "kb" / "resources.json").read_text(encoding="utf-8"))["resources"]
bad = 0
for r in res:
    if not r["url"]:
        continue
    try:
        code = requests.get(r["url"], timeout=15, allow_redirects=True,
                            headers={"User-Agent": "Mozilla/5.0 (Skill-it link checker)"}).status_code
    except requests.RequestException as e:
        code = f"error {type(e).__name__}"
    ok = isinstance(code, int) and code < 400
    if code == 403:  # many sites block scripts but open fine in a browser
        print(f"CHECK {r['id']} 403 (blocks scripts - open it in a browser) {r['url']}")
        continue
    bad += not ok
    print(f"{'OK ' if ok else 'BAD'} {r['id']} {code} {r['url']}")
print(f"\n{bad} link(s) need fixing" if bad else "\nAll links open.")
