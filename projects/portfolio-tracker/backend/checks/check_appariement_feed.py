"""Vérification du PRODUCTEUR de faits appariés (lot 3 maillon 4 — `app/knowledge/appariement_feed.py`).

Sans réseau, sans modèle, sans base : la moitié PURE de ce module est la totalité de sa décision.
L'inventaire arrive déjà lu (`fetch_company_facts` est fait une fois par `assurer_carte`), l'écriture
est un `store_knowledge` déjà éprouvé ailleurs — ce qui est NEUF ici, c'est ce que le module refuse,
ce qu'il choisit quand plusieurs lectures sont possibles, et ce qu'il inscrit dans l'entry.

  • §1 LES QUATRE REFUS SONT NOMMÉS — terme absent déclaré, aucune ancre commune, dimensions
       incohérentes, division par zéro. Chacun lève `AppariementInexecutable` avec un motif qui DIT
       ce qui manque : il finira dans un mandat, et « échec de collecte » n'est pas un motif.
  • §2 LES CHOIX DÉTERMINISTES — unité retenue, cadrage flux/instant, ancre commune. Ce module décide
       de ce qui est déterministe ; ses propres choix ne peuvent pas dépendre d'un ordre de dict.
  • §3 LE FAIT PRODUIT — valeur, dimension rendue, deux ancres quand le cadrage est mixte, provenance
       concept par concept (accession, forme, date), et le `metric` = l'EXPRESSION (identité du fait).
  • §4 LE TIER SE DÉRIVE, ET LES DEUX CAS DIFFÈRENT — `exact` ne passe pas par `derive_tier_calcul`
       (un relevé n'est pas un calcul) ; `approximation` déterministe ≠ non déterministe (#67).
  • §5 AUCUN VOCABULAIRE DE FRAMEWORK, AUCUN SCORE ÉCRIT ICI — l'aveuglement tient à la forme du type
       (#58), et le seul (tier, score) du module est LU dans `RELIABILITY_TABLE` (#46).

⚠️ LE CHIFFRE QUE CE CHECK NE MESURE PAS. Il n'établit pas que des lignes sont COLLECTÉES depuis le
dépôt — c'est l'affaire de l'acceptation réelle, sur un vrai inventaire. Un check vert ici dit que la
mécanique est juste, pas qu'elle débloque quoi que ce soit (#71 : router n'est pas collecter).

Cible : pydantic v2 (container backend). Tester en container, **pas** le python hôte (v1).
"""
import sys
from datetime import date, timedelta

from app.knowledge.appariement_feed import (
    SOURCE_TYPE,
    TOLERANCE_ANCRE_J,
    AppariementInexecutable,
    ConsigneAppariement,
    ancre_commune,
    construire_fait_apparie,
    resoudre_points,
    serie_du_concept,
)
from app.knowledge.service import RELIABILITY_TABLE

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


def leve(fn, *a, **kw):
    """Rend le message du refus, ou None si l'appel a réussi. Le motif est la moitié du contrat :
    il devient un mandat, et un mandat qui ne dit pas ce qui manque ne se traite pas."""
    try:
        fn(*a, **kw)
        return None
    except AppariementInexecutable as e:
        return str(e)


# ── LES FIXTURES : la FORME du réel, copiée de `companyfacts`, pas une forme plus commode ─────────
# Un point EDGAR porte `unit` (ajouté par `fetch_company_facts` en aplatissant `units`), `end`, `val`,
# `form`, `fp`, `accn`, `filed`, et `start` SEULEMENT pour un flux. Une fixture qui omettrait `fp` ou
# `form` rendrait `points_annuels` vide et ferait lire tous les flux comme des instants — le check
# serait vert sur un chemin que la prod ne prend jamais (`feedback_fixture_copiee_du_reel`).
# ⚠️ `filed` valait `end` jusqu'au 2026-09-23 : une fixture où la date du DOCUMENT est celle du
# FAIT ne peut pas voir leur confusion, et c'est précisément celle que #79 ferme. Un dépôt arrive
# APRÈS la clôture qu'il décrit — 36 jours, l'ordre de grandeur réel d'un 10-Q. Une fixture plus
# commode que la prod est un check aveugle au vert (`feedback_fixture_copiee_du_reel`).
def _depot(end: str) -> str:
    return (date.fromisoformat(end) + timedelta(days=36)).isoformat()


