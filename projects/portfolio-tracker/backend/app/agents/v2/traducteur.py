"""L'AGENT 1 de la chaîne de collecte — le TRADUCTEUR (spec v3 §3.6, lot 2c).

Il reçoit les questions **applicables** d'un framework (celles qui ont un objet pour l'archétype du
ticker) et le ticker, et produit un **plan de collecte** : une ligne par ingrédient requis, dans le
vocabulaire de CETTE entreprise-là. Il ne collecte rien — il planifie. Le collecteur (agent 2)
exécutera ensuite chaque ligne sans jamais connaître la question.

LA FRONTIÈRE DÉTERMINISTE, ÉPROUVÉE AVANT TOUTE DÉPENSE MODÈLE
--------------------------------------------------------------
Tout ce qui n'exige pas le modèle est ici en fonctions PURES, testées hors-ligne
(`feedback_frontiere_gratuite_avant_depense_modele`) :

  · `questions_applicables` — le filtrage par archétype (une question `sans_objet` n'a pas d'objet,
    on ne la planifie pas — c'est ce que le pont refuse en `[Q]`) ;
  · `contexte_traducteur` — CE QUE LE MODÈLE VOIT. Il ne porte **ni `plancher_tier` ni
    `nature_attendue`** : le traducteur dit *où chercher*, jamais *combien de preuve suffit* (#59,
    §3.6). Ces leviers viennent du framework et de lui seul ; les montrer au modèle rouvrirait le
    levier `RESSERRER` que le lot 2c retire de `curator.py`.

CE QUE LE MODÈLE NE PEUT PAS DÉCIDER — ET C'EST LE CODE QUI TIENT L'EN-TÊTE
---------------------------------------------------------------------------
Le modèle ne produit que les **lignes** (`TraducteurSortie.items`). L'en-tête du plan — ticker,
framework, **version**, archétype — est un **fait de la requête**, pas un jugement de modèle : il est
posé par `traduire()` en Python. Un modèle qui daterait lui-même son plan pourrait le rattacher à une
autre version du référentiel (#57, #53 : ce qui se persiste ≠ ce que le modèle émet). Même forme que
`FrameworkAnswer` (le rang est dérivé, pas déclaré) et que `ThesisValidation` (#36 : le contrat
n'accepte du client que ce qui n'est pas déjà en base).

La sortie est ensuite validée deux fois : le **contrat** `CollectionPlan` (une ligne présente est
complète), puis le **pont** `valider_pont_collection_plan` (T1bis : aucun essentiel omis). Un plan
refusé lève, il ne se rend pas en valeur.

Le prompt vit dans le CODE (comme `_SYNTHESIS_SYSTEM_PROMPT`, #54) tant qu'aucune migration ne
l'exige ; sa resynchro en `agent_prompts` viendra avec le câblage runtime (#19/#39).
"""
from __future__ import annotations

import json
from typing import Any, Optional

from pydantic import Field

from app.agents.providers import ResolvedAgent, get_agent_provider
from app.agents.v2.frameworks import load_frameworks, valider_pont_collection_plan
from app.agents.v2.runner import run_json_agent
from app.contracts.analysis_v2_schemas import Strict
from app.contracts.collection_plan_schema import CollectionPlan, CollectionPlanItem
from app.contracts.framework_definition_schema import (
    FrameworkDefinition,
    FrameworksFile,
    QuestionDefinition,
)
from app.knowledge.edgar_feed import POSTES

__all__ = [
    "TraducteurSortie",
    "TraducteurInapplicable",
    "questions_applicables",
    "contexte_traducteur",
    "traduire",
]


class TraducteurInapplicable(Exception):
    """La demande de traduction n'a pas d'objet AVANT tout appel modèle : framework ou archétype
    inconnu du référentiel. Refusé ici, pas dans le pont (#40) — on ne paie pas un appel pour
    apprendre ce qu'une lecture du référentiel dit gratuitement."""


class TraducteurSortie(Strict):
    """Ce que le MODÈLE produit — rien que les lignes. L'en-tête (ticker, framework, version,
    archétype) est posé par le code, jamais par le modèle (cf. en-tête du module)."""
    items: list[CollectionPlanItem] = Field(min_length=1)


