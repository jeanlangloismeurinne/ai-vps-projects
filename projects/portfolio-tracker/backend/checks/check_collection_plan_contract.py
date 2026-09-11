"""Vérification du contrat de PLAN DE COLLECTE (chantier v3, lot 2c — `app/contracts/collection_plan_schema.py`).

Sans réseau ni modèle ni base. Ce contrat est la sortie de l'agent 1 (le traducteur, §3.6) : c'est
lui qui décide ce qu'une ligne de plan a le DROIT d'être avant que le collecteur ne l'exécute. Un
contrat n'est éprouvé que par ce qu'il REFUSE — accepter les objets valides ne prouve rien, un
`BaseModel` vide les accepterait tous.

  • §1 VOCABULAIRE FERMÉ ET ATTEIGNABLE (#32) — les 2 statuts de LIGNE, chacun atteint PAR SON NOM
       depuis un objet réellement construit. Et `omis` N'EST PAS un statut : c'est l'absence de
       ligne (#44/#54), donc il ne figure ni dans `STATUTS_LIGNE` ni dans le `Literal` du champ.
  • §2 LE STATUT PORTE EXACTEMENT SA CHARGE — l'obligation ET l'interdiction. L'interdiction est la
       moitié qui compte : elle empêche un `traduit` sans source de partir au collecteur comme un
       ordre vide, et un `inobtenable` de porter quand même une métrique (les deux états s'excluent).
  • §3 CE QUE LE TRADUCTEUR NE PEUT PAS PORTER (#59, §3.6) — `plancher_tier`, `nature_attendue`,
       `essentiel` viennent du framework et de lui seul. `Strict` (extra='forbid') les REFUSE à la
       construction : la doctrine est impossible à violer, pas gardée par un `if`. Même forme que
       l'actualité absente de `FrameworkAnswer` (#53). Aucun champ de tier ni de score non plus.
  • §4 UN INGRÉDIENT N'EST PLANIFIÉ QU'UNE FOIS — deux lignes sur un couple (question, ingrédient)
       laissent l'aiguilleur sans savoir laquelle relier à `question_coverage`, et un `traduit` +
       un `inobtenable` sur le même ingrédient se contredisent. Un plan a au moins une ligne.
  • §5 DÉTENTEUR UNIQUE ET VOCABULAIRE NON RECOPIÉ (#46) — `archetype` n'est PAS un `Literal` figé
       (le référentiel détient la liste des archétypes) ; la version est celle du chantier, partagée
       avec le contrat de définition, pas une seconde horloge.

POURQUOI `rejete()` EXIGE UN MOTIF, ET PAS SEULEMENT UN REFUS (#56)
------------------------------------------------------------------
Un test négatif qui ne nomme pas la règle qui a rougi mesure sa propre fixture : un objet peut être
refusé par un `Field required` oublié plutôt que par l'invariant visé (4ᵉ faux vert). Chaque cas
déclare donc un fragment du message attendu, et un refus prononcé par une AUTRE règle est un FAIL.
⚠️ Corollaire éprouvé ici : une ligne `traduit` avec `metrique=""` serait rejetée par le
`min_length` du champ AVANT le validateur — pour atteindre la branche « champs manquants » du
validateur, on OMET le champ (défaut `None`), on ne le vide pas.

Cible : pydantic v2 (container backend). Tester en container, **pas** le python hôte (v1).
"""
import sys
from typing import get_args

from pydantic import ValidationError

from app.agents.v2.frameworks import (
    CollectionPlanRefused,
    load_frameworks,
    valider_pont_collection_plan,
)
from app.contracts.collection_plan_schema import (
    COLLECTION_PLAN_SCHEMA_VERSION,
    STATUTS_LIGNE,
    CollectionPlan,
    CollectionPlanItem,
)
from app.contracts.framework_definition_schema import FRAMEWORK_DEFINITION_SCHEMA_VERSION

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


