"""Vérification de la NOTE DE COMITÉ PROJETÉE (chantier v3, lot 5 — spec §6).

Sans réseau, sans modèle, sans base : la projection est purement en mémoire, et c'est ce qui la
rend vérifiable ici. Ce que ce check garde n'est PAS « les deux rubriques sortent » — ce serait
vrai d'un projecteur qui les aurait codées en dur, et la feuille de route exige l'inverse :

    « ajouter une méthodologie doit être une opération de DONNÉES, jamais de code ».

  • §1 L'ORDRE DU JOUR EST DÉRIVÉ, ET IL EST COMPLET — `BLOCS_MEMO ∪ META_MEMO` recouvre EXACTEMENT
       `ResearchMemo.model_fields`. Un champ neuf qui ne serait ni l'un ni l'autre disparaîtrait de
       l'ordre du jour sans bruit, et le comité délibérerait sur un chapitre qu'il ne sait pas
       manquant (`feedback_rendu_est_un_producteur`).
  • §2 LE CONTRAT DE LA NOTE INTERDIT LES CONFUSIONS — les quatre états sont distincts et chacun
       porte EXACTEMENT sa charge. Les deux états du milieu (`sans_acquittement`, `non_revalidable`)
       sont le cœur : fusionnés, ils font lire « le manager a tout refusé » là où la vérité est
       « personne n'a pu relire ». C'est le faux mesuré sur RVMD le 2026-09-24.
  • §3 LE PROJECTEUR REFUSE PLUTÔT QUE DE SAUTER — une réponse orpheline sautée rétrécirait la note
       en silence (`feedback_check_degrade_en_sortant_a_zero`).
  • §4 ⚠️ LA PREUVE DU LOT — un 3ᵉ framework FICTIF ajouté en YAML SEUL se projette, et occupe un
       chapitre qui sortait jusque-là « sans méthodologie approuvée ». La garantie porte sur la
       CROISSANCE, elle se teste sur la croissance.
  • §5 LE PROJECTEUR NE NOMME AUCUN FRAMEWORK — le versant statique de §4. §4 seul prouverait que
       le YAML suffit AUJOURD'HUI ; §5 interdit qu'un `if framework_id == …` s'y glisse demain.

POURQUOI §5 ASSERTE SUR L'AST ET NON SUR LE TEXTE DU FICHIER
--------------------------------------------------------------
L'en-tête de `projection_memo.py` ÉNONCE l'interdit, donc elle contient les jetons interdits
(« `qualite_financiere` et `defendabilite` n'apparaissent nulle part »). Un `grep` sur le source
brut virerait au ROUGE en lisant sa propre énonciation — convention #56,
`feedback_grep_interdit_lit_sa_propre_enonciation`. L'AST dépouille commentaires ET docstrings, et
ne laisse que ce qui s'exécute. Le miroir POSITIF est asserté juste après : la prose doit, elle,
nommer la règle.

Cible : pydantic v2 (container). Tester en container, **pas** le python hôte (v1).
"""
import ast
import inspect
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import get_args

from pydantic import ValidationError

import app.agents.v2.projection_memo as proj
from app.agents.v2.frameworks import FRAMEWORKS_YAML, FrameworkDefinitionRefused, load_frameworks
from app.contracts.analysis_v2_schemas import ResearchMemo
from app.contracts.framework_answer_schema import FrameworkAnswerServie
from app.contracts.memo_blocs import BLOCS_MEMO, META_MEMO, feuilles_memo
from app.contracts.memo_projete_schema import (
    ETATS_RUBRIQUE,
    MEMO_PROJETE_SCHEMA_VERSION,
    EtatRubrique,
    MemoProjete,
    PointProjete,
    RubriqueProjetee,
)
from app.agents.v2.projection_memo import AnswerLue, ProjectionRefusee, projeter_memo

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
              f"{str(e)[:220].replace(chr(10), ' ')}")


