"""Vérification du contrat de FRAMEWORK (chantier v3, lot 1 — `app/contracts/framework_answer_schema.py`).

Sans réseau ni modèle ni base. Ce contrat remplace, comme sortie d'analyse, la grille fermée de 19
champs (`MVDD_SPEC`) : c'est lui qui décide ce qu'une réponse d'analyste a le DROIT d'être. Un
contrat n'est éprouvé que par ce qu'il REFUSE — accepter les objets valides ne prouve rien, un
`BaseModel` vide les accepterait tous.

  • §1 VOCABULAIRE FERMÉ ET ATTEIGNABLE (#32) — les 4 statuts, chacun atteint PAR SON NOM depuis un
       objet réellement construit. Un statut déclaré qu'aucun objet n'atteint est un statut mort, et
       un `in STATUTS` ne prouverait rien.
  • §2 LE STATUT PORTE EXACTEMENT SES BLOCS — l'obligation ET l'interdiction. L'interdiction est la
       moitié qui compte : c'est elle qui empêche un `non_fondable` de publier quand même une
       `reponse` (entry #190) et un `sans_objet` de servir son substitut comme réponse à la question
       d'origine (contrôle ④ de §3.2).
  • §3 L'ACTUALITÉ N'EST PAS PERSISTABLE (#53) — `Fondation` la REFUSE (extra='forbid'), seule
       `FondationServie` la porte. Persister l'axe reproduirait la cause n°2 du diagnostic #50.
       Et son vocabulaire est celui du détenteur (`knowledge.actualite.ETATS`), pas une recopie.
  • §4 LE MANAGER NE PEUT NI RÉÉCRIRE NI RENVOYER À VIDE (§3.1/§3.3) — un renvoi produit un mandat
       (Écart B), un acquittement n'efface pas un `ko`, et le bloc n'a AUCUN champ où écrire une
       réponse ou un rang : il ne peut pas promouvoir, faute d'endroit où l'écrire.
  • §5 UN ÉTAT DE MANDAT PORTE EXACTEMENT SA TRACE — dont le cas licite `statut_apres ==
       statut_avant` : une recherche qui ne trouve rien est une information, pas une violation.
  • §6 LES COLONNES DÉNORMALISÉES RÉSOLVENT DANS LE CONTRAT (#46) — chaque chemin de
       `COLONNES_DENORMALISEES` se parcourt réellement champ par champ. C'est la garde qui empêche
       le lot 3 de nommer ses colonnes d'après une nomenclature devinée : T3/T4 liraient `None` pour
       toujours et resteraient rouges pour la MAUVAISE raison.
  • §7 DÉTENTEUR UNIQUE (#46) — le contrat ne ré-implémente ni la règle du cran (`synthesis_feed`),
       ni l'axe actualité (`knowledge.actualite`), ni `GapItem` ; et il n'a pas de jumeau figé sous
       `roadmap/provenance-cards/`.

POURQUOI `rejete()` EXIGE UN MOTIF, ET PAS SEULEMENT UN REFUS
------------------------------------------------------------
Mesuré, pas prévu : la première version de ces cas passait au vert avec des fixtures où `motif`
manquait sur `ManagerVerdict`. Les objets étaient bien rejetés — par le `Field required` du champ
absent, jamais par l'invariant testé. C'est le 4ᵉ faux vert (l'assert à côté du point de lecture) :
un test négatif qui ne nomme pas la règle qui a rougi mesure sa propre fixture. Chaque cas négatif
déclare donc un fragment du message attendu, et un refus prononcé par une AUTRE règle est un FAIL.

Cible : pydantic v2 (container backend 2.13.4). Tester en container, **pas** le python hôte (v1).
"""
import ast
import inspect
import re
import sys
from pathlib import Path
from typing import get_args

from pydantic import ValidationError

import app.contracts.framework_answer_schema as fw
from app.contracts.framework_answer_schema import (
    COLONNES_DENORMALISEES,
    FRAMEWORK_SCHEMA_VERSION,
    STATUTS,
    Approximation,
    Fondation,
    FondationServie,
    FrameworkAnswer,
    FrameworkAnswerServie,
    FrameworkMandate,
    ManagerVerdict,
    Reponse,
    SansObjet,
)
import app.agents.v2.frameworks as fwk
from app.agents.v2.frameworks import (
    FrameworkAnswerRefused,
    servir_answer,
    valider_pont_framework_answer,
)
from app.knowledge.actualite import ETATS
from app.knowledge.material_events import MaterialEventLookup

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
    except Exception as e:  # noqa: BLE001 — on veut le nom, pas la trace
        fail += 1
        print(f"  FAIL {label} → refusé alors qu'il est licite : {type(e).__name__}: "
              f"{str(e)[:200].replace(chr(10), ' ')}")