def valide(label, fn):
    """Un objet qui DOIT se construire. Une exception est nommée, jamais propagée : un script mort
    avant ses asserts ne prouve rien, il ne fait que ne pas contredire (2ᵉ faux vert)."""
    global ok, fail
    try:
        fn()
        ok += 1
        print(f"  ok   {label}")
    except Exception as e:  # noqa: BLE001
        fail += 1
        print(f"  FAIL {label} → refusé alors qu'il est licite : {type(e).__name__}: "
              f"{str(e)[:200].replace(chr(10), ' ')}")


def rejete(label, fn, motif):
    """Un objet qui doit être refusé PAR LA RÈGLE NOMMÉE. Un refus prononcé par une autre règle
    (un champ requis oublié dans la fixture) est un FAIL : la fixture n'était pas discriminante."""
    global ok, fail
    try:
        fn()
        fail += 1
        print(f"  FAIL {label} → ACCEPTÉ alors qu'il devait être refusé")
        return
    except ValidationError as e:
        msg = str(e)
    except Exception as e:  # noqa: BLE001
        fail += 1
        print(f"  FAIL {label} → mauvaise exception {type(e).__name__}: {str(e)[:150]}")
        return
    if motif in msg:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} → refusé, mais PAS par la règle visée "
              f"(attendu « {motif} ») : {msg[:220].replace(chr(10), ' ')}")


# ── fixtures : toutes valides par défaut, chaque cas n'en casse QU'UNE chose ────────────────────
TRAD = dict(question_id="qf_7", ingredient_id="consommation_de_tresorerie_recente",
            statut="traduit", metrique="cash burn trimestriel hors milestone",
            source_pressentie="communiqués + call trimestriel", ancre="dernière lecture clinique")
INOB = dict(question_id="qf_1", ingredient_id="cout_du_capital", statut="inobtenable",
            motif="aucun poste EDGAR ne produit le coût du capital ; une source web reste à ouvrir")
PLAN = dict(ticker_id="RVMD", framework_id="qualite_financiere",
            framework_version="v3.0.0", archetype="pre_revenus")


def item(**over):
    d = {**TRAD, **over}
    return lambda: CollectionPlanItem(**d)


def plan(items, **over):
    return lambda: CollectionPlan(**{**PLAN, **over}, items=items)


# ── §1 vocabulaire fermé et atteignable (#32) ───────────────────────────────────────────────────
print("[1] les 2 statuts de LIGNE sont atteignables PAR LEUR NOM ; `omis` n'en est pas un")
valide("statut 'traduit' se construit (métrique + source + ancre)", item())
valide("statut 'inobtenable' se construit (motif seul)", lambda: CollectionPlanItem(**INOB))
_statut_args = set(get_args(CollectionPlanItem.model_fields["statut"].annotation))
check("STATUTS_LIGNE == le Literal du champ `statut` (aucun statut mort, aucun manquant)",
      _statut_args == set(STATUTS_LIGNE), f"→ {_statut_args} vs {set(STATUTS_LIGNE)}")
check("`omis` n'est PAS une valeur de statut (c'est l'absence de ligne, #44/#54)",
      "omis" not in _statut_args and "omis" not in STATUTS_LIGNE)

# ── §2 le statut porte exactement sa charge — obligation ET interdiction ────────────────────────
print("\n[2] le statut DÉCIDE des champs présents (obligation + interdiction)")
# obligation côté `traduit` : les trois champs de recherche, chacun testé en OMISSION (défaut None)
for champ in ("metrique", "source_pressentie", "ancre"):
    rejete(f"'traduit' sans `{champ}` → ordre vide au collecteur",
           item(**{champ: None}), f"'traduit' mais ['{champ}']")
# interdiction côté `traduit`
rejete("'traduit' qui porte un `motif` → le motif est une raison d'impossibilité",
       item(motif="ce motif fait bien plus de vingt caractères pour passer le min_length"),
       "statut='traduit' porte un `motif`")
# obligation côté `inobtenable`
rejete("'inobtenable' sans `motif` → trou déguisé",
       lambda: CollectionPlanItem(question_id="qf_1", ingredient_id="cout_du_capital",
                                  statut="inobtenable"),
       "statut='inobtenable' sans `motif`")
# interdiction côté `inobtenable` : porter une métrique, c'est être traduit
rejete("'inobtenable' qui porte une `metrique` → les deux états s'excluent",
       lambda: CollectionPlanItem(**{**INOB, "metrique": "free cash flow"}),
       "statut='inobtenable' porte")
