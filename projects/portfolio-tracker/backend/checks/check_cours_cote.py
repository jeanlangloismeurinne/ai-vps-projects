"""Le cours coté et sa date — un non-nombre est une ABSENCE, une séance vide n'est pas une séance (#81).

Entièrement hors ligne et hors modèle : tout se joue sur des séries fabriquées à la FORME mesurée
en production le 2026-09-23, et sur la lecture AST des sources. Aucune section n'appelle yfinance.

  • §1  `fini` — LE TRIO D'ÉTATS (#44/#47). `0.0` traverse (c'est une VALEUR mesurée) ; `NaN`,
        `±inf`, `None` et le non-castable retombent sur `None`. `NaN` est le quatrième état muet :
        il a la FORME d'un nombre, il est VRAI au sens booléen, et PostgreSQL le refuse.
  • §2  `serie_cotee` — DÉTENTEUR UNIQUE (#46) de « une séance sans cours n'est pas une séance ».
        Les séances vides tombent, les autres restent, l'ORDRE est conservé.
  • §3  LE DÉFAUT RÉEL REJOUÉ — 251 séances dont la DERNIÈRE a un `Close` vide. C'est la forme
        exacte mesurée sur MSFT/NVDA/RVMD le 2026-09-23 : identique sur les trois titres, donc le
        fournisseur, pas le titre. Les quatre variations se terminent TOUTES au dernier cours :
        un seul jour manquant les emportait les quatre d'un coup. Ancre NON CIRCULAIRE — ces
        nombres viennent de la production, pas du code testé (`feedback_fixture_copiee_du_reel`).
  • §4  LE SEUIL QU'AUCUNE DONNÉE NE POUVAIT FRANCHIR — `period="1y"` rend 251 séances et la
        variation 1 an en exigeait 252 : une colonne toujours vide, dont le vide se lisait comme
        une propriété de l'émetteur (#69) alors qu'il était une propriété du seuil.
  • §5  LES DEUX DATES DU RELEVÉ — la date du prix vient de l'horodatage du MARCHÉ, lu dans le
        fuseau de la PLACE (une clôture asiatique bascule de jour en UTC et daterait la mesure
        d'un jour de trop). Sans horodatage : repli sur la dernière séance cotée.
  • §6  LE FILET AU GUICHET — `_assainir_non_finis` est le FILET de la convention #8 (DataService
        = point d'accès unique). Sa preuve est un COUPLE discriminant : la charge assainie passe
        `json.dumps(allow_nan=False)`, la charge brute le fait ÉCHOUER. C'est littéralement ce que
        PostgreSQL exigeait. Les champs tombés sont NOMMÉS dans le log — une absence silencieuse
        se lirait comme une propriété de l'émetteur (#69).
  • §7  CENSUS PAR AST — toute fonction de `m1_quantitative` qui lit une cellule de série (`.iloc`)
        passe par `fini`. La liste est DÉCOUVERTE, jamais récitée : un recensement à la main ne
        couvre qu'une partie du corpus et refait le bug au vert
        (`feedback_adressage_par_nom_exige_lecture`).
  • §8  LA CASCADE DANS LE DOSSIER (#79) — `valuation_feed` date le FAIT par le marché et le
        DOCUMENT par le jour. Les confondre faisait battre un relevé simplement rafraîchi contre
        un fait réellement plus récent.

    docker run --rm --network none -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app \
      --env-file checks/env.checks $IMG python checks/check_cours_cote.py
"""
import ast
import inspect
import json
import logging
import math
import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _harness import Bilan  # noqa: E402

from app.data_collection.data_service import _assainir_non_finis  # noqa: E402
from app.data_collection.m1_quantitative import (  # noqa: E402
    _calc_period_change,
    _calc_window_change,
    _calc_ytd_change,
    _date_du_prix,
    _derniere_cotation,
    fini,
    serie_cotee,
)
from app.knowledge.valuation_feed import _date_du_fait  # noqa: E402

b = Bilan()
BACKEND = Path(__file__).resolve().parent.parent
M1_SRC = BACKEND / "app" / "data_collection" / "m1_quantitative.py"

# ── La forme MESURÉE en production le 2026-09-23 (MSFT, NVDA, RVMD — identique sur les trois) ──
#    251 séances, du 2025-09-23 au 2026-09-22, et une seule `Close` vide : la DERNIÈRE.
SEANCES_REELLES = 251
DERNIERE_REELLE = "2026-09-22"
AVANT_DERNIERE_REELLE = "2026-09-21"


