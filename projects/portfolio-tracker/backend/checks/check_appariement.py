"""Vérification de l'APPARIEMENT PAR TICKER (chantier v3, lot 3 maillon 4bis — convention #67).

Deux fichiers sous test, et ils se répondent : le contrat
(`app/contracts/appariement_schema.py`) dit ce qu'une ligne d'appariement a le DROIT d'être ; le pont
(`app/agents/v2/apparieur.py`) la confronte à l'INVENTAIRE réellement déposé par l'émetteur et au
plan dont elle dérive. Plus la règle de tier (`synthesis_feed.derive_tier_calcul`), qui est le seul
endroit où le prix d'un calcul se décide.

Sans réseau, sans modèle, sans base : le pont reçoit l'inventaire DÉJÀ LU, donc tout ce fichier est
la frontière gratuite du maillon — il se rejoue après chaque correctif sans dépenser un appel.

  • §1 VOCABULAIRE FERMÉ ET ATTEIGNABLE (#32) — les TROIS états, chacun atteint PAR SON NOM depuis
       un objet réellement construit. Trois, jamais deux : c'est la case du milieu qui porte
       l'information, et un système à deux états n'a le choix qu'entre mentir et renoncer.
  • §2 LE STATUT PORTE EXACTEMENT SA CHARGE — l'obligation ET l'interdiction. L'interdiction est la
       moitié qui compte : elle empêche un raisonnement de se déclarer relevé (`exact` + formule) et
       une absence de porter un champ déposé (`indisponible` + concepts).
  • §3 LA CONTRAINTE PORTE SUR L'ÉLÉMENT, PAS SUR LA LISTE — `hypotheses=[""]` est une liste NON
       VIDE d'éléments vides : elle satisfait `if not hypotheses` et viderait de sa charge la garde
       « une approximation s'explique ».
  • §4 `deterministe` SE TESTE `is not None`, JAMAIS PAR VÉRITÉ — `False` est falsy : un `exact`
       portant `deterministe=False` traverserait un `if val` sans être vu. La garde serait aveugle à
       exactement la moitié des cas.
  • §5 AUCUN CHAMP DE TIER (#53/#59) — `Strict` REFUSE `tier`/`score` à la construction. La doctrine
       « le tier se dérive, il ne se déclare pas » est impossible à violer, pas gardée par un `if`.
  • §6 LA RÈGLE DE TIER #67, UN SEUL DISCRIMINANT ET UN SEUL DÉTENTEUR (#46) — le déterminisme, et
       rien d'autre. La branche non déterministe rend EXACTEMENT ce que rend la règle acquise du
       2026-09-13 : elle l'APPELLE. Et `apparieur.py` n'écrit aucune table de tier.
  • §7 LE PONT CONTRE LE RÉEL [V]/[W]/[X] — la garde qui manquait à `poste_retenu()`.
  • §8 LE PONT CONTRE LE PLAN [S]/[T]/[U] — l'omission d'un appariement est une carte REFUSÉE.
  • §9 CE QUE CE PONT N'ATTRAPE PAS, ET QUI EST DIT — le faux appariement SÉMANTIQUE passe [V].
       L'assert garde l'ÉNONCÉ de cette limite, jamais un comportement, et il le dit.

POURQUOI CHAQUE REFUS DÉCLARE SON MOTIF (#56)
----------------------------------------------
Un test négatif qui ne nomme pas la règle qui a rougi mesure sa propre fixture : un objet peut être
refusé par une contrainte de forme oubliée plutôt que par l'invariant visé (4ᵉ faux vert). Mesuré
ici même pendant l'écriture : `concepts=['A','B']` pour éprouver « un exact n'a qu'un concept » était
refusé par le `min_length=2` de `ConceptDepose`, et le validateur de charge n'était JAMAIS atteint.
Chaque cas déclare donc un fragment du message attendu, et un refus prononcé par une AUTRE règle est
un FAIL.

Cible : pydantic v2 (container backend). Tester en container, **pas** le python hôte (v1).
"""
import sys
from pathlib import Path
from typing import get_args

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Bilan, strip_code  # noqa: E402