def rejete(label, fn, motif):
    """Un objet qui doit être refusé **par la règle nommée**. Un refus prononcé par une autre (un
    champ requis oublié dans la fixture) est un FAIL : la règle visée n'aurait jamais été atteinte
    (1ᵉʳ et 4ᵉ faux verts)."""
    global ok, fail
    try:
        fn()
        fail += 1
        print(f"  FAIL {label} → ACCEPTÉ alors qu'il devait être refusé")
        return
    except (ValidationError, ProjectionRefusee, FrameworkDefinitionRefused) as e:
        msg = str(e)
    except Exception as e:  # noqa: BLE001
        fail += 1
        print(f"  FAIL {label} → mauvaise exception {type(e).__name__}: {str(e)[:180]}")
        return
    if motif in msg:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} → refusé, mais PAS par la règle visée. Attendu « {motif} », "
              f"obtenu : {msg[:240].replace(chr(10), ' ')}")


# ── Fixtures ────────────────────────────────────────────────────────────────────────────────────
# Le référentiel RÉEL, jamais une maquette : une fixture plus favorable que la production est un
# check aveugle au vert (`feedback_fixture_copiee_du_reel`). Les frameworks et leurs chapitres sont
# LUS, jamais retapés — ce fichier ne doit pas non plus nommer `qualite_financiere`.
REEL = load_frameworks()
VERSION = REEL.schema_version
CTRL = dict(completude="ok", fondation="ok", honnetete_approximation="sans_objet",
            non_substitution="ok")
ACQUITTE = dict(verdict="acquitte", controles=CTRL, motif="les 4 contrôles au vert")
RENVOYE = dict(verdict="renvoye", controles={**CTRL, "fondation": "ko"},
               motif="fondation ko — aucune entry citable", mandat_de_recherche_id=7)
FOND = dict(cited_entry_ids=[190], rang_derive="A", nature_effective="mesure",
            actualite="courante", motif_actualite="postérieure au dernier événement matériel")


def servie(f, q, *, ticker_id="ZZZ", analyste="analyste_1", manager=ACQUITTE, **over):
    """Une réponse SERVIE formellement valide — chaque cas n'en change qu'un ingrédient."""
    d = dict(schema_version="v3.0.0", framework_id=f, framework_version=VERSION, question_id=q,
             ticker_id=ticker_id, analyste=analyste, statut="repondu",
             reponse={"verbatim": "12,4 %"}, fondation=dict(FOND))
    if manager is not None:
        d["manager"] = dict(manager)
    d.update(over)
    return FrameworkAnswerServie.model_validate(d)


def lue(f, q, **kw):
    return AnswerLue(answer_id=kw.pop("answer_id", 1), answer=servie(f, q, **kw))


# Un framework RÉEL et sa première question, pris par POSITION et non par nom : le check garde une
# règle de croissance, il ne doit pas se réécrire au prochain framework ajouté.
_PILOTE = REEL.frameworks[0]
_Q1 = _PILOTE.questions[0].id
_AUTRE = REEL.frameworks[1]
_Q2 = _AUTRE.questions[0].id

POINT = dict(question_id=_Q1, enonce=_PILOTE.questions[0].enonce,
             chemin_indexation=_PILOTE.questions[0].chemin_indexation)
ADOSSE = dict(framework_id=_PILOTE.id, libelle=_PILOTE.libelle,
              methodologie=_PILOTE.methodologie, framework_version=VERSION)


print("1. l'ordre du jour est DÉRIVÉ, et il est COMPLET")
_champs = set(ResearchMemo.model_fields)
check("`BLOCS_MEMO ∪ META_MEMO` recouvre EXACTEMENT les champs du `ResearchMemo`",
      set(BLOCS_MEMO) | set(META_MEMO) == _champs,
      f"→ hors couverture : {sorted(_champs - set(BLOCS_MEMO) - set(META_MEMO))} ; "
      f"inventés : {sorted((set(BLOCS_MEMO) | set(META_MEMO)) - _champs)}")