def questions_applicables(
    fichier: FrameworksFile, framework_id: str, archetype: str
) -> list[QuestionDefinition]:
    """Les questions qui ont un OBJET pour cet archétype (`mode == 'variable'`).

    Une question `sans_objet` n'est pas planifiée : la collecter fabriquerait une réponse là où le
    framework dit qu'il n'y a pas de question (§0.2). Lève si framework/archétype inconnu — un
    archétype absent rendrait la liste vide en silence, donc « tout est couvert » sur rien (#32/#54).
    """
    fw = _framework(fichier, framework_id)
    if archetype not in set(fichier.archetypes):
        raise TraducteurInapplicable(
            f"archétype `{archetype}` hors des archétypes déclarés {sorted(fichier.archetypes)}")
    return [q for q in fw.questions
            if q.variables_par_archetype[archetype].mode == "variable"]


def contexte_traducteur(
    fichier: FrameworksFile, framework_id: str, archetype: str, ticker_id: str,
    *, questions: Optional[frozenset[str]] = None,
) -> dict[str, Any]:
    """CE QUE LE MODÈLE VOIT — lever-free par construction.

    Ne porte QUE : le ticker, l'identité + la méthodologie du framework, l'archétype, et pour chaque
    question applicable son énoncé, sa variable d'archétype, et ses ingrédients (`id`, `libelle`,
    `essentiel`). **Aucun `plancher_tier`, aucun `nature_attendue`** : ce ne sont pas des leviers du
    traducteur (#59). `essentiel` reste montré — c'est une propriété du framework (quels ingrédients
    la question ne peut pas se passer), pas un curseur de « combien de preuve suffit ».

    `questions` (optionnel) RESTREINT le contexte à un sous-ensemble d'ids — le cas du BOUCLAGE (lot
    5) : rejouer UN renvoi ne re-planifie pas tout le framework. Un id hors des questions applicables
    lève (un scope qui nomme une question `sans_objet` ou inconnue rendrait le contexte vide en
    silence — « tout est couvert » sur rien, #32).
    """
    fw = _framework(fichier, framework_id)
    applicables = questions_applicables(fichier, framework_id, archetype)
    if questions is not None:
        ids_applicables = {q.id for q in applicables}
        hors = questions - ids_applicables
        if hors:
            raise TraducteurInapplicable(
                f"scope de bouclage {sorted(hors)} hors des questions applicables "
                f"{sorted(ids_applicables)} pour l'archétype `{archetype}` : une question sans objet "
                "ou inconnue ne se re-planifie pas (#32)")
        if not questions:
            raise TraducteurInapplicable(
                "scope de bouclage VIDE : un passage sans question à rejouer ne doit pas appeler le "
                "traducteur (l'orchestrateur s'arrête avant, #40)")
        applicables = [q for q in applicables if q.id in questions]
    return {
        "ticker": ticker_id,
        "framework": {"id": fw.id, "libelle": fw.libelle, "methodologie": fw.methodologie},
        "archetype": archetype,
        "questions": [
            {
                "id": q.id,
                "enonce": q.enonce,
                "variable_archetype": q.variables_par_archetype[archetype].variable,
                "ingredients": [
                    {"id": i.id, "libelle": i.libelle, "essentiel": i.essentiel}
                    for i in q.ingredients_requis
                ],
            }
            for q in applicables
        ],
    }


def _framework(fichier: FrameworksFile, framework_id: str) -> FrameworkDefinition:
    for f in fichier.frameworks:
        if f.id == framework_id:
            return f
    raise TraducteurInapplicable(
        f"framework `{framework_id}` inconnu du référentiel "
        f"({sorted(f.id for f in fichier.frameworks)})")


def _catalogue_postes() -> str:
    """Le vocabulaire FERMÉ des postes du socle EDGAR, rendu depuis `edgar_feed.POSTES`.

    Rendu, jamais recopié : le catalogue a UN détenteur (#46). Une liste retapée dans la chaîne du
    prompt serait d'accord avec lui aujourd'hui et divergente au premier poste ajouté — et la
    divergence serait SILENCIEUSE, puisqu'un poste nommé hors catalogue route simplement au web.
    """
    return "\n".join(f"    · {p.metric} — {p.label}" for p in POSTES)