from app.agents.v2.apparieur import (  # noqa: E402
    AppariementRefuse,
    coefficients_choisis,
    concepts_de_la_formule,
    valider_pont_appariement,
)
from app.contracts.appariement_schema import (  # noqa: E402
    APPARIEMENT_SCHEMA_VERSION,
    STATUTS_APPARIEMENT,
    AppariementCarte,
    AppariementItem,
)
from app.contracts.collection_plan_schema import (  # noqa: E402
    COLLECTION_PLAN_SCHEMA_VERSION,
    CollectionPlan,
    CollectionPlanItem,
)
from app.knowledge.synthesis_feed import (  # noqa: E402
    derive_synthesis_reliability,
    derive_tier_calcul,
)

b = Bilan()

RACINE = Path(__file__).resolve().parent.parent
SRC_APPARIEUR = (RACINE / "app/agents/v2/apparieur.py").read_text(encoding="utf-8")
SRC_CONTRAT = (RACINE / "app/contracts/appariement_schema.py").read_text(encoding="utf-8")

# L'inventaire de fixture est COPIÉ DU RÉEL (`feedback_fixture_copiee_du_reel`) : ce sont des
# concepts relevés dans `tools/cartographier_xbrl.sh` sur NVDA le 2026-09-17. Une fixture plus
# généreuse que le dépôt ferait passer [V] sur des noms que l'émetteur ne dépose pas — un check
# aveugle au vert, qui neutraliserait aussi son propre test négatif.
INVENTAIRE_NVDA = {
    "Assets", "AssetsCurrent", "Liabilities", "LiabilitiesCurrent", "StockholdersEquity",
    "CashAndCashEquivalentsAtCarryingValue", "ShortTermInvestments", "NetIncomeLoss",
    "NetCashProvidedByUsedInOperatingActivities", "PaymentsToAcquirePropertyPlantAndEquipment",
    "IncomeTaxExpenseBenefit", "OperatingIncomeLoss", "ShareBasedCompensation",
    "DepreciationDepletionAndAmortization", "InventoryNet",
}


def ligne(**kw) -> AppariementItem:
    kw.setdefault("question_id", "qf_1")
    kw.setdefault("ingredient_id", "capital_employe")
    return AppariementItem(**kw)


def carte(*items, **kw) -> AppariementCarte:
    kw.setdefault("ticker_id", "NVDA")
    kw.setdefault("framework_id", "qualite_financiere")
    kw.setdefault("framework_version", "v3.0.0")
    kw.setdefault("dernier_depot_vu", "2026-06-30")
    return AppariementCarte(items=list(items), **kw)


def rejete(label: str, fragment: str, fabrique) -> None:
    """L'objet doit être REFUSÉ, et refusé par la règle qui porte `fragment`. Un refus prononcé par
    une autre règle est un FAIL — sinon le test mesure sa fixture, pas l'invariant.

    ⚠️ `ValueError` est dans la liste pour une raison mesurée pendant l'écriture : `derive_tier_calcul`
    refuse une liste vide par un `ValueError` nu, que la première version n'attrapait pas — le script
    MOURAIT à cet endroit, et les trois sections suivantes n'étaient jamais exécutées. Un check qui
    s'arrête avant ses asserts ne rend pas un bilan faux, il ne rend pas de bilan du tout : c'est
    pour ça que `run_all.sh` lit la FORME du bilan et traite son absence comme un échec.
    (`ValidationError` de pydantic v2 hérite de `ValueError` ; on la garde nommée pour la lisibilité.)
    """
    try:
        fabrique()
    except (ValidationError, ValueError, AppariementRefuse) as e:
        b.check(fragment in str(e),
                f"{label} — refusé, mais par la règle attendue ? (cherché « {fragment} »)")
        return
    b.check(False, f"{label} — ACCEPTÉ alors qu'il devait être refusé")


