"""Le PONT relationnel du contrat de framework (chantier v3, lot 1) — et rien d'autre.

Un contrat valide un **objet**, jamais la cohérence entre deux (convention #37). Tout ce qui exige
de connaître le corpus, la question ou les autres réponses vit ici, en Python, et lève
`FrameworkAnswerRefused` — comme `monitoring._valider_pont_hypotheses` le fait déjà pour les
hypothèses figées. Le partage exact est écrit dans l'en-tête de `contracts/framework_answer_schema`.

CE QUE LE PONT VÉRIFIE, ET POURQUOI CHACUN EXISTE
--------------------------------------------------
  A. la question existe dans le framework — sinon la réponse s'indexe sur une question voisine, et
     T4/T5 passeraient sur une question qui n'est pas celle qu'on croit ;
  B. les entries citées ont été RÉELLEMENT fournies (A2) — un id hors corpus, c'est le modèle qui
     apporte une source que personne n'a lue. Même mode de panne que `validate_grounding`, et c'est
     LUI qui le prononce, pas une seconde implémentation (#46) ;
  C. le rang est celui que les tiers RÉELS commandent — un `rang_derive` est dérivé, jamais déclaré
     (règle transverse 7, §3.5). Un rang auto-déclaré est un rang faux ;
  D. le rang atteint le plancher de la question — une réponse fondée sur du C ne vaut pas une
     réponse, quel que soit son aplomb ;
  E. la nature attendue est portée par une entry citée — l'axe `nature` est une propriété de
     l'assertion (#51), il ne se déduit pas du statut ;
  F. un substitut pointe la réponse d'une AUTRE question — un `sans_objet` qui se cite lui-même
     comme substitut est le contrôle ④ retourné contre lui-même ;
  S. le `sens` de la réponse appartient au vocabulaire FERMÉ de la question (`sens_admis`) — le
     contrat laisse `sens` libre parce qu'un contrat d'objet ne connaît pas la question (#37), et
     c'est ici qu'il se ferme. Un sens hors vocabulaire (ou absent) rend la réponse incomparable à
     toutes les autres réponses de la même question : l'écran la montre, et rien ne la range ;
  V. la réponse cite la VERSION du référentiel en vigueur — sans elle, un correctif d'énoncé
     laisserait une réponse ancienne se lire comme si elle répondait à l'énoncé actuel (même panne
     que l'invariant [N] du plan de collecte, §5.2, écart V10).

`servir_answer()` est le POINT DE LECTURE : il ajoute l'axe actualité, recalculé, sans rien écrire.
Un GET qui servirait la ligne stockée telle quelle servirait le verdict d'avant l'événement
matériel — le faux vert que la capacité 4 a mis une journée à voir (#54).

`load_frameworks()` (lot 2) charge les 13 questions depuis `app/frameworks/frameworks.yaml`. Elles
sont des DONNÉES INERTES, jamais du code : voir l'en-tête du YAML pour la raison — écrites en
Python, elles pourraient se dériver de `MVDD_SPEC` ou des postes EDGAR, et le test de couverture
mesurerait alors sa propre constante.
"""
from __future__ import annotations

import re

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import ValidationError

from app.agents.v2.common import NATURES, TIER_ORDER, _TIER_RANK
from app.contracts.collection_plan_schema import CollectionPlan
from app.contracts.formule_grammaire import (
    FormuleInexecutable,
    dimension_formule,
    evaluer_formule,
    noms_de_la_formule,
    references_de_la_formule,
)
from app.contracts.framework_answer_schema import (
    ChiffreCle,
    FrameworkAnswer,
    FrameworkAnswerServie,
)
from app.contracts.framework_definition_schema import (
    FRAMEWORK_DEFINITION_SCHEMA_VERSION,
    ChiffreCleDeclare,
    FrameworksFile,
)
from app.contracts.memo_blocs import BLOCS_MEMO
from app.knowledge.actualite import MaterialEventLookup, etat_actualite_entry
from app.knowledge.evenements import retirer_faits_lus
from app.knowledge.synthesis_feed import derive_synthesis_reliability

FRAMEWORKS_YAML = Path(__file__).resolve().parents[2] / "frameworks" / "frameworks.yaml"

# Les clefs COPIÉES depuis un attribut de LA QUESTION (`getattr(q, clef)`, boucle de
# `question_profiles`). `framework_version` n'en fait PAS partie : elle vient de `fichier.
# schema_version`, pas d'une `Question` — la distinguer évite un `getattr(q, "framework_version")`
# qui lèverait `AttributeError`.
CLEFS_PROFIL_QUESTION = ("plancher_tier", "nature_attendue", "sens_admis", "chiffres_cles")

# TOUTES les clefs que le pont LIT dans un profil, `profil.get(...)` — celles de la question
# ci-dessus ET celles du contrat (`framework_version`). Détenteur unique : `valider_pont_…` les
# consomme par `profil.get(...)`, et un `.get` sur une clef mal orthographiée rend `None`, ce qui
# SAUTE le contrôle au lieu de le faire échouer. Un contrôle qui ne s'exécute pas est un vert
# (`feedback_check_degrade_en_sortant_a_zero`). `check_frameworks_definitions.py` vérifie que les
# profils produits portent exactement ces clefs, non nulles.
CLEFS_PROFIL_LUES = CLEFS_PROFIL_QUESTION + ("framework_version",)


class FrameworkAnswerRefused(Exception):
    """Refus du pont — une réponse formellement valide, mais incohérente avec le corpus.

    Levée, jamais rendue en valeur : un refus qui se lit comme un résultat finit par être ignoré.
    """


class FrameworkDefinitionRefused(Exception):
    """Refus au CHARGEMENT — le fichier de définitions est formellement valide mais incohérent.

    Distincte de `FrameworkAnswerRefused` : celle-ci dit que le référentiel est cassé, pas qu'une
    réponse l'est. Elle doit faire échouer le démarrage, jamais dégrader silencieusement vers un
    référentiel partiel — un framework à demi chargé rendrait `sans_objet` des questions qui
    existent (#54, la complétude à trois états).
    """


class CollectionPlanRefused(Exception):
    """Refus d'un PLAN DE COLLECTE — formellement valide (le contrat l'accepte), mais incohérent
    avec le référentiel. Sortie du traducteur (§3.6), vérifiée AVANT que le collecteur ne dépense.

    Levée, jamais rendue en valeur : un refus qui se lit comme un résultat finit par être ignoré.
    Distincte des deux autres — elle ne dit ni que le référentiel est cassé
    (`FrameworkDefinitionRefused`), ni qu'une réponse l'est (`FrameworkAnswerRefused`), mais que le
    PLAN l'est.
    """


