"""Vérification du RÉFÉRENTIEL de frameworks (chantier v3, lot 2 — `app/frameworks/frameworks.yaml`).

Sans réseau ni modèle ni base. Le référentiel est ce qui remplace la grille fermée de 19 champs :
c'est lui qui décide ce qu'on a le droit de DEMANDER. Un référentiel n'est éprouvé ni par le fait
qu'il charge, ni par le nombre de questions qu'il contient — un fichier de 13 questions vides
charge très bien, et sa couverture sort à 100 %.

  • §1 IL CHARGE, ET IL CHARGE INERTE — `safe_load`, jamais `load` : un fichier de données ne doit
       pas pouvoir instancier un objet Python. C'est la contrepartie du choix « données inertes ».
  • §2 LE CONTRAT REFUSE LES DÉFINITIONS CREUSES — question sans ingrédient essentiel, `sans_objet`
       sans motif ou sans XOR de substitut, plancher desserré sans motif déclaré. Chaque refus est
       exigé PAR SA RÈGLE : un refus prononcé par un `Field required` oublié dans la fixture est un
       FAIL (4ᵉ faux vert).
  • §3 LES INVARIANTS RELATIONNELS G–M (#37) — collision d'id entre frameworks, chemin partagé,
       archétype manquant ou inventé, substitut qui ne résout pas, vocabulaire divergent du
       détenteur, version désaccordée.
  • §4 LES PROFILS PORTENT EXACTEMENT LES CLEFS QUE LE PONT LIT — le pont lit par `profil.get(...)`,
       et un `.get` sur une clef mal orthographiée rend `None`, ce qui SAUTE les contrôles D et E.
       Un contrôle qui ne s'exécute pas est un vert.
  • §5 ⚠️ AUCUNE QUESTION NE NOMME LE CORPUS — la section qui garde l'ORDRE du chantier. Les
       questions se dérivent d'une méthodologie ; si un énoncé, un ingrédient ou un gabarit nommait
       un émetteur, une entry ou un mécanisme de stockage, le référentiel aurait été rétro-conçu
       depuis ce que la base contient, et le test de couverture mesurerait sa propre constante.
  • §6 LES VOCABULAIRES N'ONT PAS DIVERGÉ DE LEUR DÉTENTEUR (#46) — les `Literal` des deux contrats
       de framework contre `common.NATURES` et `common.TIER_ORDER`.
  • §7 LA SPEC ET LE RÉFÉRENTIEL NE DIVERGENT PAS — §4.1.1 et §4.2.1 portent les mêmes tables en
       prose. Le YAML est le détenteur ; la spec est lue et confrontée, jamais recopiée à la main.

POURQUOI §5 ASSERTE SUR LES DONNÉES PARSÉES, JAMAIS SUR LE TEXTE DU FICHIER
---------------------------------------------------------------------------
L'en-tête du YAML ÉNONCE l'interdit, donc il contient les jetons interdits (« MVDD_SPEC »,
« notes annexes NVDA »). Un grep sur le fichier brut virerait au ROUGE en lisant sa propre
énonciation — c'est exactement la convention #56. Le parsing YAML dépouille les commentaires : on
asserte sur `enonce`, `libelle`, `variable` et `motif_gabarit`, jamais sur `p.read_text()`.

Cible : pydantic v2 (container). Tester en container, **pas** le python hôte.
"""
import inspect
import re
import sys
from pathlib import Path
from typing import get_args

import yaml
from pydantic import ValidationError