def accepte(label: str, fabrique) -> None:
    try:
        fabrique()
        b.check(True, label)
    except (ValidationError, AppariementRefuse) as e:
        b.check(False, f"{label} — refusé à tort : {str(e)[:160]}")


# La ligne nominale du maillon : `capital_employe`, l'exemple qui MOTIVE la troisième case. NVDA
# dépose les quatre postes, la soustraction est à portée, et elle sort en tier A — là où le système
# à deux états l'envoyait chercher au web un nombre que personne ne publie.
CAPITAL_EMPLOYE = dict(
    statut="approximation",
    concepts=["Assets", "LiabilitiesCurrent", "CashAndCashEquivalentsAtCarryingValue"],
    formule="Assets - LiabilitiesCurrent - CashAndCashEquivalentsAtCarryingValue",
    hypotheses=["la trésorerie est exclue du capital employé"],
    deterministe=True,
)

print("§1 VOCABULAIRE FERMÉ ET ATTEIGNABLE (#32) — trois états, jamais deux")
b.check(STATUTS_APPARIEMENT == ("exact", "approximation", "indisponible"),
        "§1 les trois états de #67 sont déclarés dans cet ordre")
litteral = set(get_args(AppariementItem.model_fields["statut"].annotation))
b.check(litteral == set(STATUTS_APPARIEMENT),
        "§1 le `Literal` du champ et la constante disent la même chose (pas deux vocabulaires)")
atteints = {
    "exact": lambda: ligne(statut="exact", concepts=["NetIncomeLoss"]),
    "approximation": lambda: ligne(**CAPITAL_EMPLOYE),
    "indisponible": lambda: ligne(
        statut="indisponible",
        motif="aucun des 627 concepts déposés ne porte les clauses restrictives de dette"),
}
b.require(atteints, 3, "§1 un constructeur par état")
for nom, fab in atteints.items():
    b.check(fab().statut == nom, f"§1 l'état `{nom}` est ATTEINT par son nom, pas seulement déclaré")
b.check(APPARIEMENT_SCHEMA_VERSION == COLLECTION_PLAN_SCHEMA_VERSION,
        "§1 même version que le plan de collecte — une seule horloge pour le chantier v3")

print("\n§2 LE STATUT PORTE EXACTEMENT SA CHARGE — l'interdiction autant que l'obligation")
accepte("§2 `exact` avec UN concept nu", lambda: ligne(statut="exact", concepts=["NetIncomeLoss"]))
rejete("§2 `exact` à DEUX concepts (c'est déjà une addition)",
       "statut='exact' avec 2 concept(s)",
       lambda: ligne(statut="exact", concepts=["NetIncomeLoss", "Assets"]))
rejete("§2 `exact` à ZÉRO concept (c'est un indisponible)",
       "statut='exact' avec 0 concept(s)",
       lambda: ligne(statut="exact", concepts=[]))
rejete("§2 `exact` portant une formule (un raisonnement déguisé en relevé)",
       "statut='exact' porte ['formule']",
       lambda: ligne(statut="exact", concepts=["NetIncomeLoss"], formule="NetIncomeLoss * 2"))
accepte("§2 `approximation` nominale (capital_employe)", lambda: ligne(**CAPITAL_EMPLOYE))
rejete("§2 `approximation` sans hypothèse (un `exact` déguisé)",
       "ce que l'état `approximation` achète",
       lambda: ligne(**{**CAPITAL_EMPLOYE, "hypotheses": []}))
rejete("§2 `approximation` sans formule",
       "ce que l'état `approximation` achète",
       lambda: ligne(**{**CAPITAL_EMPLOYE, "formule": None}))
rejete("§2 `approximation` sans aucun concept déposé (c'est une recherche web)",
       "sans aucun concept déposé",
       lambda: ligne(**{**CAPITAL_EMPLOYE, "concepts": [], "formule": "AutreChose - Encore"}))