def _valider_pont_definitions(fichier: FrameworksFile) -> None:
    """Les invariants RELATIONNELS des définitions — ceux qu'un contrat d'objet ne peut pas voir.

    Chacun garde un mode de panne qui se lit comme un succès :

      G. deux questions de frameworks DIFFÉRENTS partageant un id. §6 fait des `framework_questions`
         LE vocabulaire unique — deux `qf_1` et l'index désigne l'un pour l'autre ;
      H. deux chemins d'indexation identiques entre frameworks. Même panne, côté lien de couverture ;
      I. une question qui ne couvre pas exactement les archétypes déclarés. En trop : un archétype
         inventé n'est jamais interrogé. En moins : la question est MUETTE sur cet archétype, et
         l'agent tranchera seul — l'expérience du chantier dit qu'il fabrique une réponse plutôt
         que de se taire (entry #190, §0.2) ;
      J. un substitut qui ne résout pas, ou qui pointe sa propre question. Un hors-sujet qui se
         cite lui-même republie la question qu'il vient de déclarer sans objet ;
      K/L. `nature_attendue` et `plancher_tier` hors des vocabulaires DÉTENUS ailleurs
         (`common.NATURES`, `common.TIER_ORDER`). Le contrat les répète en `Literal` pour
         l'ergonomie ; c'est ici qu'on vérifie qu'ils n'ont pas divergé de leur détenteur (#46) ;
      M. une version de schéma qui ne correspond pas au contrat qui vient de valider le fichier ;
      N. un `chemin_indexation` dont la racine n'est pas l'id du framework qui le déclare. [H]
         garde l'unicité du chemin, pas son APPARTENANCE : `qf_3: defendabilite.cout_du_capital`
         passait G, H et tout le contrat. Le chemin serait alors rangé sous un framework qui ne
         l'instruit pas — la réconciliation §6 attribuerait la question au mauvais bloc de mémo,
         et le manager du framework `defendabilite` relirait une réponse dont il n'a pas la
         méthodologie. Ajouté le 2026-09-21, quand `reconcilier_vocabulaires` a voulu tenir cette
         règle de son côté : un invariant du référentiel se garde chez le référentiel, sinon il
         re-diverge au correctif suivant (`feedback_correctif_regle_jumeaux`) ;
      O. un `bloc_memo` qui ne désigne AUCUN bloc du `ResearchMemo` (lot 5, §6). Le contrat ne peut
         pas le voir : il ne connaît pas le mémo (#37). Non gardé, une faute de frappe
         (`financial` pour `financials`) rendrait le framework muet — sa rubrique sortirait « pas
         de méthodologie approuvée » alors que ses questions sont instruites, et le comité lirait
         l'absence comme une propriété de l'émetteur (`feedback_rendu_est_un_producteur`) ;
      P. deux frameworks qui revendiquent le MÊME bloc. §6 pose « un bloc du mémo = un framework » :
         à deux, le projecteur devrait choisir, et le choix se ferait par l'ordre du fichier — une
         méthodologie approuvée disparaîtrait de la note sans qu'aucun décompte ne bouge.
      Q. un `rouverte_par` qui nomme un type absent du catalogue `types_evenement`, ou un type qu'une
         question n'a pas à lister (#89). Absent : une faute de frappe (`financment`) ne rouvrirait
         JAMAIS la question — elle resterait à jour après chaque financement, en silence. Portée
         `aucune` : contradiction (la routine ne rouvre rien). Portée `toutes` : redondant, et
         trompeur — le lecteur croirait que les autres questions n'y sont pas soumises ;
      R. la table de FORME (`evenements.TYPE_PAR_ITEM`, code) produit un type que le catalogue
         (données) ne déclare pas, le déclare d'origine `exterieur` (#93), ou `a_qualifier` n'y
         est pas de portée `toutes`. Le premier cas
         ferait d'un dépôt reconnu un dépôt qui ne rouvre rien ; le second trahirait l'arbitrage Q3
         (« dans le doute, on rouvre large »).
    """
    if fichier.schema_version != FRAMEWORK_DEFINITION_SCHEMA_VERSION:
        raise FrameworkDefinitionRefused(
            f"[M] fichier en {fichier.schema_version}, contrat en "
            f"{FRAMEWORK_DEFINITION_SCHEMA_VERSION}"
        )

    toutes = [(f, q) for f in fichier.frameworks for q in f.questions]

    vus: dict[str, str] = {}
    for f, q in toutes:
        if q.id in vus:
            raise FrameworkDefinitionRefused(
                f"[G] la question `{q.id}` est déclarée par `{vus[q.id]}` ET par `{f.id}` — "
                f"les question_id sont LE vocabulaire unique (§6), ils ne peuvent pas collisionner"
            )
        vus[q.id] = f.id

    chemins: dict[str, str] = {}
    for _f, q in toutes:
        if q.chemin_indexation in chemins:
            raise FrameworkDefinitionRefused(
                f"[H] le chemin `{q.chemin_indexation}` est partagé par `{chemins[q.chemin_indexation]}` "
                f"et `{q.id}` — l'index ne saurait plus laquelle des deux il fonde"
            )
        chemins[q.chemin_indexation] = q.id

    # ⚠️ APRÈS [H], délibérément. Les fixtures de [G] et [H] montent deux frameworks `cadre_a` /
    # `cadre_b` portant des chemins `cadre_test.*` : placé avant, [N] leur volait le refus et les
    # deux cas négatifs rougissaient sur le mauvais assert (fixture non discriminante).
    for f, q in toutes:
        racine = q.chemin_indexation.split(".", 1)[0]
        if racine != f.id:
            raise FrameworkDefinitionRefused(
                f"[N] `{q.id}` est déclarée par `{f.id}` mais indexe sous `{racine}` — "
                f"un chemin appartient au framework qui l'instruit, sinon la réconciliation §6 "
                f"l'attribue au mauvais bloc de mémo"
            )

    attendus = set(fichier.archetypes)
    for _f, q in toutes:
        couverts = set(q.variables_par_archetype)
        if couverts != attendus:
            raise FrameworkDefinitionRefused(
                f"[I] `{q.id}` couvre {sorted(couverts)} au lieu de {sorted(attendus)} — "
                f"manquants : {sorted(attendus - couverts)}, inventés : {sorted(couverts - attendus)}"
            )

    for _f, q in toutes:
        for archetype, va in q.variables_par_archetype.items():
            cible = va.substitut_question_id
            if cible is None:
                continue
            if cible == q.id:
                raise FrameworkDefinitionRefused(
                    f"[J] `{q.id}` ({archetype}) se cite elle-même comme substitut"
                )
            if cible not in vus:
                raise FrameworkDefinitionRefused(
                    f"[J] `{q.id}` ({archetype}) renvoie au substitut `{cible}`, qui n'existe pas"
                )

    for _f, q in toutes:
        if q.nature_attendue not in NATURES:
            raise FrameworkDefinitionRefused(
                f"[K] `{q.id}` : nature `{q.nature_attendue}` hors du vocabulaire détenu par "
                f"`common.NATURES` ({sorted(NATURES)})"
            )
        if q.plancher_tier not in TIER_ORDER:
            raise FrameworkDefinitionRefused(
                f"[L] `{q.id}` : plancher `{q.plancher_tier}` hors de `common.TIER_ORDER`"
            )

    # ── [O] / [P] — le lien vers l'ordre du jour du comité (§6, lot 5) ───────────────────────────
    # L'ordre du jour est IMPORTÉ de son détenteur (`contracts.memo_blocs`), jamais recopié : un bloc
    # renommé dans le contrat du mémo fait rougir ici, au lieu de laisser un `bloc_memo` périmé
    # désigner un chapitre qui n'existe plus.
    revendique: dict[str, str] = {}
    for f in fichier.frameworks:
        if f.bloc_memo not in BLOCS_MEMO:
            raise FrameworkDefinitionRefused(
                f"[O] `{f.id}` projette sur `{f.bloc_memo}`, qui n'est pas un bloc du "
                f"`ResearchMemo` ({sorted(BLOCS_MEMO)}) — un framework qui projette dans le vide "
                f"est muet : sa rubrique sortirait « pas de méthodologie approuvée » alors qu'il "
                f"porte {len(f.questions)} question(s) instruite(s)"
            )
        if f.bloc_memo in revendique:
            raise FrameworkDefinitionRefused(
                f"[P] le bloc `{f.bloc_memo}` est revendiqué par `{revendique[f.bloc_memo]}` ET "
                f"par `{f.id}` — §6 pose « un bloc du mémo = un framework » ; à deux, le "
                f"projecteur trancherait par l'ordre du fichier et une méthodologie approuvée "
                f"disparaîtrait de la note sans qu'aucun décompte ne bouge"
            )
        revendique[f.bloc_memo] = f.id

    # ── [S] — ce qui se REPREND d'une autre méthodologie (#99) ─────────────────────────────────
    #    Une question citée qui n'existe pas ne se reprendrait jamais : la valorisation attendrait une
    #    réponse impossible, en silence. Se reprendre soi-même, c'est tourner en rond. Et la PROSE que
    #    lisent le comité et les agents doit nommer ce que la donnée reprend — sinon le libellé dirait
    #    « repris de qf_6 » pendant que le code reprend autre chose.
    #    ⚠️ Et la question reprise doit DÉCLARER au moins un chiffre clé (4 bis) : la valorisation
    #    relit l'encadré, jamais la prose. Reprendre une question qui ne se chiffre pas (se_4, une
    #    position dans le cycle — trouvé en instruisant l'encadré le 2026-09-29) ferait attendre un
    #    nombre que personne ne rendra jamais.
    questions_par_id = {q.id: q for _f, q in toutes}
    for _f, q in toutes:
        for i in q.ingredients_requis:
            for r in i.repris_de:
                if r not in questions_par_id:
                    raise FrameworkDefinitionRefused(
                        f"[S] `{q.id}.{i.id}` est repris de `{r}`, question inconnue du référentiel")
                if not questions_par_id[r].chiffres_cles:
                    raise FrameworkDefinitionRefused(
                        f"[S] `{q.id}.{i.id}` est repris de `{r}`, qui ne déclare aucun chiffre clé — "
                        "la valorisation reprend l'encadré, il n'y aurait rien à reprendre")
                if r == q.id:
                    raise FrameworkDefinitionRefused(
                        f"[S] `{q.id}.{i.id}` se reprend de sa propre question")
                if not re.search(rf"\b{r}\b", i.libelle):
                    raise FrameworkDefinitionRefused(
                        f"[S] `{q.id}.{i.id}` est repris de `{r}`, que son libellé ne nomme pas — la "
                        "prose lue par le comité et la donnée lue par le code divergeraient")

    # ── [T] — un chiffre CALCULÉ de l'encadré (#101) ───────────────────────────────────────────
    #    Sa formule ne lit que des chiffres RELEVÉS de la même question (un calculé qui en lit un
    #    autre ferait dépendre le résultat de l'ordre de calcul), jamais un décalage d'exercice (tous
    #    les chiffres d'un encadré se lisent à la même date), et ses additions portent sur une même
    #    unité (dette brute − trésorerie : M$ − M$). Une formule qui ne se calcule pas sur l'encadré
    #    rendrait une ligne toujours « non établie », en silence.
    #    Un chiffre RETENU (`le_plus_eleve_de`, #105) compare des chiffres relevés de la même question,
    #    dans SA propre unité, dont au moins un obligatoire (on ne retient jamais une prévision faute du
    #    constaté). Une formule peut lire un chiffre retenu (l'autonomie se calcule sur la consommation
    #    RETENUE) : il est établi avant elles, et ne lit lui-même que des relevés — aucun ordre caché.
    for _f, q in toutes:
        unites = {c.id: c.unite for c in q.chiffres_cles}
        releves = {c.id for c in q.chiffres_cles if not c.calcule_par_le_systeme}
        facultatifs = {c.id for c in q.chiffres_cles if c.facultatif}
        retenus = {c.id for c in q.chiffres_cles if c.le_plus_eleve_de}
        for c in q.chiffres_cles:
            if not c.le_plus_eleve_de:
                continue
            hors = sorted(n for n in c.le_plus_eleve_de if n not in releves)
            if hors:
                raise FrameworkDefinitionRefused(
                    f"[T] `{q.id}.{c.id}` retient le plus élevé de {hors}, qui ne sont pas des chiffres RELEVÉS "
                    f"de `{q.id}` ({sorted(releves)})")
            autres = sorted(f"{n} en {unites[n]!r}" for n in c.le_plus_eleve_de if unites[n] != c.unite)
            if autres:
                raise FrameworkDefinitionRefused(
                    f"[T] `{q.id}.{c.id}` ({c.unite!r}) compare {autres} : on ne retient pas le plus élevé de "
                    "deux unités")
            if all(n in facultatifs for n in c.le_plus_eleve_de):
                raise FrameworkDefinitionRefused(
                    f"[T] `{q.id}.{c.id}` ne compare que des chiffres facultatifs : il faut au moins un chiffre "
                    "obligatoire, sinon le chiffre retenu pourrait reposer sur une seule prévision")
        for c in q.chiffres_cles:
            if c.calcul is None:
                continue
            hors = sorted(n for n in noms_de_la_formule(c.calcul) if n not in releves | retenus)
            if hors:
                raise FrameworkDefinitionRefused(
                    f"[T] `{q.id}.{c.id}` se calcule sur {hors}, qui ne sont pas des chiffres RELEVÉS ou RETENUS "
                    f"de `{q.id}` ({sorted(releves | retenus)}) — le code ne saurait pas le calculer")
            decales = sorted(f"{n}[{k}]" for n, k in references_de_la_formule(c.calcul) if k != 0)
            if decales:
                raise FrameworkDefinitionRefused(
                    f"[T] `{q.id}.{c.id}` lit {decales} : un encadré se lit à une seule date, ni exercice décalé "
                    "ni douze mois glissants (ses chiffres portent déjà leur période)")
            try:
                dimension_formule(c.calcul, unites)
            except FormuleInexecutable as e:
                raise FrameworkDefinitionRefused(f"[T] `{q.id}.{c.id}` : {e}") from e

    # ── [Q] / [R] — ce qui rouvre quoi (#89) ───────────────────────────────────────────────────
    portees = {t.id: t.portee for t in fichier.types_evenement}
    for _f, q in toutes:
        for t in q.rouverte_par:
            if t not in portees:
                raise FrameworkDefinitionRefused(
                    f"[Q] `{q.id}` est rouverte par `{t}`, absent du catalogue `types_evenement` "
                    f"({sorted(portees)}) — un type inconnu ne rouvre jamais rien, et la question "
                    f"resterait à jour en silence")
            if portees[t] != "questions_declarees":
                raise FrameworkDefinitionRefused(
                    f"[Q] `{q.id}` liste `{t}`, de portée `{portees[t]}` : "
                    + ("un type qui ne rouvre rien ne peut pas rouvrir une question"
                       if portees[t] == "aucune" else
                       "il rouvre déjà TOUTES les questions — le lister ici laisserait croire que "
                       "les autres n'y sont pas soumises"))
    # Import tardif : `evenements` importe `material_events` (réseau), jamais au chargement du module.
    from app.knowledge.evenements import A_QUALIFIER, TYPES_DE_LA_FORME
    inconnus = sorted(TYPES_DE_LA_FORME - set(portees))
    if inconnus:
        raise FrameworkDefinitionRefused(
            f"[R] la qualification par la forme produit {inconnus}, absents du catalogue "
            f"`types_evenement` — un dépôt reconnu ne rouvrirait rien")
    exterieurs = sorted(TYPES_DE_LA_FORME & {t.id for t in fichier.types_evenement
                                              if t.origine == "exterieur"})
    if exterieurs:
        raise FrameworkDefinitionRefused(
            f"[R] la qualification par la forme produit {exterieurs}, déclarés d'origine extérieure "
            f"— un dépôt de l'émetteur serait lu comme un événement chez un concurrent (#93)")
    if portees.get(A_QUALIFIER) != "toutes":
        raise FrameworkDefinitionRefused(
            f"[R] `{A_QUALIFIER}` est de portée `{portees.get(A_QUALIFIER)}` au lieu de `toutes` — "
            f"un communiqué que personne n'a lu doit rouvrir tout (arbitrage Q3 du 2026-09-26)")


