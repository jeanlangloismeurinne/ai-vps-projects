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
    LEGENDE_INVENTAIRE,
    AppariementRefuse,
    AppariementSansObjet,
    coefficients_choisis,
    concepts_absents,
    concepts_de_la_formule,
    dernier_depot_vu,
    derniere_periode_vue,
    mots_du_concept,
    rendre_inventaire,
    resumer_inventaire,
    valider_pont_appariement,
    voisins_deposes,
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

print("\n§10 L'INVENTAIRE COMME OUTIL DE LECTURE — le rendu est un PRODUCTEUR, il se garde")
# POURQUOI CETTE SECTION EXISTE, ET POURQUOI ELLE EST HORS LIGNE.
# La moitié « outil de lecture » de l'apparieur est du code déterministe pur, et elle n'était
# éprouvée que par `tools/inventaire_apparieur.sh`, qui a besoin du réseau. Or c'est elle qui a
# FABRIQUÉ un défaut mesuré contre le vrai modèle : ne montrant qu'un point par concept, elle a fait
# écrire six `indisponible` sur MSFT motivés par « il n'y a pas de série de plusieurs exercices »
# alors que `companyfacts` porte la série entière. Le rendu est donc un producteur au sens de #46/#48
# — ce qu'il OMET se lit comme une propriété de l'émetteur — et il se garde comme tel, sans réseau.
#
# La fixture est copiée du réel (`feedback_fixture_copiee_du_reel`) : ce sont les formes de points
# réellement rencontrées sur MSFT/NVDA le 2026-09-17 — un flux annuel républié trois fois sous le
# même `end`, un flux semestriel plus récent que les annuels, un poste de bilan, un concept abandonné
# en 2018, et un concept déposé sans aucun point chiffré.
FACTS_FIXTURE = {
    # Républié 3 fois sous le MÊME `end` (chaque dépôt le reprend en comparatif) + un 2ᵉ exercice.
    # C'est le cas DISCRIMINANT de `nb_dates` : compter les points rendrait 4, la vérité est 2.
    "NetIncomeLoss": [
        {"start": "2024-07-01", "end": "2025-06-30", "val": 88.0, "unit": "USD", "filed": "2025-07-30"},
        {"start": "2024-07-01", "end": "2025-06-30", "val": 88.0, "unit": "USD", "filed": "2026-01-28"},
        {"start": "2024-07-01", "end": "2025-06-30", "val": 88.0, "unit": "USD", "filed": "2026-07-29"},
        {"start": "2025-07-01", "end": "2026-06-30", "val": 133.0, "unit": "USD", "filed": "2026-07-29"},
    ],
    # Le point le PLUS RÉCENT est un semestre, alors que le concept porte aussi de l'annuel : sans
    # `nb_exercices`, la table le donnerait à lire comme une métrique semestrielle.
    "Revenues": [
        {"start": "2024-07-01", "end": "2025-06-30", "val": 270.0, "unit": "USD", "filed": "2025-07-30"},
        {"start": "2026-01-01", "end": "2026-06-30", "val": 145.0, "unit": "USD", "filed": "2026-07-29"},
    ],
    "Assets": [
        {"end": "2025-06-30", "val": 700.0, "unit": "USD", "filed": "2025-07-30"},
        {"end": "2026-06-30", "val": 758.0, "unit": "USD", "filed": "2026-07-29"},
    ],
    # Abandonné : réellement déposé (donc [V] le laisse passer), dernier point vieux de huit ans.
    "AssetImpairmentCharges": [
        {"start": "2017-07-01", "end": "2018-06-30", "val": 0.0, "unit": "USD", "filed": "2018-08-03"},
    ],
    # Nommable, mais rien de chiffré à relever : il reste AFFICHÉ (le vocabulaire lu doit être
    # exactement celui que [V] accepte, sinon le taux de refus mesure notre filtre).
    "SansPointExploitable": [{"end": None, "val": None, "unit": "USD", "filed": "2026-07-29"}],
}
lignes_fx = resumer_inventaire(FACTS_FIXTURE)
par_concept = {l.concept: l for l in lignes_fx}
b.require(lignes_fx, len(FACTS_FIXTURE), "§10 une ligne par concept déposé")
b.check({l.concept for l in lignes_fx} == set(FACTS_FIXTURE),
        "§10 le résumé est TOTAL — égalité d'ensembles, jamais un décompte")