def _flux(end, val, *, start, unit="USD", form="10-K", accn="0001-25-000001", fy=2026, filed=None):
    return {"end": end, "val": val, "start": start, "unit": unit, "form": form, "fp": "FY",
            "accn": accn, "filed": filed or _depot(end), "fy": fy}


def _instant(end, val, *, unit="USD", form="10-Q", accn="0001-25-000002", filed=None):
    return {"end": end, "val": val, "unit": unit, "form": form, "fp": "Q2", "accn": accn,
            "filed": filed or _depot(end)}


_FACTS = {
    # deux postes de bilan à la MÊME date → une ancre instant commune
    "CashAndCashEquivalentsAtCarryingValue": [
        _instant("2025-12-31", 383_700_000.0),
        _instant("2026-06-30", 815_400_000.0, accn="0001-26-000007"),
    ],
    "CommonStockSharesOutstanding": [
        _instant("2025-12-31", 60_000_000.0, unit="shares"),
        _instant("2026-06-30", 62_000_000.0, unit="shares", accn="0001-26-000007"),
    ],
    # un flux annuel → une ancre flux. ⚠️ SA DERNIÈRE CLÔTURE EST ANTÉRIEURE AU DERNIER BILAN, et
    # c'est la forme réelle d'un émetteur à exercice calendaire au 2ᵉ trimestre : le 10-K porte le
    # 2025-12-31, le 10-Q porte un bilan au 2026-06-30. Une fixture où les deux dates coïncident
    # rendrait le cadrage MIXTE indistinguable d'un cadrage simple — et c'est ce qu'elle a fait :
    # la mutation « le fait naît vieux » (min au lieu de max) restait VERTE
    # (`feedback_fixture_copiee_du_reel`).
    "ResearchAndDevelopmentExpense": [
        _flux("2024-12-31", 380_000_000.0, start="2024-01-01", fy=2024),
        _flux("2025-12-31", 412_000_000.0, start="2025-01-01", fy=2025),
    ],
    # une biotech pré-revenus : le chiffre d'affaires existe au dépôt, et il vaut ZÉRO
    "Revenues": [_flux("2026-06-30", 0.0, start="2025-07-01", accn="0001-26-000007")],
    # un concept déposé mais ILLISIBLE : nommable, donc accepté par [V], et sans point exploitable
    "AbandonedTag": [{"end": None, "val": None, "unit": "USD", "form": "10-K"}],
    # un concept dont aucun point n'est ni annuel complet ni instantané (fractions d'exercice)
    "TrimestrielSeulement": [
        {"end": "2026-06-30", "val": 12.0, "start": "2026-04-01", "unit": "USD",
         "form": "10-Q", "fp": "Q2", "accn": "0001-26-000007", "filed": "2026-06-30"},
    ],
    # un concept dont le dernier point est DÉCALÉ : pas d'ancre commune avec la trésorerie
    "LiabilitiesCurrent": [_instant("2024-12-31", 90_000_000.0)],
}

_CONS_EXACT = ConsigneAppariement(
    statut="exact", expression="CashAndCashEquivalentsAtCarryingValue")
_CONS_APPROX = ConsigneAppariement(
    statut="approximation",
    expression="CashAndCashEquivalentsAtCarryingValue / CommonStockSharesOutstanding",
    hypotheses=("les actions dilutives ne sont pas retirées",),
    deterministe=True)


def _fait(consigne, facts=None):
    """Le chemin complet de la moitié pure : résolution puis construction."""
    points, af, ab = resoudre_points(consigne, facts if facts is not None else _FACTS)
    return construire_fait_apparie("RVMD", "RVMD", 1770561, "trésorerie par action",
                                   consigne, points, ancre_flux=af, ancre_bilan=ab)