@lru_cache(maxsize=1)
def load_frameworks(chemin: Optional[str] = None) -> FrameworksFile:
    """Charge et VALIDE le référentiel. Lève plutôt que de rendre un référentiel partiel.

    Le YAML est lu en `safe_load` : un fichier de données ne doit pas pouvoir instancier d'objet
    Python. C'est la contrepartie du choix « données inertes » — l'inertie doit tenir au chargement,
    pas seulement à l'écriture.
    """
    p = Path(chemin) if chemin else FRAMEWORKS_YAML
    if not p.exists():
        raise FrameworkDefinitionRefused(f"référentiel introuvable : {p}")
    brut = yaml.safe_load(p.read_text(encoding="utf-8"))
    try:
        fichier = FrameworksFile.model_validate(brut)
    except ValidationError as exc:
        raise FrameworkDefinitionRefused(f"référentiel invalide ({p}) : {exc}") from exc
    _valider_pont_definitions(fichier)
    return fichier


def question_profiles(fichier: Optional[FrameworksFile] = None) -> dict[str, dict[str, Any]]:
    """Les profils à plat, dans la forme que `valider_pont_framework_answer` consomme.

    ⚠️ Les clefs sont produites depuis `CLEFS_PROFIL_LUES` et depuis les attributs du contrat, pas
    réécrites à la main : une clef mal orthographiée ici ferait sauter le contrôle D, E ou S côté
    pont sans qu'aucun test ne rougisse.

    Les valeurs de type liste sont COPIÉES : le référentiel est mis en cache (`lru_cache`), et un
    appelant qui muterait `profil["sens_admis"]` élargirait le vocabulaire de la question pour tout
    le processus — un contrôle qui s'assouplit tout seul, en silence.
    """
    fichier = fichier or load_frameworks()
    profils: dict[str, dict[str, Any]] = {}
    for f in fichier.frameworks:
        for q in f.questions:
            profil: dict[str, Any] = {}
            for clef in CLEFS_PROFIL_QUESTION:
                valeur = getattr(q, clef)
                profil[clef] = list(valeur) if isinstance(valeur, list) else valeur
            profil.update({
                "framework_id": f.id,
                "framework_version": fichier.schema_version,
                "chemin_indexation": q.chemin_indexation,
                "rouverte_par": list(q.rouverte_par),
                "ingredients_essentiels": [i.id for i in q.ingredients_requis if i.essentiel],
            })
            profils[q.id] = profil
    return profils