rejete("§2 `approximation` portant un motif (une formule n'a pas d'excuse)",
       "porte un `motif`",
       lambda: ligne(**{**CAPITAL_EMPLOYE, "motif": "un motif suffisamment long pour passer"}))
accepte("§2 `indisponible` avec son motif",
        lambda: ligne(statut="indisponible",
                      motif="aucun des 627 concepts déposés ne porte cette information"))
rejete("§2 `indisponible` sans motif (un trou déguisé)",
       "sans `motif`",
       lambda: ligne(statut="indisponible"))
rejete("§2 `indisponible` portant un concept (contradiction #44)",
       "statut='indisponible' porte ['concepts']",
       lambda: ligne(statut="indisponible", concepts=["Liabilities"],
                     motif="aucun des 627 concepts déposés ne porte cette information"))

print("\n§3 LA CONTRAINTE PORTE SUR L'ÉLÉMENT, PAS SUR LA LISTE")
rejete("§3 `hypotheses=['']` — liste NON VIDE d'éléments vides",
       "hypotheses.0",
       lambda: ligne(**{**CAPITAL_EMPLOYE, "hypotheses": [""]}))
rejete("§3 un concept qui n'a pas la forme d'un nom XBRL",
       "concepts.0",
       lambda: ligne(statut="exact", concepts=["net income loss"]))
rejete("§3 `termes_web=['']`",
       "termes_web.0",
       lambda: ligne(**{**CAPITAL_EMPLOYE, "termes_web": [""]}))

print("\n§4 `deterministe` SE TESTE `is not None`, JAMAIS PAR VÉRITÉ — `False` est falsy")
rejete("§4 `exact` + `deterministe=False` (la moitié falsy de la garde)",
       "statut='exact' porte ['deterministe']",
       lambda: ligne(statut="exact", concepts=["NetIncomeLoss"], deterministe=False))
rejete("§4 `indisponible` + `deterministe=False`",
       "statut='indisponible' porte ['deterministe']",
       lambda: ligne(statut="indisponible", deterministe=False,
                     motif="aucun des 627 concepts déposés ne porte cette information"))
rejete("§4 `approximation` sans `deterministe` — le discriminant est obligatoire",
       "discriminant UNIQUE de la règle de tier",
       lambda: ligne(**{**CAPITAL_EMPLOYE, "deterministe": None}))

print("\n§5 AUCUN CHAMP DE TIER (#53/#59) — la doctrine est impossible à violer, pas gardée par un `if`")
for champ in ("tier", "score", "fiabilite", "plancher_tier"):
    b.check(champ not in AppariementItem.model_fields,
            f"§5 `{champ}` n'est pas un champ du contrat")
    rejete(f"§5 `{champ}` refusé à la construction par `extra='forbid'`",
           champ,
           lambda c=champ: ligne(statut="exact", concepts=["NetIncomeLoss"], **{c: "A"}))

print("\n§6 LA RÈGLE DE TIER #67 — un seul discriminant, un seul détenteur (#46)")
# Déterministe sur tout-A : le tier ne bouge pas. 2+2=4 n'est pas moins sûr que 2 et 2.
s, t, _ = derive_tier_calcul([("A", 0.95)] * 4, deterministe=True)
b.check((t, s) == ("A", 0.95), "§6 déterministe, ingrédients tous A → A sans cran")
# Mixte déterministe : le tier du plus FAIBLE, sans cran — le calcul n'ajoute pas d'incertitude.
s, t, _ = derive_tier_calcul([("A", 0.95), ("B", 0.65)], deterministe=True)
b.check((t, s) == ("B", 0.65), "§6 déterministe, ingrédients mixtes → tier du plus faible, SANS cran")
# Non déterministe : un cran sous le plus faible — et c'est LA MÊME fonction que la règle acquise.
s, t, _ = derive_tier_calcul([("A", 0.95)], deterministe=False)
attendu = derive_synthesis_reliability(["A"])
b.check((s, t) == attendu[:2],
        "§6 non déterministe = EXACTEMENT `derive_synthesis_reliability` (appelée, pas recopiée)")
