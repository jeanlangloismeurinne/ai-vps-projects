import glob, json, sys, os

d = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(__file__) + "/banc"


def _parse(raw):
    try:
        return json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
    except Exception:
        return None


for f in sorted(glob.glob(f"{d}/*.json")):
    r = json.load(open(f))
    tag = os.path.basename(f)[:-5]
    print(f"\n### {tag} — {r['etat']}  (in {r.get('tokens_in')}, out {r.get('tokens_out')})")
    a = r.get("architecture")
    if r["etat"] != "acceptee":
        print("   MOTIF :", (r.get("motif") or "")[:500].replace("\n", " "))
        s = r.get("sorties") or []
        a = _parse(s[-1][0]) if s else None
        if a: print("   (dernière sortie refusée :)")
    if not a:
        continue
    blocs = {b["id"]: b for b in a.get("blocs", [])}
    for i in a.get("inventaire_des_programmes", []):
        b = blocs.get(i.get("bloc")) or {}
        print(f"   · {i.get('programme')!s:45.45} → {i.get('traitement'):10} {i.get('bloc')!s:28.28} [{b.get('statut','')}] {(i.get('motif') or '')[:110]}")
    for b in a.get("blocs", []):
        if b.get("plateforme"):
            print(f"   ▪ plateforme {b['id']} : {b.get('nombre_de_programmes_non_nommes')} non nommé(s) — {(b.get('motif') or '')[:120]}")