def types_qui_rouvrent(fichier: FrameworksFile, question_id: str) -> frozenset[str]:
    """DÉTENTEUR UNIQUE (#46) de « quels types d'événement rouvrent cette question ? » (#89) :
    ceux qu'elle déclare, plus ceux de portée `toutes`. C'est l'argument `rouvrent` de
    `evenements.ancre_de_la_question` ; aucun lecteur ne recompose l'union de son côté."""
    for f in fichier.frameworks:
        for q in f.questions:
            if q.id == question_id:
                universels = {t.id for t in fichier.types_evenement if t.portee == "toutes"}
                return frozenset(q.rouverte_par) | universels
    raise KeyError(f"question `{question_id}` absente du référentiel")


def _plus_faible(tiers: list[str]) -> str:
    """Le tier le plus faible d'une liste — rang le plus GRAND dans `TIER_ORDER` (A=0 … C=6).

    Même convention d'ordre que `derive_synthesis_reliability` (elle-même détenteur de la règle du
    cran) : un tier inconnu compte pour le pire, jamais pour le meilleur.
    """
    return max(tiers, key=lambda t: _TIER_RANK.get(t, len(TIER_ORDER)))


def nature_effective_de(natures: list[Any], *, approximation: bool) -> str:
    """La nature d'une FONDATION, dérivée des natures RÉELLES de ses entries citées.
    DÉTENTEUR UNIQUE de la règle (#46), pendant exact de `_plus_faible` sur l'axe fiabilité.

    RÈGLE : la nature forte ne se concède jamais par mélange. Une fondation vaut `mesure` seulement
    si TOUTES ses entries citées sont des mesures — un chiffre relevé cité à côté d'un commentaire
    (ou d'un calcul) produit une lecture DES DEUX, donc une `interpretation` (#51/#44). Sur une
    approximation, elle est forcée à `interpretation` : reconstruire, c'est interpréter, et le
    contrat le re-vérifie (§1.5). Une nature inconnue compte pour le pire, comme un tier inconnu.

    ⚠️ CETTE FONCTION EST NÉE D'UN JUMEAU (2026-09-21, #78). La règle vivait en une expression
    en ligne dans `assembler_answer` ; le pont, en la lisant sur le contrôle [E], allait la recopier.
    Deux exemplaires d'accord le jour où on les écrit, divergents au correctif suivant — c'est
    précisément ce que #46 interdit, et le geste que `feedback_correctif_regle_jumeaux` demande
    (greper la constante caractéristique, livrer un détenteur unique).

    ⚠️ ET ELLE EXISTE SURTOUT POUR QUE [E] NE CROIE PAS L'ANNONCE. Une `FrameworkAnswer` PORTE son
    `nature_effective`, et le pont valide aussi des réponses qui ne viennent pas d'`assembler_answer`
    (c'est sa raison d'être). Lire le champ déclaré plutôt que de le dériver serait exactement la
    faute que le contrôle [C] nomme pour le rang : « un rang auto-déclaré est un rang faux, il se
    dérive, il ne s'annonce pas ». Mesuré, pas supposé : la première rédaction de [E] lisait le
    champ, et `check_framework_contract` [E] est passé de ROUGE (refus attendu) à VERT — une
    fixture qui déclarait `mesure` en citant une entry d'interprétation était acquittée.
    """
    if approximation:
        return "interpretation"
    distinctes = {str(n) for n in natures}
    if len(distinctes) == 1 and distinctes <= NATURES:
        return distinctes.pop()
    return "interpretation"


def nature_satisfait(effective: str, attendue: str) -> bool:
    """La nature d'une fondation SATISFAIT-elle la nature attendue par la question ? DÉTENTEUR UNIQUE
    (#46), lu par le pont [E] et par `analyste.statuts_admissibles` (qui doit ouvrir exactement ce que
    le pont acceptera, #63).

    ARBITRAGE DE L'UTILISATEUR DU 2026-09-26, rendu comme un vrai fonds : un JUGEMENT de l'analyste
    appuyé sur des faits vérifiés est une réponse directe à une question de jugement — dans un mémo de
    comité, l'analyste répond à « qu'est-ce qui empêche un concurrent de capter ce profit ? » en citant
    les brevets et l'approbation réglementaire, sans avoir besoin qu'une opinion extérieure le dise à
    sa place. La nature attendue `interpretation` décrit l'ASSERTION demandée (un jugement), pas une
    exigence sur ses PIÈCES : elle PERMET de s'appuyer sur des opinions (d'où ses planchers plus bas),
    elle n'OBLIGE pas à en citer. Toute fondation la satisfait donc — des mesures, des événements, des
    opinions, ou un mélange.
    L'exigence inverse reste ENTIÈRE (#78) : une question de MESURE (« quelle preuve observable ? »)
    ne se satisfait que d'une fondation entièrement mesurée — un chiffre calculé ou une opinion citée
    à côté d'un relevé en ferait une lecture des deux.

    Mesuré avant d'écrire (RVMD × defendabilite, plan 130) : l'égalité stricte refusait 4 réponses sur
    4 questions de jugement (mo_1/3/4/5) fondées sur des brevets datés et un stade clinique, alors que
    `statuts_admissibles` leur avait ouvert `repondu` — le modèle ne voit pas la nature des pièces
    (#59), il ne pouvait ni savoir ni éviter. Les questions restaient sans réponse.
    """
    if attendue == "interpretation":
        return effective in NATURES
    return effective == attendue