def rejete(label, fn, motif):
    """Un objet qui doit être refusé **par la règle nommée**.

    `motif` est un fragment du message de CETTE règle. Un refus prononcé par une autre (un champ
    requis oublié dans la fixture, par exemple) est un FAIL : il signifierait que la fixture n'est
    pas discriminante et que la règle visée n'a jamais été atteinte (1ᵉʳ et 4ᵉ faux verts).
    """
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


# ── fixtures : toutes valides par défaut, chaque cas n'en casse QU'UNE chose ───────────────────
BASE = dict(schema_version=FRAMEWORK_SCHEMA_VERSION, framework_id="qf", question_id="qf_1",
            ticker_id="AAPL", analyste="analyste_1")
FOND = dict(cited_entry_ids=[190], rang_derive="A-", nature_effective="mesure")
FOND_ITP = {**FOND, "nature_effective": "interpretation"}
APX = dict(methode="règle de trois sur le CA 2024", ingredients_entry_ids=[190, 191],
           hypotheses_explicites=["mix produit stable"], sensibilite="±3 pts si le mix bouge de 10 %")
GAP = dict(dimension="rentabilite", champs_cibles=["qf_1"], manque="marge brute 2024 absente",
           priorite="haute", coverage_actuelle="0 entry citable")
CTRL = dict(completude="ok", fondation="ok", honnetete_approximation="sans_objet",
            non_substitution="ok")
MGR = dict(verdict="acquitte", controles=CTRL, motif="les 4 contrôles au vert")
MAND = dict(framework_id="qf", question_id="qf_1", ticker_id="AAPL", origine="manager_renvoi",
            motif="fondation `ko` : aucune entry citée", mandat="Relever la marge brute 2024 de AAPL "
            "dans le 10-K, poste « cost of sales »", statut_avant="non_fondable")


print("1. vocabulaire fermé et ATTEIGNABLE — chaque statut atteint par un objet réel (#32)")
atteints = {}
for statut, blocs in (
    ("repondu",      dict(reponse={"verbatim": "12,4 %"}, fondation=FOND)),
    ("approxime",    dict(reponse={"verbatim": "~12 %"}, fondation=FOND_ITP, approximation=APX,
                          manager={**MGR, "controles": {**CTRL, "honnetete_approximation": "ok"}})),
    ("sans_objet",   dict(sans_objet={"motif": "société sans stocks", "aucun_substitut": True})),
    ("non_fondable", dict(gap=GAP)),
):
    try:
        atteints[statut] = FrameworkAnswer(**BASE, statut=statut, **blocs)
        ok += 1
        print(f"  ok   `{statut}` est atteignable par un objet valide")
    except Exception as e:  # noqa: BLE001
        fail += 1
        print(f"  FAIL `{statut}` déclaré mais inatteignable : {str(e)[:200]}")
check("les 4 statuts déclarés sont exactement les 4 atteints",
      set(STATUTS) == set(atteints), f"→ déclarés {set(STATUTS)}, atteints {set(atteints)}")
rejete("un 5ᵉ statut (« partiellement répondu ») est refusé",
       lambda: FrameworkAnswer(**BASE, statut="repondu_partiel", reponse={"verbatim": "x"},
                               fondation=FOND),
       "Input should be 'repondu'")
rejete("un champ hors contrat est refusé, pas ignoré (extra='forbid')",
       lambda: FrameworkAnswer(**BASE, statut="non_fondable", gap=GAP, confiance=0.9),
       "Extra inputs are not permitted")
valide("une réponse chiffrée porte son unité",
       lambda: Reponse(verbatim="12,4 %", valeur=12.4, unite="%"))
rejete("un nombre nu (valeur sans unité) est refusé (#45/#46)",
       lambda: Reponse(verbatim="12,4", valeur=12.4),
       "un nombre nu n'est pas une")
rejete("un verbatim vide est refusé",
       lambda: Reponse(verbatim=""), "at least 1 character")


print("\n2. le statut porte EXACTEMENT ses blocs — l'obligation, et surtout l'interdiction")
rejete("`repondu` sans fondation",
       lambda: FrameworkAnswer(**BASE, statut="repondu", reponse={"verbatim": "12,4 %"}),
       "sans ['fondation']")
rejete("`repondu` sans réponse",
       lambda: FrameworkAnswer(**BASE, statut="repondu", fondation=FOND),
       "sans ['reponse']")