b.check([l.concept for l in lignes_fx] == sorted(FACTS_FIXTURE),
        "§10 tri ALPHABÉTIQUE : le modèle localise un nom et voit ses voisins, pas un classement "
        "par pertinence qui aurait déjà fait l'appariement à sa place")

# LE CAS DISCRIMINANT DE LA PROFONDEUR — celui sans lequel la mesure serait fausse dans le sens
# rassurant : `companyfacts` républie le même `end` à chaque dépôt qui le reprend en comparatif.
ni = par_concept["NetIncomeLoss"]
b.check(ni.nb_dates == 2 and ni.nb_points == 4,
        "§10 `nb_dates` compte les DATES DISTINCTES, pas les points (4 points → 2 dates) : compter "
        "les points surestimerait la profondeur d'un facteur 3 ou 4")
b.check(ni.nb_exercices == 2,
        "§10 `nb_exercices` compte les exercices ANNUELS distincts, pas les points annuels")
b.check(ni.premier_end == "2025-06-30" and ni.dernier_end == "2026-06-30",
        "§10 la série est bornée par ses deux extrémités, toutes deux rendues")

# LE DÉFAUT MESURÉ CONTRE LE VRAI MODÈLE, REPRODUIT ICI : un rendu qui ne montre que le dernier
# point fait conclure à l'absence de série. C'est l'assert qui l'aurait vu — et il porte sur le
# TEXTE RENDU, pas sur le résumé, parce que c'est le texte qui part au modèle (#54 : un contrôle se
# teste au point de lecture).
texte_fx = rendre_inventaire(lignes_fx)


def ligne_rendue(concept: str) -> str:
    """La ligne du texte rendu qui commence par `concept`, ou la chaîne VIDE si le rendu ne la porte
    pas. Le repli n'est pas une commodité : un `next(...)` nu lèverait `StopIteration`, le script
    mourrait AVANT son bilan, et le test négatif classerait la mutation « script mort » au lieu de
    « garde absente » — un assert doit pouvoir ROUGIR, jamais planter (`feedback_test_negatif_trois_faux_verts`)."""
    return next((l for l in texte_fx.splitlines() if l.split()[:1] == [concept]), "")


ligne_ni = ligne_rendue("NetIncomeLoss")
b.check("2 dates depuis 2025-06-30" in ligne_ni,
        "§10 le TEXTE rendu porte la profondeur de la série — sans elle, le modèle répond "
        "`indisponible` « pas de série de plusieurs exercices » sur un concept qui la porte "
        "(mesuré sur MSFT, 6 ingrédients)")
b.check("+A×2" in ligne_ni,
        "§10 le TEXTE rendu porte le NOMBRE d'exercices annuels, pas un simple drapeau `+A` : "
        "« un exercice existe » ne dit pas si « cinq exercices » est servable")
ligne_rev = ligne_rendue("Revenues")
b.check("+A×1" in ligne_rev and "flux 180j" in ligne_rev,
        "§10 un concept dont le point le plus récent est un SEMESTRE annonce quand même son "
        "annuel — sinon le rendu mentirait par omission")
ligne_aic = ligne_rendue("AssetImpairmentCharges")
b.check("1 seule date" in ligne_aic,
        "§10 une profondeur de 1 est imprimée EXPLICITEMENT : c'est elle qui rend un "
        "`indisponible` LÉGITIME sur une question pluriannuelle. L'omettre laisserait deviner")
b.check("2018-06-30" in ligne_aic,
        "§10 la date du dernier point d'un concept ABANDONNÉ est rendue — le trou connu de [V] "
        "n'est pas gardé, il est LISIBLE")
b.check([l.split()[0] for l in texte_fx.splitlines() if l.split()] == sorted(FACTS_FIXTURE),
        "§10 le texte reste RELISIBLE par son premier mot, une ligne par concept — c'est ce qui "
        "permet à la frontière gratuite de prouver sa totalité en relisant son propre rendu")
b.check(ligne_rendue("SansPointExploitable") != "",
        "§10 un concept sans point chiffré reste NOMMÉ : le vocabulaire lu est exactement celui "
        "que [V] accepte, sinon le taux de refus mesurerait notre filtre")