def serie(n=SEANCES_REELLES, *, fin=DERNIERE_REELLE, dernier_vide=False, debut_prix=100.0):
    """Une série de clôtures à la forme de celles du fournisseur. Prix strictement croissants :
    toute variation calculée dessus est donc POSITIVE et non nulle — un `0.0` ou un `None` en
    sortie ne peut pas passer pour un résultat plausible."""
    idx = pd.bdate_range(end=fin, periods=n)
    closes = [debut_prix + i for i in range(n)]
    if dernier_vide:
        closes[-1] = float("nan")
    return pd.DataFrame({"Close": closes}, index=idx)


# ── §1 `fini` — le trio d'états ────────────────────────────────────────────────────────────────
print("§1 fini — un non-nombre est une ABSENCE, pas un nombre")

b.check(fini(0.0) == 0.0 and fini(0.0) is not None, "`0.0` TRAVERSE — c'est une valeur mesurée (#47)")
b.check(fini(0) == 0.0, "`0` entier traverse aussi")
b.check(fini(-3.5) == -3.5, "un négatif fini traverse inchangé")
b.check(fini(float("nan")) is None, "`NaN` → None (le quatrième état muet)")
b.check(fini(float("inf")) is None, "`+inf` → None")
b.check(fini(float("-inf")) is None, "`-inf` → None")
b.check(fini(None) is None, "`None` reste None")
b.check(fini("pas un nombre") is None, "un non-castable → None, sans lever")
b.check(fini("3.5") == 3.5, "une chaîne numérique est castée (les séries yfinance en rendent)")
# La preuve que `if x:` ne peut PAS tenir lieu de `fini` — c'est tout le défaut en une ligne.
b.check(bool(float("nan")) is True, "rappel mesuré : `if nan:` est VRAI — `if x:` ne discrimine rien")


# ── §2 `serie_cotee` — détenteur unique ────────────────────────────────────────────────────────
print("\n§2 serie_cotee — une séance sans cours n'est pas une séance")

pleine = serie(10)
b.check(len(serie_cotee(pleine)) == 10, "une série sans trou n'est pas amputée")

trouee = serie(10, dernier_vide=True)
cotee = serie_cotee(trouee)
b.check(len(cotee) == 9, "la séance vide tombe (10 → 9)")
b.check(cotee["Close"].tolist() == pleine["Close"].tolist()[:9], "les cours restants sont INCHANGÉS et dans l'ORDRE")
b.check(cotee.index[-1] == pleine.index[-2], "la dernière séance cotée est bien l'avant-dernière ligne")

toute_vide = serie(5)
toute_vide["Close"] = float("nan")
b.check(len(serie_cotee(toute_vide)) == 0, "une série entièrement vide rend une série VIDE, sans lever")

infinie = serie(6)
infinie.iloc[3, 0] = float("inf")
b.check(len(serie_cotee(infinie)) == 5, "`±inf` tombe aussi — pas seulement `NaN`")


# ── §3 Le défaut réel rejoué ───────────────────────────────────────────────────────────────────
print("\n§3 le défaut RÉEL du 2026-09-23 — 251 séances, la dernière vide")

reelle = serie(SEANCES_REELLES, dernier_vide=True)
b.require(reelle.index, SEANCES_REELLES, "la fixture a bien la cardinalité MESURÉE en production")
b.check(str(reelle.index[-1].date()) == DERNIERE_REELLE, f"sa dernière séance est bien le {DERNIERE_REELLE}")
b.check(math.isnan(reelle["Close"].iloc[-1]), "et c'est bien SA CLÔTURE qui manque (le cas mesuré)")

variations = {
    "1m": _calc_period_change(reelle, 21),
    "3m": _calc_period_change(reelle, 63),
    "6m": _calc_period_change(reelle, 126),
    "1an": _calc_window_change(reelle),
    "ytd": _calc_ytd_change(reelle),
}
b.require(variations, 5, "les cinq variations de la fiche sont éprouvées")
for nom, v in variations.items():
    b.check(v is not None, f"variation {nom} : RENSEIGNÉE malgré la séance manquante (arbitrage 2026-09-23)")
    b.check(not (isinstance(v, float) and not math.isfinite(v)), f"variation {nom} : jamais un non-nombre")
    b.check(v is None or v > 0, f"variation {nom} : valeur plausible sur une série croissante")