rejete("`approxime` sans son bloc d'approximation",
       lambda: FrameworkAnswer(**BASE, statut="approxime", reponse={"verbatim": "~12 %"},
                               fondation=FOND_ITP),
       "sans ['approximation']")
rejete("`non_fondable` qui publie quand même une réponse (entry #190)",
       lambda: FrameworkAnswer(**BASE, statut="non_fondable", gap=GAP,
                               reponse={"verbatim": "ROIC 14 %"}, fondation=FOND),
       "porte ['reponse', 'fondation']")
rejete("`sans_objet` qui sert son substitut comme réponse (contrôle ④)",
       lambda: FrameworkAnswer(**BASE, statut="sans_objet",
                               sans_objet={"motif": "m", "substitut_applique": "rotation des "
                                           "créances", "substitut_answer_id": 7,
                                           "aucun_substitut": False},
                               reponse={"verbatim": "rotation = 42 j"}),
       "porte ['reponse']")
valide("… mais `sans_objet` TOLÈRE une fondation (les entries qui prouvent le hors-sujet)",
       lambda: FrameworkAnswer(**BASE, statut="sans_objet", fondation=FOND,
                               sans_objet={"motif": "aucun revenu", "aucun_substitut": True}))
rejete("une approximation présentée comme une `mesure` (contrôle ④, règle de rang §1.5)",
       lambda: FrameworkAnswer(**BASE, statut="approxime", reponse={"verbatim": "~12 %"},
                               fondation=FOND, approximation=APX),
       "une estimation est")
rejete("une approximation incomplète (sans sens d'erreur) est refusée",
       lambda: Approximation(methode="m", ingredients_entry_ids=[1],
                             hypotheses_explicites=["h"]),
       "sensibilite")
rejete("un gap qui ne nomme pas la question qu'il comble",
       lambda: FrameworkAnswer(**BASE, statut="non_fondable",
                               gap={**GAP, "champs_cibles": ["qf_7"]}),
       "ne le nomme pas dans `champs_cibles`")
rejete("un `sans_objet` qui ne dit ni son substitut ni qu'il n'y en a pas",
       lambda: SansObjet(motif="m", aucun_substitut=False),
       "le silence n'est pas une option")
rejete("un `sans_objet` qui déclare les DEUX",
       lambda: SansObjet(motif="m", substitut_applique="s", aucun_substitut=True),
       "il faut choisir")
rejete("`aucun_substitut` n'a pas de défaut : l'omettre ne vaut pas déclaration",
       lambda: SansObjet(motif="m", substitut_applique="s", substitut_answer_id=7),
       "aucun_substitut")
# L'ÉQUIVALENCE, dans les deux sens — un `sans_objet` sur une approximation laisserait le contrôle ③
# muet là où il est le plus utile ; un `ok` sur une non-approximation serait un vert sur zéro ligne.
rejete("`honnetete_approximation='sans_objet'` sur une approximation",
       lambda: FrameworkAnswer(**BASE, statut="approxime", reponse={"verbatim": "~12 %"},
                               fondation=FOND_ITP, approximation=APX, manager=MGR),
       "si et seulement si")
rejete("`honnetete_approximation='ok'` sur une réponse qui n'approxime pas",
       lambda: FrameworkAnswer(**BASE, statut="repondu", reponse={"verbatim": "12,4 %"},
                               fondation=FOND,
                               manager={**MGR, "controles": {**CTRL,
                                                             "honnetete_approximation": "ok"}}),
       "si et seulement si")


print("\n3. l'actualité n'est PAS persistable (#53) — un axe de relation n'est pas une colonne")
rejete("`Fondation` (émise/persistée) REFUSE un champ `actualite`",
       lambda: Fondation(**FOND, actualite="courante"),
       "Extra inputs are not permitted")
rejete("… et `FrameworkAnswer` le refuse aussi en profondeur",
       lambda: FrameworkAnswer(**BASE, statut="repondu", reponse={"verbatim": "x"},
                               fondation={**FOND, "actualite": "courante"}),
       "Extra inputs are not permitted")
valide("`FondationServie` (lecture) la porte, avec son motif",
       lambda: FondationServie(**FOND, actualite="perimee",
                               motif_actualite="entry 190 datée 2019, ancre 2025"))
valide("`FrameworkAnswerServie` sert l'axe recalculé",
       lambda: FrameworkAnswerServie(**BASE, statut="repondu", reponse={"verbatim": "x"},
                                     fondation={**FOND, "actualite": "courante",
                                                "motif_actualite": "10-K 2025"}))