# le min_length des champs de recherche n'est pas décoratif (il MORD avant le validateur)
rejete("`metrique` trop courte est rejetée par le plancher du champ, pas décorative",
       item(metrique="ab"), "at least 3 characters")

# ── §3 ce que le traducteur ne peut pas porter (#59, §3.6) — extra='forbid' ──────────────────────
print("\n[3] le traducteur n'a AUCUN levier sur l'exigence — les champs sont ABSENTS, pas ignorés")
for interdit in ("plancher_tier", "nature_attendue", "essentiel", "reliability_tier", "score"):
    rejete(f"un `{interdit}` sur une ligne est REFUSÉ à la construction (impossible, pas gardé)",
           item(**{interdit: "A"}), "Extra inputs are not permitted")
check("… et le contrat ne DÉCLARE aucun de ces champs (l'absence est structurelle)",
      not ({"plancher_tier", "nature_attendue", "essentiel", "reliability_tier", "score"}
           & set(CollectionPlanItem.model_fields)))

# ── §4 un ingrédient n'est planifié qu'une fois ; un plan a au moins une ligne ───────────────────
print("\n[4] la couverture est déterministe : un ingrédient, une ligne")
valide("un plan à deux lignes distinctes se construit",
       plan([CollectionPlanItem(**TRAD), CollectionPlanItem(**INOB)]))
rejete("deux lignes sur le même (question, ingrédient) → l'aiguilleur ne saurait plus laquelle lier",
       plan([CollectionPlanItem(**INOB),
             CollectionPlanItem(**{**INOB, "motif": "un autre motif d'au moins vingt caractères ici"})]),
       "planifié plusieurs fois")
rejete("un plan sans aucune ligne est refusé (rien à collecter n'est pas un plan)",
       plan([]), "at least 1 item")

# ── §5 détenteur unique, vocabulaire non recopié (#46) ──────────────────────────────────────────
print("\n[5] rien n'est recopié d'un autre détenteur")
_arch = CollectionPlan.model_fields["archetype"].annotation
check("`archetype` n'est PAS un Literal figé — le référentiel détient la liste (#46, #31)",
      _arch is str and not get_args(_arch), f"→ {_arch}")
check("la version est celle du chantier, partagée avec le contrat de définition (une seule horloge)",
      COLLECTION_PLAN_SCHEMA_VERSION == FRAMEWORK_DEFINITION_SCHEMA_VERSION,
      f"→ {COLLECTION_PLAN_SCHEMA_VERSION} vs {FRAMEWORK_DEFINITION_SCHEMA_VERSION}")


# ── §6 le PONT — invariants relationnels contre le RÉFÉRENTIEL (#37) ─────────────────────────────
# Le contrat valide UN objet ; le pont confronte le plan aux questions, à leurs ingrédients et à
# l'archétype. La fixture valide est construite PROGRAMMATIQUEMENT depuis le référentiel réel — elle
# reste donc complète par construction, même si une question gagne un ingrédient essentiel demain
# (une fixture écrite à la main deviendrait incomplète en silence, un faux ROUGE).
print("\n[6] le pont confronte le plan au RÉFÉRENTIEL — ce qu'un contrat d'objet ne peut pas voir")
_FICHIER = load_frameworks()
_FW = {f.id: f for f in _FICHIER.frameworks}


def plan_complet(framework_id, archetype, extra=None, drop_first=False):
    """Un plan qui couvre EXACTEMENT les ingrédients essentiels des questions applicables."""
    items = []
    for q in _FW[framework_id].questions:
        if q.variables_par_archetype[archetype].mode != "variable":
            continue
        for ing in q.ingredients_requis:
            if ing.essentiel:
                items.append(CollectionPlanItem(
                    question_id=q.id, ingredient_id=ing.id, statut="traduit",
                    metrique=f"métrique nommée pour {ing.id}", source_pressentie="10-Q",
                    ancre="clôture du trimestre"))
    if drop_first:
        items = items[1:]
    return CollectionPlan(ticker_id="TESTCO", framework_id=framework_id,
                          framework_version=_FICHIER.schema_version, archetype=archetype,
                          items=items + (extra or []))