def provient_du_depot(entry: dict[str, Any], depot: str) -> bool:
    """La pièce a-t-elle été tirée de CE dépôt EDGAR ? DÉTENTEUR UNIQUE (#103), lu par le pont [P] et par
    le contexte de l'analyste. EDGAR range chaque dépôt sous un dossier nommé par son numéro d'accession
    sans tirets (`/Archives/edgar/data/<cik>/000119312526377362/…`) : c'est l'adresse qui le prouve, pas
    le titre ni la date, qu'un article sur le dépôt porterait aussi."""
    return bool(depot) and depot.replace("-", "") in str(entry.get("source_url") or "")


def valider_pont_framework_answer(
    answer: FrameworkAnswer,
    *,
    questions: dict[str, dict[str, Any]],
    entries: dict[int, dict[str, Any]],
    autres_reponses: Optional[dict[int, FrameworkAnswer]] = None,
) -> None:
    """Vérifie A→F, K, P, S et V. Ne rend rien : le seul résultat possible est « pas de refus ».

    `questions` : `{question_id: {plancher_tier, nature_attendue, sens_admis, ...}}` — les DONNÉES
    du lot 2, telles que `question_profiles()` les produit.
    `entries`   : le corpus RÉELLEMENT fourni, `{id: {reliability_tier, entry_type, ...}}`.
    """
    # A. la question existe. Vérifié AVANT tout le reste : les contrôles D et E lisent son profil,
    #    et un profil absent les rendrait muets — un contrôle qui ne s'exécute pas est un vert.
    if answer.question_id not in questions:
        raise FrameworkAnswerRefused(
            f"question `{answer.question_id}` inconnue du framework `{answer.framework_id}` "
            f"({len(questions)} questions chargées) : une réponse qui ne s'indexe sur aucune "
            "question s'indexerait sur une question voisine")
    profil = questions[answer.question_id]

    # V. la réponse porte la VERSION du référentiel en vigueur pour cette question — sinon un
    #    correctif d'énoncé de `qf_1` laisserait une réponse ancienne se lire comme si elle répondait
    #    à l'énoncé actuel. Même panne, même remède que l'invariant [N] du plan de collecte (§5.2,
    #    écart V10) : une lignée non versionnée survit à ce qu'elle décrivait.
    version_attendue = profil.get("framework_version")
    if version_attendue is not None and answer.framework_version != version_attendue:
        raise FrameworkAnswerRefused(
            f"réponse en `{answer.framework_version}`, référentiel en `{version_attendue}` pour "
            f"`{answer.question_id}` : une réponse sans la version de la question qu'elle répond "
            "n'est plus interprétable dès le premier correctif d'énoncé (§2.4/§5.2)")

    if answer.fondation is not None:
        cites = list(answer.fondation.cited_entry_ids)

        # B. citations RÉELLEMENT fournies (A2).
        hors_corpus = [i for i in cites if i not in entries]
        if hors_corpus:
            raise FrameworkAnswerRefused(
                f"entries citées hors du corpus fourni : {hors_corpus}. Une source que personne n'a "
                "chargée n'est pas une source — c'est le modèle qui l'apporte de mémoire")

        tiers_reels = [str(entries[i].get("reliability_tier")) for i in cites]

        # C. LE RANG EST DÉRIVÉ. Deux règles distinctes, jamais confondues :
        #    • `repondu`   → le rang de la plus faible entry citée ;
        #    • `approxime` → UN CRAN SOUS, via le détenteur unique de la règle du cran. Le recopier
        #      ici le ferait diverger au prochain ajustement de seuil (#46).
        if answer.statut == "approxime":
            _, attendu, _ = derive_synthesis_reliability(tiers_reels)
            regle = "un cran sous la plus faible citée (estimation)"
        else:
            attendu = _plus_faible(tiers_reels)
            regle = "le rang de la plus faible citée"
        if answer.fondation.rang_derive != attendu:
            raise FrameworkAnswerRefused(
                f"`rang_derive` = {answer.fondation.rang_derive} alors que les tiers réels "
                f"{tiers_reels} commandent {attendu} ({regle}). Un rang auto-déclaré est un rang "
                "faux : il se dérive, il ne s'annonce pas (règle transverse 7)")

        # D. le rang atteint le PLANCHER de la question.
        plancher = profil.get("plancher_tier")
        if plancher is not None and _TIER_RANK.get(attendu, len(TIER_ORDER)) > _TIER_RANK.get(
                plancher, len(TIER_ORDER)):
            raise FrameworkAnswerRefused(
                f"rang {attendu} sous le plancher {plancher} de `{answer.question_id}` : une "
                "réponse qui n'atteint pas son plancher est un `non_fondable`, pas une réponse "
                "faible — la nuance est ce qui déclenche une collecte au lieu d'un affichage")

        # E. la nature attendue est portée par TOUTES les entries citées, pas déduite du statut
        #    (#51). Sauté sur `approxime`, dont la nature est `interpretation` par construction.
        #
        #    ⚠️ DURCI le 2026-09-21 (garde du guichet, #78) : « au moins une » est devenu « toutes ».
        #    Ce n'est pas un tour de vis d'humeur, c'est la fermeture du dernier passage. La
        #    rétrogradation au guichet range les chiffres calculés en `interpretation` ; mais [E]
        #    dans sa forme « au moins une » laissait un `repondu` citer une pièce calculée À CÔTÉ
        #    d'un relevé, recopier son chiffre, et garder statut `repondu` + rang du dépôt — le
        #    trajet exact de la réponse #475. Le mélange était déjà NOMMÉ par le code :
        #    `assembler_answer` calcule `nature_effective = mesure` seulement si TOUTES les citées
        #    sont des mesures. Ce verdict était stocké et personne ne le lisait — un drapeau calculé
        #    que rien n'applique est un affichage (`feedback_controle_au_point_de_lecture`). [E] le
        #    LIT désormais, au lieu de refaire sa propre lecture à côté (#46).
        #
        #    CE QUE ÇA COÛTE, MESURÉ SUR LA BASE AVANT D'ÊTRE ÉCRIT : zéro. La seule réponse
        #    `repondu` vivante (#473, qf_4) cite six entries, toutes `mesure`, aucune du lot dérivé.
        #    Et ça ne ferme aucune question : un analyste qui a BESOIN d'une pièce calculée garde
        #    `approxime` — où il doit écrire ses hypothèses et descendre d'un cran. C'est la
        #    troisième case de #68 : la forme force l'hypothèse à s'écrire au lieu de se taire.
        #    ⚠️ La nature effective se DÉRIVE des entries réelles (`nature_effective_de`,
        #    détenteur unique partagé avec `assembler_answer`), elle ne se lit JAMAIS sur la
        #    réponse : le pont valide aussi ce qui ne vient pas de l'analyste, et croire le champ
        #    déclaré serait la faute que [C] nomme pour le rang.
        natures_reelles = [entries[i].get("nature") for i in cites]
        effective = nature_effective_de(natures_reelles, approximation=answer.statut == "approxime")

        # E0. le pendant de [C] sur l'axe nature : la fondation ANNONCE ce que les entries commandent.
        if answer.fondation.nature_effective != effective:
            raise FrameworkAnswerRefused(
                f"`nature_effective` = {answer.fondation.nature_effective} alors que les natures "
                f"réelles {sorted(str(n) for n in natures_reelles)} commandent `{effective}`. Une "
                "nature auto-déclarée est une nature fausse : elle se dérive des sources citées, "
                "elle ne s'annonce pas (#51, pendant de la règle transverse 7)")

        attendue = profil.get("nature_attendue")
        # ⚠️ ASSOUPLI le 2026-09-26 pour les seules questions de JUGEMENT (arbitrage utilisateur,
        #    `nature_satisfait`) : un jugement fondé sur des faits vérifiés est une réponse directe.
        #    Les questions de MESURE gardent l'exigence « tout mesuré » de #78, intacte.
        if (attendue is not None and answer.statut != "approxime"
                and not nature_satisfait(effective, attendue)):
            portees = sorted({str(entries[i].get("nature")) for i in cites})
            raise FrameworkAnswerRefused(
                f"`{answer.question_id}` attend une assertion de nature `{attendue}`, mais la "
                f"fondation vaut `{effective}` : les entries citées portent {portees}. La nature "
                "est une propriété de l'assertion — elle se lit sur les sources, elle ne se déduit "
                "pas du statut de la réponse, et elle ne se concède jamais par mélange : un relevé "
                "cité à côté d'un chiffre calculé produit une LECTURE DES DEUX. S'appuyer sur le "
                "calcul est permis, mais alors c'est une approximation : elle s'écrit avec ses "
                "hypothèses et elle descend d'un cran")

    # S. le `sens` appartient au vocabulaire FERMÉ de la question. Le contrat le laisse libre (il ne
    #    connaît pas la question, #37) ; il se ferme ici, au seul endroit qui voit les deux.
    #    ⚠️ `sens_admis` absent du profil ⟹ contrôle SAUTÉ : le référentiel en garantit toujours un
    #    (`Field(min_length=2)`), donc un profil qui n'en porte pas vient d'ailleurs et on ne lui
    #    impose pas un vocabulaire qu'il n'a pas déclaré.
    admis = profil.get("sens_admis")
    if admis and answer.reponse is not None:
        if answer.reponse.sens not in admis:
            raise FrameworkAnswerRefused(
                f"`sens` = {answer.reponse.sens!r} hors du vocabulaire de `{answer.question_id}` "
                f"({sorted(admis)}) : un sens libre rend la réponse incomparable à toutes les "
                "autres réponses de la même question — l'écran la montre, et rien ne la range")

    # K. L'ENCADRÉ DE CHIFFRES CLÉS (4 bis) porte EXACTEMENT les chiffres que la question déclare, chacun
    #    dans l'unité déclarée. Ni plus (un chiffre inventé par l'analyste n'a pas de place dans le
    #    modèle de valorisation, qui relit l'encadré) ; ni moins (un chiffre omis se lirait « pas
    #    demandé » — l'absence se MOTIVE, `ChiffreCle.motif_absence`) ; jamais une autre unité (un coût du
    #    capital en fraction chez l'un et en % chez l'autre ferait deux chiffres, #95).
    #    ⚠️ `chiffres_cles` absent du profil ⟹ refus, pas saut : une liste vide est une déclaration
    #    (« ne se chiffre pas »), `None` serait un profil qui ne vient pas du référentiel — et un contrôle
    #    sauté est un vert (`feedback_check_degrade_en_sortant_a_zero`).
    if answer.reponse is not None:
        declares = profil.get("chiffres_cles")
        if declares is None:
            raise FrameworkAnswerRefused(
                f"profil de `{answer.question_id}` sans `chiffres_cles` : l'encadré ne peut pas être vérifié")
        unites = {c.id: c.unite for c in declares}
        rendus = {c.id: c.unite for c in answer.reponse.chiffres_cles}
        manquants = sorted(set(unites) - set(rendus))
        inventes = sorted(set(rendus) - set(unites))
        if manquants or inventes:
            raise FrameworkAnswerRefused(
                f"l'encadré de `{answer.question_id}` ne porte pas les chiffres que la question déclare — "
                f"manquants {manquants}, non déclarés {inventes}. Un chiffre que le dossier n'établit pas "
                "se rend avec son motif d'absence, il ne s'omet pas")
        mauvaises = sorted(f"{i} en {u!r} au lieu de {unites[i]!r}" for i, u in rendus.items() if u != unites[i])
        if mauvaises:
            raise FrameworkAnswerRefused(
                f"l'encadré de `{answer.question_id}` change l'unité déclarée : {mauvaises} — deux unités pour "
                "un même chiffre font deux chiffres (#95)")
        # K bis (#101). Un chiffre CALCULÉ vaut sa formule sur les chiffres RELEVÉS de ce même encadré —
        # d'où qu'arrive la réponse : c'est le code qui calcule (`completer_encadre`), et une réponse qui
        # porterait un autre nombre dirait autre chose que les chiffres qu'elle affiche à côté.
        attendus = {c.id: c for c in completer_encadre(declares, answer.reponse.chiffres_cles)}
        faux = []
        for c in answer.reponse.chiffres_cles:
            d = next((x for x in declares if x.id == c.id), None)
            if d is None or not d.calcule_par_le_systeme:
                continue
            e = attendus[c.id]
            if (c.valeur is None) != (e.valeur is None) or (
                    c.valeur is not None and abs(c.valeur - e.valeur) > 1e-6 * max(1.0, abs(e.valeur))):
                regle = d.calcul or f"le plus élevé de {', '.join(d.le_plus_eleve_de)}"
                faux.append(f"{c.id} = {c.valeur!r} au lieu de {e.valeur!r} ({regle})")
        if faux:
            raise FrameworkAnswerRefused(
                f"l'encadré de `{answer.question_id}` porte un chiffre calculé qui ne vaut pas sa formule : "
                f"{faux} — le calcul appartient au code, jamais à l'analyste (#101)")

    # P. UN FAIT POSTÉRIEUR SE LIT DANS LE DÉPÔT MÊME (#103). Déclarer « lu » le 8-K du 27/08 retire ce
    #    dépôt de l'horloge de la réponse (`servir_answer`) : c'est une déclaration qui rend À JOUR, donc
    #    elle se prouve. Chaque lecture cite au moins une pièce TIRÉE DE CE DÉPÔT (son numéro d'accession
    #    dans l'adresse de la pièce) — un article qui commente le dépôt n'est pas le dépôt ; et ces
    #    pièces sont dans la fondation, qui porte alors leur rang et leur nature (on ne lit pas hors de
    #    ce qu'on cite). Un effet non écrit est refusé par le contrat.
    if answer.reponse is not None and answer.reponse.faits_posterieurs:
        fondation = set(answer.fondation.cited_entry_ids) if answer.fondation else set()
        for fait in answer.reponse.faits_posterieurs:
            hors_fondation = sorted(set(fait.cited_entry_ids) - fondation)
            if hors_fondation:
                raise FrameworkAnswerRefused(
                    f"le fait postérieur {fait.depot} est lu dans {hors_fondation}, absentes des citations de la "
                    "réponse : une lecture qui ne fonde pas la réponse ne peut pas la rendre à jour")
            if not any(provient_du_depot(entries.get(i, {}), fait.depot) for i in fait.cited_entry_ids):
                raise FrameworkAnswerRefused(
                    f"le fait postérieur {fait.depot} est déclaré lu, mais aucune pièce citée "
                    f"({fait.cited_entry_ids}) ne provient de ce dépôt : on ne lit pas un dépôt dans une "
                    "source qui en parle (#103)")

    # F. un substitut pointe la réponse d'une AUTRE question.
    motif_substitut = motif_substitut_hors_sujet(answer, autres_reponses)
    if motif_substitut is not None:
        raise FrameworkAnswerRefused(motif_substitut)