rejete("une actualité servie sans motif est refusée (un état sans cause ne se conteste pas)",
       lambda: FondationServie(**FOND, actualite="perimee"),
       "motif_actualite")
# DÉTENTEUR UNIQUE du vocabulaire : recopier les trois états ici les ferait diverger au prochain
# correctif de l'axe (#46). On vérifie l'égalité, pas l'inclusion.
_etats_servis = set(get_args(FondationServie.model_fields["actualite"].annotation))
check("le vocabulaire de l'axe servi est EXACTEMENT celui du détenteur (`actualite.ETATS`)",
      _etats_servis == set(ETATS), f"→ contrat {_etats_servis} vs détenteur {set(ETATS)}")


print("\n4. le manager acquitte ou renvoie — il ne réécrit pas, il ne promeut pas (§3.1/§3.3)")
valide("un renvoi porte son mandat et au moins un contrôle `ko`",
       lambda: ManagerVerdict(controles={**CTRL, "completude": "ko"}, verdict="renvoye",
                              motif="question sans réponse", mandat_de_recherche_id=3))
rejete("un renvoi SANS mandat — c'est l'Écart B que la v3 ferme",
       lambda: ManagerVerdict(controles={**CTRL, "fondation": "ko"}, verdict="renvoye",
                              motif="aucune entry citée"),
       "un renvoi qui ne")
rejete("un renvoi avec les 4 contrôles au vert (une opinion, pas un contrôle)",
       lambda: ManagerVerdict(controles=CTRL, verdict="renvoye",
                              motif="je n'aime pas cette société", mandat_de_recherche_id=3),
       "pas une opinion sur l'entreprise")
rejete("un acquittement malgré un `ko`",
       lambda: ManagerVerdict(controles={**CTRL, "non_substitution": "ko"}, verdict="acquitte",
                              motif="ça ira"),
       "n'a plus d'autorité")
rejete("un acquittement qui porte quand même un mandat",
       lambda: ManagerVerdict(controles=CTRL, verdict="acquitte", motif="ok",
                              mandat_de_recherche_id=3),
       "ne porte pas de mandat")
rejete("un manager qui tenterait de RÉÉCRIRE la réponse",
       lambda: ManagerVerdict(controles=CTRL, verdict="acquitte", motif="je corrige",
                              reponse={"verbatim": "en fait 14 %"}),
       "Extra inputs are not permitted")
rejete("… ou de PROMOUVOIR le rang",
       lambda: ManagerVerdict(controles=CTRL, verdict="acquitte", motif="je promeus",
                              rang_derive="A"),
       "Extra inputs are not permitted")
# La garde structurelle, en plus de la garde par instance : le bloc n'a AUCUN champ où écrire une
# correction. Un `extra='forbid'` se desserre d'une ligne ; un champ absent doit être AJOUTÉ.
_champs_mgr = set(ManagerVerdict.model_fields)
check("le bloc manager n'a aucun champ de réponse ni de rang (il ne peut pas en écrire)",
      not (_champs_mgr & {"reponse", "rang_derive", "rang", "fondation", "approximation"}),
      f"→ {sorted(_champs_mgr)}")


print("\n5. un état de mandat porte EXACTEMENT sa trace (Écart B, T8)")
valide("un mandat `ouvert` n'a pas de suite",
       lambda: FrameworkMandate(**MAND, etat="ouvert"))
rejete("… un `ouvert` qui porte déjà des entries produites",
       lambda: FrameworkMandate(**MAND, etat="ouvert", entry_ids_produits=[900]),
       "n'a pas de suite")
valide("un mandat `servi` porte l'avant, l'après et sa consommation",
       lambda: FrameworkMandate(**MAND, etat="servi", statut_apres="repondu",
                                consomme_at="2026-09-09T10:00:00Z", entry_ids_produits=[900]))
valide("… y compris quand la recherche n'a RIEN changé (`apres == avant` est licite)",
       lambda: FrameworkMandate(**MAND, etat="servi", statut_apres="non_fondable",
                                consomme_at="2026-09-09T10:00:00Z", entry_ids_produits=[]))
rejete("un `servi` sans son après — on ne pourrait pas dire si la boucle a changé quoi que ce soit",
       lambda: FrameworkMandate(**MAND, etat="servi", consomme_at="2026-09-09T10:00:00Z"),
       "sans l'avant ET l'après")
rejete("un `abandonne` qui conclurait sur la question",
       lambda: FrameworkMandate(**MAND, etat="abandonne", statut_apres="repondu"),
       "un abandon ne")