# ── §1 LES QUATRE REFUS, ET CHACUN DIT CE QUI MANQUE ──────────────────────────────────────────────
# Un refus est ce qui distingue ce module d'un calculateur : il produit un mandat motivé (#25) là où
# une tolérance produirait un nombre. Les quatre ne sont pas interchangeables — chacun décrit une
# façon différente d'avoir « tous les nombres justes et le fait faux » (#43).
print("\n[1] les quatre refus nommés — jamais un nombre approché, jamais un silence")

_m = leve(resoudre_points, ConsigneAppariement(
    statut="approximation", expression="CashAndCashEquivalentsAtCarryingValue / Revenues",
    termes_web=("dette nette hors bilan",), deterministe=True), _FACTS)
check("§1 REFUS 1 — un terme déclaré ABSENT du dépôt (`termes_web`) arrête le calcul, et le motif "
      "NOMME le terme manquant : l'exécuter produirait un nombre amputé portant le tier de ses "
      "termes déposés (#67)",
      _m is not None and "dette nette hors bilan" in _m, f"→ {_m!r}")

_m = leve(resoudre_points, ConsigneAppariement(
    statut="approximation",
    expression="CashAndCashEquivalentsAtCarryingValue - LiabilitiesCurrent",
    deterministe=True), _FACTS)
check("§1 REFUS 2 — aucune ancre commune : le motif donne le DERNIER point de chaque concept, ce qui "
      "rend le refus contestable et permet de dire si c'est un retard de dépôt ou un abandon",
      _m is not None and "aucune date" in _m and "2024-12-31" in _m and "2026-06-30" in _m,
      f"→ {_m!r}")

_m = leve(_fait, ConsigneAppariement(
    statut="approximation",
    expression="CashAndCashEquivalentsAtCarryingValue + CommonStockSharesOutstanding",
    deterministe=True))
check("§1 REFUS 3 — additionner des USD et des shares est refusé, alors que les DIVISER ne l'est pas "
      "(§3) : le discriminant est l'opérateur, lu sur l'arbre, pas la liste des concepts",
      _m is not None and "incohérentes" in _m, f"→ {_m!r}")

_m = leve(_fait, ConsigneAppariement(
    statut="approximation",
    expression="CashAndCashEquivalentsAtCarryingValue / Revenues", deterministe=True))
check("§1 REFUS 4 — division par un dénominateur à ZÉRO : chez une biotech pré-revenus le ratio "
      "n'existe pas, et le publier en 0 ou en `inf` dirait le contraire d'une information vraie",
      _m is not None and ("zéro" in _m.lower() or "division" in _m.lower()), f"→ {_m!r}")

# Deux refus de plus, sur la LECTURE d'un concept — ils gardent des faits qui seraient tier A et faux.
_m = leve(serie_du_concept, _FACTS["AbandonedTag"], "AbandonedTag")
check("§1 un concept déposé mais sans aucun point daté et chiffré est refusé : il est NOMMABLE, donc "
      "[V] l'accepte à la production de la carte — c'est la signature d'une étiquette abandonnée",
      _m is not None and "abandonnée" in _m, f"→ {_m!r}")

_m = leve(serie_du_concept, _FACTS["TrimestrielSeulement"], "TrimestrielSeulement")
check("§1 un concept qui ne porte que des FRACTIONS d'exercice est refusé : l'employer tel quel "
      "ferait passer un trimestre pour un exercice, et ce nombre-là ne rougit nulle part",
      _m is not None and "trimestre" in _m, f"→ {_m!r}")


# ── §2 LES CHOIX DÉTERMINISTES DE LECTURE ─────────────────────────────────────────────────────────
print("\n[2] les choix de lecture sont déterministes (ce module décide de ce qui est déterministe)")

_serie, _unite, _cadrage = serie_du_concept(
    _FACTS["CommonStockSharesOutstanding"], "CommonStockSharesOutstanding")
check("§2 l'unité retenue est celle de la série, pas une supposition : un décompte d'actions est lu "
      "en `shares`, et c'est cette unité qui portera la dimension du résultat",
      _unite == "shares" and _cadrage == "instant", f"→ unite={_unite}, cadrage={_cadrage}")