def completer_encadre(declares: list[ChiffreCleDeclare], lignes: list[ChiffreCle]) -> list[ChiffreCle]:
    """L'encadré COMPLÉTÉ de ses chiffres calculés (#101). DÉTENTEUR UNIQUE, lu par l'assemblage de
    l'analyste (qui écrit) et par le pont [K] (qui vérifie) — deux lectures d'une même formule
    divergeraient au premier correctif (#46). Pur.

    Comme un vrai fonds : la dette nette de l'encadré est la différence des deux lignes au-dessus,
    jamais un chiffre retapé à part. Les lignes RELEVÉES passent telles quelles ; une ligne qu'on
    fournirait pour un chiffre calculé est ÉCARTÉE (ce n'est pas au rédacteur de la calculer) et
    remplacée par le calcul. Trois issues, jamais un silence (#25/#44) : calculé (daté par les
    périodes de ses termes, #42), ou non établi parce qu'un terme ne l'est pas (le terme est NOMMÉ),
    ou non calculable (un dénominateur nul — une propriété de l'entreprise, pas un zéro).
    """
    systeme = [d for d in declares if d.calcule_par_le_systeme]
    ids_systeme = {d.id for d in systeme}
    releves = [c for c in lignes if c.id not in ids_systeme]
    par_id = {c.id: c for c in releves}
    sortie = list(releves)
    facultatifs = {d.id for d in declares if d.facultatif}
    # Les chiffres RETENUS d'abord (#105) : une formule peut les lire, eux ne lisent que des relevés.
    for d in (x for x in systeme if x.le_plus_eleve_de):
        etablis = [par_id[n] for n in d.le_plus_eleve_de
                   if par_id.get(n) is not None and par_id[n].valeur is not None]
        absents = [n for n in d.le_plus_eleve_de if n not in {c.id for c in etablis}]
        obligatoires_absents = [n for n in absents if n not in facultatifs]
        if obligatoires_absents:
            ligne = ChiffreCle(id=d.id, unite=d.unite, motif_absence=(
                f"non établi (le plus élevé de {', '.join(d.le_plus_eleve_de)}) : "
                f"{', '.join(obligatoires_absents)} non établi(s) dans l'encadré — on ne retient pas une "
                "prévision faute du constaté"))
        else:
            gagnant = max(etablis, key=lambda c: c.valeur)   # à égalité, le premier déclaré
            saute = (f" ; {', '.join(absents)} non établi(s), facultatif(s)" if absents else "")
            ligne = ChiffreCle(id=d.id, unite=d.unite, valeur=gagnant.valeur, date_ou_periode=(
                f"{gagnant.date_ou_periode} — retenu : {gagnant.id}, le plus élevé de "
                f"{', '.join(d.le_plus_eleve_de)}{saute}"))
        sortie.append(ligne)
        par_id[d.id] = ligne
    for d in (x for x in systeme if x.calcul is not None):
        noms = sorted(noms_de_la_formule(d.calcul))
        absents = [n for n in noms if par_id.get(n) is None or par_id[n].valeur is None]
        if absents:
            sortie.append(ChiffreCle(id=d.id, unite=d.unite, motif_absence=(
                f"non calculable ({d.calcul}) : {', '.join(absents)} non établi(s) dans l'encadré")))
            continue
        try:
            valeur = evaluer_formule(d.calcul, {(n, 0): par_id[n].valeur for n in noms})
        except FormuleInexecutable as e:
            sortie.append(ChiffreCle(id=d.id, unite=d.unite, motif_absence=f"non calculable : {e}"))
            continue
        periodes = list(dict.fromkeys(par_id[n].date_ou_periode for n in noms))
        date = (f"{periodes[0]} — calculé : {d.calcul}" if len(periodes) == 1 else
                f"calculé : {d.calcul} — " + " ; ".join(f"{n} {par_id[n].date_ou_periode}" for n in noms))
        sortie.append(ChiffreCle(id=d.id, unite=d.unite, valeur=round(valeur, 6), date_ou_periode=date))
    return sortie