check("le mandat est EXÉCUTABLE : il porte une consigne, pas un sac de mots-clefs",
      "mandat" in FrameworkMandate.model_fields
      and FrameworkMandate.model_fields["mandat"].annotation is str,
      "→ c'est ce qui remplace `SYNTHESIS_TARGETS` (§5.1)")


print("\n6. les colonnes dénormalisées résolvent dans le contrat (#46)")


def resout(chemin: str) -> str:
    """Parcourt le chemin champ par champ depuis `FrameworkAnswer` et rend le nom du modèle final.
    Lève si un segment n'existe pas — c'est tout l'objet de la section."""
    modele = FrameworkAnswer
    for seg in chemin.split("."):
        champs = modele.model_fields
        if seg not in champs:
            raise KeyError(f"segment `{seg}` absent de {modele.__name__}")
        ann = champs[seg].annotation
        sous = [a for a in (get_args(ann) or (ann,)) if hasattr(a, "model_fields")]
        modele = sous[0] if sous else modele
    return modele.__name__


check("la table de correspondance n'est pas vide", bool(COLONNES_DENORMALISEES))
for col, chemin in sorted(COLONNES_DENORMALISEES.items()):
    try:
        resout(chemin)
        ok += 1
        print(f"  ok   colonne `{col}` → `{chemin}` résout dans le contrat")
    except Exception as e:  # noqa: BLE001
        fail += 1
        print(f"  FAIL colonne `{col}` → `{chemin}` ne résout pas : {e}")
rejete_faux = "fondation.rang_inexistant"
try:
    resout(rejete_faux)
    fail += 1
    print(f"  FAIL un chemin bidon (`{rejete_faux}`) est accepté → la section ne discrimine rien")
except KeyError:
    ok += 1
    print(f"  ok   un chemin bidon (`{rejete_faux}`) est bien détecté — la section discrimine")
# La garde qui protège T3/T4 : le test d'acceptation doit IMPORTER cette table, pas la redeviner.
_acc = Path("tools/acceptation_frameworks.py")
if _acc.exists():
    _src_acc = _acc.read_text(encoding="utf-8")
    # L'IMPORT, pas le token. Mesuré, pas prévu : la 1ʳᵉ version cherchait `"COLONNES_DENORMALISEES"
    # in _src_acc`, et la mutation « retirer l'import » la laissait VERTE — le nom survit dans le
    # commentaire qui l'explique et dans le `_COLONNE_DE` qui l'inverse. Un grep de présence qui lit
    # sa propre énonciation est un faux VERT ici, exactement comme il était un faux ROUGE en §7.
    _importe = any(
        isinstance(n, ast.ImportFrom)
        and (n.module or "").endswith("framework_answer_schema")
        and any(a.name == "COLONNES_DENORMALISEES" for a in n.names)
        for n in ast.walk(ast.parse(_src_acc))
    )
    check("`tools/acceptation_frameworks.py` IMPORTE la table plutôt que de deviner ses colonnes",
          _importe,
          "→ deux nomenclatures d'accord restent deux nomenclatures (#46) ; sans cet import, T3/T4 "
          "liraient `None` pour toujours et resteraient rouges pour la MAUVAISE raison")
    check("… et il adresse bien les colonnes par CHEMIN de contrat, pas par nom deviné",
          "fondation.cited_entry_ids" in _src_acc and "approximation.methode" in _src_acc,
          "→ importer la table sans s'en servir la rendrait décorative")
else:
    fail += 1
    print("  FAIL `tools/acceptation_frameworks.py` introuvable → section non mesurée "
          "(un prérequis manquant ne doit jamais passer pour un 0)")


print("\n7. détenteur unique — le contrat ne ré-implémente aucune règle qui vit ailleurs (#46)")
_src = inspect.getsource(fw)


def code_seul(source: str) -> str:
    """Le source DÉPOUILLÉ de ses commentaires et de ses docstrings.

    Mesuré, pas prévu : la 1ʳᵉ version coupait au `\"\"\"` du module et rougissait sur
    `etat_actualite` — qui n'est pas dans le code, mais dans la docstring de `FondationServie` qui
    DIT que l'axe vit ailleurs. Un grep d'interdit qui lit sa propre énonciation est un faux ROUGE,
    et un faux rouge fait « corriger » de la prose juste. La prose doit pouvoir nommer ce que le
    code n'a pas le droit de faire ; on la retire ici, et on l'assert en POSITIF juste après.
    """
    import io
    import tokenize
    morceaux = []
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type in (tokenize.COMMENT, tokenize.STRING):
            continue
        morceaux.append(tok.string)
    return " ".join(morceaux)