# LE CRITÈRE DE CHOIX A TROIS ÉTAGES, et le troisième est ce qui le rend reproductible : à série
# également longue et également récente, l'ordre alphabétique tranche. Sans lui, le fait produit
# dépendrait de l'ordre d'itération d'un dict — dans le module qui qualifie les calculs de
# déterministes.
_deux_unites = [
    _instant("2026-06-30", 5.0, unit="USD/shares"),
    _instant("2026-06-30", 100.0, unit="USD"),
]
_s1, _u1, _ = serie_du_concept(_deux_unites, "Ambigu")
_s2, _u2, _ = serie_du_concept(list(reversed(_deux_unites)), "Ambigu")
check("§2 à récence et longueur ÉGALES, deux unités concurrentes donnent le MÊME choix quel que soit "
      "l'ordre des points : le fait produit ne dépend pas de l'ordre d'itération d'un dict",
      _u1 == _u2, f"→ {_u1} vs {_u2}")

# Le refus est CAPTURÉ plutôt que laissé propager : un assert qui tue le script avant son bilan se
# lit comme une absence de mesure, pas comme un échec nommé (`feedback_bilan_par_sa_forme`).
try:
    _serie_flux, _, _cadrage_flux = serie_du_concept(
        _FACTS["ResearchAndDevelopmentExpense"], "ResearchAndDevelopmentExpense")
except AppariementInexecutable as _e:
    _cadrage_flux = f"REFUSÉ — {_e}"
check("§2 un concept porteur de points ANNUELS est lu comme un FLUX : lu comme un instant, il "
      "ramènerait un trimestre là où l'on attend un exercice, sans erreur visible",
      _cadrage_flux == "flux", f"→ {_cadrage_flux}")

_series = {c: serie_du_concept(_FACTS[c], c)[0]
           for c in ("CashAndCashEquivalentsAtCarryingValue", "CommonStockSharesOutstanding")}
check("§2 l'ancre commune est la date la PLUS RÉCENTE où TOUS les concepts ont un point — pas le "
      "dernier point de chacun, qui soustrairait des dettes de décembre à des actifs de juin (#43)",
      ancre_commune(_series) == "2026-06-30", f"→ {ancre_commune(_series)}")
check("§2 l'ancre est CHOISIE parmi les dates réellement déposées : aucune date n'est fabriquée",
      ancre_commune(_series) in {str(p["end"]) for s in _series.values() for p in s},
      f"→ {ancre_commune(_series)}")
check("§2 sans concept, l'ancre est None — un résultat, pas une exception : l'appelant en fait un "
      "refus nommé",
      ancre_commune({}) is None, f"→ {ancre_commune({})}")
check("§2 la tolérance d'ancre est NOMMÉE (et non un 20 écrit au fil du code) : elle apparaît dans "
      "le motif de refus, donc un lecteur peut contester le seuil lui-même",
      TOLERANCE_ANCRE_J == 20, f"→ {TOLERANCE_ANCRE_J}")


# ── §3 LE FAIT PRODUIT : la valeur, ses deux ancres, et une provenance CONTESTABLE ────────────────
print("\n[3] le fait produit — valeur, dimension, ancres, provenance concept par concept")

_f = _fait(_CONS_APPROX)
check("§3 la valeur est l'expression ÉVALUÉE sur les points de l'ancre commune (815,4 M$ / 62 M "
      "actions ≈ 13,15 $/action), pas une des deux dates les plus récentes prises séparément",
      abs(_f.structure["value"] - (815_400_000.0 / 62_000_000.0)) < 1e-9,
      f"→ {_f.structure['value']}")
check("§3 la dimension est CALCULÉE sur l'arbre : USD / shares → `USD/shares`. Un ratio légitime "
      "garde sa dimension composée, il ne devient pas « USD » par commodité d'affichage",
      _f.structure["currency"] == "USD/shares", f"→ {_f.structure['currency']}")
check("§3 le `metric` du fait EST l'expression : deux exécutions de la même formule à la même ancre "
      "écrivent le même `metric`, donc la seconde SUPERSÈDE la première au lieu de la doubler (#43)",
      _f.metric == _CONS_APPROX.expression and _f.structure["metric"] == _CONS_APPROX.expression,
      f"→ {_f.metric!r}")