check("aucun champ n'est à la fois un bloc et un méta-champ",
      not (set(BLOCS_MEMO) & set(META_MEMO)),
      f"→ {sorted(set(BLOCS_MEMO) & set(META_MEMO))}")
check("l'ordre du jour n'est pas vide",
      bool(BLOCS_MEMO), "→ une note sans chapitre passerait toutes les gardes de complétude")
check("chaque méta-champ porte le MOTIF qui l'exclut, jamais un simple nom",
      all(isinstance(m, str) and len(m) > 20 for m in META_MEMO.values()),
      "→ un champ exclu sans raison écrite se relit comme un oubli, et se ré-exclut par habitude")
check("les feuilles sont préfixées par un bloc de l'ordre du jour",
      bool(feuilles_memo())
      and all(f.split(".")[0] in BLOCS_MEMO for f in feuilles_memo()),
      f"→ {sorted(f for f in feuilles_memo() if f.split('.')[0] not in BLOCS_MEMO)[:5]}")
# La dérivation doit rester une dérivation : un `BLOCS_MEMO = {"financials": …}` écrit à la main
# passerait tous les asserts ci-dessus le jour où on l'écrit, et divergerait au premier renommage.
_src_blocs = inspect.getsource(__import__("app.contracts.memo_blocs", fromlist=["x"]))
check("`BLOCS_MEMO` est DÉRIVÉ de `ResearchMemo.model_fields`, pas énuméré",
      "ResearchMemo.model_fields" in _src_blocs and "BLOCS_MEMO: dict[str, type] = _deriver_blocs()"
      in _src_blocs,
      "→ une liste retapée est un jumeau (#46) : elle reste juste jusqu'au premier renommage")


print("\n2. le CONTRAT de la note interdit les confusions (#25/#44/#54/#68)")
check("les quatre états ont UN seul détenteur (`ETATS_RUBRIQUE` == `EtatRubrique`)",
      tuple(get_args(EtatRubrique)) == tuple(ETATS_RUBRIQUE),
      f"→ {get_args(EtatRubrique)} ≠ {ETATS_RUBRIQUE}")
check("les deux états du milieu existent tous les deux, distincts",
      "sans_acquittement" in ETATS_RUBRIQUE and "non_revalidable" in ETATS_RUBRIQUE,
      "→ fusionnés, ils font lire « le manager a refusé » là où personne n'a pu relire")
check("le contrat de la note est versionné à part des 4 JSON d'analyse",
      MEMO_PROJETE_SCHEMA_VERSION == "v3.0.0"
      and MemoProjete.model_fields["schema_version"].default == "v3.0.0")

rejete("un point qui publie une réponse NON acquittée",
       lambda: PointProjete(**POINT, answer=servie(_PILOTE.id, _Q1, manager=RENVOYE)),
       "n'est pas acquittée")
rejete("un point qui publie une réponse jamais passée au manager",
       lambda: PointProjete(**POINT, answer=servie(_PILOTE.id, _Q1, manager=None)),
       "n'est pas acquittée")
rejete("un point MAL ÉTIQUETÉ (la réponse répond à une autre question)",
       lambda: PointProjete(**POINT, answer=servie(_PILOTE.id, _PILOTE.questions[1].id)),
       "un point mal étiqueté")
valide("un point acquitté et bien étiqueté se construit",
       lambda: PointProjete(**POINT, answer=servie(_PILOTE.id, _Q1)))

_pt = PointProjete(**POINT, answer=servie(_PILOTE.id, _Q1))
rejete("une rubrique `instruite` SANS aucun point",
       lambda: RubriqueProjetee(bloc=_PILOTE.bloc_memo, etat="instruite", motif="m", **ADOSSE),
       "se lit « rien à signaler »")
rejete("une rubrique `sans_acquittement` qui porte quand même un point",
       lambda: RubriqueProjetee(bloc=_PILOTE.bloc_memo, etat="sans_acquittement", motif="m",
                                points=[_pt], **ADOSSE),
       "`sans_acquittement` mais porte 1 point(s)")