_corps = code_seul(_src)
check("la règle du cran n'est pas recopiée (elle vit dans `synthesis_feed`)",
      "_NOTCH_BELOW" not in _corps and "TIER_ORDER" not in _corps,
      "→ une règle recopiée re-diverge au correctif suivant")
check("l'axe actualité n'est pas ré-implémenté (il vit dans `knowledge.actualite`)",
      "etat_actualite" not in _corps and "source_date" not in _corps,
      "→ le contrat DÉCLARE l'axe servi, il ne le calcule pas")
check("… et la prose, elle, NOMME le détenteur qui le calcule (l'interdit en positif)",
      "etat_actualite_entry" in _src,
      "→ un interdit sans porte de sortie écrite se contourne par ré-implémentation")
check("`GapItem` est importé, jamais redéfini (#54 : un seul couple manque ↔ remède)",
      "from .readiness_report_schema import GapItem" in _src
      and "class GapItem" not in _corps)
check("le contrat n'invente pas un score composite des trois axes (#50, cause n°1)",
      "score_global" not in _corps and "composite" not in _corps)
# La prose, elle, DOIT porter le « pourquoi » : un garde-fou dont la raison n'est écrite nulle part
# se fait desserrer à la première gêne.
_doc = _src.split('"""')[1]
check("… et la docstring DIT pourquoi (le grep ci-dessus la retire à dessein)",
      "#53" in _doc and "actualité" in _doc.lower())
# Pas de jumeau figé : les copies sous `roadmap/provenance-cards/` ont dérivé de leurs originaux.
_jumeaux = sorted(Path("/contract_frozen").glob("*framework*schema*.py")) \
    if Path("/contract_frozen").is_dir() else None
if _jumeaux is None:
    fail += 1
    print("  FAIL `/contract_frozen` non monté → section non mesurée (cf. checks/README.md)")
else:
    check("aucune copie figée du contrat sous `roadmap/provenance-cards/` (#46)",
          not _jumeaux, f"→ {[p.name for p in _jumeaux]} : la carte POINTE le contrat, ne le duplique pas")
check("le contrat est versionné avec son chantier, sans bousculer `SCHEMA_VERSION` v2",
      FRAMEWORK_SCHEMA_VERSION == "v3.0.0"
      and FrameworkAnswer.model_fields["schema_version"].default == "v3.0.0",
      "→ bumper la v2 forcerait les 3 points de synchro (#19) et les 12 prompts (#39)")


print("\n8. le PONT relationnel — ce qu'un contrat ne peut PAS vérifier (#37)")
# Un contrat valide un objet ; la cohérence avec le corpus, la question et les autres réponses vit
# en Python. Les cas ci-dessous sont tous formellement VALIDES : s'ils passaient, ce serait la
# démonstration que le contrat seul ne suffit pas — et c'est précisément pourquoi le pont existe.
QUESTIONS = {
    "qf_1": {"plancher_tier": "B", "nature_attendue": "mesure"},
    "qf_7": {"plancher_tier": "B+", "nature_attendue": "mesure"},
}
ENTRIES = {
    190: {"reliability_tier": "A-", "nature": "mesure"},
    191: {"reliability_tier": "B", "nature": "mesure"},
    192: {"reliability_tier": "C", "nature": "interpretation"},
    # Tier A-, mais nature `interpretation` : cette entry existe pour que [E] soit ATTEIGNABLE.
    # Mesuré, pas prévu : [E] visait d'abord l'entry 192, dont le tier C faisait rougir [D] AVANT
    # que [E] ne soit atteint — le contrôle passait pour gardé alors qu'il n'avait jamais tourné.
    # Une fixture qui déclenche deux contrôles ne dit pas lequel des deux discrimine (1ᵉʳ faux vert).
    193: {"reliability_tier": "A-", "nature": "interpretation"},
}


def rep(**kw):
    """Une réponse formellement valide — chaque cas n'en change QU'UN ingrédient."""
    blocs = dict(reponse={"verbatim": "12,4 %"}, fondation=FOND)
    blocs.update(kw.pop("blocs", {}))
    return FrameworkAnswer(**{**BASE, **kw}, statut=kw.pop("statut", "repondu"), **blocs)


def pont(label, answer, motif, **kw):
    """Le pont doit REFUSER, et par la raison nommée."""
    global ok, fail
    args = dict(questions=QUESTIONS, entries=ENTRIES)
    args.update(kw)
    try:
        valider_pont_framework_answer(answer, **args)
        fail += 1
        print(f"  FAIL {label} → ACCEPTÉ par le pont alors qu'il devait être refusé")
    except FrameworkAnswerRefused as e:
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