def motif_substitut_hors_sujet(
    answer: FrameworkAnswer,
    autres_reponses: Optional[dict[int, FrameworkAnswer]] = None,
) -> Optional[str]:
    """Le contrôle ④ « substitut » — DÉTENTEUR UNIQUE, partagé par le pont (control F) et le manager.

    Retourne un motif si le substitut d'un `sans_objet` est inouvrable ou pointe la MÊME question ;
    `None` si tout va bien. Le pont le `raise`, le manager en fait un contrôle `ko` — deux emplois,
    une règle (#46). La recopier ferait diverger le message du pont de celui du manager au premier
    correctif, et un lecteur croirait à deux contrôles là où il n'y en a qu'un.
    """
    if answer.sans_objet is None or answer.sans_objet.substitut_answer_id is None:
        return None
    cible = (autres_reponses or {}).get(answer.sans_objet.substitut_answer_id)
    if cible is None:
        return (f"`substitut_answer_id` = {answer.sans_objet.substitut_answer_id} ne désigne "
                "aucune réponse fournie : un substitut qu'on ne peut pas ouvrir n'est pas un "
                "substitut, c'est une promesse")
    if cible.question_id == answer.question_id:
        return (f"le substitut de `{answer.question_id}` est une réponse à `{answer.question_id}` "
                "elle-même : un hors-sujet qui se cite en substitut republie la question qu'il "
                "vient de déclarer sans objet (contrôle ④, §3.2)")
    return None


def servir_answer(
    answer: FrameworkAnswer,
    *,
    ancre: MaterialEventLookup,
    entries: dict[int, dict[str, Any]],
) -> FrameworkAnswerServie:
    """LE POINT DE LECTURE : la réponse persistée + l'axe actualité RECALCULÉ. N'écrit rien.

    L'actualité d'une réponse est celle de sa fondation, et la fondation se date par **la plus
    ancienne** de ses entries citées — jamais la plus récente, qui blanchirait la péremption en
    citant un communiqué frais à côté d'un chiffre de 2019. Cette règle a déjà un détenteur
    (`actualite.date_effective`) : plutôt que de la ré-implémenter, on présente la réponse dans la
    forme que ce détenteur sait lire (#46).
    """
    if answer.fondation is None:
        return FrameworkAnswerServie(**answer.model_dump())

    pseudo_entry = {
        "source_date": None,  # aucune date propre : la fondation se date par ses citations
        "content_structured": {"source_entry_refs": list(answer.fondation.cited_entry_ids)},
    }
    # #103 — les faits postérieurs que la réponse a LUS ne la périment plus : elle en a écrit l'effet.
    # La date de la fondation ne bouge pas (la plus ancienne pièce, jamais blanchie) ; c'est l'horloge
    # qui perd les dépôts lus — et seulement ceux qu'un analyste peut lire (`retirer_faits_lus`).
    lus = {f.depot: f.effet for f in answer.reponse.faits_posterieurs} if answer.reponse else {}
    horloge = retirer_faits_lus(ancre, lus)
    act = etat_actualite_entry(pseudo_entry, ancre=horloge, corpus=entries)
    motif = act.motif
    absorbes = [e for e in (ancre.recents if ancre.status == "found" else ())
                if e not in horloge.recents and e.accession in lus]
    if absorbes:
        motif += " — fait(s) postérieur(s) lu(s) par l'analyste : " + " ; ".join(
            f"{e.form} du {e.event_date.isoformat()} — effet : {lus[e.accession]}" for e in absorbes)

    donnees = answer.model_dump()
    donnees["fondation"] = {**donnees["fondation"], "actualite": act.etat,
                            "motif_actualite": motif}
    return FrameworkAnswerServie(**donnees)