s2, t2, _ = derive_tier_calcul([("A", 0.95), ("B", 0.65)], deterministe=False)
b.check((s2, t2) == derive_synthesis_reliability(["A", "B"])[:2],
        "§6 la coïncidence tient aussi sur des ingrédients mixtes (pas un accident sur un cas)")
b.check(t != t2 or s != s2,
        "§6 le cran DISCRIMINE : deux jeux d'ingrédients différents ne rendent pas le même tier")
# L'ordre de la liste ne doit rien changer — une non-détermination dans la fonction qui juge du
# déterminisme serait la faute la plus difficile à voir.
b.check(derive_tier_calcul([("A", 0.95), ("A", 0.90)], deterministe=True)
        == derive_tier_calcul([("A", 0.90), ("A", 0.95)], deterministe=True),
        "§6 à tier égal, le résultat ne dépend pas de l'ORDRE des ingrédients")
rejete("§6 aucun ingrédient → refus, jamais un tier par défaut",
       "aucun ingrédient",
       lambda: derive_tier_calcul([], deterministe=True))
# #46 : le pont ne réécrit aucune table de tier. Lu sur le CODE dépouillé de sa prose, sinon
# l'énonciation de l'interdit dans la docstring ferait rougir le test (faux ROUGE mesuré sur ce
# projet — `feedback_grep_interdit_lit_sa_propre_enonciation`).
code_apparieur = strip_code(SRC_APPARIEUR)
for interdit in ('"A-"', "'A-'", '"B+"', "'B+'", "NOTCH", "TIER_RANK"):
    b.check(interdit not in code_apparieur,
            f"§6 `apparieur.py` n'écrit pas `{interdit}` — le tier ne se décide pas dans le pont")
# ⚠️ La première version de cet assert cherchait le MOT « tier » dans le code dépouillé du contrat,
# et rougissait sur trois occurrences qui sont toutes de la prose : une `description=` de `Field` et
# deux messages d'erreur. `strip_code` retire les docstrings et les commentaires, pas les chaînes
# ARGUMENTS — et c'est correct, une chaîne passée à une fonction est du code. L'assert était faux,
# pas le contrat : ce qui compte n'est pas que le mot soit absent, c'est qu'aucune VALEUR de tier n'y
# soit écrite, car une valeur recopiée diverge (#46) là où un mot n'engage rien.
code_contrat = strip_code(SRC_CONTRAT)
for interdit in ('"A-"', "'A-'", '"B+"', "'B+'", '"A"', "'A'"):
    b.check(interdit not in code_contrat,
            f"§6 le contrat n'écrit aucune valeur de tier ({interdit}) — il n'en déclare pas")

print("\n§7 LE PONT CONTRE LE RÉEL [V]/[W]/[X] — la garde absente de `poste_retenu()`")
accepte("§7 carte nominale contre l'inventaire NVDA",
        lambda: valider_pont_appariement(carte(ligne(**CAPITAL_EMPLOYE)), INVENTAIRE_NVDA))
rejete("§7 [V] un concept VOISIN d'un concept réel, non déposé",
       "que cet émetteur NE DÉPOSE PAS",
       lambda: valider_pont_appariement(
           carte(ligne(statut="exact", ingredient_id="stocks", concepts=["InventoryNetCurrent"])),
           INVENTAIRE_NVDA))
rejete("§7 [V] un concept réel ailleurs, absent de CE dépôt (les 6 postes manquants de RVMD)",
       "que cet émetteur NE DÉPOSE PAS",
       lambda: valider_pont_appariement(
           carte(ligne(statut="exact", ingredient_id="stocks", concepts=["InventoryNet"])),
           INVENTAIRE_NVDA - {"InventoryNet"}))