import app.agents.v2.frameworks as fwk
from app.agents.v2.common import NATURES, TIER_ORDER
from app.contracts.framework_answer_schema import NatureEntry
from app.contracts.framework_definition_schema import (
    FRAMEWORK_DEFINITION_SCHEMA_VERSION,
    PLANCHERS_DESSERRES,
    FrameworksFile,
    QuestionDefinition,
    VariableArchetype,
)
from app.agents.v2.frameworks import (
    CLEFS_PROFIL_LUES,
    FRAMEWORKS_YAML,
    FrameworkDefinitionRefused,
    load_frameworks,
    question_profiles,
)

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
    """Un objet qui DOIT se construire. L'exception est nommée, jamais propagée : un script mort
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
    """Un objet qui doit être refusé **par la règle nommée**.

    `motif` est un fragment du message de CETTE règle. Un refus prononcé par une autre (un champ
    requis oublié dans la fixture) est un FAIL : la fixture ne serait pas discriminante et la règle
    visée n'aurait jamais été atteinte (1ᵉʳ et 4ᵉ faux verts).
    """
    global ok, fail
    try:
        fn()
        fail += 1
        print(f"  FAIL {label} → ACCEPTÉ alors qu'il devait être refusé")
        return
    except (ValidationError, FrameworkDefinitionRefused) as e:
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
        print(f"  FAIL {label} → refusé, mais PAS par la règle visée. Attendu « {motif} », "
              f"obtenu : {msg[:220].replace(chr(10), ' ')}")


# ── Fixtures ────────────────────────────────────────────────────────────────────────────────────
# Une question minimale mais LICITE, dont chaque cas négatif ne défait qu'une chose. Une fixture
# plus favorable que le référentiel réel serait un check aveugle au vert
# (`feedback_fixture_copiee_du_reel`) : celle-ci est calquée sur `qf_2`, plancher A, deux
# archétypes déclarés.
ARCHETYPES = ["rentable", "pre_revenus"]


def q_base(**over):
    d = {
        "id": "zz_1",
        "enonce": "Le résultat comptable se transforme-t-il en trésorerie disponible ?",
        "chemin_indexation": "cadre_test.conversion",
        "nature_attendue": "mesure",
        "plancher_tier": "A",
        "actualite_bloquante": True,
        "sens_admis": ["fort", "faible"],
        "ingredients_requis": [
            {"id": "resultat_net", "libelle": "Résultat net de l'exercice considéré",
             "essentiel": True},
        ],
        "variables_par_archetype": {
            "rentable": {"mode": "variable", "variable": "Part du résultat retrouvée en cash"},
            "pre_revenus": {"mode": "sans_objet",
                            "motif_gabarit": "Un résultat structurellement négatif ne se convertit pas",
                            "aucun_substitut": True},
        },
    }
    d.update(over)
    return d


def fichier_base(**over):
    d = {
        "schema_version": FRAMEWORK_DEFINITION_SCHEMA_VERSION,
        "archetypes": list(ARCHETYPES),
        "frameworks": [{
            "id": "cadre_test",
            "libelle": "Cadre de test",
            "etape_benchmark": 5,
            "methodologie": "Méthodologie de test, assez longue pour passer la longueur minimale.",
            "nature_dominante": "mesure",
            "questions": [q_base()],
        }],
    }
    d.update(over)
    return d


def charge(brut):
    """Le chemin RÉEL de chargement : contrat puis pont. Valider seulement le contrat sauterait
    les invariants relationnels, et les cas G–M passeraient au vert sans avoir été atteints."""
    fichier = FrameworksFile.model_validate(brut)
    fwk._valider_pont_definitions(fichier)
    return fichier


print("1. le référentiel charge, et il charge INERTE")
_src_pont = inspect.getsource(fwk)
check("le chargeur utilise `yaml.safe_load` (jamais `yaml.load`)",
      "yaml.safe_load" in _src_pont and not re.search(r"yaml\.load\s*\(", _src_pont),
      "→ un fichier de données qui peut instancier un objet Python n'est plus inerte")
check(f"`{FRAMEWORKS_YAML.name}` existe et est le chemin par défaut du chargeur",
      FRAMEWORKS_YAML.exists(),
      f"→ introuvable : {FRAMEWORKS_YAML}")
valide("le référentiel RÉEL charge et passe contrat + invariants", load_frameworks)

_reel = load_frameworks()
_questions = [q for f in _reel.frameworks for q in f.questions]
check("le référentiel porte les 2 pilotes et leurs 13 questions (§4)",
      len(_reel.frameworks) == 2 and len(_questions) == 13,
      f"→ {len(_reel.frameworks)} framework(s), {len(_questions)} question(s)")


print("\n2. le contrat REFUSE les définitions creuses")
rejete("une question sans aucun ingrédient ESSENTIEL",
       lambda: QuestionDefinition.model_validate(q_base(ingredients_requis=[
           {"id": "accessoire", "libelle": "Un ingrédient utile mais pas indispensable",
            "essentiel": False}])),
       "sa couverture serait satisfaite par le corpus vide")
rejete("deux ingrédients qui portent le même id",
       lambda: QuestionDefinition.model_validate(q_base(ingredients_requis=[
           {"id": "resultat_net", "libelle": "Résultat net de l'exercice considéré",
            "essentiel": True},
           {"id": "resultat_net", "libelle": "Résultat net, une seconde fois par mégarde",
            "essentiel": True}])),
       "deux ingrédients portent le même id")
rejete("un ingrédient dont le libellé tient en trois mots",
       lambda: QuestionDefinition.model_validate(q_base(ingredients_requis=[
           {"id": "roic", "libelle": "Le ROIC", "essentiel": True}])),
       "at least 20 characters")
rejete("un énoncé écrit en artefact comptable (« Quel est le ROIC ? »)",
       lambda: QuestionDefinition.model_validate(q_base(enonce="Quel est le ROIC ?")),
       "at least 30 characters")
rejete("un plancher desserré SANS motif déclaré (§4.2.2)",
       lambda: QuestionDefinition.model_validate(q_base(plancher_tier="B")),
       "Un desserrage se DÉCLARE")
rejete("un motif de desserrage sur un plancher qui n'est PAS desserré",
       lambda: QuestionDefinition.model_validate(
           q_base(plancher_tier="A",
                  motif_plancher="Un motif orphelin qui survivra au prochain resserrage")),
       "non desserré")
rejete("un `sans_objet` sans motif",
       lambda: VariableArchetype.model_validate({"mode": "sans_objet", "aucun_substitut": True}),
       "un hors-sujet sans motif est un trou déguisé")
rejete("un `sans_objet` qui ne dit NI son substitut NI son absence de substitut",
       lambda: VariableArchetype.model_validate(
           {"mode": "sans_objet", "motif_gabarit": "Un motif suffisamment long pour passer"}),
       "jamais les deux, jamais aucun des deux")
rejete("un `sans_objet` qui déclare les DEUX à la fois",
       lambda: VariableArchetype.model_validate(
           {"mode": "sans_objet", "motif_gabarit": "Un motif suffisamment long pour passer",
            "substitut_question_id": "qf_7", "aucun_substitut": True}),
       "jamais les deux, jamais aucun des deux")
rejete("un archétype `variable` sans variable",
       lambda: VariableArchetype.model_validate({"mode": "variable"}),
       "sans dire à quoi elle s'applique")
rejete("un archétype `variable` qui porte quand même un substitut",
       lambda: VariableArchetype.model_validate(
           {"mode": "variable", "variable": "Une variable licite", "aucun_substitut": True}),
       "soit couvert, soit sans objet, jamais les deux")
rejete("un champ inconnu dans une définition (extra='forbid')",
       lambda: QuestionDefinition.model_validate(q_base(seuil_de_couverture=0.8)),
       "Extra inputs are not permitted")
valide("la question minimale licite se construit",
       lambda: QuestionDefinition.model_validate(q_base()))


print("\n3. les invariants RELATIONNELS (#37) — ceux qu'un contrat d'objet ne peut pas voir")
rejete("[G] deux frameworks qui déclarent la MÊME question",
       lambda: charge(fichier_base(frameworks=[
           {"id": "cadre_a", "libelle": "Cadre A", "etape_benchmark": 5,
            "methodologie": "Méthodologie de test, assez longue pour passer la longueur minimale.",
            "nature_dominante": "mesure", "questions": [q_base()]},
           {"id": "cadre_b", "libelle": "Cadre B", "etape_benchmark": 4,
            "methodologie": "Méthodologie de test, assez longue pour passer la longueur minimale.",
            "nature_dominante": "mesure",
            "questions": [q_base(chemin_indexation="cadre_test.autre")]}])),
       "[G]")
# ⚠️ Les deux questions sont dans des frameworks DIFFÉRENTS, et portent des id différents. Dans un
# même framework, c'est le contrat (`_les_questions_sont_distinctes`) qui prononce le refus, et le
# cas passerait au vert sans jamais atteindre [H] : la fixture serait non discriminante (1ᵉʳ faux
# vert). Mesuré, pas prévu — la première version de ce cas rougissait sur l'autre règle.
rejete("[H] deux frameworks dont deux questions partagent un chemin d'indexation",
       lambda: charge(fichier_base(frameworks=[
           {"id": "cadre_a", "libelle": "Cadre A", "etape_benchmark": 5,
            "methodologie": "Méthodologie de test, assez longue pour passer la longueur minimale.",
            "nature_dominante": "mesure", "questions": [q_base()]},
           {"id": "cadre_b", "libelle": "Cadre B", "etape_benchmark": 4,
            "methodologie": "Méthodologie de test, assez longue pour passer la longueur minimale.",
            "nature_dominante": "mesure", "questions": [q_base(id="zz_2")]}])),
       "l'index ne saurait plus laquelle des deux il fonde")
rejete("[I] une question MUETTE sur un archétype déclaré",
       lambda: charge(fichier_base(archetypes=["rentable", "pre_revenus", "financiere"])),
       "[I]")
rejete("[I] une question qui INVENTE un archétype non déclaré",
       lambda: charge(fichier_base(archetypes=["rentable"])),
       "inventés"),
rejete("[J] un substitut qui pointe une question inexistante",
       lambda: charge(fichier_base(frameworks=[
           {"id": "cadre_test", "libelle": "Cadre A", "etape_benchmark": 5,
            "methodologie": "Méthodologie de test, assez longue pour passer la longueur minimale.",
            "nature_dominante": "mesure",
            "questions": [q_base(variables_par_archetype={
                "rentable": {"mode": "variable", "variable": "Part du résultat en cash"},
                "pre_revenus": {"mode": "sans_objet",
                                "motif_gabarit": "Un motif suffisamment long pour passer le seuil",
                                "substitut_question_id": "zz_404"}})]}])),
       "qui n'existe pas")
rejete("[J] un substitut qui pointe SA PROPRE question",
       lambda: charge(fichier_base(frameworks=[
           {"id": "cadre_test", "libelle": "Cadre A", "etape_benchmark": 5,
            "methodologie": "Méthodologie de test, assez longue pour passer la longueur minimale.",
            "nature_dominante": "mesure",
            "questions": [q_base(variables_par_archetype={
                "rentable": {"mode": "variable", "variable": "Part du résultat en cash"},
                "pre_revenus": {"mode": "sans_objet",
                                "motif_gabarit": "Un motif suffisamment long pour passer le seuil",
                                "substitut_question_id": "zz_1"}})]}])),
       "se cite elle-même comme substitut")
rejete("[M] un fichier dont la version ne correspond pas au contrat qui l'a validé",
       lambda: charge(fichier_base(schema_version="v2.9.0")),
       "[M]")
valide("le fichier de test minimal passe contrat ET invariants",
       lambda: charge(fichier_base()))


print("\n4. les profils portent EXACTEMENT les clefs que le pont lit")
# Le pont lit par `profil.get("plancher_tier")` / `.get("nature_attendue")`. Un `.get` sur une clef
# absente rend `None`, et les contrôles D et E se contentent alors de ne rien faire : le mode de
# panne n'est pas une erreur, c'est un SAUT. On l'asserte donc au point de lecture réel — la clef
# telle que le pont l'épelle — et pas sur une liste réécrite ici.
_profils = question_profiles(_reel)
check("un profil est produit pour chacune des 13 questions",
      len(_profils) == len(_questions),
      f"→ {len(_profils)} profils pour {len(_questions)} questions")
_src_valid = inspect.getsource(fwk.valider_pont_framework_answer)
_lues_reellement = set(re.findall(r'profil\.get\(\s*"([a-z_]+)"', _src_valid))
check("les clefs réellement lues par le pont sont celles déclarées dans `CLEFS_PROFIL_LUES`",
      _lues_reellement == set(CLEFS_PROFIL_LUES),
      f"→ le pont lit {sorted(_lues_reellement)}, la table déclare {sorted(CLEFS_PROFIL_LUES)}")
check("chaque profil porte ces clefs, non nulles",
      all(p.get(c) is not None for p in _profils.values() for c in _lues_reellement),
      "→ une clef nulle fait SAUTER les contrôles D/E sans rien signaler")
check("chaque profil porte au moins un ingrédient essentiel",
      all(p["ingredients_essentiels"] for p in _profils.values()),
      "→ une question qui n'exige rien est couverte par le corpus vide")


print("\n5. ⚠️ aucune question ne nomme le CORPUS — la garde de l'ordre questions → données")
# Les données de la base sont l'HISTORIQUE DE TEST d'un système inachevé : elles peuvent servir à
# éprouver le référentiel, jamais à le concevoir. Si un énoncé ou un ingrédient nommait un émetteur,
# une entry ou un mécanisme de stockage, le référentiel aurait été rétro-conçu depuis ce que la base
# contient — et la couverture qu'on en mesurerait serait sa propre constante.
#
# ⚠️ On asserte sur les données PARSÉES. L'en-tête du YAML énonce l'interdit, donc il contient les
# jetons interdits : un grep sur le texte brut lirait sa propre énonciation (#56).
JETONS_INTERDITS = [
    # des émetteurs — un référentiel universel ne nomme aucun acteur (#31)
    "nvda", "nvidia", "msft", "microsoft", "rvmd", "revolution medicines", "aapl", "apple",
    # des références au corpus stocké
    "entry", "entrée #", "covers", "mvdd", "agent_synthesis", "llm_memory", "context pack",
    "orphelin", "knowledge_entries", "synthesis_targets",
    # des artefacts de dépôt : nommer le document, c'est présumer qu'il existe déjà en base
    "10-k", "10-q", "8-k", "edgar", "xbrl", "sec.gov",
]
_champs_libres: list[tuple[str, str, str]] = []
for f in _reel.frameworks:
    for q in f.questions:
        _champs_libres.append((q.id, "enonce", q.enonce))
        for i in q.ingredients_requis:
            _champs_libres.append((q.id, f"ingredient.{i.id}", i.libelle))
        for a, va in q.variables_par_archetype.items():
            for nom, val in (("variable", va.variable), ("motif_gabarit", va.motif_gabarit)):
                if val:
                    _champs_libres.append((q.id, f"{a}.{nom}", val))

_fautes = [(qid, ou, j) for qid, ou, txt in _champs_libres
           for j in JETONS_INTERDITS if j in txt.lower()]
check("aucun énoncé, ingrédient ou gabarit ne nomme un émetteur, une entry ou un dépôt",
      not _fautes,
      f"→ {_fautes[:5]}")
_refs = [(qid, ou) for qid, ou, txt in _champs_libres if re.search(r"#\s*\d+", txt)]
check("aucun champ ne référence une entry par son numéro",
      not _refs, f"→ {_refs[:5]}")
# L'assert POSITIF qui va avec : dépouiller la prose ne suffit pas, encore faut-il que la prose
# restante dise quelque chose. Un référentiel de 13 libellés vides passerait les deux asserts
# ci-dessus sans effort.
check("les libellés d'ingrédients sont écrits pour être CHERCHÉS (≥ 5 mots en moyenne)",
      (sum(len(t.split()) for _, ou, t in _champs_libres if ou.startswith("ingredient."))
       / max(1, sum(1 for _, ou, _ in _champs_libres if ou.startswith("ingredient.")))) >= 5,
      "→ un libellé télégraphique ne descend pas au search-worker comme un mandat")


print("\n6. les vocabulaires n'ont pas divergé de leur DÉTENTEUR (#46)")
check("`NatureEntry` (contrat de réponse) == `common.NATURES`",
      set(get_args(NatureEntry)) == set(NATURES),
      f"→ {sorted(get_args(NatureEntry))} vs {sorted(NATURES)}")
_nat_def = set(get_args(QuestionDefinition.model_fields["nature_attendue"].annotation))
check("`nature_attendue` (contrat de définition) == `common.NATURES`",
      _nat_def == set(NATURES), f"→ {sorted(_nat_def)} vs {sorted(NATURES)}")
check("`PLANCHERS_DESSERRES` est un sous-ensemble STRICT de `TIER_ORDER`",
      set(PLANCHERS_DESSERRES) < set(TIER_ORDER),
      "→ un tier desserré hors du référentiel de tiers ne serait jamais atteint")
check("les planchers réellement employés appartiennent tous à `TIER_ORDER`",
      all(q.plancher_tier in TIER_ORDER for q in _questions))


print("\n7. la spec et le référentiel ne divergent PAS (§4.1.1 / §4.2.1)")
# La spec porte les mêmes tables en prose. Le YAML est le DÉTENTEUR ; la spec est PARSÉE et
# confrontée, jamais recopiée à la main. Sans cette confrontation, les deux nomenclatures
# divergeraient au premier correctif — c'est exactement ce qui est arrivé aux cartes de provenance
# du lot 1 (#46).
_spec = Path("/roadmap/03-spec-frameworks.md")
if not _spec.exists():
    fail += 1
    print(f"  FAIL spec absente ({_spec}) → section non mesurée ; un prérequis manquant ne doit "
          "jamais passer pour un 0")
else:
    _txt = _spec.read_text(encoding="utf-8")
    # Les lignes de tableau de la forme : | `qf_1` | … | `mesure` | A | oui |
    _lignes = re.findall(
        r"^\|\s*`((?:qf|mo)_\d+)`\s*\|[^|]*\|\s*`(\w+)`\s*\|\s*\**([AB][+-]?)\**\s*\|\s*\**(\w+)\**\s*\|",
        _txt, flags=re.M)
    _spec_tab = {qid: (nat, tier, act) for qid, nat, tier, act in _lignes}
    check("les tables §4.1.1 et §4.2.1 sont lisibles et portent 13 questions",
          len(_spec_tab) == 13, f"→ {len(_spec_tab)} ligne(s) reconnue(s) : {sorted(_spec_tab)}")
    _yaml_tab = {q.id: (q.nature_attendue, q.plancher_tier,
                        "oui" if q.actualite_bloquante else "non") for q in _questions}
    check("les identifiants de la spec et du référentiel sont les mêmes",
          set(_spec_tab) == set(_yaml_tab),
          f"→ spec seule : {sorted(set(_spec_tab) - set(_yaml_tab))}, "
          f"référentiel seul : {sorted(set(_yaml_tab) - set(_spec_tab))}")
    _ecarts = {k: (_spec_tab[k], _yaml_tab[k]) for k in set(_spec_tab) & set(_yaml_tab)
               if _spec_tab[k] != _yaml_tab[k]}
    check("nature, plancher et actualité bloquante coïncident question par question",
          not _ecarts, f"→ (spec, référentiel) : {_ecarts}")

print(f"\n{'=' * 60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
