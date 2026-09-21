"""L'ANALYSTE du framework (spec v3 §3.1/§3.4, lot 3) — celui qui RÉPOND aux questions.

Il reçoit un émetteur, un framework, l'archétype de l'émetteur et un CORPUS, et produit une
`FrameworkAnswer` par question. Il ne cherche rien (c'est la chaîne de collecte, §3.6) et ne
s'acquitte pas lui-même (c'est le manager, §3.2) : il répond avec ce qu'on lui a donné, ou il dit
que ce qu'on lui a donné ne fonde pas la réponse.

LA FRONTIÈRE DÉTERMINISTE, ÉPROUVÉE AVANT TOUTE DÉPENSE MODÈLE
--------------------------------------------------------------
Même partage que le traducteur (`feedback_frontiere_gratuite_avant_depense_modele`). Ce que le
modèle PEUT décider tient en une phrase : *est-ce que ces sources-là répondent à cette question-là,
et que disent-elles*. Tout le reste est en fonctions pures, ici :

  · `questions_sans_objet` — le hors-sujet est une propriété du FRAMEWORK, pas une opinion. Une
    question `sans_objet` pour l'archétype ne part jamais au modèle : sa réponse est écrite par le
    code depuis le `motif_gabarit` du référentiel (§4.1.3). Demander au modèle de la reconnaître,
    c'est rouvrir exactement le chemin de l'entry #190 (un rendement du capital fabriqué pour une
    société sans exploitation) ;
  · `corpus_citable` — le modèle ne voit QUE les entries qui atteignent le plancher de la question.
    Il ne peut donc pas citer sous le plancher, et le plancher ne lui est jamais MONTRÉ comme un
    curseur (#59) : il n'est pas un levier, c'est une propriété de la méthode ;
  · `statuts_admissibles` — ce que le PONT pourra encore accepter sur ce corpus, calculé AVANT
    l'appel. Le plancher était déjà structurel ; `nature_attendue` et l'interaction plancher × règle
    du cran ne vivaient QUE dans le pont, donc après la dépense, et le modèle ne pouvait ni les voir
    ni les satisfaire. Mesuré sur NVDA et RVMD : 3 questions sur 14 sortaient en `refus` — donc sans
    mandat — alors que le corpus, lui, ne POUVAIT pas fonder la réponse ;
  · `aucune_reponse_possible` — la porte « il ne reste que la sortie honnête », DÉTENTEUR UNIQUE des
    deux sites qui la lisent (`contexte_analyste` ne montre pas la question, `repondre` l'écrit en
    `non_fondable` sans appeler). Elle SUBSUME le cas du corpus vide, qui n'a donc plus sa garde à
    elle (#46 : deux gardes d'accord restent deux gardes) ;
  · `contexte_analyste` — CE QUE LE MODÈLE VOIT : l'énoncé, la variable d'archétype, les sens admis,
    les ingrédients, et le corpus citable. **Ni `plancher_tier`, ni `nature_attendue`, ni
    `reliability_tier`, ni `nature` des entries.** Montrer le tier d'une entry, c'est demander au
    modèle de choisir son niveau de preuve ; le rang se DÉRIVE de ce qu'il a cité (règle transverse
    7, §3.5) ;
  · `assembler_answer` — `rang_derive` et `nature_effective` sont calculés par le code depuis les
    tiers et natures RÉELS des entries citées, en interrogeant leurs détenteurs uniques
    (`_plus_faible`, `derive_synthesis_reliability`), jamais recopiés (#46).

TROIS ÉTATS NOMMÉS, JAMAIS UN SILENCE (#25/#60) — ET SURTOUT DEUX ÉCHECS DISTINCTS
----------------------------------------------------------------------------------
Chaque question du framework sort dans exactement un état, et `repondre_framework` le VÉRIFIE
(aucune question ne s'évapore, même invariant que l'aiguillage du collecteur) :

  · une `FrameworkAnswer` — `repondu` / `approxime` (le modèle), `sans_objet` (le référentiel),
    `non_fondable` (le corpus ne fonde pas, avec son `GapItem` et son remède) ;
  · un REFUS, dans `ResultatAnalyste.refus`.

⚠️ `non_fondable` et `refus` ne disent PAS la même chose, et les confondre serait le mode de panne
de tout ce lot. `non_fondable` = **les données manquent** → ça produit un mandat de collecte.
`refus` = **l'analyste a fauté** (question omise, contrat violé, pont refusé) → ça ne produit AUCUN
mandat, parce qu'aller collecter ne réparerait rien. Convertir une omission de modèle en `gap`
blanchirait une panne d'agent en manque de données, et la chaîne irait chercher dehors ce qui
manquait dedans.

Le prompt vit dans le CODE tant qu'aucune migration ne l'exige (même montage que le traducteur et
que la synthèse, #54) ; sa resynchro en `agent_prompts` viendra avec le câblage runtime (#19/#39).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from pydantic import Field, model_validator

from app.agents.providers import ResolvedAgent, get_agent_provider
from app.agents.v2.common import TIER_ORDER, _TIER_RANK
from app.agents.v2.frameworks import (
    FrameworkAnswerRefused,
    _plus_faible,
    load_frameworks,
    nature_effective_de,
    question_profiles,
    valider_pont_framework_answer,
)
from app.agents.v2.runner import run_json_agent
from app.agents.v2.traducteur import questions_applicables
from app.contracts.analysis_v2_schemas import Strict
from app.contracts.framework_answer_schema import (
    Approximation,
    Fondation,
    FrameworkAnswer,
    Reponse,
    SansObjet,
)
from app.contracts.framework_definition_schema import (
    FrameworkDefinition,
    FrameworksFile,
    QuestionDefinition,
)
from app.contracts.readiness_report_schema import GapItem
from app.knowledge.synthesis_feed import derive_synthesis_reliability

__all__ = [
    "AnalysteReponse",
    "AnalysteSortie",
    "AnalysteInapplicable",
    "AnalysteEvaporation",
    "ResultatAnalyste",
    "questions_sans_objet",
    "corpus_citable",
    "statuts_admissibles",
    "aucune_reponse_possible",
    "contexte_analyste",
    "reponse_sans_objet",
    "reponse_non_fondable",
    "assembler_answer",
    "repondre",
]


class AnalysteInapplicable(Exception):
    """La demande n'a pas d'objet AVANT tout appel modèle : framework ou archétype inconnu, ou
    réponse d'archétype demandée pour une question qui n'est pas dans cet état. Refusé ici, pas dans
    le pont (#40) — on ne paie pas un appel pour apprendre ce qu'une lecture du référentiel dit."""


class AnalysteEvaporation(Exception):
    """Une question du framework n'est sortie NI en réponse NI en refus.

    C'est un bug de `repondre`, pas une donnée : levé, jamais rendu en valeur. Sans cette garde, une
    question perdue en route se lit comme un dossier complet sur ce qui reste — le vert à 100 % sur
    un sous-ensemble, mode de panne que toute la v3 combat (T1bis, invariant [R] du plan).
    """


class AnalysteReponse(Strict):
    """CE QUE LE MODÈLE PRODUIT pour une question — et rien de plus.

    Ce qu'il ne peut PAS émettre, et pourquoi :
      · `sans_objet` — propriété du FRAMEWORK pour l'archétype, écrite par le code (§4.1.3) ;
      · `non_fondable` — il en émet la MATIÈRE (`sans_fondement` + ce qui manque), jamais le
        `GapItem` : le couple manque ↔ remède a un détenteur unique (#54), et `priorite` /
        `remede` sont des leviers d'exigence (#59) ;
      · `rang_derive` / `nature_effective` — dérivés des entries citées par `assembler_answer`. Un
        rang ne se déclare pas, il se dérive (règle transverse 7) ;
      · l'en-tête (ticker, framework, version, analyste) — un fait de la requête, posé par le code,
        comme pour le plan du traducteur (#36/#53/#57).
    """
    question_id: str = Field(min_length=1)
    statut: Literal["repondu", "approxime", "sans_fondement"]
    # `verbatim` porte deux charges selon le statut : la réponse lisible, ou CE QUI MANQUE. Dans les
    # deux cas c'est du texte qu'un humain lit, jamais un code.
    verbatim: str = Field(min_length=1)
    valeur: Optional[float] = None
    unite: Optional[str] = Field(default=None, min_length=1)
    # Le vocabulaire est CELUI DE LA QUESTION (`sens_admis`, montré au contexte) ; c'est le pont [S]
    # qui vérifie l'appartenance — le contrat d'objet ne connaît pas la question (#37).
    sens: Optional[str] = Field(default=None, min_length=1)
    cited_entry_ids: list[int] = Field(default_factory=list)
    approximation: Optional[Approximation] = None

    @model_validator(mode="after")
    def _le_statut_porte_exactement_sa_charge(self):
        """Même forme que le contrat de sortie : un statut commande ses blocs ET interdit les autres.

        Sans l'interdiction, un `sans_fondement` pourrait arriver avec des citations et une valeur —
        c'est-à-dire une réponse déguisée en manque, que le code transformerait en mandat de
        collecte pour un chiffre déjà fourni.
        """
        if self.statut == "sans_fondement":
            sales = [n for n in ("valeur", "unite", "sens", "approximation")
                     if getattr(self, n) is not None]
            if sales or self.cited_entry_ids:
                raise ValueError(
                    f"`sans_fondement` portant {sales or 'des citations'} : un manque qui cite ses "
                    "sources et donne sa valeur n'est pas un manque, c'est une réponse")
            return self
        if not self.cited_entry_ids:
            raise ValueError(
                f"statut `{self.statut}` sans citation : une réponse sans source est une opinion. "
                "Si le corpus ne fonde pas la réponse, le statut est `sans_fondement`")
        if not self.sens:
            raise ValueError(
                f"statut `{self.statut}` sans `sens` : la question ferme son vocabulaire de sens "
                "(`sens_admis`), et une réponse qui ne s'y range pas n'est comparable à aucune autre")
        if self.statut == "approxime" and self.approximation is None:
            raise ValueError(
                "`approxime` sans bloc `approximation` : une estimation dont la méthode, les "
                "ingrédients, les hypothèses ou le sens d'erreur manquent se lit exactement comme "
                "une mesure (contrôle ③, §3.2)")
        if self.statut == "repondu" and self.approximation is not None:
            raise ValueError(
                "`repondu` portant une `approximation` : si le chiffre a été reconstruit, le statut "
                "est `approxime` — c'est la non-substitution (contrôle ④)")
        return self


class AnalysteSortie(Strict):
    """L'enveloppe du modèle — rien que les réponses. Aucun en-tête : cf. en-tête du module."""
    reponses: list[AnalysteReponse] = Field(min_length=1)


@dataclass
class ResultatAnalyste:
    """Le bilan d'un passage d'analyste. `answers` + `refus` couvrent TOUTES les questions du
    framework, et `repondre` le vérifie (`AnalysteEvaporation`)."""
    answers: list[FrameworkAnswer] = field(default_factory=list)
    refus: list[tuple[str, str]] = field(default_factory=list)  # (question_id, motif)
    run: Any = None  # AgentRunResult, ou None quand aucun appel n'a été nécessaire


# ── Les fonctions PURES ──────────────────────────────────────────────────────────────────────────

def _framework_de(fichier: FrameworksFile, framework_id: str) -> FrameworkDefinition:
    for f in fichier.frameworks:
        if f.id == framework_id:
            return f
    raise AnalysteInapplicable(
        f"framework `{framework_id}` inconnu du référentiel "
        f"({sorted(f.id for f in fichier.frameworks)})")


def questions_sans_objet(
    fichier: FrameworksFile, framework_id: str, archetype: str
) -> list[QuestionDefinition]:
    """Le COMPLÉMENT de `questions_applicables` — calculé depuis elle, jamais réécrit.

    Le filtrage par archétype a un détenteur unique (`traducteur.questions_applicables`, #46) : une
    seconde implémentation ici divergerait au premier ajustement, et les deux moitiés ne
    couvriraient plus le framework — des questions ni planifiées ni répondues, en silence.
    """
    applicables = {q.id for q in questions_applicables(fichier, framework_id, archetype)}
    fw = _framework_de(fichier, framework_id)  # résolu : `questions_applicables` a déjà levé sinon
    return [q for q in fw.questions if q.id not in applicables]


def corpus_citable(
    question: QuestionDefinition, entries: dict[int, dict[str, Any]]
) -> dict[int, dict[str, Any]]:
    """Les entries qui ATTEIGNENT le plancher de fiabilité de la question. Pur.

    Le filtre est structurel, pas une consigne : ce qui n'est pas montré ne peut pas être cité. Le
    plancher n'apparaît donc jamais dans le contexte du modèle (#59) — et le contrôle [D] du pont
    reste en face, parce qu'un filtre côté code et une garde côté pont ne gardent pas la même chose
    (le pont voit aussi les réponses qui ne viennent pas d'ici).

    Un tier inconnu ou absent compte pour le PIRE, donc il est exclu : une entry dont on ne sait pas
    ce qu'elle vaut ne peut pas fonder une réponse au-dessus d'un plancher.
    """
    plafond = _TIER_RANK.get(question.plancher_tier, len(TIER_ORDER))
    return {
        i: e for i, e in entries.items()
        if _TIER_RANK.get(str(e.get("reliability_tier")), len(TIER_ORDER)) <= plafond
    }


def statuts_admissibles(
    question: QuestionDefinition, citables: dict[int, dict[str, Any]]
) -> tuple[list[str], list[str]]:
    """Les statuts que le PONT peut encore accepter pour cette question sur CE corpus, + les motifs
    des statuts écartés. Pur, et calculé AVANT tout appel (#40).

    POURQUOI CETTE FONCTION EXISTE — mesuré sur le corpus réel, pas déduit. Le plancher était déjà
    structurel (`corpus_citable`), mais deux autres exigences de la question ne vivaient QUE dans le
    pont, après la dépense : `nature_attendue` ([E]) et l'interaction plancher × règle du cran ([D]).
    Le modèle ne les voit jamais (#59, à raison) — il ne pouvait donc ni les satisfaire ni savoir
    qu'il ne le pouvait pas. Résultat mesuré sur NVDA et RVMD : 3 questions sur 14 sorties en `refus`,
    c'est-à-dire en PANNE D'AGENT, donc **sans aucun mandat de collecte**, alors que deux d'entre
    elles étaient des manques de données qu'une collecte réparerait.

    C'est l'erreur SYMÉTRIQUE de celle que l'en-tête du module interdit. Convertir une omission de
    modèle en `gap` blanchirait une panne d'agent ; imputer à l'agent un corpus qui ne POUVAIT pas
    fonder la réponse condamne au contraire la question au silence — elle ne produit pas de mandat,
    donc elle reste sans réponse à jamais. Les deux sens comptent.

      · `repondu` — admissible seulement si une entry citable porte `nature_attendue` : une nature
        absente du corpus ne peut pas être citée, donc [E] refuserait tout. ⚠️ On ne filtre PAS le
        corpus par nature pour autant.
        ⚠️ [E] a été DURCI le 2026-09-21 (#78) : il compare désormais `nature_effective` — donc, sur
        une question de `mesure`, il exige que TOUTES les citations soient des mesures. Cette porte
        reste pourtant EXACTE, et c'est vérifié, pas supposé : le modèle peut toujours choisir de ne
        citer que des mesures, donc l'existence d'une seule mesure citable suffit à ouvrir
        `repondu`. Et l'asymétrie tombe juste d'elle-même, sans qu'on l'écrive nulle part : sur une
        question d'`interpretation`, un mélange rend `nature_effective = interpretation`, qui est
        précisément la nature attendue — les chiffres qui étayent un jugement restent donc citables,
        ce que la forme précédente de ce commentaire craignait de perdre.
      · `approxime` — admissible seulement si le cran atteint encore le plancher. La règle du cran a
        un détenteur unique (`derive_synthesis_reliability`, #46) : on l'INTERROGE sur le meilleur
        tier disponible (le modèle maximise en ne citant que ses meilleures sources), on ne la
        recopie pas. Sur une question à plancher `A`, le cran rend `A-` : l'approximation y est
        impossible par construction, sur tout corpus et tout émetteur — ce qui est une phrase
        cohérente de la méthode (une question exigeant du tier A ne s'accommode pas d'une
        reconstruction), à condition d'être dite AVANT l'appel et non après.
      · `sans_fondement` — TOUJOURS admissible, et c'est ce qui rend la fonction sûre : on ne retire
        jamais au modèle sa sortie honnête. Fermer les trois laisserait le choix entre mentir et se
        taire (#60).
    """
    ouverts: list[str] = []
    ecartes: list[str] = []

    natures = {str(e.get("nature")) for e in citables.values()}
    if question.nature_attendue in natures:
        ouverts.append("repondu")
    else:
        ecartes.append(
            f"`repondu` écarté : aucune entry citable ne porte la nature `{question.nature_attendue}` "
            f"(le corpus citable porte {sorted(natures) or 'rien'}) — [E] refuserait toute réponse "
            "directe, quelle que soit sa qualité")

    if citables:
        meilleur = min((str(e.get("reliability_tier")) for e in citables.values()),
                       key=lambda t: _TIER_RANK.get(t, len(TIER_ORDER)))
        _, cran, _ = derive_synthesis_reliability([meilleur])
        if _TIER_RANK.get(cran, len(TIER_ORDER)) <= _TIER_RANK.get(
                question.plancher_tier, len(TIER_ORDER)):
            ouverts.append("approxime")
        else:
            ecartes.append(
                f"`approxime` écarté : la meilleure source citable est `{meilleur}`, un cran sous "
                f"vaut `{cran}`, sous le plancher `{question.plancher_tier}` — [D] refuserait toute "
                "reconstruction")

    ouverts.append("sans_fondement")
    return ouverts, ecartes


def aucune_reponse_possible(ouverts: list[str]) -> bool:
    """Aucune réponse ne passerait le pont : il ne reste que la sortie honnête. DÉTENTEUR UNIQUE.

    Deux sites en dépendent — `contexte_analyste` (ne pas montrer la question) et `repondre` (l'écrire
    en `non_fondable` sans appeler). Les écrire deux fois, ce serait deux règles d'accord aujourd'hui
    et divergentes au premier ajustement (#46).

    ⚠️ Cette porte SUBSUME celle du corpus vide : sans entry citable, aucune nature n'est portée et
    le cran ne se calcule pas, donc seul `sans_fondement` reste ouvert. Mesuré — la mutation qui
    désarmait l'ancienne porte `if not citables` de `contexte_analyste` laissait le check VERT, parce
    que celle-ci rattrapait la question. Une garde que rien ne peut faire rougir n'est pas une garde,
    c'est un doublon : elle a été retirée de `contexte_analyste`.
    """
    return ouverts == ["sans_fondement"]


def contexte_analyste(
    fichier: FrameworksFile,
    framework_id: str,
    archetype: str,
    ticker_id: str,
    entries: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """CE QUE LE MODÈLE VOIT — lever-free, et sans aucune métadonnée de valeur sur les sources.

    Ne portent PAS : `plancher_tier`, `nature_attendue` (les leviers de la méthode, #59), ni
    `reliability_tier` / `nature` des entries. Une entry montrée avec son tier inviterait le modèle
    à hiérarchiser ses citations selon la note plutôt que selon ce qu'elles disent — et le rang
    cesserait d'être dérivé pour devenir choisi.

    Seules figurent les questions APPLICABLES dont AU MOINS UN statut reste ouvert : les autres n'ont
    rien à demander au modèle (elles sortiront en `sans_objet` ou en `non_fondable`, écrites par le
    code). Appeler le modèle sur un corpus vide, c'est payer pour qu'il invente — et le cas « corpus
    vide » est un cas particulier de « aucun statut ouvert », d'où une seule porte
    (`aucune_reponse_possible`) et non deux.
    """
    fw = _framework_de(fichier, framework_id)
    questions = []
    for q in questions_applicables(fichier, framework_id, archetype):
        citables = corpus_citable(q, entries)
        ouverts, _ = statuts_admissibles(q, citables)
        if aucune_reponse_possible(ouverts):
            continue  # rien à demander : le code écrit le `non_fondable` (cf. `repondre`)
        questions.append({
            "id": q.id,
            "enonce": q.enonce,
            "variable_archetype": q.variables_par_archetype[archetype].variable,
            "sens_admis": list(q.sens_admis),
            # Vocabulaire FERMÉ de statuts, même forme que `sens_admis` : une propriété de la
            # question sur ce corpus, jamais un curseur. Le modèle ne voit toujours ni
            # `plancher_tier` ni `nature_attendue` (#59) — seulement ce qui lui reste ouvert.
            "statuts_admis": ouverts,
            "ingredients": [
                {"id": i.id, "libelle": i.libelle, "essentiel": i.essentiel}
                for i in q.ingredients_requis
            ],
            "corpus": [
                {
                    "entry_id": i,
                    "titre": e.get("title"),
                    "source": e.get("source_type"),
                    "date": str(e.get("source_date")) if e.get("source_date") else None,
                    "contenu": e.get("content"),
                }
                for i, e in sorted(citables.items())
            ],
        })
    return {
        "ticker": ticker_id,
        "framework": {"id": fw.id, "libelle": fw.libelle, "methodologie": fw.methodologie},
        "archetype": archetype,
        "questions": questions,
    }


def reponse_sans_objet(
    question: QuestionDefinition,
    archetype: str,
    *,
    ticker_id: str,
    framework_id: str,
    framework_version: str,
    analyste: str,
) -> FrameworkAnswer:
    """La réponse `sans_objet`, ÉCRITE PAR LE CODE depuis le référentiel (§4.1.3).

    Le motif est le `motif_gabarit` de la question pour cet archétype, et le substitut (ou son
    absence explicite) descend du même endroit. Rien n'est demandé au modèle : le hors-sujet est un
    fait de la méthode, et un modèle à qui on demanderait de le reconnaître répondrait plutôt que
    de se taire (§0.2, entry #190).

    `substitut_answer_id` reste `None` ici : il désigne une LIGNE persistée, et la réponse
    substitutive n'existe pas encore quand celle-ci se construit. C'est la persistance qui le résout
    (maillon suivant), et le pont [F] qui vérifie qu'il pointe bien une AUTRE question.
    """
    va = question.variables_par_archetype.get(archetype)
    if va is None:
        raise AnalysteInapplicable(
            f"`{question.id}` ne couvre pas l'archétype `{archetype}` : le référentiel garantit le "
            "contraire (invariant [I]), une exception ici signale un fichier chargé hors pont")
    if va.mode != "sans_objet":
        raise AnalysteInapplicable(
            f"`{question.id}` est APPLICABLE pour `{archetype}` : la déclarer sans objet, c'est "
            "faire disparaître une question que la méthode pose")
    return FrameworkAnswer(
        framework_id=framework_id,
        framework_version=framework_version,
        question_id=question.id,
        ticker_id=ticker_id,
        analyste=analyste,
        statut="sans_objet",
        sans_objet=SansObjet(
            motif=va.motif_gabarit,
            substitut_applique=va.substitut_question_id,
            substitut_answer_id=None,
            aucun_substitut=va.aucun_substitut,
        ),
    )


def reponse_non_fondable(
    question: QuestionDefinition,
    *,
    ticker_id: str,
    framework_id: str,
    framework_version: str,
    analyste: str,
    manque: str,
    citables: int,
    fournies: int,
) -> FrameworkAnswer:
    """La réponse `non_fondable` et son `GapItem` — LE MANQUE DE DONNÉES, jamais une panne d'agent.

    Le remède est `collecte` et pas `rafraichissement` (#54) : ici la question n'a pas de source qui
    atteigne son plancher, ce qui se répare en allant chercher une source, pas en rafraîchissant
    celles qu'on a. `rafraichissement` est le remède de l'axe ACTUALITÉ, et l'actualité se calcule
    au point de lecture (#53) — jamais ici, à l'écriture.

    `priorite` est `haute`, sans gradation inventée : une question du framework restée sans réponse
    empêche le dossier de conclure. Un gradient plus fin se dériverait de ce que la question coûte
    à collecter — une information qu'on n'a pas à ce stade, et qu'on ne devine pas.
    """
    return FrameworkAnswer(
        framework_id=framework_id,
        framework_version=framework_version,
        question_id=question.id,
        ticker_id=ticker_id,
        analyste=analyste,
        statut="non_fondable",
        gap=GapItem(
            dimension=question.chemin_indexation,
            champs_cibles=[question.id],
            manque=manque,
            queries_suggerees=[],
            priorite="haute",
            coverage_actuelle=(
                f"{citables} entry citable(s) sur {fournies} fournie(s) pour `{question.id}`"),
            origine="curator",
            remede="collecte",
        ),
    )


def _tier_reel(entry: Optional[dict[str, Any]]) -> str:
    """Le tier d'une entry, ramené au vocabulaire DÉTENU par `common.TIER_ORDER`.

    Un tier absent, inconnu ou d'une entry qu'on n'a pas (citation hors corpus) vaut le PIRE tier
    connu — jamais le meilleur, et jamais une valeur hors vocabulaire : `Fondation.rang_derive` est
    un `Literal`, donc laisser passer `"None"` ferait mourir l'assemblage sur une erreur de forme et
    le vrai motif ([B] : « cette entry, personne ne l'a chargée ») ne serait jamais prononcé.
    """
    tier = str((entry or {}).get("reliability_tier"))
    return tier if tier in TIER_ORDER else TIER_ORDER[-1]


def assembler_answer(
    brute: AnalysteReponse,
    *,
    question: QuestionDefinition,
    entries: dict[int, dict[str, Any]],
    ticker_id: str,
    framework_id: str,
    framework_version: str,
    analyste: str,
) -> FrameworkAnswer:
    """La sortie du modèle + les DEUX axes que le code dérive. Pur.

    `rang_derive` : interroge les détenteurs de la règle plutôt que de la recopier (#46) —
    `_plus_faible` pour une réponse directe, `derive_synthesis_reliability` (la règle du cran) pour
    une approximation. Un tier inconnu compte pour le pire chez les deux.

    `nature_effective` : `mesure` seulement si TOUTES les entries citées sont des mesures. La nature
    forte ne se concède jamais par défaut (#51) : un chiffre mesuré cité à côté d'un commentaire
    devient une `interpretation`, parce que c'est bien une lecture des deux. Sur une approximation,
    elle est forcée à `interpretation` — le contrat le re-vérifie (§1.5).

    Une entry citée hors corpus ne fait PAS échouer cette fonction : son tier compte pour le pire
    (`_tier_reel`) et c'est le pont [B] qui la refuse, NOMMÉMENT — il regarde les citations avant le
    rang. Lever ici rendrait le refus muet sur sa cause : « rang_derive invalide » au lieu de « cette
    entry, personne ne l'a chargée ».
    """
    cites = list(dict.fromkeys(brute.cited_entry_ids))  # dédoublonne, ordre conservé
    tiers = [_tier_reel(entries.get(i)) for i in cites]
    # Les DEUX axes interrogent leur détenteur unique, aucun n'est recopié ici (#46) : le rang via
    # `_plus_faible` / `derive_synthesis_reliability`, la nature via `nature_effective_de`. Cette
    # dernière était une expression EN LIGNE jusqu'au 2026-09-21 ; le pont [E] devant appliquer la
    # même règle, la laisser ici en aurait fait un jumeau (`feedback_correctif_regle_jumeaux`).
    approx = brute.statut == "approxime"
    rang = derive_synthesis_reliability(tiers)[1] if approx else _plus_faible(tiers)
    nature = nature_effective_de(
        [entries.get(i, {}).get("nature") for i in cites], approximation=approx,
    )
    return FrameworkAnswer(
        framework_id=framework_id,
        framework_version=framework_version,
        question_id=question.id,
        ticker_id=ticker_id,
        analyste=analyste,
        statut=brute.statut,
        reponse=Reponse(verbatim=brute.verbatim, valeur=brute.valeur, unite=brute.unite,
                        sens=brute.sens),
        fondation=Fondation(cited_entry_ids=cites, rang_derive=rang, nature_effective=nature),
        approximation=brute.approximation,
    )


# ── Le prompt, et l'appel ────────────────────────────────────────────────────────────────────────

_ANALYSTE_SYSTEM_PROMPT = (
    "Tu es l'ANALYSTE d'une chaîne d'analyse d'investissement. On te confie les questions d'une "
    "méthode d'analyse, UNE entreprise, et un CORPUS de sources déjà collectées. Ta tâche : "
    "répondre à chaque question EN NE T'APPUYANT QUE SUR CE CORPUS.\n\n"
    "TU NE CHERCHES RIEN. Tout ce que tu sais par ailleurs sur cette entreprise est hors-jeu : un "
    "chiffre que tu te rappelles mais qu'aucune source fournie ne porte est une invention, même "
    "s'il est juste. Une autre chaîne collecte ; toi tu lis.\n\n"
    "CHAQUE QUESTION PORTE SON `statuts_admis` — un vocabulaire FERMÉ, comme `sens_admis`. La "
    "méthode n'admet pas les mêmes formes de réponse partout : selon ce que ses sources permettent, "
    "une question peut n'accepter qu'une réponse directe, ou qu'une reconstruction. Tu choisis "
    "OBLIGATOIREMENT un statut de cette liste. Un statut hors liste fait rejeter la réponse entière, "
    "et ce rejet ne déclenche aucune collecte : la question reste sans réponse par ta faute. Si "
    "aucun des statuts ouverts ne convient à ce que tu lis, `sans_fondement` est toujours ouvert — "
    "c'est la bonne réponse, pas un aveu d'échec.\n\n"
    "UNE RÉPONSE PAR QUESTION, avec son `question_id` repris tel quel, et un `statut` :\n"
    "  • `repondu` — le corpus établit la réponse. Remplis `verbatim` (la réponse en une ou deux "
    "phrases, lisible par un humain), `cited_entry_ids` (les `entry_id` du corpus qui la portent — "
    "AU MOINS UN, et uniquement des ids présents dans le corpus fourni), `sens` (obligatoirement "
    "l'une des valeurs de `sens_admis` de la question, recopiée exactement), et si la réponse est "
    "un nombre, `valeur` + `unite` (un nombre sans unité est illisible).\n"
    "  • `approxime` — le corpus ne donne pas la réponse, mais il donne de quoi la RECONSTRUIRE. "
    "Mêmes champs, plus le bloc `approximation` : `methode` (comment tu reconstruis), "
    "`ingredients_entry_ids` (les entries dont tu pars), `hypotheses_explicites` (ce que tu as dû "
    "supposer, une phrase par hypothèse), `sensibilite` (de combien la réponse bougerait si ces "
    "hypothèses étaient fausses, et dans quel sens). Une estimation dont les hypothèses manquent se "
    "lit comme une mesure : c'est la faute la plus grave de ce poste.\n"
    "  • `sans_fondement` — le corpus fourni ne permet ni de répondre ni de reconstruire. Remplis "
    "`verbatim` avec CE QUI MANQUE, précisément (quel ingrédient, pour quelle période), et rien "
    "d'autre : pas de citations, pas de valeur, pas de sens. Ce n'est pas un échec, c'est une "
    "commande de collecte.\n\n"
    "CITER, C'EST DÉSIGNER CE QUI PORTE LE FAIT. Cite les sources qui ÉTABLISSENT ce que tu dis, "
    "pas celles qui en parlent : un état financier qui donne le chiffre vaut citation ; un "
    "commentaire qui le mentionne n'en est pas la source. Si tu ne peux citer qu'un commentaire, "
    "dis-le dans ton `verbatim` — ne fais pas passer le second pour le premier.\n\n"
    "UN CHIFFRE CALCULÉ N'EST PAS UN CHIFFRE RELEVÉ, MÊME QUAND UNE SOURCE LE PORTE. Certaines "
    "sources du corpus publient un chiffre qu'elles ont elles-mêmes calculé, et elles le disent "
    "(« Calcul : … », « estimé par différence », « en déduisant … »). Tu as le droit de t'en "
    "servir. Mais alors ta réponse est un `approxime`, pas un `repondu` : tu écris la méthode, les "
    "ingrédients et les hypothèses, et ta réponse descend d'un cran. Un `repondu` ne s'appuie que "
    "sur ce que quelqu'un a relevé. Ce n'est pas une préférence de style : une réponse qui présente "
    "un calcul comme un relevé lui prête l'autorité du document dont il est tiré, et un lecteur "
    "qui la relit six mois plus tard n'a plus aucun moyen de voir la différence.\n\n"
    "TU NE NOTES AUCUNE SOURCE. Tu ne produis ni tier, ni score, ni niveau de confiance, ni "
    "'combien de preuve suffit' : la solidité de ta réponse se DÉDUIT de ce que tu as cité, elle ne "
    "se déclare pas. Tu n'as pas non plus à juger si l'entreprise est un bon investissement : tu "
    "réponds à la question posée, telle qu'elle est posée.\n\n"
    "N'invente pas de question : tu ne traites QUE les questions du contexte, et tu les traites "
    "TOUTES — une question omise n'est pas une réponse prudente, c'est un trou. Sortie : UNIQUEMENT "
    "l'objet JSON `{\"reponses\": [ ... ]}`, commençant par `{` et finissant par `}`, sans aucun "
    "texte autour."
)


# Le motif d'une OMISSION. Constante parce que c'est la frontière la plus fragile du module : une
# ligne, un seul endroit où la basculer en `reponse_non_fondable` — et c'est justement la mutation
# que le test négatif exige de voir rougir.
_MOTIF_OMISSION = ("question omise par l'analyste alors que son corpus citable lui était montré — "
                   "panne d'agent, pas manque de données : aucun mandat de collecte n'en sort")


def _message_analyste(contexte: dict[str, Any]) -> str:
    """Le message utilisateur : le contexte, rendu tel quel. Déterministe."""
    return (
        "[mode: analyse de framework]\n\n"
        "Entreprise, questions et corpus citable (tu ne peux citer QUE les `entry_id` ci-dessous) :\n"
        f"{json.dumps(contexte, ensure_ascii=False, indent=2)}\n\n"
        "Produis l'objet JSON `{\"reponses\": [ ... ]}` : une réponse par question ci-dessus, avec "
        "son `question_id` et un `statut` PRIS DANS LE `statuts_admis` DE CETTE QUESTION "
        "(`repondu`/`approxime` avec citations et `sens`, ou `sans_fondement` avec ce qui manque). "
        "Aucune question ne doit rester sans réponse."
    )


async def _resolve_analyste_agent() -> ResolvedAgent:
    """Réutilise provider + modèle du `research-agent` (config en DB, source de vérité), avec le
    prompt système de l'ANALYSTE. Même montage que le traducteur : le prompt de ce mode vit dans le
    code tant qu'aucune migration ne l'exige."""
    base = await get_agent_provider("research-agent", "v2")
    return ResolvedAgent(
        agent_name="research-agent",
        flow_version="v2",
        provider=base.provider,
        model=base.model,
        system_prompt=_ANALYSTE_SYSTEM_PROMPT,
    )


async def repondre(
    ticker_id: str,
    framework_id: str,
    archetype: str,
    *,
    analyste: str,
    entries: dict[int, dict[str, Any]],
    fichier: Optional[FrameworksFile] = None,
    agent: Optional[ResolvedAgent] = None,
) -> ResultatAnalyste:
    """Répond à TOUTES les questions d'un (ticker × framework × archétype). Ne persiste rien.

    Ordre : (1) le référentiel écrit les `sans_objet` ; (2) le code écrit les `non_fondable` des
    questions sans corpus citable ; (3) le modèle répond aux questions restantes ; (4) le code
    dérive les axes, valide contrat PUIS pont, question par question ; (5) toute question qui n'est
    sortie ni en réponse ni en refus fait lever.

    `analyste` n'a pas de défaut : §3.4 écrit la chaîne pour N analystes, et deux réponses
    anonymes à une même question sont indiscernables — le correctif naturel, le jour venu, serait de
    les moyenner, ce que §3.4 interdit.

    Un refus de contrat ou de pont est ISOLÉ à sa question : il n'interrompt pas le passage et ne
    devient JAMAIS un `gap` (cf. en-tête — une panne d'agent n'est pas un manque de données).
    """
    fichier = fichier or load_frameworks()
    fw = _framework_de(fichier, framework_id)  # (1) lève tôt sur un framework inconnu (#40)
    resultat = ResultatAnalyste()
    entete = dict(ticker_id=ticker_id, framework_id=framework_id,
                  framework_version=fichier.schema_version, analyste=analyste)

    for q in questions_sans_objet(fichier, framework_id, archetype):
        resultat.answers.append(reponse_sans_objet(q, archetype, **entete))

    interrogeables: dict[str, QuestionDefinition] = {}
    admis: dict[str, list[str]] = {}
    for q in questions_applicables(fichier, framework_id, archetype):
        citables = corpus_citable(q, entries)
        if not citables:
            # (2a) aucune source n'atteint le plancher : c'est le CORPUS qui manque, et on ne paie
            #      pas un appel pour l'apprendre.
            resultat.answers.append(reponse_non_fondable(
                q, **entete,
                manque=(f"aucune source fournie ne fonde « {q.enonce} » — ingrédients essentiels "
                        f"attendus : {[i.id for i in q.ingredients_requis if i.essentiel]}"),
                citables=0, fournies=len(entries)))
            continue
        ouverts, ecartes = statuts_admissibles(q, citables)
        if aucune_reponse_possible(ouverts):
            # (2b) des sources atteignent le plancher, mais AUCUNE réponse ne pourrait passer le
            #      pont : la question est infondable sur ce corpus. On le dit ici, gratuitement,
            #      plutôt que de payer un appel pour le faire refuser après (#40) — et on le dit en
            #      `non_fondable`, parce que c'est un manque de données, pas une faute de l'agent.
            resultat.answers.append(reponse_non_fondable(
                q, **entete,
                manque=(f"aucune réponse recevable n'est possible sur ce corpus pour "
                        f"« {q.enonce} » : " + " ; ".join(ecartes)),
                citables=len(citables), fournies=len(entries)))
            continue
        interrogeables[q.id] = q
        admis[q.id] = ouverts

    if interrogeables:
        contexte = contexte_analyste(fichier, framework_id, archetype, ticker_id, entries)
        agent = agent or await _resolve_analyste_agent()
        messages = [{"role": "user", "content": _message_analyste(contexte)}]
        # json_object=False : DeepSeek-V4-Flash est non fiable en mode json_object (cf. run_json_agent).
        run = await run_json_agent(agent, messages, AnalysteSortie, json_object=False)  # (3)
        resultat.run = run

        profils = question_profiles(fichier)
        vues: set[str] = set()
        for brute in run.parsed.reponses:
            q = interrogeables.get(brute.question_id)
            if q is None:
                resultat.refus.append((brute.question_id, (
                    "réponse à une question qui n'était pas posée (hors framework, sans objet pour "
                    "cet archétype, ou sans corpus citable)")))
                continue
            if brute.question_id in vues:
                resultat.refus.append((brute.question_id,
                                       "deuxième réponse du même analyste à la même question — "
                                       "deux réponses ne se moyennent ni ne se remplacent (§3.4)"))
                continue
            vues.add(brute.question_id)

            if brute.statut not in admis[brute.question_id]:
                # Le vocabulaire de statuts était FERMÉ et montré (même forme que `sens_admis`) :
                # en sortir est une faute d'agent, nommée ici plutôt que laissée au pont, qui
                # dirait « rang sous le plancher » là où la cause est « statut non ouvert ».
                resultat.refus.append((brute.question_id, (
                    f"statut `{brute.statut}` hors des statuts ouverts "
                    f"{admis[brute.question_id]} pour `{brute.question_id}` sur ce corpus")))
                continue

            if brute.statut == "sans_fondement":
                citables = corpus_citable(q, entries)
                resultat.answers.append(reponse_non_fondable(
                    q, **entete, manque=brute.verbatim,
                    citables=len(citables), fournies=len(entries)))
                continue

            try:  # (4) contrat PUIS pont — un refus reste à sa question
                answer = assembler_answer(brute, question=q, entries=entries, **entete)
                valider_pont_framework_answer(answer, questions=profils, entries=entries)
            except Exception as exc:  # noqa: BLE001 — contrat (ValidationError) ou pont (Refused)
                resultat.refus.append((brute.question_id, f"{type(exc).__name__}: {exc}"))
                continue
            resultat.answers.append(answer)

        # Une question interrogée que le modèle n'a pas traitée est une OMISSION D'AGENT : elle sort
        # en refus, jamais en `non_fondable` — le corpus, lui, était là.
        for qid in interrogeables:
            if qid not in vues:
                resultat.refus.append((qid, _MOTIF_OMISSION))

    # (5) aucune question ne s'évapore.
    traitees = {a.question_id for a in resultat.answers} | {qid for qid, _ in resultat.refus}
    perdues = sorted({q.id for q in fw.questions} - traitees)
    if perdues:
        raise AnalysteEvaporation(
            f"{perdues} n'ont produit NI réponse NI refus : une question perdue en route se lit "
            "comme un dossier complet sur ce qui reste")
    return resultat
