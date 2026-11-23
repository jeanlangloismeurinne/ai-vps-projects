"""Garde de la valeur du temps passé (`app/nasdaq/valeur.py`) : hors ligne.

Fixture RÉELLE (`fixtures/nasdaq_valeur/nvda_eps.json`, comptes SEC de Nvidia 2022-2025, deux divisions
d'actions dont une au milieu d'un exercice) : c'est le cas qui a cassé le premier essai — l'ajustement des
divisions APRÈS l'addition des trimestres mélangeait deux bases et allumait « plancher caduc » chez Apple
et Nvidia. Le reste (décomposition, plancher, départ décalé) est de l'arithmétique, éprouvée sur séries construites.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.nasdaq import valeur as V  # noqa: E402

ko: list[str] = []
ok_n = 0


def check(name: str, cond: bool) -> None:
    global ok_n
    if cond:
        ok_n += 1
    else:
        ko.append(name)


def safe(fn, *a):
    """Une mutation peut faire lever le calcul : le check doit quand même atteindre son bilan."""
    try:
        return fn(*a)
    except Exception as ex:  # noqa: BLE001
        ko.append(f"{fn.__name__} lève {type(ex).__name__}")
        return {}


fx = json.loads((Path(__file__).parent / "fixtures/nasdaq_valeur/nvda_eps.json").read_text())
pts, splits = fx["points"], [tuple(s) for s in fx["splits"]]
ttm = V.ttm_points(V.adjust_splits(pts, splits))
by_end = {p["end"]: p for p in ttm}

# ── divisions d'actions : chaque valeur déposée est ajustée par SA date de dépôt ──
fy25 = by_end.get("2025-01-26")
check("exercice 2025 (4 trimestres de part et d'autre de la division du 2024-06-10) = 2,94 $",
      fy25 is not None and abs(fy25["ttm"] - 2.94) < 0.02)
fy24 = by_end.get("2024-01-28")
check("exercice 2024 (déposé avant la division) = 11,93 / 10", fy24 is not None and abs(fy24["ttm"] - 1.193) < 0.01)
check("aucun saut de plus de ×3 d'un trimestre à l'autre",
      all(b["ttm"] <= 3 * a["ttm"] for a, b in zip(ttm, ttm[1:]) if a["ttm"] > 0.3))

# ── 4ᵉ trimestre déduit : exercice − 9 mois ──
# Le repli « exercice annuel » donne aussi 2,94 au 26 janvier : seul un glissement à cheval sur le T4
# (mai 2024 → avril 2025) n'existe QUE si le T4 est déduit.
q1 = by_end.get("2025-04-27")
check("T4 de l'exercice 2025 déduit (2,94 − 2,04)", q1 is not None and abs(q1["ttm"] - (0.67 + 0.78 + 0.90 + 0.76)) < 0.01)

# ── point-in-time : connu au dépôt le plus tardif des quatre trimestres, jamais à la clôture ──
check("disponible au dépôt du 10-K (2025-02-26), pas à la clôture", fy25 is not None and fy25["avail"] == "2025-02-26")
st = V.state_by_month(ttm, ["2025-01", "2025-02"])
check("janvier 2025 ne voit pas encore l'exercice clos le 26", st[0] is not None and abs(st[0] - 2.54) < 0.02)
check("février 2025 le voit", st[1] is not None and abs(st[1] - 2.948) < 0.02)

# ── décomposition : cours = inflation × bénéfices réels × multiple ; total = cours × dividendes ──
n = 72
m = [f"{2010 + i // 12}-{i % 12 + 1:02d}" for i in range(n)]
cpi = [100 * 1.002 ** i for i in range(n)]
e = [1.0 * 1.01 ** i for i in range(n)]
p = [20 * 1.015 ** i for i in range(n)]
tr = [p[i] * 1.001 ** i for i in range(n)]
sp = [1000 * 1.008 ** i for i in range(n)]
d = {"ticker": "X", "m": m, "p": p, "tr": tr, "e": e, "cpi": cpi, "sp": sp}
dec = safe(V.decompose, d, "3y")
f = dec.get("factor", {})
check("décomposition calculable", dec.get("ok") is True)
check("cours₁/cours₀ = inflation × bénéfices réels × multiple",
      dec.get("ok") and abs(f["infl"] * f["real"] * f["mult"] - f["price"]) < 1e-9)
check("rendement total = cours × dividendes", dec.get("ok") and abs(f["price"] * f["div"] - f["total"]) < 1e-9)
check("multiple : PER d'arrivée / PER de départ",
      dec.get("ok") and abs(f["mult"] - (p[-1] / e[-1]) / (p[n - 1 - 36] / e[n - 1 - 36])) < 1e-9)
cu = safe(V.cumulative, d, "3y") or {"infl": [0], "real": [0], "mult": [0]}
check("aire empilée : la somme des couches (logs) retombe sur le cours",
      abs(cu["infl"][-1] + cu["real"][-1] + cu["mult"][-1] - math.log(f.get("price", 1))) < 1e-9)
check("aire empilée : départ à zéro", cu["infl"][0] == 0 and cu["real"][0] == 0 and cu["mult"][0] == 0)

# ── départ décalé quand l'entreprise est en perte au départ ──
e2 = [-1.0] * 30 + e[30:]
d2 = {**d, "e": e2}
dec2 = safe(V.decompose, d2, "5y")
check("perte au départ : départ décalé au premier bénéfice", dec2.get("shifted") is True and dec2.get("start") == m[30])
d3 = {**d, "e": e[:-1] + [-0.5]}
dec3 = safe(V.decompose, d3, "3y")
check("perte aujourd'hui : pas de décomposition, et on dit pourquoi",
      dec3.get("ok") is False and "perte" in dec3.get("reason", ""))

# ── plancher : moyenne 3 ans × multiple des pires jours (ou fixe), bande = sensibilité de la marge 0,7 à 0,9 ──
fl = V.floor_series(e, p, cpi)
own = V.own_floor(e, p, cpi)
a3 = (e[-1] + e[-13] + e[-25]) / 3
k_own = own["mult"][-1] or 0
check("plancher central = moyenne des états à t, t-12, t-24 × multiple des pires jours",
      k_own > 0 and fl["mid"][-1] is not None and abs(fl["mid"][-1] - k_own * a3) < 1e-9)
check("ratio = cours / plancher central", fl["ratio"][-1] is not None and abs(fl["ratio"][-1] - p[-1] / (k_own * a3)) < 1e-9)
check("bande = la même règle avec une marge de 0,7 et de 0,9 au lieu de 0,8",
      fl["lo"][-1] is not None and abs(fl["lo"][-1] - k_own * a3 * 0.7 / 0.8) < 1e-9
      and abs(fl["hi"][-1] - k_own * a3 * 0.9 / 0.8) < 1e-9)
flx = V.floor_series(e, p, cpi, 8)
check("multiple provisoire fixe : plancher = moyenne 3 ans × 8, bande 7 à 9",
      flx["mid"][-1] is not None and abs(flx["mid"][-1] - 8 * a3) < 1e-9
      and abs(flx["lo"][-1] - 7 * a3) < 1e-9 and abs(flx["hi"][-1] - 9 * a3) < 1e-9)
check("multiple provisoire : plancher dès 24 mois, sans attendre 3 ans de multiples", flx["mid"][30] is not None and fl["mid"][30] is None)
check("sans multiple des pires jours : la raison est portée par la série", "moins de 3 ans" in (fl["why"][30] or ""))
check("état qui progresse : plancher valide", fl["degraded"][-1] is False)
e4 = e[:60] + [e[59] * 0.5] * 12
fl4 = V.floor_series(e4, p, cpi, 8)
check("bénéfices divisés par deux : plancher caduc", fl4["degraded"][-1] is True)
check("fantôme = meilleur état réel indexé × le même multiple (au-dessus du plancher quand l'état se dégrade)",
      fl4["ghost"][-1] is not None and fl4["ghost"][-1] > fl4["mid"][-1])
check("avant 24 mois d'historique : pas de plancher", flx["mid"][10] is None)

# ── plancher propre au titre : 5ᵉ centile de ses multiples des 120 mois PRÉCÉDENTS × 0,8 (arbitré le 2026-11-23) ──
import numpy as np  # noqa: E402

N = 200
flat = [1.0] * N
eg = [1.0 * 1.01 ** i for i in range(N)]
a3g = [None] * 24 + [(eg[i] + eg[i - 12] + eg[i - 24]) / 3 for i in range(24, N)]
pg = [15 + 5 * math.sin(i / 7) if a3g[i] is None else a3g[i] * (15 + 5 * math.sin(i / 7)) for i in range(N)]
ow = safe(V.own_floor, eg, pg, flat) or {"floor": [None] * N, "ratio": [None] * N, "why": [""] * N, "mult": [None] * N}
i = 190
want = float(np.percentile([pg[j] / a3g[j] for j in range(i - 120, i)], 5)) * 0.8
check("multiple du titre = 5ᵉ centile de ses multiples des 120 mois précédents × 0,8",
      ow["mult"][i] is not None and abs(ow["mult"][i] - want) < 1e-9)
check("plancher = multiple du titre × moyenne 3 ans", ow["floor"][i] is not None and abs(ow["floor"][i] - want * a3g[i]) < 1e-9)
check("rapport au plancher = cours / plancher", ow["ratio"][i] is not None and abs(ow["ratio"][i] - pg[i] / (want * a3g[i])) < 1e-9)
pf = pg[:i + 1] + [pg[j] * 0.1 for j in range(i + 1, N)]
ow2 = safe(V.own_floor, eg, pf, flat) or {"floor": [None] * N}
check("rien de l'avenir : changer les cours APRÈS t ne bouge pas le plancher de t", ow2["floor"][i] == ow["floor"][i])
pc = pg[:i] + [pg[i] * 0.1] + pg[i + 1:]
ow3 = safe(V.own_floor, eg, pc, flat) or {"floor": [None] * N}
check("le cours du jour n'entre pas dans son propre plancher", ow3["floor"][i] == ow["floor"][i])
check("moins de 3 ans de multiples : pas de plancher, et la raison est dite",
      ow["floor"][40] is None and "moins de 3 ans" in (ow["why"][40] or ""))
check("avec 36 multiples précédents : plancher", ow["floor"][24 + 36] is not None)
check("avec 35 multiples précédents : pas de plancher", ow["floor"][24 + 35] is None)
eb = eg[:100] + [eg[100] * 0.3] * 30 + eg[130:]
pb = [pg[j] * (0.02 if 100 <= j < 140 else 1) for j in range(N)]
ow4 = safe(V.own_floor, eb, pb, flat) or {"floor": [None] * N}
ow5 = safe(V.own_floor, eb, pg, flat) or {"floor": [None] * N}
check("mois à état dégradé exclus des multiples : un cours délirant sur un état dégradé ne bouge pas le plancher",
      ow4["floor"][170] is not None and abs(ow4["floor"][170] - ow5["floor"][170]) < 1e-9)
el = [-1.0] * N
check("bénéfice moyen négatif : pas de plancher, raison dite",
      (safe(V.own_floor, el, pg, flat) or {"floor": [0], "why": [""]})["floor"][-1] is None)

# ── position dans le cycle : bénéfice 12 mois ÷ moyenne des 10 derniers exercices en monnaie d'aujourd'hui ──
cy = safe(V.cycle_position, [2.0] * 120, [100.0] * 120) or {"x": None}
check("bénéfices constants et prix stables : position = 1", cy["x"] is not None and abs(cy["x"] - 1) < 1e-9)
infl = [100 * 1.003 ** j for j in range(120)]
ei = [infl[j] / 100 for j in range(120)]
cy2 = safe(V.cycle_position, ei, infl) or {"x": None}
check("bénéfice qui ne suit que l'inflation : position = 1 (chaque exercice remis en monnaie d'aujourd'hui)",
      cy2["x"] is not None and abs(cy2["x"] - 1) < 1e-9)
ec = [1.0] * 108 + [3.0] * 12
cy3 = safe(V.cycle_position, ec, [100.0] * 120) or {"x": None}
check("bénéfice 12 mois triplé sur le dernier mois seulement : x = 3 / moyenne des 10 exercices",
      cy3["x"] is not None and abs(cy3["x"] - 3.0 / ((3.0 + 9 * 1.0) / 10)) < 1e-9)
cy4 = safe(V.cycle_position, [2.0] * 100, [100.0] * 100) or {"x": 1, "why": ""}
check("moins de 10 ans de bénéfices : non affiché, raison dite", cy4["x"] is None and "10 ans" in cy4["why"])
cy5 = safe(V.cycle_position, [-1.0] * 119 + [1.0], [100.0] * 120) or {"x": 1, "why": ""}
check("moyenne de cycle négative : « pas de moyenne de cycle (pertes) »", cy5["x"] is None and "pertes" in cy5["why"])

# ── PER à terme ──
s = safe(V.summary, d, {"fwd_eps": 2.0, "fwd_lo": 1.0, "fwd_hi": 4.0, "n_analysts": 10}) or {"forward": {"pe": 0, "pe_lo": 0, "pe_hi": 0, "ratio": 0}}
check("PER à terme = cours / bénéfice attendu", abs(s["forward"]["pe"] - p[-1] / 2.0) < 1e-9)
check("fourchette : l'analyste le plus optimiste donne le PER le plus bas",
      abs(s["forward"]["pe_lo"] - p[-1] / 4.0) < 1e-9 and abs(s["forward"]["pe_hi"] - p[-1] / 1.0) < 1e-9)
check("rapport au plancher = PER à terme / multiple des pires jours",
      s["forward"].get("ratio") is not None and abs(s["forward"]["ratio"] - p[-1] / 2.0 / k_own) < 1e-9)
check("le résumé dit quel multiple il applique (propre au titre)", s.get("mult") == k_own and s.get("mult_kind") == "propre")

# ── contrôle croisé : un bénéfice désavoué par Yahoo ne s'affiche pas ──
check("contrôle croisé en défaut : analyse masquée", V.usable({"m": [], "check": {"ok": False}}) is False)
check("contrôle croisé réussi ou absent : analyse affichée",
      V.usable({"m": [], "check": {"ok": True}}) is True and V.usable({"m": []}) is True)

for k in ko:
    print("FAIL", k)
print(f"check_nasdaq_valeur : {ok_n} ok / {len(ko)} FAIL")
sys.exit(1 if ko else 0)