check("§3 la provenance est écrite CONCEPT PAR CONCEPT (tag XBRL, valeur, unité, date, forme, "
      "accession) : le lecteur peut ouvrir le dépôt et contester le nombre terme à terme",
      len(_f.structure["ingredients"]) == 2
      and all({"concept", "xbrl_tag", "value", "unit", "end", "form", "accn"} <= set(i)
              for i in _f.structure["ingredients"])
      and all(i["xbrl_tag"].startswith("us-gaap:") for i in _f.structure["ingredients"]),
      f"→ {_f.structure['ingredients']}")
check("§3 les hypothèses du calcul voyagent AVEC le fait, dans le structuré et dans le texte : une "
      "approximation dont les hypothèses ne sont pas lisibles se lit comme une mesure",
      _f.structure["hypotheses"] == list(_CONS_APPROX.hypotheses)
      and "contester" in _f.contenu and _CONS_APPROX.hypotheses[0] in _f.contenu,
      f"→ {_f.structure['hypotheses']}")
check("§3 la date du fait est celle de l'ancre, et la datation la porte comme une DATE (pas une "
      "chaîne) : l'axe actualité se calcule à la lecture, encore faut-il ne pas lui mentir en amont",
      _f.datation.date_du_fait == date(2026, 6, 30) and _f.structure["period_end"] == "2026-06-30",
      f"→ {_f.datation.date_du_fait}")
check("§3 (#79) le DOCUMENT est daté du dépôt, pas de la clôture : les deux dates sont distinctes "
      "et `source_date` dérive de celle du FAIT",
      _f.datation.date_du_document == date(2026, 8, 5)
      and _f.datation.date_du_document != _f.datation.date_du_fait
      and _f.datation.source_date() == _f.datation.date_du_fait,
      f"→ doc={_f.datation.date_du_document} fait={_f.datation.date_du_fait}")
check("§3 un fait de bilan pur est marqué `stock` et non `flow` : le cadrage décide de l'identité du "
      "fait en base (clé par `metric` seul pour un stock, `metric`+`end` pour un flux)",
      _f.structure["poste_kind"] == "stock" and _f.flux is False,
      f"→ {_f.structure['poste_kind']}, flux={_f.flux}")

# LE CADRAGE MIXTE : une intensité (un flux rapporté à un solde) porte ses DEUX dates. Les confondre
# reviendrait à supposer l'une des deux, et c'est exactement le défaut de sens que ce module refuse.
try:
    _f_mixte = _fait(ConsigneAppariement(
        statut="approximation",
        expression="ResearchAndDevelopmentExpense / CashAndCashEquivalentsAtCarryingValue",
        deterministe=True))
    _mixte, _periode_mixte = _f_mixte.structure, _f_mixte.fiscal_period
except AppariementInexecutable as _e:
    _mixte = {"ancre_flux": None, "ancre_bilan": None, "period_end": None}
    _periode_mixte = f"REFUSÉ — {_e}"
_ancres_mixte = [d for d in (_mixte["ancre_flux"], _mixte["ancre_bilan"]) if d]
check("§3 une formule MIXTE (flux ÷ bilan) porte ses DEUX ancres, séparément : un flux appartient à "
      "un exercice, un solde date d'un instant, et en supposer une seule fabrique du faux",
      len(_ancres_mixte) == 2 and "FLUX" in _periode_mixte and "BILAN" in _periode_mixte,
      f"→ {_periode_mixte}")
check("§3 la date du fait mixte est la PLUS RÉCENTE des deux ancres — l'instant à partir duquel il "
      "est affirmable ; le dater de la plus ancienne le ferait vieillir le jour de son écriture",
      bool(_ancres_mixte) and _mixte["period_end"] == max(_ancres_mixte),
      f"→ period_end={_mixte['period_end']}, ancres={_ancres_mixte}")
check("§3 l'URL de source pointe un dépôt RÉEL (l'accession du point le plus récent) : une "
      "provenance non ouvrable est une promesse, pas une preuve",
      _f.source_url and "1770561" in _f.source_url and "000126000007" in _f.source_url.replace(
          "-", ""),
      f"→ {_f.source_url}")