# Le calcul marque au DERNIER COURS COTÉ, donc la variation 1m compare 21 séances COTÉES entre
# elles — pas 21 lignes dont une vide. Sur une série à pas de 1, l'écart est exactement 20 points.
cotee_reelle = serie_cotee(reelle)
attendu_1m = round((cotee_reelle["Close"].iloc[-1] / cotee_reelle["Close"].iloc[-21] - 1) * 100, 2)
b.check(variations["1m"] == attendu_1m, "variation 1m calculée sur 21 séances COTÉES, pas 21 lignes")

b.check(_derniere_cotation(reelle) == AVANT_DERNIERE_REELLE,
        f"la date de marquage est celle du dernier cours COTÉ ({AVANT_DERNIERE_REELLE}), pas de la ligne vide")
b.check(_derniere_cotation(serie(3)) == str(serie(3).index[-1].date()),
        "sans trou, la date de marquage est bien la dernière séance")
b.check(_derniere_cotation(pd.DataFrame({"Close": []}, index=pd.to_datetime([]))) is None,
        "série vide → pas de date de marquage (ABSENT, pas un jour inventé)")


# ── §4 Le seuil qu'aucune donnée ne pouvait franchir ───────────────────────────────────────────
print("\n§4 le seuil infranchissable — 251 séances reçues, 252 exigées")

b.check(_calc_period_change(serie(SEANCES_REELLES), 252) is None,
        f"l'ANCIEN calcul (252 séances) rendait None sur les {SEANCES_REELLES} réelles — colonne morte")
b.check(_calc_window_change(serie(SEANCES_REELLES)) is not None,
        "le calcul sur FENÊTRE, lui, rend un nombre sur la même donnée")
b.check(_calc_window_change(serie(150)) is None,
        "une fenêtre TRONQUÉE (150 séances) reste refusée — le seuil gardait bien quelque chose")
b.check(_calc_window_change(serie(SEANCES_REELLES, dernier_vide=True)) is not None,
        "251 séances dont une vide (= 250 cotées) franchissent encore le minimum")

# Un début à zéro rendrait une division par zéro : c'est ABSENT, jamais `inf`.
plat = serie(220)
plat.iloc[0, 0] = 0.0
b.check(_calc_window_change(plat) is None, "un premier cours à 0 → ABSENT (jamais `inf`, jamais un ratio)")


# ── §5 Les deux dates du relevé ────────────────────────────────────────────────────────────────
print("\n§5 la date du prix vient du MARCHÉ, pas de l'horloge du serveur")

# Valeur MESURÉE sur MSFT le 2026-09-23 : la clôture du 22/09 à New York.
MSFT_TS, MSFT_TZ, MSFT_JOUR = 1790107201, "America/New_York", "2026-09-22"
b.check(_date_du_prix({"regularMarketTime": MSFT_TS, "exchangeTimezoneName": MSFT_TZ}, None) == MSFT_JOUR,
        f"horodatage réel MSFT → {MSFT_JOUR} (la clôture de la VEILLE, pas le jour de lecture)")

# Le même instant à Tokyo tombe le LENDEMAIN : c'est ce que le fuseau de la place empêche.
tokyo = _date_du_prix({"regularMarketTime": MSFT_TS, "exchangeTimezoneName": "Asia/Tokyo"}, None)
b.check(tokyo == "2026-09-23", "même instant, place de Tokyo → jour suivant (le fuseau de la PLACE est lu)")
b.check(tokyo != MSFT_JOUR, "les deux places ne datent donc PAS pareil — le fuseau n'est pas décoratif")

b.check(_date_du_prix({}, "2026-09-21") == "2026-09-21", "sans horodatage : repli sur la dernière cotation")
b.check(_date_du_prix({}, None) is None, "sans horodatage NI repli : ABSENT, jamais aujourd'hui")
# Enveloppé : si la garde du non-fini saute, `fromtimestamp(nan)` LÈVE et tuerait le script avant
# son bilan (2ᵉ faux-vert). Un refus doit être un FAIL NOMMÉ, jamais une mort (cf. #79 §`date_de`).
try:
    _nan_ts = _date_du_prix({"regularMarketTime": float("nan")}, "2026-09-21")
except Exception as exc:  # noqa: BLE001
    _nan_ts = f"A LEVÉ : {type(exc).__name__}: {exc}"
b.check(_nan_ts == "2026-09-21",
        "un horodatage non fini retombe sur le repli (le trio d'états vaut aussi pour les dates)")