rejete("une rubrique `non_revalidable` qui porte quand même un point",
       lambda: RubriqueProjetee(bloc=_PILOTE.bloc_memo, etat="non_revalidable", motif="m",
                                points=[_pt], **ADOSSE),
       "`non_revalidable` mais porte 1 point(s)")
rejete("une rubrique `non_revalidable` qui ne dit PAS à quelle méthodologie elle est adossée",
       lambda: RubriqueProjetee(bloc=_PILOTE.bloc_memo, etat="non_revalidable", motif="m"),
       "doit dire LAQUELLE")
rejete("une rubrique `pas_de_methodologie_approuvee` qui nomme quand même un framework",
       lambda: RubriqueProjetee(bloc=_PILOTE.bloc_memo, etat="pas_de_methodologie_approuvee",
                                motif="m", **ADOSSE),
       "l'absence serait alors celle du dossier")
rejete("une rubrique `pas_de_methodologie_approuvee` qui compte des réponses au dossier",
       lambda: RubriqueProjetee(bloc=_PILOTE.bloc_memo, etat="pas_de_methodologie_approuvee",
                                motif="m", reponses_non_acquittees=3),
       "une réponse sans question approuvée")
valide("une rubrique `non_revalidable` adossée et sans point se construit",
       lambda: RubriqueProjetee(bloc=_PILOTE.bloc_memo, etat="non_revalidable", motif="m",
                                reponses_non_acquittees=6, **ADOSSE))

_ordre = sorted(BLOCS_MEMO)
_rub = [RubriqueProjetee(bloc=b, etat="pas_de_methodologie_approuvee", motif="m") for b in _ordre]
_memo = dict(ticker_id="ZZZ", genere_le=datetime(2026, 9, 24, tzinfo=timezone.utc),
             framework_version=VERSION)
rejete("une note à qui il MANQUE un chapitre",
       lambda: MemoProjete(**_memo, rubriques=_rub[:-1]),
       "ne couvre pas l'ordre du jour")
rejete("une note qui INVENTE un chapitre",
       lambda: MemoProjete(**_memo, rubriques=_rub + [RubriqueProjetee(
           bloc="chapitre_invente", etat="pas_de_methodologie_approuvee", motif="m")]),
       "inventés")
rejete("une note qui porte DEUX fois le même chapitre",
       lambda: MemoProjete(**_memo, rubriques=_rub + [_rub[0]]),
       "deux rubriques pour un même chapitre")
valide("une note qui couvre exactement l'ordre du jour se construit",
       lambda: MemoProjete(**_memo, rubriques=_rub))


print("\n3. le PROJECTEUR refuse plutôt que de SAUTER")
rejete("une réponse d'un AUTRE émetteur glissée dans la note",
       lambda: projeter_memo(ticker_id="ZZZ", comite={}, archetype="rentable",
                             lues=[lue(_PILOTE.id, _Q1, ticker_id="AAAA")]),
       "une note qui mélange deux émetteurs")
rejete("une réponse rattachée à un framework ABSENT du référentiel",
       lambda: projeter_memo(ticker_id="ZZZ", comite={}, archetype="rentable",
                             lues=[lue("cadre_disparu", _Q1)]),
       "elle rétrécirait la note en silence")
rejete("une réponse écrite contre une version PÉRIMÉE du référentiel",
       lambda: projeter_memo(ticker_id="ZZZ", comite={}, archetype="rentable",
                             lues=[lue(_PILOTE.id, _Q1, framework_version="v2.0.0")]),
       "n'est plus la réponse à la question qu'on publie")
rejete("une réponse dont la question est inconnue de SON framework",
       lambda: projeter_memo(ticker_id="ZZZ", comite={}, archetype="rentable",
                             lues=[lue(_PILOTE.id, _Q2)]),
       "s'indexerait sur une question voisine")