# ── §4 LE TIER SE DÉRIVE, ET UN RELEVÉ N'EST PAS UN CALCUL ────────────────────────────────────────
print("\n[4] le tier dérivé — `exact` n'est pas un calcul, et le déterminisme change le verdict (#67)")

_f_exact = _fait(_CONS_EXACT)
check("§4 `exact` ne dérive AUCUN tier (`fiabilite is None`) : l'entry sera scorée par sa SOURCE "
      "comme tout relevé EDGAR. Le passer par `derive_tier_calcul` lui ferait hériter « du plus "
      "faible de ses ingrédients » alors qu'il n'en a pas — un calcul à un terme n'est pas un calcul",
      _f_exact.fiabilite is None, f"→ {_f_exact.fiabilite}")
check("§4 un `exact` le DIT dans son contenu (relevé recopié tel quel) : le lecteur distingue une "
      "recopie d'un calcul sans avoir à relire la carte",
      "EXACT" in _f_exact.contenu, f"→ {_f_exact.contenu[:120]!r}")

_f_det = _fait(_CONS_APPROX)
_f_non_det = _fait(_CONS_APPROX._replace(deterministe=False))
# `RELIABILITY_TABLE` rend (tier, score) et `derive_tier_calcul` rend (score, tier, note) : les deux
# ordres coexistent dans le code, et les lire à l'envers ici aurait fabriqué un faux rouge.
_tier_a, _score_a = RELIABILITY_TABLE[SOURCE_TYPE]
check("§4 une approximation DÉTERMINISTE garde le tier du plus faible de ses ingrédients, sans cran : "
      "tous ses termes sont `edgar_official`, donc tier A (#67)",
      _f_det.fiabilite is not None and _f_det.fiabilite[1] == _tier_a,
      f"→ {_f_det.fiabilite}")
check("§4 la MÊME formule déclarée NON déterministe descend d'un cran : c'est le déterminisme qui "
      "discrimine, pas la nature des ingrédients — les deux calculs ont les mêmes",
      _f_non_det.fiabilite is not None and _f_non_det.fiabilite[1] != _f_det.fiabilite[1]
      and _f_non_det.fiabilite[0] < _f_det.fiabilite[0],
      f"→ det={_f_det.fiabilite} vs non_det={_f_non_det.fiabilite}")
check("§4 le caractère déterministe est écrit DANS le fait (structuré et texte) : sans lui, un "
      "calcul non déterministe se relit comme un relevé",
      _f_det.structure["deterministe"] is True and "DÉTERMINISTE" in _f_det.contenu
      and _f_non_det.structure["deterministe"] is False
      and "NON DÉTERMINISTE" in _f_non_det.contenu,
      f"→ {_f_det.structure['deterministe']} / {_f_non_det.structure['deterministe']}")
check("§4 le score dérivé est LU dans `RELIABILITY_TABLE`, jamais écrit ici : une troisième table "
      "aurait divergé des deux autres au premier ajustement (#46)",
      (_f_det.fiabilite or (None,))[0] == _score_a,
      f"→ {(_f_det.fiabilite or (None,))[0]} vs table={_score_a}")


# ── §5 AUCUN VOCABULAIRE DE FRAMEWORK, ET AUCUN SCORE ÉCRIT DANS CE MODULE ────────────────────────
# L'aveuglement est une propriété du TYPE (#58) : ce module ne reçoit pas le couple, donc il ne peut
# pas l'écrire. L'assert de forme ci-dessous le tient là où une relecture ne le tiendrait pas.
print("\n[5] l'entry ne peut pas nommer la question, et le module n'écrit aucun score")

check("§5 `ConsigneAppariement` ne porte aucun champ de question : le producteur ne REÇOIT pas le "
      "vocabulaire de framework, il n'a donc pas à s'abstenir de l'écrire",
      not (set(ConsigneAppariement._fields)
           & {"question_id", "ingredient_id", "framework_id", "question"}),
      f"→ {ConsigneAppariement._fields}")