_TRADUCTEUR_SYSTEM_PROMPT = (
    "Tu es le TRADUCTEUR d'une chaîne d'analyse d'investissement. On te confie les questions "
    "UNIVERSELLES d'une méthode d'analyse (posées en substance économique, sans nommer d'entreprise) "
    "et UNE entreprise précise. Ta tâche : produire un PLAN DE COLLECTE — pour chaque ingrédient de "
    "chaque question, dire COMMENT cette entreprise-là le nomme et OÙ le chercher. Tu ne collectes "
    "RIEN : tu planifies. Un autre agent exécutera chaque ligne sans connaître la question.\n\n"
    "UNE LIGNE PAR INGRÉDIENT. Pour chaque ingrédient fourni, produis exactement une ligne, avec son "
    "`question_id` et son `ingredient_id` (repris tels quels du contexte — n'en invente aucun), et un "
    "`statut` :\n"
    "  • `traduit` — tu sais où chercher. Remplis alors `metrique` (le nom que CETTE entreprise "
    "donne à l'ingrédient — 'free cash flow' pour un industriel rentable, 'consommation de "
    "trésorerie trimestrielle hors paiement d'étape' pour une biotech pré-revenus), "
    "`source_pressentie` (où chercher d'abord — '10-Q', 'communiqué + call trimestriel'), et `ancre` "
    "(l'événement par rapport auquel le fait sera daté — voir la RÈGLE D'ANCRAGE ci-dessous). Pas de "
    "`motif`.\n"
    "  • `inobtenable` — aucune source connue ne produit cet ingrédient pour cette entreprise. "
    "Remplis alors `motif` (POURQUOI, en une phrase — il deviendra un mandat de recherche), et "
    "laisse `metrique`/`source_pressentie`/`ancre`/`poste` vides.\n\n"
    "NOMMER LE POSTE COMPTABLE, QUAND IL Y EN A UN. Les émetteurs américains déposent auprès de la "
    "SEC des états financiers balisés : chaque ligne du compte de résultat, du bilan et du tableau de "
    "flux y porte une étiquette normalisée, et se lit alors sans interprétation ni recherche. Voici "
    "les postes que nous savons relever ainsi :\n"
    f"{_catalogue_postes()}\n"
    "\n"
    "  CE N'EST PAS UN MENU À REMPLIR. C'est une liste de nombres que nous savons aller chercher tout "
    "seuls, et le défaut est de NE PAS en mettre. Avant d'écrire un `poste`, fais-lui passer ce test, "
    "et ne l'écris que s'il le passe :\n"
    "\n"
    "    « Si je relève CE nombre dans le dépôt et que je le recopie tel quel, sans rien y ajouter "
    "ni en retrancher, est-ce que j'ai répondu à l'ingrédient COMPLÈTEMENT et EXACTEMENT ? »\n"
    "\n"
    "  Si pour répondre il faut encore ADDITIONNER un autre poste, SOUSTRAIRE, DIVISER, prendre une "
    "PART du nombre, choisir une AUTRE PÉRIODE que celle déposée, ou LIRE DU TEXTE à côté du nombre — "
    "alors le test échoue et `poste` reste VIDE. La ligne part simplement se faire chercher "
    "autrement, ce qui est le cas NORMAL et ne coûte rien.\n"
    "  Sur un plan bien fait, la plupart des lignes n'ont pas de `poste`. Une seule question "
    "financière sur trois environ demande un nombre brut ; les autres demandent un calcul, une "
    "comparaison, une politique ou une explication, et aucune ne se lit sur une étiquette.\n"
    "\n"
    "  Exemples qui ÉCHOUENT le test, tous vus sur des plans réels — le poste avait l'air voisin, et "
    "le nombre aurait répondu à une AUTRE question :\n"
    "    · « clauses restrictives (covenants) des contrats de dette » — c'est du TEXTE, pas un "
    "montant. Aucun poste. (Ni `total_liabilities`, ni aucun autre : la dette totale ne dit rien des "
    "seuils à respecter.)\n"
    "    · « politique de capitalisation des coûts de développement » — une RÈGLE comptable, pas un "
    "montant. Le capex ne l'énonce pas.\n"
    "    · « lignes de crédit disponibles NON UTILISÉES » — un montant qui n'est justement PAS au "
    "bilan, puisqu'il n'a pas été tiré. Aucun poste de passif ne le porte.\n"
    "    · « échéancier de la dette, montants exigibles PAR ANNÉE » — un tableau. "
    "`long_term_debt_current` n'en est qu'une ligne : incomplet, donc non.\n"
    "    · « charges sans décaissement : amortissements, rémunération en actions, provisions » — une "
    "SOMME. `depreciation_amortization` n'en est qu'un terme.\n"
    "    · « taux d'imposition effectif » — une DIVISION. `income_tax_expense` en est le numérateur.\n"
    "    · « résultat d'exploitation APRÈS IMPÔT » — `operating_income` est avant impôt. Le nombre "
    "existe, il ne répond pas à la question posée.\n"
    "    · « flux d'exploitation sur les QUATRE DERNIERS TRIMESTRES » — une autre période que "
    "l'exercice déposé.\n"
    "    · « éléments présentés comme non récurrents » — une SÉLECTION à faire dans le compte de "
    "résultat, pas une ligne du compte de résultat.\n"
    "\n"
    "  Exemples qui PASSENT le test : « résultat net », « flux net de trésorerie provenant des "
    "activités d'exploitation », « trésorerie et équivalents plus titres de placement à court "
    "terme », « part de la dette à long terme exigible sous douze mois ». Dans chaque cas on relève "
    "le nombre et c'est fini.\n"
    "\n"
    "  — `poste` est FACULTATIF et la liste ne restreint RIEN : un ingrédient qui n'y figure pas se "
    "planifie exactement comme avant, avec `poste` vide. Ne change jamais ce que tu demandes pour le "
    "faire entrer dans cette liste, et ne déclare jamais `inobtenable` un ingrédient au prétexte qu'il "
    "n'y est pas. La liste dit où un ingrédient DÉJÀ décidé peut se lire directement — rien d'autre.\n"
    "  — `metrique` ne change pas : c'est toujours le nom que CETTE entreprise donne à l'ingrédient. "
    "`poste` est une information EN PLUS, pas un remplacement.\n"
    "  — DANS LE DOUTE, laisse `poste` vide. Un poste vide fait simplement chercher l'information "
    "autrement ; un poste FAUX fait remonter un nombre exact qui répond à une AUTRE question, et "
    "personne ne s'en apercevra.\n\n"
    "RÈGLE D'ANCRAGE — l'ancre n'est PAS par défaut la clôture comptable. Pose-toi la question : quel "
    "ÉVÉNEMENT du monde réel rendrait ce chiffre PÉRIMÉ pour CETTE entreprise-là ? Pour une société "
    "stable et régulière, c'est souvent la clôture du trimestre, et c'est très bien. Mais quand la "
    "situation de l'entreprise est gouvernée par un événement récurrent propre à son activité, ancre "
    "sur CET événement : une lecture d'essai clinique ou une décision d'autorité de santé pour une "
    "biotech ou une pharma ; un renouvellement de contrat majeur pour un prestataire concentré ; un "
    "reset de prix pour un producteur de matière première ; une échéance de refinancement pour une "
    "société très endettée. Une bonne ancre est celle par rapport à laquelle « ce chiffre est-il "
    "encore d'actualité ? » a la réponse la plus informative. Ne mets pas « clôture du trimestre » "
    "par réflexe si un événement plus parlant existe.\n\n"
    "RÈGLE ABSOLUE — un ingrédient marqué `essentiel: true` DOIT avoir une ligne, `traduit` ou "
    "`inobtenable`, JAMAIS aucune. Un essentiel omis fait rejeter tout le plan : c'est le mode de "
    "panne qu'on combat (un dossier qui paraît complet en ayant tu ce qu'il ne trouvait pas). Un "
    "ingrédient non essentiel se planifie aussi, mais son omission ne bloque pas.\n\n"
    "TU NE JUGES PAS LA VALEUR D'UNE SOURCE. Tu ne produis ni tier, ni score, ni niveau de fiabilité, "
    "ni 'combien de preuve suffit' : ce n'est pas ton rôle, c'est celui de la méthode. Un même "
    "document (un 10-K) ne 'vaut' pas moins pour une entreprise que pour une autre — s'il est plus "
    "ou moins à jour, cela se voit à l'ANCRE que tu nommes, pas à une note que tu donnerais.\n\n"
    "N'invente pas de question : tu ne traites QUE les questions du contexte (les autres n'ont pas "
    "d'objet pour cette entreprise, la méthode l'a déjà tranché). Sortie : UNIQUEMENT l'objet JSON "
    "`{\"items\": [ ... ]}`, commençant par `{` et finissant par `}`, sans aucun texte autour."
)