b.check(_date_du_prix({"regularMarketTime": MSFT_TS, "exchangeTimezoneName": "Mars/Olympus"}, None) is not None,
        "un fuseau inconnu ne tue pas la collecte — elle dégrade en UTC")


# ── §6 Le filet au guichet ─────────────────────────────────────────────────────────────────────
print("\n§6 le filet du DataService — rien de non fini ne franchit la porte")

brut = {
    "ticker": "MSFT",
    "price": {"current_price": 498.0, "ytd_change_pct": float("nan"), "1m_change_pct": float("nan"),
              "3m_change_pct": float("nan"), "6m_change_pct": float("nan"), "payout_ratio": 0.0},
    "financials_3y": {"2026": {"fcf": float("inf"), "revenue": 281_700_000_000.0}},
    "series": [1.0, float("nan"), 3.0],
    "texte": "inchangé",
}

logs = []
handler = logging.Handler()
handler.emit = lambda record: logs.append(record.getMessage())
logger_ds = logging.getLogger("app.data_collection.data_service")
logger_ds.addHandler(handler)
logger_ds.setLevel(logging.WARNING)
propre = _assainir_non_finis("MSFT", brut)
logger_ds.removeHandler(handler)

b.check(propre["price"]["current_price"] == 498.0, "un nombre fini traverse le filet inchangé")
b.check(propre["price"]["payout_ratio"] == 0.0, "`0.0` traverse le filet — mesure, pas absence (#44)")
b.check(propre["texte"] == "inchangé", "une chaîne n'est pas touchée")
b.check(all(propre["price"][k] is None for k in ("ytd_change_pct", "1m_change_pct", "3m_change_pct", "6m_change_pct")),
        "les quatre variations non finies deviennent None — ABSENTES, jamais `0`")
b.check(propre["financials_3y"]["2026"]["fcf"] is None, "le filet descend dans les dicts IMBRIQUÉS")
b.check(propre["series"] == [1.0, None, 3.0], "le filet descend aussi dans les LISTES, sans les réordonner")

# Le COUPLE discriminant : c'est exactement l'exigence que PostgreSQL opposait à l'écriture du cache.
try:
    json.dumps(propre, allow_nan=False)
    strict_ok = True
except ValueError:
    strict_ok = False
try:
    json.dumps(brut, allow_nan=False)
    brut_refuse = False
except ValueError:
    brut_refuse = True
b.check(strict_ok, "la charge ASSAINIE passe `json.dumps(allow_nan=False)` — ce que Postgres exigeait")
b.check(brut_refuse, "la charge BRUTE, elle, le fait ÉCHOUER — le couple discrimine (sinon on ne garde rien)")

b.require(logs, 1, "le filet a émis exactement un avertissement")
# Lu par un accès TOLÉRANT : si le filet est désarmé, `logs` est vide et `logs[0]` tuerait le
# script avant son bilan (2ᵉ faux-vert). Mesuré — c'est le test négatif qui l'a trouvé.
avert = logs[0] if logs else "<aucun avertissement émis>"
# « 6 » tout court serait VERT même avec un décompte faux : le chemin `m1.financials_3y.2026.fcf`
# contient déjà un 6. Mesuré aussi par le test négatif. On lit donc le décompte AVEC son unité.
b.check("6 champ(s)" in avert, "l'avertissement DÉNOMBRE les champs tombés (6 ici)")
for chemin in ("m1.price.ytd_change_pct", "m1.financials_3y.2026.fcf", "m1.series[1]"):
    b.check(chemin in avert, f"il NOMME le chemin tombé : `{chemin}` (#69 — pas d'absence muette)")

logs.clear()
logger_ds.addHandler(handler)
_assainir_non_finis("MSFT", {"price": {"current_price": 498.0}})
logger_ds.removeHandler(handler)
b.check(logs == [], "aucune charge saine ne produit d'avertissement (pas de bruit qui masque le vrai)")

# Un filet juste mais NON POSÉ ne garde rien — c'est un décideur sans producteur
# (`feedback_controle_au_point_de_lecture`). Il doit être sur la PORTE, et la porte est le fetch.
arbre_ds = ast.parse((BACKEND / "app" / "data_collection" / "data_service.py").read_text(encoding="utf-8"))
portes = [n for n in ast.walk(arbre_ds) if isinstance(n, ast.AsyncFunctionDef) and n.name == "_fetch_m1"]
b.require(portes, 1, "`_fetch_m1` existe — la porte unique de la convention #8")
b.check(
    any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "_assainir_non_finis"
        for n in ast.walk(portes[0])),
    "le filet est POSÉ SUR LA PORTE — `_fetch_m1` l'appelle vraiment",
)