# #46 — la profondeur annuelle APPELLE `is_annual_flow`, elle ne recopie pas ses bornes. Lu sur le
# code DÉPOUILLÉ de sa prose : les bornes sont citées dans les commentaires qui expliquent l'appel,
# et un grep brut rougirait sur sa propre énonciation.
b.check("is_annual_flow(" in code_apparieur,
        "§10 `is_annual_flow` est APPELÉE — un seul détenteur de « ce point couvre-t-il un "
        "exercice ? » (#46)")
for borne in ("350", "370", "365", "_ANNUAL_MIN_DAYS", "_ANNUAL_MAX_DAYS"):
    b.check(borne not in code_apparieur,
            f"§10 `apparieur.py` ne recopie pas la borne `{borne}` — une règle recopiée diverge "
            "au correctif suivant")

# La colonne ne sert à rien si la légende ne la déclare pas : le modèle ne peut pas employer une
# colonne qu'il ne sait pas lire. Assert d'ÉNONCÉ, et il se déclare comme tel (même discipline que
# §9 et que `check_collecte_executor` §3bis).
# Les fragments sont recopiés de la légende, pas reconstitués de mémoire : la première version de
# cet assert cherchait « N'EST PLUS ALIMENTÉ » là où la légende écrit « n'est PLUS ALIMENTÉ », et
# elle a rougi sur sa propre paraphrase. On n'asserte donc que les segments TOUT EN MAJUSCULES, qui
# sont ceux que la légende met en emphase et les seuls dont la casse ne soit pas une supposition.
for phrase in ("PROFONDEUR", "LA DATE DU DERNIER POINT EST DÉCISIVE", "PLUS ALIMENTÉ",
               "NE MONTRE QU'UN POINT PAR CONCEPT"):
    b.check(phrase in LEGENDE_INVENTAIRE,
            f"§10 la légende DÉCLARE la colonne au modèle (« {phrase[:34]}… ») — une colonne non "
            "expliquée est une colonne non employée")

# Les deux bornes temporelles, et elles ne se confondent pas : la PÉRIODE la plus récente couverte
# (max `end`, bornée à aujourd'hui) n'est pas le DERNIER DÉPÔT vu (max `filed`), qui est ce que la
# carte persistera pour savoir qu'elle a vieilli (#67).
b.check(derniere_periode_vue(FACTS_FIXTURE) == "2026-06-30",
        "§10 `derniere_periode_vue` = max `end` — la référence contre laquelle une date se lit")
b.check(derniere_periode_vue(
            {"X": [{"end": "2099-12-31", "val": 1.0, "unit": "USD"}]}) is None,
        "§10 une période ENTIÈREMENT future est écartée, jamais rendue : une référence dans le "
        "futur ferait paraître périmé tout l'inventaire (échéancier de dette, comparatif)")
b.check(dernier_depot_vu(FACTS_FIXTURE) == "2026-07-29",
        "§10 `dernier_depot_vu` = max `filed`, JAMAIS max `end` — c'est la date de DÉPÔT qui dit "
        "si la carte a vieilli ; un `end` peut être postérieur au dépôt")
try:
    dernier_depot_vu({"X": [{"end": "2026-06-30", "val": 1.0, "unit": "USD"}]})
    b.check(False, "§10 un inventaire sans aucun `filed` doit lever, pas rendre une date fabriquée")
except AppariementSansObjet:
    b.check(True, "§10 un inventaire non datable lève `AppariementSansObjet` AVANT toute dépense "
                  "(#40) — jamais une date fabriquée qui se lirait comme une mesure")

# L'outil de lecture du tour de réparation : le code LISTE les voisins déposés, le modèle DÉCIDE.
# Aucune suggestion de remplacement — sur un critère lexical, ce serait la table de sous-chaînes qui
# fabriquait 5 faux appariements sur 7 (mesure du 2026-09-14).
b.check(mots_du_concept("InventoryNetCurrent") == {"inventory", "net", "current"},
        "§10 `mots_du_concept` découpe le CamelCase en mots — la base du listage des voisins")
voisins = voisins_deposes("InventoryNetCurrent", INVENTAIRE_NVDA)
b.check("InventoryNet" in voisins and "Assets" not in voisins,
        "§10 `voisins_deposes` ne rend que des concepts DÉPOSÉS partageant un mot avec l'absent")
b.check(concepts_absents(carte(ligne(statut="exact", concepts=["InventoryNetCurrent"])),
                         INVENTAIRE_NVDA) == ["InventoryNetCurrent"],
        "§10 `concepts_absents` nomme ce que [V] a refusé, pour que la réparation soit ciblée")

sys.exit(b.summary())
