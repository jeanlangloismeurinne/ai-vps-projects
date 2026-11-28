"""Vérifie un relevé de BPA (sortie d'agent) : forme, nombre dans l'extrait, source non agrégateur,
et comparaison avec le chiffre ESEF (comparatif 2019 / 2020) stocké en base. Usage : verify.py fichier.json [esef.json]"""
import json
import re
import sys

BAD = ("zonebourse", "marketscreener", "boursorama", "macrotrends", "yahoo", "wikipedia", "investing.com",
       "abcbourse", "boursier.com", "statista", "stockanalysis", "companiesmarketcap")
d = json.load(open(sys.argv[1]))
esef = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else {}


def forms(v):
    a = abs(v)
    out = set()
    for nd in (0, 1, 2, 3):
        s = f"{a:.{nd}f}"
        if float(s) == round(a, nd) and abs(float(s) - a) < 1e-9:
            out |= {s, s.replace(".", ",")}
    return out


tot = {"rows": 0, "found": 0, "null": 0, "bad": 0}
for sym, rows in d.items():
    years = sorted(r["fy_end"][:4] for r in rows)
    probs = []
    if years != [str(y) for y in range(2010, 2021)] and not (sym == "RI.PA"):
        probs.append(f"exercices {years}")
    for r in rows:
        tot["rows"] += 1
        if r.get("eps") is None:
            tot["null"] += 1
            continue
        tot["found"] += 1
        ex = (r.get("excerpt") or "").replace(" ", " ").replace(" ", " ")
        if not any(f in ex for f in forms(r["eps"])):
            probs.append(f"{r['fy_end'][:4]} {r['eps']} absent de l'extrait « {ex[:80]} »")
        u = (r.get("url") or "").lower()
        if not u or (any(b in u for b in BAD) and not u.endswith(".pdf")):
            probs.append(f"{r['fy_end'][:4]} source refusée {u[:80]}")
        if not re.match(r"^\d{4}-\d{2}(-\d{2})?$", r.get("published") or ""):
            probs.append(f"{r['fy_end'][:4]} date de publication {r.get('published')}")
        elif (r["published"][:7]) <= r["fy_end"][:7]:
            probs.append(f"{r['fy_end'][:4]} publié {r['published']} avant la clôture")
        if r.get("from_comparative"):
            probs.append(f"{r['fy_end'][:4]} pris d'un comparatif ({r.get('doc')})")
        ev = esef.get(sym, {}).get(r["fy_end"][:7])
        if ev is not None and ev[1] == r.get("cur") and abs(ev[0] - r["eps"]) > 0.05 * max(abs(ev[0]), 0.01):
            probs.append(f"{r['fy_end'][:4]} écart ESEF : relevé {r['eps']} / ESEF {ev[0]}")
        elif ev is not None:
            probs.append(f"{r['fy_end'][:4]} = ESEF ok ({r['eps']} / {ev[0]})")
    tot["bad"] += sum("ok" not in p and "comparatif" not in p for p in probs)
    nn = sum(r.get("eps") is None for r in rows)
    print(f"{sym}: {len(rows) - nn} trouvés, {nn} nuls")
    for p in probs:
        print("   ", p)
print(tot)