def ingredients_a_collecter(q) -> list:
    """DÉTENTEUR UNIQUE (#46, #99) de « quels ingrédients de cette question se COLLECTENT ? » : tous, sauf
    ceux repris d'une autre méthodologie (`repris_de`) — un chiffre déjà instruit ne se recherche pas une
    seconde fois, sinon le dossier aurait deux coûts du capital. Lu par le traducteur (ce qu'il planifie)
    et par le pont du plan (ce qu'il exige, ce qu'il refuse)."""
    return [i for i in q.ingredients_requis if not i.repris_de]


def valider_pont_collection_plan(
    plan: CollectionPlan,
    *,
    fichier: Optional[FrameworksFile] = None,
    questions: Optional[frozenset[str]] = None,
) -> None:
    """Vérifie qu'un plan de collecte est cohérent avec le RÉFÉRENTIEL. Ne rend rien : le seul
    résultat possible est « pas de refus ».

    Ce que le contrat d'objet (`collection_plan_schema`) ne peut pas voir, parce qu'il exige de
    connaître les questions et leurs ingrédients (#37). Chaque invariant garde un mode de panne qui
    se lit comme un succès :

      N. le framework existe, ET à la version du plan. Un plan daté d'une autre version décrit un
         framework qui a pu changer de questions — le mode de panne de la couverture rétroactive
         (#57) ;
      O. l'archétype est l'un des archétypes DÉCLARÉS (§4.1.3). Un archétype inventé n'est jamais
         interrogé, et le plan paraîtrait complet en ayant sauté la moitié des questions ;
      P. chaque ligne RÉSOUT — la question appartient au framework, l'ingrédient à la question. Un
         ingrédient inventé écrirait le corrigé (le §0.2, entry #190, est né d'exactement ça) ;
      Q. une ligne ne planifie pas une question SANS OBJET pour cet archétype. Collecter pour une
         question que le framework déclare hors-sujet, c'est fabriquer une réponse là où il n'y a
         pas de question — l'inverse du signal que `sans_objet` porte ;
      R. LE CŒUR — T1bis (§9.2). Chaque ingrédient ESSENTIEL d'une question APPLICABLE a une ligne
         (`traduit` ou `inobtenable motivé`). Une omission n'est pas un trou : c'est un plan
         REFUSÉ. Un essentiel qui disparaît en silence produit un VERT (couverture à 100 % sur ce
         qui reste) — le mode de panne que toute la v3 combat.

    `questions` (optionnel) SCOPE la validation au BOUCLAGE (lot 5) : un plan qui rejoue un renvoi ne
    couvre légitimement que la question renvoyée. Alors `[R]` n'exige QUE les questions du scope, et
    `[P]` refuse une ligne HORS scope (le modèle n'a vu que le scope — une ligne ailleurs est une
    dérive, pas un cas d'usage). `questions=None` = le comportement historique, plan complet.

    Ce que ce pont NE fait PAS : émettre le mandat d'une ligne `inobtenable` (c'est le flux
    traducteur → `framework_mandates`), ni écrire `question_coverage` (c'est l'aiguilleur du
    collecteur). Il VALIDE, il ne collecte pas.
    """
    fichier = fichier or load_frameworks()

    # N. le framework existe, à la bonne version.
    frameworks = {f.id: f for f in fichier.frameworks}
    fw = frameworks.get(plan.framework_id)
    if fw is None:
        raise CollectionPlanRefused(
            f"[N] framework `{plan.framework_id}` inconnu du référentiel ({sorted(frameworks)}) : "
            "un plan pour un framework qui n'existe pas ne collecte sur rien")
    if plan.framework_version != fichier.schema_version:
        raise CollectionPlanRefused(
            f"[N] plan en `{plan.framework_version}`, référentiel en `{fichier.schema_version}` : "
            "un plan daté d'une autre version décrit un framework qui a pu changer de questions")

    # O. l'archétype est déclaré. Vérifié AVANT de lire `variables_par_archetype[plan.archetype]` —
    #    le chargement garantit que chaque question couvre exactement les archétypes déclarés
    #    (invariant [I]), donc l'indexation qui suit est sûre une fois O franchi.
    if plan.archetype not in set(fichier.archetypes):
        raise CollectionPlanRefused(
            f"[O] archétype `{plan.archetype}` hors des archétypes déclarés "
            f"{sorted(fichier.archetypes)} : une question ne s'instancie que sur un archétype connu")

    # `qdefs`, PAS `questions` : le paramètre `questions` (scope de bouclage) ne doit pas être
    # shadowé par le dict des définitions du framework — la collision rendait le scope inopérant.
    qdefs = {q.id: q for q in fw.questions}

    # P + Q. chaque ligne résout, et ne vise pas une question sans objet pour cet archétype.
    for it in plan.items:
        q = qdefs.get(it.question_id)
        if q is None:
            raise CollectionPlanRefused(
                f"[P] la ligne vise la question `{it.question_id}`, absente de "
                f"`{plan.framework_id}` : une collecte qui ne s'indexe sur aucune question relie "
                "un fait à rien")
        ingredients = {i.id for i in q.ingredients_requis}
        if it.ingredient_id not in ingredients:
            raise CollectionPlanRefused(
                f"[P] `{it.question_id}` n'a pas d'ingrédient `{it.ingredient_id}` "
                f"({sorted(ingredients)}) : un ingrédient inventé écrirait le corrigé")
        if it.ingredient_id not in {i.id for i in ingredients_a_collecter(q)}:
            raise CollectionPlanRefused(
                f"[P] `{it.question_id}.{it.ingredient_id}` est REPRIS d'une autre méthodologie : il ne "
                "se collecte jamais — un second chiffre au dossier contredirait le premier (#95, #99)")
        if questions is not None and it.question_id not in questions:
            raise CollectionPlanRefused(
                f"[P] la ligne vise `{it.question_id}`, HORS du scope de bouclage {sorted(questions)} : "
                "un plan scopé ne collecte que les questions renvoyées (le modèle n'a vu qu'elles)")
        if q.variables_par_archetype[plan.archetype].mode == "sans_objet":
            raise CollectionPlanRefused(
                f"[Q] `{it.question_id}` est SANS OBJET pour l'archétype `{plan.archetype}` : "
                "planifier sa collecte, c'est fabriquer une réponse là où le framework dit qu'il "
                "n'y a pas de question (§0.2)")

    # R. T1bis — chaque ingrédient essentiel d'une question APPLICABLE a une ligne. `sans_objet`
    #    n'a aucun ingrédient à collecter : on ne l'exige pas, mais on ne le tolère pas non plus (Q).
    couples = {(it.question_id, it.ingredient_id) for it in plan.items}
    for q in fw.questions:
        if q.variables_par_archetype[plan.archetype].mode != "variable":
            continue
        if questions is not None and q.id not in questions:
            continue  # bouclage : seules les questions renvoyées sont exigées (les autres sont déjà traitées)
        for i in ingredients_a_collecter(q):
            if i.essentiel and (q.id, i.id) not in couples:
                raise CollectionPlanRefused(
                    f"[R] l'ingrédient essentiel `{q.id}.{i.id}` n'a AUCUNE ligne dans le plan : "
                    "un essentiel omis n'est pas un trou, c'est un plan REFUSÉ (T1bis). Il doit "
                    "sortir en `traduit` ou en `inobtenable motivé`, jamais en rien")