_texte = (_f.contenu + " " + _f.titre + " " + repr(_f.structure) + " " + " ".join(_f.tags)).lower()
# LE MOTIF INTERDIT EST `ingredient_id`, PAS `ingredient`. La première rédaction cherchait le second
# et rougissait sur la clef `ingredients` du structuré — c'est-à-dire sur la PROVENANCE, la chose que
# ce module est fait pour écrire. Un faux rouge se creuse avant de se corriger : le tort était dans
# la sonde, pas dans le fait produit (`feedback_faux_rouge_se_creuse`).
check("§5 aucun fragment de vocabulaire de framework dans le fait produit (contenu, titre, "
      "structuré, tags) — `us-gaap` n'en est pas : c'est le plan comptable américain (#58)",
      not any(j in _texte for j in ("qf_", "framework", "question_id", "ingredient_id")),
      f"→ {_texte[:200]!r}")

import ast  # noqa: E402
from pathlib import Path  # noqa: E402

import app.knowledge.appariement_feed as _mod  # noqa: E402

_SRC = Path(_mod.__file__).read_text(encoding="utf-8")
_ARBRE = ast.parse(_SRC)
# UN SCORE EN DUR SERAIT UNE TROISIÈME TABLE. On cherche les littéraux flottants qui ressemblent à un
# score (0 < x <= 1) ailleurs que dans les tests de ce fichier — l'AST, jamais un grep, parce que la
# prose du module CITE les tiers pour les expliquer (`feedback_grep_interdit_lit_sa_propre_enonciation`).
_scores = [n.value for n in ast.walk(_ARBRE)
           if isinstance(n, ast.Constant) and isinstance(n.value, float) and 0 < n.value <= 1]
check("§5 aucun score en dur dans le module : le seul (tier, score) qui y apparaît est LU dans "
       "`RELIABILITY_TABLE`, et le cran vient de `derive_synthesis_reliability` (#46/#67)",
      _scores == [], f"→ {_scores}")
_tiers = [n.value for n in ast.walk(_ARBRE)
          if isinstance(n, ast.Constant) and n.value in ("A", "B", "C", "D")]
check("§5 aucune lettre de tier en dur non plus : un `\"A\"` posé ici survivrait à un changement de "
      "la table et publierait un tier que personne n'a décidé",
      _tiers == [], f"→ {_tiers}")

# ── §6 LE TEMPOREL — une croissance annuelle S'EXÉCUTE, et le fait porte la période la plus récente ─
# La grammaire sait désormais référencer le même concept à un exercice antérieur (`Revenues[-1]`).
# C'est ce qui débloque l'archétype `rentable` (qf_3 « progression de l'activité, exercice par
# exercice ») : le producteur lit `Revenues` à DEUX exercices et calcule la variation, là où le
# modèle inventait `Revenues_previous_year`. Ce module en est l'exécution.
print("\n[6] le temporel — `Revenues[-1]` s'exécute, le fait est daté de l'exercice le plus récent")

_FACTS_CROISSANCE = {
    "Revenues": [
        _flux("2023-12-31", 100_000_000_000.0, start="2023-01-01", fy=2023),
        _flux("2024-12-31", 120_000_000_000.0, start="2024-01-01", fy=2024),
        _flux("2025-12-31", 150_000_000_000.0, start="2025-01-01", fy=2025),
    ],
}
_CONS_CROISSANCE = ConsigneAppariement(
    statut="approximation",
    expression="(Revenues[0] - Revenues[-1]) / Revenues[-1]",
    hypotheses=("progression mesurée d'un exercice annuel au suivant, sur les exercices déposés",),
    deterministe=True)

# Le chemin complet est CAPTURÉ, jamais laissé propager : un assert qui tue le script avant son bilan
# se lit comme une absence de mesure, pas comme un échec nommé (`feedback_bilan_par_sa_forme`).
try:
    _points_c, _af_c, _ab_c = resoudre_points(_CONS_CROISSANCE, _FACTS_CROISSANCE)
    _f_c = construire_fait_apparie("NVDA", "NVDA", 1045810, "progression de l'activité",
                                   _CONS_CROISSANCE, _points_c, ancre_flux=_af_c, ancre_bilan=_ab_c)