# Les quatre états, produits pour de bon — un état déclaré dans un contrat que rien ne produit est
# un décideur sans producteur (`feedback_controle_au_point_de_lecture`).
_vide = projeter_memo(ticker_id="ZZZ", comite={}, archetype="rentable", lues=[])
check("émetteur classé, dossier vide → les chapitres pilotés sortent `sans_acquittement`",
      _vide.par_bloc()[_PILOTE.bloc_memo].etat == "sans_acquittement",
      f"→ {_vide.par_bloc()[_PILOTE.bloc_memo].etat}")
check("… et les chapitres sans pilote sortent `pas_de_methodologie_approuvee`",
      all(r.etat == "pas_de_methodologie_approuvee" for r in _vide.rubriques
          if r.bloc not in {f.bloc_memo for f in REEL.frameworks}),
      "→ un chapitre non instruit qui sortirait vide se lirait « rien à signaler »")

_non_classe = projeter_memo(ticker_id="ZZZ", comite={}, archetype=None,
                            lues=[lue(_PILOTE.id, _Q1, manager=RENVOYE)])
_r = _non_classe.par_bloc()[_PILOTE.bloc_memo]
check("émetteur NON CLASSÉ → `non_revalidable`, jamais `sans_acquittement`",
      _r.etat == "non_revalidable", f"→ {_r.etat}")
check("… et le motif dit que le remède est un CLASSEMENT, pas une collecte",
      "PAS CLASSÉ" in _r.motif and "classement" in _r.motif,
      f"→ {_r.motif[:160]}")
check("… et les réponses au dossier sont comptées, jamais tues",
      _r.reponses_non_acquittees == 1, f"→ {_r.reponses_non_acquittees}")

_instruite = projeter_memo(ticker_id="ZZZ", comite={}, archetype="rentable", lues=[
    lue(_PILOTE.id, _Q1, answer_id=11),
    lue(_PILOTE.id, _PILOTE.questions[1].id, answer_id=12, manager=RENVOYE)])
_r = _instruite.par_bloc()[_PILOTE.bloc_memo]
check("une réponse acquittée → `instruite`, et SEULE l'acquittée est publiée",
      _r.etat == "instruite" and [p.question_id for p in _r.points] == [_Q1],
      f"→ {_r.etat} / {[p.question_id for p in _r.points]}")
check("… le renvoi n'est pas publié mais il est COMPTÉ",
      _r.reponses_non_acquittees == 1, f"→ {_r.reponses_non_acquittees}")
check("… le point porte l'énoncé lu au référentiel, pas un id",
      _r.points[0].enonce == _PILOTE.questions[0].enonce)
check("… et l'id de la ligne, pour que le comité remonte à la pièce",
      _r.points[0].answer_id == 11)

# Deux analystes sur une même question donnent DEUX points, jamais une moyenne (§3.4).
_deux = projeter_memo(ticker_id="ZZZ", comite={}, archetype="rentable", lues=[
    lue(_PILOTE.id, _Q1, answer_id=21, analyste="analyste_2"),
    lue(_PILOTE.id, _Q1, answer_id=22, analyste="analyste_1")])
_r = _deux.par_bloc()[_PILOTE.bloc_memo]
check("deux analystes sur une même question → DEUX points, jamais une moyenne (§3.4)",
      len(_r.points) == 2, f"→ {len(_r.points)}")
check("… dans un ordre décidé par le référentiel + l'analyste, jamais par la base",
      [p.answer.analyste for p in _r.points] == ["analyste_1", "analyste_2"],
      f"→ {[p.answer.analyste for p in _r.points]}")


print("\n4. ⚠️ LA PREUVE DU LOT — un 3ᵉ framework ajouté en YAML SEUL se projette")
# Le test n'est pas « les 2 pilotes marchent » : ce serait vrai d'un projecteur qui les aurait
# codées en dur. On fait CROÎTRE le référentiel, sans toucher une ligne de Python, et on exige que
# le chapitre visé change d'état. Le bloc ciblé est choisi parmi ceux que personne ne revendique —
# lu, jamais retapé : le jour où un pilote le prendra, ce test se déplacera tout seul.
_libres = sorted(set(BLOCS_MEMO) - {f.bloc_memo for f in REEL.frameworks})
check("il reste un chapitre sans méthodologie sur lequel faire croître le référentiel",
      bool(_libres), "→ tous les chapitres sont pilotés : choisir un autre support de test")