rejete("§7 [V] inventaire VIDE = défaut de récupération, jamais un émetteur muet",
       "inventaire VIDE",
       lambda: valider_pont_appariement(carte(ligne(**CAPITAL_EMPLOYE)), set()))
rejete("§7 [W] un concept qui n'existe QUE dans la formule échapperait à [V]",
       "sans les déclarer en `concepts`",
       lambda: valider_pont_appariement(
           carte(ligne(**{**CAPITAL_EMPLOYE,
                          "formule": CAPITAL_EMPLOYE["formule"] + " - InventeDeToutePiece"})),
           INVENTAIRE_NVDA))
rejete("§7 [W] un concept déclaré mais absent de la formule pèse sur le tier sans contribuer",
       "sans les employer dans sa formule",
       lambda: valider_pont_appariement(
           carte(ligne(**{**CAPITAL_EMPLOYE,
                          "concepts": CAPITAL_EMPLOYE["concepts"] + ["ShareBasedCompensation"]})),
           INVENTAIRE_NVDA))
rejete("§7 [X] `deterministe=True` sur une formule à coefficient choisi (investissement_de_maintien)",
       "un coefficient décimal est un paramètre CHOISI",
       lambda: valider_pont_appariement(
           carte(ligne(statut="approximation", ingredient_id="investissement_de_maintien",
                       concepts=["PaymentsToAcquirePropertyPlantAndEquipment"],
                       formule="0.6 * PaymentsToAcquirePropertyPlantAndEquipment",
                       hypotheses=["60 % du capex est du capex de maintien"],
                       deterministe=True)),
           INVENTAIRE_NVDA))
accepte("§7 [X] le MÊME calcul déclaré non déterministe est accepté (il descendra d'un cran)",
        lambda: valider_pont_appariement(
            carte(ligne(statut="approximation", ingredient_id="investissement_de_maintien",
                        concepts=["PaymentsToAcquirePropertyPlantAndEquipment"],
                        formule="0.6 * PaymentsToAcquirePropertyPlantAndEquipment",
                        hypotheses=["60 % du capex est du capex de maintien"],
                        deterministe=False)),
            INVENTAIRE_NVDA))
accepte("§7 [X] un ENTIER reste déterministe (conversion d'unité, pas un paramètre)",
        lambda: valider_pont_appariement(
            carte(ligne(statut="approximation", ingredient_id="capex_trimestriel",
                        concepts=["PaymentsToAcquirePropertyPlantAndEquipment"],
                        formule="PaymentsToAcquirePropertyPlantAndEquipment / 4",
                        hypotheses=["le capex est réparti uniformément sur l'exercice"],
                        deterministe=True)),
            INVENTAIRE_NVDA))
b.check(concepts_de_la_formule("Assets - LiabilitiesCurrent / 4") ==
        {"Assets", "LiabilitiesCurrent"},
        "§7 `concepts_de_la_formule` lit les identifiants CamelCase et rien d'autre")
b.check(coefficients_choisis("0.6 * X") == ["0.6"] and coefficients_choisis("X / 4") == [],
        "§7 `coefficients_choisis` distingue un décimal d'un entier")

print("\n§8 LE PONT CONTRE LE PLAN [S]/[T]/[U]")
PLAN = CollectionPlan(
    ticker_id="NVDA", framework_id="qualite_financiere", framework_version="v3.0.0",
    archetype="compounder_rentable",
    items=[
        CollectionPlanItem(question_id="qf_1", ingredient_id="capital_employe", statut="traduit",
                           metrique="capitaux employés", source_pressentie="10-K",
                           ancre="clôture de l'exercice"),
        CollectionPlanItem(question_id="qf_2", ingredient_id="clauses_restrictives",
                           statut="inobtenable",
                           motif="les covenants sont du texte contractuel, aucun montant déposé"),
    ])