# ── §7 Census par AST ──────────────────────────────────────────────────────────────────────────
print("\n§7 census — toute lecture de cellule passe par `fini` (DÉCOUVERT, pas récité)")

arbre = ast.parse(M1_SRC.read_text(encoding="utf-8"))
lecteurs, via_fini = [], []
for noeud in arbre.body:
    if not isinstance(noeud, ast.FunctionDef):
        continue
    corps = list(ast.walk(noeud))
    lit_cellule = any(isinstance(n, ast.Attribute) and n.attr == "iloc" for n in corps)
    appelle_fini = any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "fini" for n in corps
    )
    if lit_cellule:
        lecteurs.append(noeud.name)
        if appelle_fini:
            via_fini.append(noeud.name)

b.require(lecteurs, 4, "fonctions lisant une cellule de série, découvertes par AST")
b.check(sorted(lecteurs) == sorted(via_fini),
        f"chacune passe par `fini` — hors-la-loi : {sorted(set(lecteurs) - set(via_fini))}")
# `serie_cotee` n'est pas un lecteur de cellule mais le filtre en amont : il doit exister et appeler `fini`.
b.check("fini(" in inspect.getsource(serie_cotee), "`serie_cotee` fonde son filtre sur `fini`, pas sur `notna()`")


# ── §8 La cascade dans le dossier ──────────────────────────────────────────────────────────────
print("\n§8 cascade #79 — le FAIT est daté par le marché, le DOCUMENT par le jour")

b.check(_date_du_fait({"price": {"price_as_of": "2026-09-22", "last_close_date": "2026-09-21"}}) == date(2026, 9, 22),
        "`price_as_of` PRIME — c'est la date du prix sur lequel le relevé est fondé")
b.check(_date_du_fait({"price": {"last_close_date": "2026-09-21"}}) == date(2026, 9, 21),
        "sans horodatage de cotation : repli sur la dernière séance cotée")
b.check(_date_du_fait({"price": {}}) is None, "sans aucune date de marché : ABSENT (l'appelant décide du repli)")
b.check(_date_du_fait({}) is None, "un m1 sans bloc `price` rend ABSENT (et ne lève pas)")
b.check(_date_du_fait({"price": {"price_as_of": "pas une date"}}) is None,
        "une date illisible est ÉCARTÉE et signalée, jamais coercée en aujourd'hui")

src_vf = (BACKEND / "app" / "knowledge" / "valuation_feed.py").read_text(encoding="utf-8")
arbre_vf = ast.parse(src_vf)
appels = [
    n for n in ast.walk(arbre_vf)
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "constatee"
]
b.require(appels, 1, "`valuation_feed` construit exactement une datation `constatee`")
kw = {k.arg: k.value for k in appels[0].keywords}
b.check(set(kw) == {"date_du_fait", "date_du_document"}, "elle nomme ses DEUX dates (#79 : la forme, pas la sévérité)")
b.check(isinstance(kw.get("date_du_fait"), ast.Name) and kw["date_du_fait"].id == "as_of",
        "le FAIT est daté par `as_of` (issu du marché), pas par un appel d'horloge")
fait_est_horloge = isinstance(kw.get("date_du_fait"), ast.Call)
b.check(not fait_est_horloge, "le FAIT n'est JAMAIS `date.today()` — c'était le défaut mesuré le 2026-09-23")
b.check(isinstance(kw.get("date_du_document"), ast.Call), "le DOCUMENT, lui, est bien daté du jour de lecture")

# `as_of` ne vaut que ce que son PRODUCTEUR vaut : si `run_valuation_feed` reprenait l'horloge,
# l'assert ci-dessus resterait vert sur un nom qui ne veut plus rien dire.
runs = [n for n in ast.walk(arbre_vf) if isinstance(n, ast.AsyncFunctionDef) and n.name == "run_valuation_feed"]
b.require(runs, 1, "`run_valuation_feed` existe")
b.check(
    any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "_date_du_fait"
        for n in ast.walk(runs[0])),
    "`as_of` est PRODUIT par `_date_du_fait` — sinon le nom serait juste et la valeur fausse",
)

sys.exit(b.summary())