def plan_manuel(items, **over):
    base = dict(ticker_id="TESTCO", framework_id="qualite_financiere",
                framework_version=_FICHIER.schema_version, archetype="rentable")
    base.update(over)
    return CollectionPlan(**base, items=items)


def pont_ok(label, plan):
    global ok, fail
    try:
        valider_pont_collection_plan(plan, fichier=_FICHIER)
        ok += 1
        print(f"  ok   {label}")
    except Exception as e:  # noqa: BLE001
        fail += 1
        print(f"  FAIL {label} → refusé alors qu'il est cohérent : {type(e).__name__}: {str(e)[:180]}")


def refuse_pont(label, plan, motif):
    """Le pont doit REFUSER, et par la raison nommée (même discipline que `rejete`, #56)."""
    global ok, fail
    try:
        valider_pont_collection_plan(plan, fichier=_FICHIER)
        fail += 1
        print(f"  FAIL {label} → ACCEPTÉ par le pont alors qu'il devait être refusé")
    except CollectionPlanRefused as e:
        if motif in str(e):
            ok += 1
            print(f"  ok   {label}")
        else:
            fail += 1
            print(f"  FAIL {label} → refusé, mais PAS par la raison visée "
                  f"(attendu « {motif} ») : {str(e)[:200]}")
    except Exception as e:  # noqa: BLE001
        fail += 1
        print(f"  FAIL {label} → mauvaise exception {type(e).__name__}: {str(e)[:150]}")


_ITEM_QF1 = CollectionPlanItem(question_id="qf_1", ingredient_id="resultat_operationnel_apres_impot",
                               statut="traduit", metrique="résultat d'exploitation après impôt",
                               source_pressentie="10-K", ancre="clôture de l'exercice")

pont_ok("[réf] un plan complet passe le pont (sinon rien ci-dessous ne discrimine)",
        plan_complet("qualite_financiere", "rentable"))
pont_ok("[réf] … et sur un autre archétype (pre_revenus, où des questions sont sans objet)",
        plan_complet("qualite_financiere", "pre_revenus"))
refuse_pont("[N] framework inconnu du référentiel",
            plan_manuel([_ITEM_QF1], framework_id="inexistant"), "[N] framework `inexistant`")
refuse_pont("[N] version divergente du référentiel",
            plan_manuel([_ITEM_QF1], framework_version="v2.0.0"), "[N] plan en `v2.0.0`")
refuse_pont("[O] archétype non déclaré",
            plan_manuel([_ITEM_QF1], archetype="archetype_bidon"), "[O] archétype `archetype_bidon`")
refuse_pont("[P] question absente du framework",
            plan_complet("qualite_financiere", "rentable", extra=[CollectionPlanItem(
                question_id="zz_9", ingredient_id="bidon", statut="inobtenable",
                motif="ligne dont la question n'existe pas au référentiel du framework")]),
            "[P] la ligne vise la question `zz_9`")
refuse_pont("[P] ingrédient inventé pour une vraie question",
            plan_complet("qualite_financiere", "rentable", extra=[CollectionPlanItem(
                question_id="qf_1", ingredient_id="ingredient_qui_n_existe_pas",
                statut="inobtenable", motif="ingrédient absent de la question qf_1 du référentiel")]),
            "n'a pas d'ingrédient `ingredient_qui_n_existe_pas`")
refuse_pont("[Q] question SANS OBJET planifiée quand même (fabrique une réponse, §0.2)",
            plan_complet("qualite_financiere", "pre_revenus", extra=[CollectionPlanItem(
                question_id="qf_1", ingredient_id="resultat_operationnel_apres_impot",
                statut="traduit", metrique="rendement du capital", source_pressentie="10-K",
                ancre="clôture de l'exercice")]),
            "[Q] `qf_1` est SANS OBJET")
refuse_pont("[R] essentiel omis → plan REFUSÉ (T1bis, le cœur)",
            plan_complet("qualite_financiere", "rentable", drop_first=True),
            "n'a AUCUNE ligne dans le plan")


print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