accepte("§8 carte complète contre son plan",
        lambda: valider_pont_appariement(
            carte(ligne(**CAPITAL_EMPLOYE)), INVENTAIRE_NVDA, plan=PLAN))
rejete("§8 [U] carte et plan sur des versions différentes",
       "[U] la carte porte sur",
       lambda: valider_pont_appariement(
           carte(ligne(**CAPITAL_EMPLOYE), framework_version="v2.0.0"),
           INVENTAIRE_NVDA, plan=PLAN))
rejete("§8 [S] apparier une ligne que le plan déclare `inobtenable` (contradiction)",
       "est `inobtenable` au plan",
       lambda: valider_pont_appariement(
           carte(ligne(**CAPITAL_EMPLOYE),
                 ligne(question_id="qf_2", ingredient_id="clauses_restrictives",
                       statut="exact", concepts=["Liabilities"])),
           INVENTAIRE_NVDA, plan=PLAN))
rejete("§8 [S] apparier un ingrédient absent du plan",
       "apparié sans ligne au plan",
       lambda: valider_pont_appariement(
           carte(ligne(**CAPITAL_EMPLOYE),
                 ligne(question_id="qf_9", ingredient_id="invente", statut="exact",
                       concepts=["Assets"])),
           INVENTAIRE_NVDA, plan=PLAN))
rejete("§8 [T] une ligne `traduit` SANS appariement — l'omission est une carte refusée",
       "n'ont AUCUN appariement",
       lambda: valider_pont_appariement(
           carte(ligne(question_id="qf_2", ingredient_id="clauses_restrictives",
                       statut="indisponible",
                       motif="les covenants sont du texte, aucun montant déposé")),
           INVENTAIRE_NVDA,
           plan=CollectionPlan(
               ticker_id="NVDA", framework_id="qualite_financiere", framework_version="v3.0.0",
               archetype="compounder_rentable",
               items=[PLAN.items[0],
                      CollectionPlanItem(question_id="qf_2",
                                         ingredient_id="clauses_restrictives", statut="traduit",
                                         metrique="covenants", source_pressentie="10-K",
                                         ancre="clôture de l'exercice")])))

print("\n§9 UN INGRÉDIENT N'EST APPARIÉ QU'UNE FOIS, ET LA LIMITE DU PONT EST ÉCRITE")
rejete("§9 deux appariements pour un même couple (question, ingrédient)",
       "est apparié plusieurs fois",
       lambda: carte(ligne(**CAPITAL_EMPLOYE), ligne(statut="exact", concepts=["Assets"])))
rejete("§9 une carte sans aucune ligne",
       "items",
       lambda: carte())
# ⚠️ Cet assert garde l'ÉNONCÉ d'une limite, jamais un comportement — même discipline que
# `check_collecte_executor` §3bis. Le pont NE PEUT PAS voir qu'apparier « clauses restrictives » à
# `Liabilities` est faux : `Liabilities` est déposé par tous les émetteurs, donc [V] le laisse
# passer. Ce qui s'y oppose est la FORME de la réponse (un `exact` ne porte qu'un concept nu, donc
# tout raisonnement doit sortir en `approximation` écrite et contestable), pas un `if`. Si cette
# limite cesse d'être écrite, un lecteur croira le pont sémantique et s'y fiera.
demo = valider_pont_appariement(
    carte(ligne(question_id="qf_2", ingredient_id="clauses_restrictives", statut="exact",
                concepts=["Liabilities"])),
    INVENTAIRE_NVDA)
b.check(demo is None,
        "§9 le faux appariement SÉMANTIQUE passe [V] — mesuré, pas supposé")
for phrase in ("n'attrape PAS le faux appariement SÉMANTIQUE",
               "gardent donc une STRUCTURE, jamais une sémantique"):
    b.check(phrase in SRC_APPARIEUR,
            f"§9 la limite est ÉCRITE dans `apparieur.py` (« {phrase[:40]}… »)")

sys.exit(b.summary())