_CIBLE = _libres[0] if _libres else None

_FICTIF = """
  - id: cadre_fictif
    libelle: Cadre fictif du test de croissance
    etape_benchmark: 3
    methodologie: >-
      Méthodologie fictive, ajoutée par le test de croissance du lot 5. Elle n'a aucune valeur
      analytique : elle existe pour prouver qu'un chapitre cesse d'être sans méthodologie
      approuvée par une opération de DONNÉES, sans diff de code.
    nature_dominante: interpretation
    bloc_memo: __CIBLE__
    questions:

      - id: cx_1
        enonce: La structure du secteur laisse-t-elle durablement de la rentabilité aux acteurs ?
        chemin_indexation: cadre_fictif.structure_du_secteur
        nature_attendue: interpretation
        plancher_tier: A
        rouverte_par: [resultats, surprise_concurrence]
        sens_admis: [favorable, defavorable]
        ingredients_requis:
          - id: intensite_concurrentielle
            libelle: Nombre et poids relatif des acteurs qui se disputent la même demande solvable
            essentiel: true
        variables_par_archetype:
__ARCHETYPES__
"""
_VAR = ("          {a}:\n"
        "            mode: variable\n"
        "            variable: Rentabilité que la structure du secteur laisse aux acteurs en place\n")


def _referentiel_augmente(bloc: str) -> str:
    """Le référentiel RÉEL + un framework de plus, écrit en YAML. Rendu : le chemin du fichier.

    Le fichier de base est LU, jamais reconstruit : un test qui se fabriquerait un mini-référentiel
    prouverait que le projecteur sait projeter une maquette (`feedback_fixture_copiee_du_reel`).
    """
    bloc_yaml = (_FICTIF.replace("__CIBLE__", bloc)
                 .replace("__ARCHETYPES__",
                          "".join(_VAR.format(a=a) for a in REEL.archetypes).rstrip("\n")))
    p = Path(tempfile.mkdtemp()) / "frameworks.yaml"
    p.write_text(FRAMEWORKS_YAML.read_text(encoding="utf-8") + "\n" + bloc_yaml, encoding="utf-8")
    return str(p)


if _CIBLE is not None:
    _avant = projeter_memo(ticker_id="ZZZ", comite={}, archetype="rentable", lues=[]).par_bloc()[_CIBLE]
    check(f"avant : le chapitre visé sort « pas de méthodologie approuvée »",
          _avant.etat == "pas_de_methodologie_approuvee", f"→ {_avant.etat}")

    _augmente = None
    valide("le référentiel augmenté charge et passe contrat + invariants relationnels",
           lambda: load_frameworks(_referentiel_augmente(_CIBLE)))
    try:
        _augmente = load_frameworks(_referentiel_augmente(_CIBLE))
    except Exception as e:  # noqa: BLE001
        print(f"       (référentiel augmenté non chargeable : {type(e).__name__}: {str(e)[:200]})")

    if _augmente is not None:
        _apres = projeter_memo(ticker_id="ZZZ", comite={}, archetype="rentable", lues=[],
                               fichier=_augmente).par_bloc()[_CIBLE]
        check("APRÈS, sans UNE ligne de Python modifiée : le chapitre est instruit par le YAML",
              _apres.etat == "sans_acquittement" and _apres.framework_id == "cadre_fictif",
              f"→ {_apres.etat} / {_apres.framework_id}")
        check("… et il porte la méthodologie déclarée dans le YAML, pas un libellé du code",
              _apres.libelle == "Cadre fictif du test de croissance"
              and _apres.methodologie.startswith("Méthodologie fictive"),
              f"→ {_apres.libelle}")

        _avec = projeter_memo(ticker_id="ZZZ", comite={}, archetype="rentable", fichier=_augmente,
                              lues=[lue("cadre_fictif", "cx_1", answer_id=31)]).par_bloc()[_CIBLE]
        check("… et une réponse acquittée s'y publie comme dans n'importe quel chapitre piloté",
              _avec.etat == "instruite" and [p.question_id for p in _avec.points] == ["cx_1"],
              f"→ {_avec.etat} / {[p.question_id for p in _avec.points]}")
        check("… la note couvre toujours exactement l'ordre du jour après la croissance",
              set(_avec.bloc for _avec in projeter_memo(
                  ticker_id="ZZZ", comite={}, archetype="rentable", lues=[], fichier=_augmente).rubriques)
              == set(BLOCS_MEMO))

    # Le versant DONNÉES de la garantie : croître est une opération de données, mais une opération
    # GARDÉE. Deux frameworks sur un même chapitre se refusent au chargement, pas à la projection.
    rejete("croître sur un chapitre DÉJÀ revendiqué est refusé par le référentiel ([P])",
           lambda: load_frameworks(_referentiel_augmente(REEL.frameworks[0].bloc_memo)),
           "[P]")


