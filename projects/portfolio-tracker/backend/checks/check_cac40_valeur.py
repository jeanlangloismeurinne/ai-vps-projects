"""Garde de la valeur du temps passé, version CAC 40 (`app/nasdaq/europe.py` + le filtre par marché de `valeur.py`) :
hors ligne.

Fixture RÉELLE (`fixtures/cac40_valeur/esef_eps.json`, dépôts ESEF réduits aux faits de BPA, BPA et divisions Yahoo
relevés le 2026-11-22). Le cas qui compte est Air Liquide : ses attributions gratuites (×1,1 en 2024 et 2026) font
que Yahoo affiche 4,36 € pour 2022 quand le rapport annuel publiait 5,27 €. Ajuster chaque BPA par SA date de
publication retombe sur Yahoo ; ajuster toutes les divisions (ou aucune) fabrique un écart, donc un faux « caduc ».
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.nasdaq import europe as E  # noqa: E402
from app.nasdaq import valeur as V  # noqa: E402

ko: list[str] = []
ok_n = 0


def check(name: str, cond: bool) -> None:
    global ok_n
    if cond:
        ok_n += 1
    else:
        ko.append(name)


def safe(fn, *a, default=None):
    """Une mutation peut faire lever le calcul : le check doit quand même atteindre son bilan."""
    try:
        return fn(*a)
    except Exception as ex:  # noqa: BLE001
        ko.append(f"{fn.__name__} lève {type(ex).__name__}")
        return default


fx = json.loads((Path(__file__).parent / "fixtures/cac40_valeur/esef_eps.json").read_text())
by_end = lambda pts: {p["end"]: p for p in pts}  # noqa: E731

# ── lecture d'un dépôt ESEF : fin de période exclusive, dilué d'abord, repli « activités poursuivies » ──
lv = safe(E.esef_eps, fx["lvmh"]["filings"][0], default={}) or {}
check("ESEF : la fin xBRL-JSON est exclusive (« 2025-01-01 » clôt 2024)", "2024-12-31" in lv and "2025-01-01" not in lv)
check("ESEF : le BPA dilué passe avant le BPA de base (LVMH 2024 : 25,12 et non 25,13)",
      abs((lv.get("2024-12-31") or [0])[0] - 25.12) < 1e-9)
check("ESEF : la devise vient de l'unité du fait", (lv.get("2024-12-31") or [0, ""])[1] == "EUR")
bo = safe(E.esef_eps, fx["bouygues"]["filings"][0], default={}) or {}
check("ESEF : Bouygues ne déclare que le BPA des activités poursuivies (2024 : 2,80)",
      abs((bo.get("2024-12-31") or [0])[0] - 2.80) < 1e-9)

# ── un exercice prend le chiffre de SON dépôt ; le comparatif ne sert qu'à défaut ──
ai_f = [[f["period_end"], E.esef_eps(f)] for f in fx["air_liquide"]["filings"]]
fp = by_end(safe(E.first_published, ai_f, default=[]) or [])
check("chiffre publié à l'époque : 2022 vient du dépôt 2022", fp.get("2022-12-31", {}).get("own") is True)
check("à défaut, le plus ancien dépôt qui le porte : 2021 (comparatif du dépôt 2022)",
      fp.get("2021-12-31", {}).get("own") is False and "2021-12-31" in fp)
check("2023 n'existe que comme comparatif du dépôt 2024", fp.get("2023-12-31", {}).get("own") is False)

# ── erreur d'échelle d'un dépôt : le chiffre cède devant celui qui le répète (cas réels) ──
tt = by_end(safe(E.first_published, [[f["period_end"], E.esef_eps(f)] for f in fx["totalenergies"]["filings"]], default=[]) or [])
check("TotalEnergies 2022 : dépôt 2022 en centièmes (0,0785 $), repris du dépôt 2023 (7,85 $)",
      abs(tt.get("2022-12-31", {}).get("v", 0) - 7.85) < 1e-9 and tt.get("2022-12-31", {}).get("scale") == 0.0785)
check("TotalEnergies 2023 : sans erreur d'échelle, le chiffre de son propre dépôt reste", tt.get("2023-12-31", {}).get("own") is True)
cp = safe(E.first_published, [[f["period_end"], E.esef_eps(f)] for f in fx["capgemini"]["filings"]], default=[]) or []
cpts, cwarn = safe(E.merge, cp, E.yahoo_points(fx["capgemini"]["yahoo"], "EUR"), default=([], [])) or ([], [])
c22 = by_end(cpts).get("2022-12-31", {})
check("Capgemini : l'exercice remplacé pour erreur d'échelle n'est pas « contrôlé » (le titre n'est pas masqué)",
      (safe(E.cross_check, cp, E.yahoo_points(fx["capgemini"]["yahoo"], "EUR"), default={}) or {}).get("ok") is not False)
check("Capgemini 2022 : 8 790 000 € par action au dépôt, sans dépôt suivant : Yahoo (8,79 €) le remplace, et la note le dit",
      c22.get("src") == "yahoo" and abs(c22.get("v", 0) - 8.79) < 1e-9 and any("échelle" in w for w in cwarn))

# Crédit Agricole (réel) : dépôts 2020 et 2021 en millions ; 2021 est démenti par le dépôt 2022, 2019-2020 non.
aca = [{"end": f"{y}-12-31", "v": v, "cur": "EUR", "src": "esef"} for y, v in
       ((2019, 1482000.0), (2020, 804000.0), (2021, 1.836), (2022, 1.681), (2023, 1.943), (2024, 2.109), (2025, 2.18))]
akept, awarn = safe(E.drop_outliers, aca, default=(aca, [])) or (aca, [])
check("Crédit Agricole 2019-2020 : hors d'échelle de la série (×100 la médiane), écartés et signalés",
      [p["end"][:4] for p in akept] == ["2021", "2022", "2023", "2024", "2025"] and len(awarn) == 2)
saf = [{"end": f"{y}-12-31", "v": v, "cur": "EUR", "src": "esef"} for y, v in
       ((2019, 5.63), (2020, 0.8), (2021, 0.1), (2022, -5.76), (2023, 8.07), (2024, -1.6), (2025, 17.17))]
check("Safran (réel) : un bénéfice proche de zéro ou une forte variation ne sont pas des erreurs d'échelle",
      len((safe(E.drop_outliers, saf, default=([], [])) or ([], []))[0]) == 7)

# ── disponibilité : 4 mois après la clôture, jamais à la clôture ──
check("exercice 2024 connu fin avril 2025", E.avail_date("2024-12-31") == "2025-04-30")
check("exercice décalé (clôture 30 juin) connu fin octobre", E.avail_date("2025-06-30") == "2025-10-31")
ttm = safe(E.to_ttm, [{"end": "2024-12-31", "v": 5.0, "cur": "EUR", "src": "esef"}], lambda c, m: None, default=[]) or []
st = V.state_by_month(ttm, ["2025-03", "2025-04"])
check("mars 2025 ne voit pas encore l'exercice 2024, avril le voit", st == [None, 5.0])

# ── divisions d'actions : par date de PUBLICATION (le cas réel d'Air Liquide) ──
splits = [tuple(s) for s in fx["air_liquide"]["splits"]]
adj = by_end(safe(E.adjust_esef, list(fp.values()), splits, default=[]) or [])
yh = fx["air_liquide"]["yahoo"]
check("Air Liquide 2022 : 5,27 € publiés ÷ 1,1² (attributions de 2024 et 2026) = 4,36 € comme Yahoo",
      abs(adj.get("2022-12-31", {}).get("v", 0) - yh["2022-12-31"]) < 0.01)
check("Air Liquide 2024 : seule l'attribution de 2026 est postérieure à la publication (5,72 ÷ 1,1 = 5,20)",
      abs(adj.get("2024-12-31", {}).get("v", 0) - yh["2024-12-31"]) < 0.01)
check("Air Liquide 2023, lu au dépôt 2024 (déjà retraité de juin 2024) : ÷ 1,1 seulement = 4,85 € comme Yahoo",
      abs(adj.get("2023-12-31", {}).get("v", 0) - yh["2023-12-31"]) < 0.01)

# ── fusion ESEF / Yahoo : priorité, comblement, signal d'écart ──
ys = E.yahoo_points(yh, "EUR")
pts, warn = safe(E.merge, list(adj.values()), ys, default=([], [])) or ([], [])
mp = by_end(pts)
check("fusion : l'ESEF passe avant Yahoo sur un exercice commun", mp.get("2024-12-31", {}).get("src") == "esef")
check("fusion : Yahoo comble l'exercice que l'ESEF n'a pas encore (2025)", mp.get("2025-12-31", {}).get("src") == "yahoo")
check("fusion : une fois ajusté, Air Liquide ne signale aucun écart", warn == [])
_, warn2 = safe(E.merge, [{"end": "2024-12-31", "v": 5.72, "cur": "EUR", "src": "esef"}], ys, default=([], [])) or ([], [])
check("fusion : un écart de plus de 5 % se signale (ESEF non ajusté 5,72 contre 5,20)", len(warn2) == 1 and "2024" in warn2[0])
ke = E.yahoo_points(fx["kering"]["yahoo"], "EUR")
kesef = [p for p in ke if p["end"][:4] <= fx["kering"]["esef_through"]]
kesef = [{**p, "src": "esef"} for p in kesef]
kpts, _ = safe(E.merge, kesef, ke, default=([], [])) or ([], [])
check("fusion : Kering, indexé jusqu'à 2023 seulement, est complété par Yahoo pour 2024 et 2025",
      [p["src"] for p in kpts if p["end"][:4] >= "2024"] == ["yahoo", "yahoo"])

# ── contrôle croisé : même exercice, même tolérance que le Nasdaq ──
cc = safe(E.cross_check, list(adj.values()), ys, default={}) or {}
check("contrôle croisé sur le dernier exercice commun (2024)", cc.get("year") == "2024" and cc.get("ok") is True)
cc2 = safe(E.cross_check, [{"end": "2025-12-31", "v": 0.33, "cur": "USD", "src": "esef"}],
           [{"end": "2025-12-31", "v": 0.18, "cur": "USD", "src": "yahoo"}], default={}) or {}
check("contrôle croisé : hors tolérance, l'analyse est masquée (STMicro 2025, IFRS 0,33 contre US GAAP 0,18)",
      cc2.get("ok") is False and V.usable({"m": [], "check": cc2}) is False)
cc3 = safe(E.cross_check, [], ys, default={}) or {}
check("contrôle croisé : sans exercice commun, impossible mais pas masqué (Puma)",
      cc3.get("ok") is None and V.usable({"m": [], "check": cc3}) is True)

# ── change : un BPA en dollars passe en euros, sinon il tombe ──
usd = safe(E.to_ttm, [{"end": "2024-12-31", "v": 2.0, "cur": "USD", "src": "esef"}], lambda c, m: 0.9 if c == "USD" else None, default=[]) or []
check("BPA en dollars converti au change du mois de clôture", len(usd) == 1 and abs(usd[0]["ttm"] - 1.8) < 1e-9)
nofx = safe(E.to_ttm, [{"end": "2024-12-31", "v": 2.0, "cur": "GBP", "src": "esef"}], lambda c, m: None, default=[0]) or []
check("sans change, le point tombe plutôt que d'entrer dans une autre devise", nofx == [])

# ── marchés : non-régression du Nasdaq, périodes du CAC 40 ──
check("une ligne sans marché déclaré est une ligne Nasdaq", V.market_of({"m": []}) == "nasdaq" and V.market_of(None) == "nasdaq")
check("une ligne CAC 40 n'est pas une ligne Nasdaq", V.market_of({"market": "cac40", "m": []}) == "cac40")
check("une ligne CAC 40 en échec (marché seul, sans séries) n'est pas affichable", V.usable({"market": "cac40", "name": "X"}) is False)
mix = {"NVDA": {"m": []}, "ZZZZ": None, "MC.PA": {"market": "cac40", "m": []}, "PUM.DE": {"market": "cac40"}}
check("la page Nasdaq (et ses badges) ne lit que le Nasdaq, échecs compris",
      sorted(V.select(mix, "nasdaq")) == ["NVDA", "ZZZZ"] and sorted(V.select(mix, "cac40")) == ["MC.PA", "PUM.DE"])
n = 72
d = {"ticker": "X", "m": [f"{2020 + i // 12}-{i % 12 + 1:02d}" for i in range(n)], "p": [20 * 1.01 ** i for i in range(n)],
     "tr": [20 * 1.012 ** i for i in range(n)], "e": [1.0 * 1.005 ** i for i in range(n)],
     "cpi": [100 * 1.002 ** i for i in range(n)], "sp": [1000 * 1.008 ** i for i in range(n)]}
s_eu = safe(V.summary, d, None, "cac40", default={}) or {}
s_us = safe(V.summary, d, None, default={}) or {}
check("CAC 40 : « 10 ans » rend « historique insuffisant », pas un départ décalé",
      (s_eu.get("periods") or {}).get("10y", {}).get("ok") is False
      and "historique insuffisant" in (s_eu.get("periods") or {}).get("10y", {}).get("reason", ""))
check("CAC 40 : 5 ans se décompose", (s_eu.get("periods") or {}).get("5y", {}).get("ok") is True)
check("Nasdaq : « 10 ans » reste calculé", (s_us.get("periods") or {}).get("10y", {}).get("ok") is True)

for k in ko:
    print("FAIL", k)
print(f"check_cac40_valeur : {ok_n} ok / {len(ko)} FAIL")
sys.exit(1 if ko else 0)