def pont_ok(label, answer, **kw):
    global ok, fail
    args = dict(questions=QUESTIONS, entries=ENTRIES)
    args.update(kw)
    try:
        valider_pont_framework_answer(answer, **args)
        ok += 1
        print(f"  ok   {label}")
    except Exception as e:  # noqa: BLE001
        fail += 1
        print(f"  FAIL {label} → refusé alors qu'il est cohérent : {str(e)[:200]}")

pont_ok("[réf] une réponse cohérente passe le pont (sinon rien ci-dessous ne discrimine)",
        rep())
pont("[A] une question inconnue du framework",
     rep(question_id="qf_99"), "inconnue du framework")
pont("[B] une entry citée hors du corpus fourni (A2)",
     rep(blocs={"fondation": {**FOND, "cited_entry_ids": [190, 999]}}),
     "hors du corpus fourni")
pont("[C] un rang auto-déclaré meilleur que ses sources",
     rep(blocs={"fondation": {**FOND, "cited_entry_ids": [190, 191], "rang_derive": "A-"}}),
     "commandent B")
pont_ok("[C] … et le rang JUSTE (la plus faible citée) passe",
        rep(blocs={"fondation": {**FOND, "cited_entry_ids": [190, 191], "rang_derive": "B"}}))
# La règle du cran s'applique à l'approximation, et à elle seule : le pont interroge le détenteur
# (`derive_synthesis_reliability`), il ne recopie pas la table des crans.
pont("[C] une approximation rangée comme une mesure (le cran manque)",
     FrameworkAnswer(**BASE, statut="approxime", reponse={"verbatim": "~12 %"},
                     fondation={**FOND, "cited_entry_ids": [190], "rang_derive": "A-",
                                "nature_effective": "interpretation"}, approximation=APX),
     "un cran sous")
pont_ok("[C] … et l'approximation d'un cran sous (A- → B+) passe",
        FrameworkAnswer(**BASE, statut="approxime", reponse={"verbatim": "~12 %"},
                        fondation={**FOND, "cited_entry_ids": [190], "rang_derive": "B+",
                                   "nature_effective": "interpretation"}, approximation=APX))
pont("[D] un rang sous le plancher de la question",
     rep(question_id="qf_7", blocs={"fondation": {**FOND, "cited_entry_ids": [191],
                                                  "rang_derive": "B"}}),
     "sous le plancher")
pont("[E] la nature attendue n'est portée par aucune entry citée (#51)",
     rep(blocs={"fondation": {**FOND, "cited_entry_ids": [193], "rang_derive": "A-",
                              "nature_effective": "mesure"}}),
     "propriété de l'assertion")
_so = dict(sans_objet={"motif": "société sans stocks", "substitut_applique": "rotation",
                       "substitut_answer_id": 7, "aucun_substitut": False})
pont("[F] un substitut qui pointe une réponse à LA MÊME question (contrôle ④)",
     FrameworkAnswer(**BASE, statut="sans_objet", **_so),
     "elle-même",
     autres_reponses={7: FrameworkAnswer(**BASE, statut="repondu",
                                         reponse={"verbatim": "x"}, fondation=FOND)})
pont("[F] … ou qui ne désigne aucune réponse fournie",
     FrameworkAnswer(**BASE, statut="sans_objet", **_so), "pas un substitut",
     autres_reponses={})
pont_ok("[F] … et un substitut vers une AUTRE question passe",
        FrameworkAnswer(**BASE, statut="sans_objet", **_so),
        autres_reponses={7: FrameworkAnswer(**{**BASE, "question_id": "qf_7"}, statut="repondu",
                                            reponse={"verbatim": "18 mois"},
                                            fondation={**FOND, "rang_derive": "A-"})})

# Le POINT DE LECTURE. Un axe calculé mais non servi est un axe qui n'existe pas.
_ancre = MaterialEventLookup(status="unavailable", raison="flux injoignable (check hors-ligne)")
_servie = servir_answer(rep(), ancre=_ancre, entries=ENTRIES)
check("`servir_answer` rend bien une réponse SERVIE, porteuse de l'axe",
      isinstance(_servie, FrameworkAnswerServie) and _servie.fondation.actualite in ETATS,
      f"→ {type(_servie).__name__}")
check("… avec le motif de l'axe qui voyage avec lui",
      bool(_servie.fondation.motif_actualite))