except AppariementInexecutable as _e:
    _points_c, _af_c, _ab_c = {}, None, None

    class _Vide:  # sentinelle : chaque assert de §6 rougit proprement, sans KeyError ni AttributeError
        structure = {"value": None, "period_end": None, "ingredients": []}
        contenu = f"REFUSÉ — {_e}"
        fiabilite = None
    _f_c = _Vide()
check("§6 une croissance annuelle S'EXÉCUTE : (150 − 120) / 120 = 0,25, le même concept lu à deux "
      "exercices — pas un `Revenues_previous_year` inventé",
      _f_c.structure["value"] is not None and abs(_f_c.structure["value"] - 0.25) < 1e-9,
      f"→ {_f_c.structure['value']}")
check("§6 le fait est daté de l'exercice le PLUS RÉCENT (offset 0), pas de l'exercice antérieur qui "
      "n'est que sa provenance : une croissance est affirmable « au dernier exercice »",
      _f_c.structure["period_end"] == "2025-12-31" and _af_c == "2025-12-31",
      f"→ period_end={_f_c.structure['period_end']}, ancre_flux={_af_c}")
check("§6 la provenance NOMME l'exercice de chaque terme (`offset`) : le lecteur voit que Revenues a "
      "été lu à 2025 ET à 2024, et lequel est lequel",
      sorted((i["concept"], i["offset"], i["end"]) for i in _f_c.structure["ingredients"])
      == [("Revenues", -1, "2024-12-31"), ("Revenues", 0, "2025-12-31")],
      f"→ {_f_c.structure['ingredients']}")
# LE FAIT QUE MON PROPRE CHANGEMENT A INTRODUIT, ET QU'IL FAUT GARDER : un résultat SANS DIMENSION
# (une croissance = flux ÷ flux) rendu par `montant` serait arrondi à « 0 » (sa mantisse ne vaut que
# pour les paliers M/Md). Le nombre structuré serait juste et le CONTENU mentirait (#42/#45).
check("§6 un résultat SANS DIMENSION est rendu à chiffres significatifs dans le contenu (`0,25`), "
      "jamais arrondi à « 0 » par `montant` : le contenu est ce que l'agent lit (#42/#45)",
      "0,25" in _f_c.contenu and " 0 sans dimension" not in _f_c.contenu, f"→ {_f_c.contenu[:90]!r}")
check("§6 le tier d'une croissance déterministe reste A (tous les termes sont `edgar_official`, la "
      "formule est fermée) : le décalage d'exercice n'ajoute aucune incertitude (#67)",
      _f_c.fiabilite is not None and _f_c.fiabilite[1] == RELIABILITY_TABLE[SOURCE_TYPE][0],
      f"→ {_f_c.fiabilite}")

# LE REFUS NOMMÉ : un émetteur qui n'a pas assez d'historique. `Revenues[-1]` sur une seule année ne
# se replie PAS sur le point courant (une croissance de 0 %, fait faux et rassurant) — il refuse.
_m = leve(resoudre_points, _CONS_CROISSANCE,
          {"Revenues": [_flux("2025-12-31", 150_000_000_000.0, start="2025-01-01", fy=2025)]})
check("§6 un exercice décalé ABSENT (émetteur sans historique) est un refus NOMMÉ, jamais un repli "
      "sur le point courant : le motif dit l'exercice manquant et les exercices lisibles",
      _m is not None and "Revenues[-1]" in _m and "2025-12-31" in _m, f"→ {_m!r}")

# LE FUTUR N'EXISTE PAS — la garde de forme du contrat, éprouvée au point de production. `Revenues[1]`
# est refusé à l'analyse, avant toute lecture de dépôt.
_m = leve(resoudre_points, ConsigneAppariement(
    statut="approximation", expression="Revenues[1] - Revenues", deterministe=True),
    _FACTS_CROISSANCE)
check("§6 un décalage POSITIF (`Revenues[1]`, un exercice futur) est refusé : un exercice postérieur "
      "au plus récent n'existe pas",
      _m is not None and ("POSITIF" in _m or "positif" in _m.lower()), f"→ {_m!r}")


print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