def _message_traducteur(contexte: dict[str, Any]) -> str:
    """Le message utilisateur : le contexte lever-free, rendu tel quel. Déterministe."""
    return (
        "[mode: traduction]\n\n"
        "Entreprise et questions applicables (chaque ingrédient attend une ligne dans ton plan) :\n"
        f"{json.dumps(contexte, ensure_ascii=False, indent=2)}\n\n"
        "Produis l'objet JSON `{\"items\": [ ... ]}` : une ligne par ingrédient ci-dessus, avec son "
        "`question_id`, son `ingredient_id`, et son `statut` (`traduit` avec metrique/source/ancre, "
        "et `poste` s'il correspond exactement à un poste du catalogue ; ou `inobtenable` avec "
        "motif). Tout `essentiel: true` DOIT avoir sa ligne."
    )


async def _resolve_traducteur_agent() -> ResolvedAgent:
    """Réutilise provider + modèle de l'ingestion-agent (config en DB, source de vérité), avec le
    prompt système du TRADUCTEUR. Même montage que la synthèse (#54) : le prompt de ce mode vit dans
    le code tant qu'aucune migration ne l'exige."""
    base = await get_agent_provider("ingestion-agent", "v2")
    return ResolvedAgent(
        agent_name="ingestion-agent",
        flow_version="v2",
        provider=base.provider,
        model=base.model,
        system_prompt=_TRADUCTEUR_SYSTEM_PROMPT,
    )