check("… et une panne de flux ne se lit JAMAIS « rien n'a changé » (#49)",
      _servie.fondation.actualite == "indeterminable",
      f"→ {_servie.fondation.actualite} : un flux injoignable rend l'axe indéterminable, pas courant")
check("l'objet PERSISTÉ, lui, reste sans actualité (rien n'a été écrit — #53)",
      "actualite" not in rep().model_dump()["fondation"])
_src_pont = inspect.getsource(fwk)
check("le pont ne recopie pas la table des crans (il interroge son détenteur)",
      "_NOTCH_BELOW" not in code_seul(_src_pont)
      and "derive_synthesis_reliability" in _src_pont,
      "→ une règle recopiée re-diverge au correctif suivant (#46)")
check("le pont ne ré-implémente pas « la plus ancienne citée » (il la délègue)",
      "etat_actualite_entry" in _src_pont and "min(" not in code_seul(_src_pont),
      "→ prendre la plus récente blanchirait la péremption")
# Cet assert était inversé au lot 1 (« `load_frameworks` n'est PAS écrit ») : c'était une vanne, et
# elle a tenu — les 13 questions n'ont été écrites qu'au lot 2, comme données. Elle se retourne ici
# plutôt que de disparaître, parce que le mode de panne suivant est l'inverse du précédent : des
# questions codées EN DUR dans le pont se dériveraient de ce que la base contient déjà.
check("`load_frameworks` charge les questions depuis un fichier de DONNÉES, jamais du Python",
      "def load_frameworks" in _src_pont and "yaml.safe_load" in _src_pont
      and "MVDD_SPEC" not in code_seul(_src_pont),
      "→ des questions écrites en Python pourraient se dériver de la grille de 19 ou des postes "
      "EDGAR, et le test de couverture mesurerait alors sa propre constante")


print("\n9. « chaque champ du contrat a SON PIXEL » (§8.1) — rendu EXÉCUTABLE")
# Le point de lecture fait partie de la capacité : un champ calculé, validé, persisté, mais jamais
# affiché est un champ qui n'existe pas pour l'utilisateur. §8.1 l'exige en prose ; une exigence en
# prose se vérifie à l'œil, donc se perd au premier ajout de champ. On l'asserte comme une
# BIJECTION : tout ce que le contrat porte a un pixel, et tout pixel rend un champ réel.
_maq = Path("/contract_frozen/framework_screen_niveau3.md")
if not _maq.exists():
    fail += 1
    print(f"  FAIL maquette absente ({_maq}) → section non mesurée ; un prérequis manquant ne doit "
          "jamais passer pour un 0")
else:
    _txt = _maq.read_text(encoding="utf-8")

    def feuilles(modele, prefixe=""):
        """Les chemins TERMINAUX du contrat servi — ce qu'un écran doit savoir rendre."""
        out = []
        for nom, f in modele.model_fields.items():
            sous = [a for a in (get_args(f.annotation) or (f.annotation,))
                    if hasattr(a, "model_fields")]
            out += feuilles(sous[0], f"{prefixe}{nom}.") if sous else [f"{prefixe}{nom}"]
        return out

    attendues = set(feuilles(FrameworkAnswerServie))
    affiches = set(re.findall(r"⟦([a-z_.]+)⟧", _txt))
    check("la maquette annote bien ses zones par chemin de contrat", bool(affiches),
          "→ aucune annotation ⟦…⟧ trouvée : la maquette n'est alors qu'un dessin")
    orphelins = sorted(attendues - affiches)
    check("tout champ du contrat a son pixel", not orphelins,
          f"→ sans pixel : {orphelins} — un champ qu'aucun écran ne rend n'existe pas pour le "
          "lecteur, quel que soit le soin mis à le valider")
    inventes = sorted(affiches - attendues)
    check("… et tout pixel rend un champ RÉEL du contrat", not inventes,
          f"→ pixels sans champ : {inventes} — un écran qui promet un champ que le contrat ne porte "
          "pas est une maquette qui ment")
    check("la maquette rend le modèle SERVI (elle affiche l'actualité recalculée)",
          "fondation.actualite" in affiches and "fondation.motif_actualite" in affiches,
          "→ un niveau 3 qui servirait `FrameworkAnswer` afficherait le verdict d'avant le dernier "
          "événement matériel")
    check("… et elle n'invente aucun score composite des trois axes (#50)",
          "score_global" not in _txt and "score composite" not in _txt.lower().replace(
              "aucune zone n'affiche de score composite", ""),
          "→ fondre rang, nature et actualité en une pastille referait le défaut de la v2")


print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