print("\n5. le PROJECTEUR ne nomme AUCUN framework (le versant statique de §4)")
# L'AST dépouille commentaires et docstrings : sans cela, l'en-tête qui ÉNONCE l'interdit ferait
# rougir le check en lisant sa propre énonciation (#56).
_arbre = ast.parse(inspect.getsource(proj))
_docs = set()
for _n in ast.walk(_arbre):
    if isinstance(_n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        if _n.body and isinstance(_n.body[0], ast.Expr) and \
                isinstance(_n.body[0].value, ast.Constant) and \
                isinstance(_n.body[0].value.value, str):
            _docs.add(id(_n.body[0].value))
# Deux blobs, pas un seul, et la distinction est mesurée : un nom de framework peut se cacher dans
# un littéral comme dans un identifiant, tandis qu'une écriture SQL ne vit QUE dans un littéral.
# Fondus ensemble, `cites.update(...)` — un `set` — se lisait « UPDATE » et faisait rougir la garde
# d'écriture. Faux rouge mesuré, pas prévu (`feedback_faux_rouge_se_creuse`).
_litteraux = " ".join(
    _n.value for _n in ast.walk(_arbre)
    if isinstance(_n, ast.Constant) and isinstance(_n.value, str) and id(_n) not in _docs)
_noms = " ".join(_n.id for _n in ast.walk(_arbre) if isinstance(_n, ast.Name)) + " " + " ".join(
    _n.attr for _n in ast.walk(_arbre) if isinstance(_n, ast.Attribute))

_interdits = sorted({f.id for f in REEL.frameworks} | {f.bloc_memo for f in REEL.frameworks})
_trouves = [t for t in _interdits if t in _litteraux or t in _noms]
check("aucun id de framework ni nom de chapitre dans le CODE du projecteur",
      not _trouves,
      f"→ {_trouves} : un nom en dur transforme « ajouter une méthodologie » en opération de code")
check("… le dépouillement a bien retiré la prose (le check ne lit pas sa propre énonciation)",
      all(t in inspect.getsource(proj) for t in _interdits[:1]),
      "→ si le source brut ne contient plus l'énonciation, ce test ne prouve plus rien")
_doc = ast.get_docstring(_arbre) or ""
check("… et la docstring, elle, DIT la règle et nomme son test",
      "opération de DONNÉES" in _doc and "sans\ndiff de code" in _doc.replace("**", ""),
      "→ une règle tenue sans être écrite se perd au premier refactor")
check("le projecteur n'ÉCRIT rien — aucun ordre SQL d'écriture dans ses littéraux",
      not any(m in _litteraux.upper() for m in ("INSERT ", "UPDATE ", "DELETE ")),
      "→ une note est produite à la lecture ; l'écrire servirait le verdict d'avant (#53/#54)")


print("\n" + "=" * 60)
print(f"{ok} vérifications OK, {fail} échec(s)")
raise SystemExit(1 if fail else 0)