async def traduire(
    ticker_id: str,
    framework_id: str,
    archetype: str,
    *,
    fichier: Optional[FrameworksFile] = None,
    agent: Optional[ResolvedAgent] = None,
    questions: Optional[frozenset[str]] = None,
):
    """Produit et VALIDE le plan de collecte d'un (ticker × framework × archétype).

    Ordre : (1) refuser l'inapplicable AVANT toute dépense (#40) ; (2) assembler le contexte
    lever-free ; (3) le modèle produit les LIGNES ; (4) le CODE pose l'en-tête et construit le
    `CollectionPlan` ; (5) contrat puis pont. Rend l'`AgentRunResult` (télémétrie) et le plan validé.

    `questions` RESTREINT le plan à un sous-ensemble (BOUCLAGE, lot 5) : le contexte ET le pont sont
    scopés au MÊME ensemble, sinon `[R]` refuserait un plan légitimement partiel (il exige tout
    ingrédient essentiel des questions applicables).
    """
    fichier = fichier or load_frameworks()
    contexte = contexte_traducteur(
        fichier, framework_id, archetype, ticker_id, questions=questions)  # (1)+(2), lève tôt
    agent = agent or await _resolve_traducteur_agent()

    messages = [{"role": "user", "content": _message_traducteur(contexte)}]
    # json_object=False : DeepSeek-V4-Flash est non fiable en mode json_object (cf. run_json_agent).
    run = await run_json_agent(agent, messages, TraducteurSortie, json_object=False)  # (3)

    # (4) l'en-tête est un fait de la requête, pas un jugement de modèle : le code le pose.
    plan = CollectionPlan(
        ticker_id=ticker_id,
        framework_id=framework_id,
        framework_version=fichier.schema_version,
        archetype=archetype,
        items=run.parsed.items,
    )
    valider_pont_collection_plan(plan, fichier=fichier, questions=questions)  # (5) lève si incohérent
    return run, plan
