"""
Alimentateur de SYNTHÈSE GROUNDED (ingestion-agent, mode synthèse) — V2.

Motif (00-REPRISE, MàJ 2026-08-26) : deux champs qualitatifs bloquent encore la readiness NVDA —
`produits.unit_economics` et `marche.structure_5forces`. Le search-worker a été exercé dessus
(2026-08-26, dry-run) → `not_found` : ce ne sont PAS des faits fetchables (l'économie unitaire n'est
pas disclosée ; l'analyse de Porter n'existe nulle part telle quelle). Le KB a pourtant déjà les
matériaux tier A/B+ (marges/coûts pour unit_economics ; menace ASIC / concentration clients /
AMD-Huawei / TSMC / export controls pour les 5 forces) — mais aucune entry ne les SYNTHÉTISE au niveau
que le curator exige.

Cet alimentateur comble ce trou, même patron que `valuation_feed`/`financials_feed` (transformation
PURE testable + couche IO) mais avec UN tour LLM, GROUNDED :
  1. charger les entries CITABLES (tier A/A-/B+) pertinentes pour le champ visé ;
  2. un tour LLM (DeepInfra, modèle de l'ingestion-agent) compose la synthèse STRICTEMENT à partir de
     ces entries — chaque assertion cite ≥1 `entry_id`, aucun fait hors-KB (GroundedSynthesis) ;
  3. VÉRIFIER en Python que chaque id cité appartient au corpus citable (grounding réel, pas déclaré,
     #24/#28) ; DÉRIVER le tier « un cran sous la plus faible entry citée » (règle validée : une
     synthèse n'est jamais plus solide que son maillon le plus faible, moins un cran de risque de
     composition) ; persister une entry `entry_type='analysis'`, `source_type='agent_synthesis'`,
     `requires_human_review=True` (une synthèse machine se relit avant d'être exploitée par la chaîne).

Ce qu'il NE fait PAS (G3, le cœur du projet) : il n'injecte jamais un fait absent des entries citées
pour forcer `ready`. Si le KB n'a pas assez de matériau citable pour un champ → `SynthesisUnavailable`
(un trou honnête, jamais une entrée fabriquée, #25). Si la synthèse cite hors du corpus →
`SynthesisUngrounded` (rejetée, rien n'est écrit).

La transformation est pure (`derive_synthesis_reliability`, `validate_grounding`,
`build_content_structured`) → vérifiable hors-ligne (`backend/checks/check_synthesis_feed.py`). L'IO
(chargement KB + tour LLM + écriture) vit dans `run_synthesis_feed`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from app.agents.providers import ResolvedAgent, get_agent_provider
from app.agents.v2.common import TIER_ORDER, format_entries_for_prompt
from app.agents.v2.runner import run_json_agent
from app.contracts import GroundedSynthesis
from app.db.database import get_db_session
from app.knowledge.service import query_knowledge, store_knowledge

logger = logging.getLogger(__name__)

_SOURCE_TYPE = "agent_synthesis"

# Tiers qu'une synthèse a le droit de citer (≥ plancher B+ des champs visés). Une synthèse adossée à
# une entry sous B+ serait plus faible que le plancher qu'on cherche à franchir → hors corpus citable.
CITABLE_TIERS = ("A", "A-", "B+")

# Dérivation « un cran sous » : (tier, score) de la synthèse selon la PLUS FAIBLE entry citée.
# A→A- (0.85), A-→B+ (0.75), B+→B (0.70). Cohérent avec RELIABILITY_TABLE (mêmes baselines de tier).
# ⚠️ RÈGLE PROVISOIRE (décision utilisateur 2026-08-26, option conservatrice) : à REVOIR à l'usage si
# elle bloque trop (un champ à plancher B+ citant une seule entry B+ tombe à B < plancher). Pistes de
# relâche si besoin : « un cran sous la MEILLEURE citée dès ≥N tier-A », ou re-tag après revue humaine.
# Plus largement, la catégorisation de qualité des sources (baselines de tier) pourra être réajustée.
_NOTCH_BELOW: dict[str, tuple[str, float]] = {
    "A": ("A-", 0.85),
    "A-": ("B+", 0.75),
    "B+": ("B", 0.70),
}
_FALLBACK_NOTCH = ("B-", 0.60)  # plus faible cité sous B+ (ne devrait pas arriver après filtre citable)

_TIER_RANK = {t: i for i, t in enumerate(TIER_ORDER)}  # 0 = meilleur (A) … plus grand = plus faible


# ── La consigne de LACUNE, détenteur unique ──────────────────────────────────
# ⚠️ Avant le 2026-09-09, cette consigne existait en QUATRE exemplaires, un par champ, chacun dans sa
# formulation (« non documenté à ce jour » · « non documenté » · « non documentée ») — et le premier
# mesureur de la ligne de base n'en a attrapé qu'une forme sur trois, sous-comptant les trous en
# silence. Une règle recopiée re-diverge au correctif suivant (#48) : elle vit ici, une fois, et les
# `guidance` la concatènent.
#
# Le changement de fond : le trou ne se déclare plus DANS LA PROSE. La prose est invisible à la porte
# de couverture et à l'écran — c'est la convention #55, et c'est le défaut que la capacité 5 corrige.
# Il se déclare dans `lacunes[]`, où un lecteur peut le compter, l'afficher et le rouvrir.
_CONSIGNE_LACUNES = (
    "\n\nCE QUE TU N'AS PAS TROUVÉ SE DÉCLARE DANS `lacunes[]`, JAMAIS DANS LA PROSE. N'écris nulle "
    "part dans `synthesis_markdown` qu'une donnée « n'est pas documentée », « n'est pas fournie » ou "
    "« n'est pas dérivable » : chaque question restée ouverte quitte le texte et devient un objet de "
    "`lacunes[]`. Si tu n'as laissé aucune question ouverte, rends `lacunes: []` : c'est une "
    "affirmation, pas un oubli."
    "\n\nET CHERCHE À L'APPROCHER AVANT DE RENONCER. `approximation: null` n'est PAS le cas par "
    "défaut : il est réservé aux questions dont le corpus ne porte AUCUN ingrédient. On travaille "
    "comme dans un fonds — quand la donnée exacte n'existe pas, on la borne et on dit comment. "
    "Passe en revue, pour chaque question ouverte :\n"
    "  • une PART se déduit du rapport entre deux montants du corpus (composante / total) ;\n"
    "  • une MOYENNE se déduit d'un total divisé par un dénombrement, même approximatif — et si le "
    "dénombrement est un « plus de N », la moyenne obtenue est un `plafond` (diviser par un "
    "dénominateur sous-estimé surestime le résultat) ;\n"
    "  • un ORDRE DE GRANDEUR se borne par encadrement entre deux quantités connues ;\n"
    "  • un chiffre ABSENT peut se déduire d'un autre exercice, d'un segment voisin ou d'un agrégat "
    "dont il est une composante.\n"
    "Les ingrédients peuvent venir d'entries DIFFÉRENTES, et c'est le cas le plus fréquent : le "
    "numérateur dans l'une, le dénominateur dans l'autre. Une estimation grossière, assortie de son "
    "sens d'erreur et de ses hypothèses, vaut mieux qu'un `null` — c'est même exactement ce qu'on "
    "attend de toi. Ce qui reste interdit est d'apporter un ingrédient qui n'est dans AUCUNE entry."
    "\n\nEnfin : si tu produis dans la prose un chiffre que tu as toi-même CALCULÉ à partir des "
    "entries (un ratio, une marge dérivée, un taux approché), et que ce calcul repose sur une "
    "hypothèse — par exemple assimiler deux grandeurs voisines — alors ce n'est pas un fait, c'est "
    "une approximation : elle doit figurer dans `lacunes[]` avec sa méthode et son hypothèse."
)


@dataclass(frozen=True)
class SynthesisTarget:
    """Descripteur d'un champ synthétisable : quelles entries charger, et la consigne de composition."""
    field_path: str
    dimension: str
    entry_type: str
    # `query` et `guidance` sont des GABARITS : elles décrivent ce qu'est le champ, jamais un
    # émetteur en particulier. Seul `{company}` les spécialise (cf. `resolve`).
    query: str                       # requête sémantique de chargement des entries citables
    candidate_entry_types: tuple[str, ...]
    min_citations: int               # sous ce seuil de matériau citable → SynthesisUnavailable
    guidance: str                    # ce que la synthèse doit couvrir (injecté au LLM)
    # Tiers admis dans le corpus citable de CE champ. Par défaut A/A-/B+. Un champ dont le matériau
    # honnête est purement tier A (ex. unit_economics = marges/coûts EDGAR/IR) restreint à ("A","A-") :
    # ça exclut par PERTINENCE les entries hors-champ de moindre tier (presse marché) qui, sinon,
    # tireraient la synthèse sous le plancher via la règle « un cran sous la plus faible citée ».
    citable_tiers: tuple[str, ...] = CITABLE_TIERS

    def resolve(self, company: str) -> tuple[str, str]:
        """`(query, guidance)` spécialisées pour CET émetteur, consigne de lacune INCLUSE. Pur.

        La concaténation se fait ici et pas dans les descripteurs : c'est le seul passage obligé des
        quatre champs, donc le seul endroit où la consigne ne peut pas se recopier (#46/#48)."""
        return (
            self.query.format(company=company),
            self.guidance.format(company=company) + _CONSIGNE_LACUNES,
        )


# Cibles connues. Le descripteur porte la définition du CHAMP, jamais la connaissance d'un émetteur.
#
# ⚠️ Constaté sur le 2ᵉ ticker (MSFT, 2026-08-30) : ces cibles se disaient « génériques par
# construction » alors que seul le MÉCANISME l'était. Les `query`/`guidance` étaient rédigées pour
# NVIDIA (« segments Data Center Gaming », « coût par GPU », « écosystème CUDA », « TSMC/HBM »).
# Sur un autre émetteur, la requête sémantique cherchait le mauvais vocabulaire et la consigne
# demandait au modèle de synthétiser une entreprise qui n'est pas celle analysée — une invitation
# directe à sortir du corpus, dans le seul agent dont toute la valeur est de n'en pas sortir.
# Règle : ce qui décrit le champ vit ici ; ce qui décrit l'émetteur vient des entries citées.
SYNTHESIS_TARGETS: dict[str, SynthesisTarget] = {
    "business_model.description": SynthesisTarget(
        field_path="business_model.description",
        dimension="business_model",
        entry_type="analysis",
        query=(
            "modèle économique {company} activité principale segments opérationnels publiables "
            "produits et services vendus chiffre d'affaires par segment clients cibles "
            "canaux de monétisation structure du groupe"
        ),
        candidate_entry_types=("fact_qualitative", "fact_financial", "analysis", "quote"),
        min_citations=2,
        citable_tiers=("A", "A-"),
        guidance=(
            "Synthétise la DESCRIPTION du modèle économique de {company}, telle qu'elle ressort des "
            "entries : (1) activité principale — ce que l'entreprise vend réellement, (2) segments "
            "opérationnels publiables et poids relatif de chacun, (3) clients cibles et canaux de "
            "distribution, (4) mode de monétisation (vente unitaire, licence, abonnement, usage, "
            "publicité) et profil de revenus chiffré. N'introduis AUCUN segment, produit ou client "
            "qui ne figure pas dans les entries citées : la structure de l'entreprise se lit dans le "
            "corpus, elle ne se suppose pas. Chaque affirmation cite les entries qui la fondent."
        ),
    ),
    "produits.unit_economics": SynthesisTarget(
        field_path="produits.unit_economics",
        dimension="produits",
        entry_type="analysis",
        query=(
            "économie unitaire {company} marge brute marge opérationnelle structure de coûts "
            "coût unitaire prix de vente moyen pouvoir de fixation des prix rentabilité par "
            "produit ou par client"
        ),
        candidate_entry_types=("fact_qualitative", "fact_financial", "analysis", "quote"),
        min_citations=2,
        citable_tiers=("A", "A-"),  # socle marges/coûts tier A ; exclut la presse marché B+ (hors-champ)
        guidance=(
            "Synthétise l'ÉCONOMIE UNITAIRE (unit economics) de l'offre de {company} : structure de "
            "marge (marge brute / opérationnelle présentes dans les entries), levier de prix (prix de "
            "vente moyen, pouvoir de fixation des prix), coûts unitaires SEULEMENT s'ils sont "
            "dérivables des entries citées. L'unité pertinente dépend du métier (unité vendue, "
            "siège, utilisateur, contrat, unité de consommation) : retiens celle que les entries "
            "documentent, n'en invente pas. N'invente aucun chiffre absent des entries."
        ),
    ),
    "positionnement.moat_preuves": SynthesisTarget(
        field_path="positionnement.moat_preuves",
        dimension="positionnement",
        entry_type="analysis",
        query=(
            "avantage concurrentiel durable moat {company} coûts de transition base installée "
            "effets de réseau économies d'échelle actifs incorporels marque brevets "
            "rétention des clients barrières à l'entrée durabilité"
        ),
        candidate_entry_types=("fact_qualitative", "analysis", "quote", "risk", "fact_financial"),
        min_citations=2,
        citable_tiers=("A", "A-"),  # preuves du moat = socle A (dépôts, échelle, risques EDGAR A) ; la
                                    # presse marché B+ porte des MENACES, pas des preuves
        guidance=(
            "Synthétise les PREUVES du moat (avantage concurrentiel durable) de {company} : d'abord "
            "la NATURE du moat telle qu'elle ressort des entries — parmi coûts de transition, effets "
            "de réseau, économies d'échelle, actifs incorporels (marque, brevets, licences), avantage "
            "de coût — puis, pour chacune retenue, les preuves CHIFFRÉES ou factuelles tirées des "
            "entries, et enfin sa durabilité face aux menaces documentées. Ne postule aucun type de "
            "moat que les entries n'étayent pas : une nature de moat est une conclusion, pas une "
            "hypothèse de départ. Chaque preuve est adossée aux entries citées."
        ),
    ),
    "marche.structure_5forces": SynthesisTarget(
        field_path="marche.structure_5forces",
        dimension="marche",
        entry_type="analysis",
        query=(
            "cinq forces de Porter {company} rivalité concurrentielle concurrents directs "
            "menace de nouveaux entrants barrières à l'entrée pouvoir de négociation des clients "
            "concentration de la clientèle pouvoir de négociation des fournisseurs dépendance "
            "produits de substitution réglementation"
        ),
        candidate_entry_types=("risk", "fact_qualitative", "analysis", "quote"),
        min_citations=3,
        citable_tiers=("A", "A-"),  # les 5 forces s'adossent aux facteurs de risque EDGAR tier A ; la
                                    # presse B+ porte la même chose en moins fiable → exclue
        guidance=(
            "Structure une analyse des 5 forces de Porter pour {company}, une par une : (1) intensité "
            "de la rivalité concurrentielle, (2) menace de nouveaux entrants, (3) pouvoir de "
            "négociation des clients, (4) pouvoir de négociation des fournisseurs, (5) menace de "
            "produits de substitution. Pour chaque force, nomme les acteurs et les mécanismes que les "
            "entries documentent RÉELLEMENT — n'importe aucun concurrent, fournisseur ou substitut "
            "qui n'y figure pas. Chaque force est adossée aux entries citées et qualifiée (faible / "
            "modérée / élevée) avec la preuve."
        ),
    ),
}


_SYNTHESIS_SYSTEM_PROMPT = (
    "Tu es l'ingestion-agent en MODE SYNTHÈSE. On te confie UN champ d'analyse et un corpus d'entries "
    "de connaissance déjà vérifiées et scorées (tier A/A-/B+). Ta tâche : composer une synthèse "
    "dense et structurée de ce champ, STRICTEMENT à partir de ce corpus.\n\n"
    "RÈGLE ABSOLUE (anti-hallucination) : tu n'apportes AUCUN fait qui ne soit dans les entries "
    "fournies. Chaque assertion de `claims[]` doit citer, dans `cited_entry_ids`, le ou les `entry_id` "
    "(#N dans le listing) qui la fondent. Une assertion sans source dans le corpus est INTERDITE : "
    "si l'information manque, elle part en `lacunes[]` (voir ci-dessous) plutôt que d'être "
    "reconstruite de mémoire. Tu ne cites QUE des id présents dans le listing.\n\n"
    "ÉCHELLE D'ESCALADE — que faire d'une information que le corpus ne donne pas. On travaille comme "
    "dans un fonds : on cherche à modéliser, et si on n'a pas l'info on DÉGRADE en signalant les "
    "hypothèses, on n'abandonne pas et on n'invente pas. Dans l'ordre :\n"
    "  1. Tu nommes la question en toutes lettres dans `lacunes[].question`.\n"
    "  2. Tu dis POURQUOI elle reste ouverte, dans `lacunes[].statut` — et les deux causes ne se "
    "confondent pas : `non_publie_source` = l'émetteur ne publie pas ce chiffre (c'est une "
    "information SUR l'émetteur, aucune recherche supplémentaire ne le trouvera) ; "
    "`non_documente_base` = le corpus fourni ne le porte pas (une collecte pourrait le trouver).\n"
    "  3. Tu regardes si les entries fournies permettent de l'APPROCHER par un calcul. Si oui, tu "
    "remplis `lacunes[].approximation` : `valeur` (le chiffre approché avec son unité), `methode` "
    "(le calcul en toutes lettres, refaisable par un lecteur — les nombres utilisés y figurent), "
    "`sens_erreur` (`plancher` si le vrai chiffre est AU-DESSUS de ton estimation, `plafond` s'il "
    "est en dessous, `indetermine` si tu ne peux pas trancher le sens), `hypotheses` (ce que tu as "
    "dû supposer — au moins une : une estimation sans hypothèse est un chiffre déguisé), et "
    "`cited_entry_ids` (les #id d'où viennent les ingrédients du calcul).\n"
    "  4. Si aucune méthode n'est tenable à partir des entries fournies, laisse `approximation` à "
    "`null`. C'est une réponse valide et attendue. N'invente JAMAIS une méthode pour éviter le "
    "`null` : approcher un chiffre n'est pas une autorisation d'apporter un fait hors corpus, et "
    "les ingrédients d'un calcul obéissent à la même règle absolue que les assertions.\n\n"
    "Tu NE fournis PAS de score, de tier ni de source_type : ils sont dérivés par le backend depuis "
    "les entries que tu cites — y compris le rang d'une approximation, que tu ne t'attribues pas. Tu "
    "ne juges pas la valeur d'investissement : tu synthétises.\n\n"
    "`synthesis_markdown` = la synthèse lisible (Markdown, structurée selon la consigne). `claims[]` = "
    "la décomposition en assertions atomiques sourcées (elles doivent couvrir le contenu de la "
    "synthèse). `lacunes[]` = les questions restées ouvertes, VIDE si tu n'en as aucune. Sortie : "
    "UNIQUEMENT l'objet JSON du contrat GroundedSynthesis, rien d'autre."
)


class SynthesisUnavailable(Exception):
    """Le champ n'est pas synthétisable : cible inconnue, ou pas assez de matériau citable en base.
    Distinct d'un résultat vide — l'appelant DOIT le remonter (#25), jamais fabriquer une entrée."""


class SynthesisUngrounded(Exception):
    """La synthèse produite cite hors du corpus citable (ou une assertion non sourcée) : elle est
    rejetée, rien n'est écrit. Le grounding est VÉRIFIÉ, pas déclaré (#24/#28)."""


# ── Transformations PURES (testables hors-ligne) ─────────────────────────────
def derive_synthesis_reliability(cited_tiers: list[str]) -> tuple[float, str, str]:
    """(score, tier, note) d'une synthèse = un cran SOUS la plus faible entry citée (règle validée).

    Pur. `cited_tiers` = tiers RÉELS (lus en base) des entries citées, pas déclarés par le modèle.
    """
    if not cited_tiers:
        raise ValueError("derive_synthesis_reliability: aucune entry citée")
    # plus faible = rang le plus grand dans TIER_ORDER (A=0 … C=6)
    weakest = max(cited_tiers, key=lambda t: _TIER_RANK.get(t, len(TIER_ORDER)))
    tier, score = _NOTCH_BELOW.get(weakest, _FALLBACK_NOTCH)
    uniq = sorted(set(cited_tiers), key=lambda t: _TIER_RANK.get(t, len(TIER_ORDER)))
    note = (
        f"synthèse grounded de {len(cited_tiers)} citation(s) [tiers {', '.join(uniq)}] ; "
        f"plus faible cité = {weakest} → un cran sous = {tier} ({score:.2f}) ; "
        f"agent_synthesis ; revue humaine requise avant exploitation par la chaîne d'analyse"
    )
    return score, tier, note


def validate_grounding(
    claims: list[dict[str, Any]],
    citable_ids: set[int],
    approximations: Optional[list[dict[str, Any]]] = None,
) -> list[str]:
    """Renvoie la liste des VIOLATIONS de grounding (vide = ok). Pur.

    Un claim doit citer ≥1 id (déjà garanti par le contrat) ET chaque id cité doit appartenir au
    corpus citable réellement chargé. Un id hors corpus = le modèle a apporté une source non vérifiée.

    ⚠️ `approximations` passe par LA MÊME fonction, délibérément (#46). Une estimation est le point
    du système où la tentation d'apporter un ingrédient de mémoire est la plus forte : c'est
    exactement là qu'il ne faut pas d'une seconde implémentation de la règle, qui divergerait au
    correctif suivant. Chaque élément porte `question` (pour que le message d'erreur nomme la lacune
    fautive, pas un index) et `cited_entry_ids`.
    """
    errors: list[str] = []
    for idx, claim in enumerate(claims):
        cited = claim.get("cited_entry_ids") or []
        if not cited:
            errors.append(f"claim #{idx} sans citation (assertion non sourcée)")
            continue
        for cid in cited:
            if cid not in citable_ids:
                errors.append(
                    f"claim #{idx} cite #{cid} hors du corpus citable {sorted(citable_ids)}"
                )
    for approx in approximations or []:
        question = str(approx.get("question") or "?")[:80]
        cited = approx.get("cited_entry_ids") or []
        if not cited:
            errors.append(f"approximation « {question} » sans ingrédient cité (chiffre non sourcé)")
            continue
        for cid in cited:
            if cid not in citable_ids:
                errors.append(
                    f"approximation « {question} » utilise #{cid} hors du corpus citable "
                    f"{sorted(citable_ids)}"
                )
    return errors


def qualify_lacunes(
    lacunes: list[Any],
    tiers_by_id: dict[int, str],
) -> list[dict[str, Any]]:
    """Sérialise les lacunes déclarées en DÉRIVANT le rang de chaque approximation. Pur.

    Le rang n'est pas déclaré par le modèle : il vaut « un cran sous la pièce citée la plus faible »,
    second emploi de la règle des synthèses grounded. Le motif est le même dans les deux cas — une
    composition n'est jamais plus solide que son maillon le plus faible, moins un cran pour le risque
    de composition. Une estimation adossée à deux pièces tier A vaut donc A-, pas A : elle n'hérite
    PAS de l'autorité d'un dépôt réglementaire (#51), même quand tous ses ingrédients en viennent.

    `lacunes` = objets `LacuneDeclaree` (le contrat garantit déjà `hypotheses` et `cited_entry_ids`
    non vides côté approximation ; ici on ne fait que dériver et mettre à plat).
    """
    out: list[dict[str, Any]] = []
    for lac in lacunes:
        item: dict[str, Any] = {
            "question": lac.question,
            "statut": lac.statut,
            # Le barreau atteint sur l'échelle, écrit DANS la ligne : un lecteur voit d'un coup d'œil
            # si la question a été approchée ou si elle reste ouverte, sans relire la prose (#55).
            "barreau": "approximee" if lac.approximation is not None else "declaree",
            "approximation": None,
        }
        if lac.approximation is not None:
            ap = lac.approximation
            cited = sorted(set(ap.cited_entry_ids))
            tiers = [tiers_by_id[c] for c in cited if c in tiers_by_id]
            score, tier, note = derive_synthesis_reliability(tiers)
            item["approximation"] = {
                "valeur": ap.valeur,
                "methode": ap.methode,
                "sens_erreur": ap.sens_erreur,
                "hypotheses": list(ap.hypotheses),
                "cited_entry_ids": cited,
                "cited_tiers": {str(c): tiers_by_id.get(c) for c in cited},
                "derived_tier": tier,
                "derived_score": score,
                "derived_note": note,
                # `nature` au sens de la migration 034 : une estimation est une INTERPRÉTATION, jamais
                # une mesure — quels que soient ses ingrédients. C'est le discriminant que la porte de
                # couverture et l'écran doivent pouvoir lire sans ouvrir la méthode.
                "nature": "interpretation",
            }
        out.append(item)
    return out


def build_content_structured(
    target: SynthesisTarget,
    synth: GroundedSynthesis,
    cited_ids: list[int],
    tiers_by_id: dict[int, str],
) -> dict[str, Any]:
    """content_structured d'une entry de synthèse (traçabilité du grounding). Pur."""
    lacunes = qualify_lacunes(synth.lacunes, tiers_by_id)
    return {
        "field_path": target.field_path,
        "dimension": target.dimension,
        "synthesis_kind": "grounded_synthesis",
        "cited_entry_ids": cited_ids,
        "claims": [{"text": c.text, "cited_entry_ids": sorted(c.cited_entry_ids)} for c in synth.claims],
        "derived_from_tiers": {str(cid): tiers_by_id.get(cid) for cid in cited_ids},
        # ⚠️ Les questions restées ouvertes, en clair et comptables. Elles ne sont PAS un sous-produit
        # de la prose : le champ existe pour qu'un lecteur (porte de couverture, écran, mesureur)
        # puisse les compter sans lire le markdown. `lacunes_n` est redondant avec `len(lacunes)` et
        # c'est voulu — un compte à zéro affirmé se distingue d'une clef absente (contrat antérieur).
        "lacunes": lacunes,
        "lacunes_n": len(lacunes),
        "lacunes_approximees_n": sum(1 for x in lacunes if x["barreau"] == "approximee"),
        "review_status": "pending",
    }


_LIBELLE_STATUT = {
    "non_publie_source": "non publié par l'émetteur",
    "non_documente_base": "absent du corpus",
}
_LIBELLE_SENS = {
    "plancher": "le chiffre réel est AU-DESSUS",
    "plafond": "le chiffre réel est EN DESSOUS",
    "indetermine": "sens de l'erreur indéterminé",
}


def render_lacunes_markdown(lacunes: list[dict[str, Any]]) -> str:
    """Rend les questions ouvertes en Markdown lisible, à joindre au texte de l'entry. Pur.

    ⚠️ Ce bloc est une COURTOISIE pour l'œil humain qui lit l'entry ; le discriminant reste
    `content_structured['lacunes']`. Aucun lecteur machine ne doit re-parser ce Markdown pour savoir
    s'il y a un trou — ce serait re-fabriquer exactement le défaut qu'on ferme (#55). Il est ici pour
    qu'une entry consultée à la main ne mente pas par omission par rapport à sa propre structure.
    """
    if not lacunes:
        # Formulation AFFIRMATIVE, pas un silence : « aucune » et « pas posé la question » ne se
        # lisent pas pareil, et c'est toute la raison pour laquelle `lacunes` est requis au contrat.
        return "\n**Questions restées ouvertes** : aucune.\n"
    lignes = ["\n**Questions restées ouvertes**\n"]
    for lac in lacunes:
        statut = _LIBELLE_STATUT.get(lac["statut"], lac["statut"])
        ap = lac.get("approximation")
        if ap is None:
            lignes.append(f"- ❓ {lac['question']} — *{statut}* ; aucune méthode d'approche tenable.")
            continue
        base = ", ".join("#" + str(i) for i in ap["cited_entry_ids"])
        sens = _LIBELLE_SENS.get(ap["sens_erreur"], ap["sens_erreur"])
        hypo = " ; ".join(ap["hypotheses"])
        lignes.append(
            f"- 📐 {lac['question']} — *{statut}* → **estimation {ap['valeur']}** "
            f"({ap['sens_erreur']} : {sens}), rang {ap['derived_tier']}.\n"
            f"  - Méthode : {ap['methode']}\n"
            f"  - Base : {base}\n"
            f"  - Hypothèses : {hypo}"
        )
    return "\n".join(lignes) + "\n"


def _tags(target: SynthesisTarget) -> list[str]:
    return ["synthesis", target.dimension, target.field_path]


# ── Couche IO ────────────────────────────────────────────────────────────────
async def _current_synthesis_entry_id(conn, ticker_id: str, target: SynthesisTarget) -> Optional[int]:
    """Id de la synthèse COURANTE pour ce champ (à superseder). Ce feed est le seul producteur du
    triplet de tags → pas de collision avec une entry de recherche."""
    row = await conn.fetchrow(
        """
        SELECT id FROM knowledge_entries
        WHERE ticker_id = $1 AND superseded_by IS NULL AND is_deleted = FALSE
          AND tags @> $2
        ORDER BY id DESC LIMIT 1
        """,
        ticker_id, _tags(target),
    )
    return row["id"] if row else None


# Squelette JSON explicite injecté au tour : sous response_format=json_object, DeepSeek se rabat sur
# `{}` (JSON valide mais vide) quand la forme attendue n'est pas montrée noir sur blanc. Le curator
# évite ce piège parce que son prompt DB détaille le schéma — on fait pareil ici (vérifié : sans ce
# squelette, le modèle renvoyait `{}` deux fois de suite, 2026-08-26).
_SYNTHESIS_SKELETON = (
    '{\n'
    '  "title": "<titre court du champ synthétisé>",\n'
    '  "synthesis_markdown": "<synthèse Markdown structurée selon la consigne>",\n'
    '  "claims": [\n'
    '    {"text": "<assertion atomique>", "cited_entry_ids": [<#id du corpus>, ...]},\n'
    '    {"text": "<autre assertion>", "cited_entry_ids": [<#id>]}\n'
    '  ],\n'
    # Les DEUX formes de lacune sont montrées : avec et sans approximation. Un squelette qui ne
    # montrerait que la forme approchée pousserait le modèle à fabriquer une méthode pour remplir
    # le gabarit — l'exemple est une consigne implicite, et ici il doit enseigner que `null` est
    # une réponse normale.
    '  "lacunes": [\n'
    '    {"question": "<information cherchée et non trouvée, en toutes lettres>",\n'
    '     "statut": "non_publie_source | non_documente_base",\n'
    '     "approximation": {"valeur": "<chiffre approché avec son unité>",\n'
    '                       "methode": "<le calcul en toutes lettres, refaisable>",\n'
    '                       "sens_erreur": "plancher | plafond | indetermine",\n'
    '                       "hypotheses": ["<ce qu\'il a fallu supposer>"],\n'
    '                       "cited_entry_ids": [<#id des ingrédients>]}},\n'
    '    {"question": "<autre question ouverte, qu\'aucun calcul ne permet d\'approcher>",\n'
    '     "statut": "non_documente_base",\n'
    '     "approximation": null}\n'
    '  ],\n'
    '  "lang": "fr"\n'
    '}'
)


def _synthesis_task_message(target: SynthesisTarget, listing: str, guidance: str) -> str:
    return (
        f"[mode: synthese]\n\n"
        f"Champ à synthétiser : `{target.field_path}` (dimension {target.dimension}).\n\n"
        f"Consigne de composition :\n{guidance}\n\n"
        f"Corpus citable — entries de connaissance COURANTES, tier A/A-/B+ (cite-les par leur #id, "
        f"et UNIQUEMENT celles-ci) :\n{listing}\n\n"
        f"Produis l'objet GroundedSynthesis, en respectant EXACTEMENT cette forme (commence par `{{` "
        f"et termine par `}}`, aucun texte autour) :\n{_SYNTHESIS_SKELETON}\n\n"
        f"`claims[]` doit être NON VIDE et chaque assertion porte au moins un `cited_entry_ids` pris "
        f"dans le corpus ci-dessus. Aucun fait hors de ce corpus — et cela vaut aussi pour les "
        f"ingrédients d'une approximation. `lacunes[]` est OBLIGATOIRE : liste les questions que ce "
        f"corpus ne referme pas, ou rends `[]` si tu n'en as aucune."
    )


async def _resolve_synthesis_agent() -> ResolvedAgent:
    """Réutilise le provider + modèle de l'ingestion-agent (config en DB, #DB source de vérité), mais
    avec le prompt système de SYNTHÈSE (le prompt DB de l'ingestion-agent est celui de l'extraction de
    document, qui interdit explicitement la synthèse). Le prompt de ce mode vit dans le code, comme la
    logique des autres feeds (valuation/financials/base_rate)."""
    base = await get_agent_provider("ingestion-agent", "v2")
    return ResolvedAgent(
        agent_name="ingestion-agent",
        flow_version="v2",
        provider=base.provider,
        model=base.model,
        system_prompt=_SYNTHESIS_SYSTEM_PROMPT,
    )


async def run_synthesis_feed(
    ticker_id: str,
    field_path: str,
    *,
    persist: bool = True,
    max_candidates: int = 20,
    debug_raw: bool = False,
) -> dict[str, Any]:
    """Fonde un champ qualitatif par SYNTHÈSE grounded des entries tier A/A-/B+ déjà en base.

    `persist=False` = dry-run (base append-only : on regarde ce qui entrerait avant d'écrire). Lève
    `SynthesisUnavailable` si le champ est inconnu ou le matériau citable insuffisant ;
    `SynthesisUngrounded` si la synthèse produite sort du corpus (rien n'est écrit).
    """
    target = SYNTHESIS_TARGETS.get(field_path)
    if target is None:
        raise SynthesisUnavailable(
            f"champ non synthétisable : {field_path} (connus : {sorted(SYNTHESIS_TARGETS)})"
        )

    # 1) charger le corpus citable (tier A/A-/B+ pertinent pour le champ) --------------------------
    async with get_db_session() as conn:
        # L'émetteur ne vient jamais du descripteur de champ : il est résolu ici, pour CE run.
        row = await conn.fetchrow("SELECT name FROM tickers WHERE id = $1", ticker_id)
        company = ((row["name"] if row else None) or ticker_id).strip()
        query, guidance = target.resolve(company)
        found = await query_knowledge(
            conn, ticker_id=ticker_id, query=query,
            entry_types=list(target.candidate_entry_types),
            min_reliability=0.70, include_sector=True, limit=max_candidates,
        )
    citable = [e for e in found if e.get("reliability_tier") in target.citable_tiers]
    if len(citable) < target.min_citations:
        raise SynthesisUnavailable(
            f"{ticker_id}/{field_path} : {len(citable)} entrie(s) citable(s) tier A/A-/B+ en base "
            f"(< {target.min_citations} requis) — le champ n'est pas synthétisable sans plus de "
            f"matériau ; lancer d'abord le search-worker / l'ingestion sur cette dimension (#25)"
        )

    tiers_by_id = {e["id"]: e["reliability_tier"] for e in citable}
    citable_ids = set(tiers_by_id)

    # 2) tour LLM grounded --------------------------------------------------------------------------
    agent = await _resolve_synthesis_agent()
    listing = format_entries_for_prompt(citable, content_limit=700)
    task = _synthesis_task_message(target, listing, guidance)

    if debug_raw:
        # Observabilité de la frontière LLM : renvoie la sortie brute sans validation (diagnostic).
        res = await agent.complete([{"role": "user", "content": task}], temperature=0.2)
        return {
            "ticker_id": ticker_id, "field_path": field_path, "debug_raw": True,
            "citable_count": len(citable), "citable_ids": sorted(citable_ids), "model": agent.model,
            "finish_reason": res.finish_reason, "tokens_out": res.tokens_out,
            "raw_content": res.content[:3000],
        }

    # json_object=False : DeepSeek-V4-Flash est non fiable en mode json_object (cf. run_json_agent).
    run = await run_json_agent(
        agent, [{"role": "user", "content": task}],
        GroundedSynthesis, temperature=0.2, json_object=False,
    )
    synth: GroundedSynthesis = run.parsed  # type: ignore[assignment]

    # 3) vérifier le grounding (RÉEL, pas déclaré) --------------------------------------------------
    # ⚠️ Les approximations passent par le même appel, et AVANT `build_content_structured` : la
    # dérivation du rang lit `tiers_by_id[cid]` et n'a de sens que sur des ingrédients dont on a
    # vérifié qu'ils sont dans le corpus. Inverser les deux ferait dériver un rang depuis une pièce
    # non vérifiée — un chiffre noté A- sur un ingrédient venu de nulle part.
    errors = validate_grounding(
        [{"text": c.text, "cited_entry_ids": c.cited_entry_ids} for c in synth.claims],
        citable_ids,
        approximations=[
            {"question": lac.question, "cited_entry_ids": lac.approximation.cited_entry_ids}
            for lac in synth.lacunes if lac.approximation is not None
        ],
    )
    if errors:
        raise SynthesisUngrounded(
            f"{ticker_id}/{field_path} : synthèse non fondée ({len(errors)} violation(s)) — "
            + " ; ".join(errors[:5])
        )

    cited_ids = synth.cited_entry_ids()
    cited_tiers = [tiers_by_id[cid] for cid in cited_ids]
    score, tier, note = derive_synthesis_reliability(cited_tiers)
    content_structured = build_content_structured(target, synth, cited_ids, tiers_by_id)

    content = (
        f"{synth.synthesis_markdown}\n"
        f"{render_lacunes_markdown(content_structured['lacunes'])}\n"
        f"_Synthèse grounded (`{target.field_path}`) composée à partir des entries "
        f"{', '.join('#' + str(i) for i in cited_ids)}. Tier dérivé {tier} (un cran sous la plus "
        f"faible entry citée). Revue humaine requise._"
    )

    persisted: Optional[dict[str, Any]] = None
    if persist:
        async with get_db_session() as conn:
            async with conn.transaction():
                prev = await _current_synthesis_entry_id(conn, ticker_id, target)
                # ⚠️ GARDE : une estimation ne retire JAMAIS un fait du corpus (spec capacité 5). Le
                # seul `supersedes` légitime ici est la synthèse PRÉCÉDENTE du même champ. Si `prev`
                # était une pièce citée — comme ingrédient d'une assertion ou d'une approximation —
                # on périmerait la source qu'on vient d'utiliser pour l'approcher. Le socle ne
                # s'actualise qu'à la prochaine publication officielle, pas par un calcul.
                ingredients = set(cited_ids) | set(synth.approximation_entry_ids())
                if prev is not None and prev in ingredients:
                    raise SynthesisUngrounded(
                        f"{ticker_id}/{field_path} : refus d'écrire — la synthèse superséderait "
                        f"#{prev}, qui est une pièce CITÉE de son propre grounding. Une estimation "
                        f"ne retire pas du corpus la source dont elle se sert."
                    )
                stored = await store_knowledge(
                    conn, ticker_id=ticker_id, entry_type=target.entry_type, content=content,
                    source_type=_SOURCE_TYPE, title=synth.title,
                    content_structured=content_structured, tags=_tags(target), lang=synth.lang,
                    supersedes_entry_id=prev, requires_human_review=True,
                    derived_reliability=(score, tier, note),
                    covers=[target.field_path],   # index 029 : chemin complet, plus le nom nu
                )
                persisted = dict(stored) | {"supersedes": prev}
        logger.info(
            "synthesis_feed %s/%s → entry #%s tier %s (%.2f) ; %d citation(s) %s ; supersede %s",
            ticker_id, field_path, persisted["id"], tier, score, len(cited_ids), cited_ids,
            persisted["supersedes"],
        )

    return {
        "ticker_id": ticker_id,
        "field_path": field_path,
        "dimension": target.dimension,
        "entry_type": target.entry_type,
        "source_type": _SOURCE_TYPE,
        "derived_tier": tier,
        "derived_score": score,
        "reliability_note": note,
        "citable_count": len(citable),
        "cited_entry_ids": cited_ids,
        "cited_tiers": cited_tiers,
        "n_claims": len(synth.claims),
        # Remontés à l'appelant (route, dry-run, mesureur) : sans ça, un dry-run n'affiche pas ce que
        # le lot vient d'ajouter, et la frontière gratuite ne peut pas se lire EN TEXTE.
        "lacunes": content_structured["lacunes"],
        "n_lacunes": content_structured["lacunes_n"],
        "n_lacunes_approximees": content_structured["lacunes_approximees_n"],
        "title": synth.title,
        "content": content,
        "content_structured": content_structured,
        "requires_human_review": True,
        "cost_usd": run.cost_usd,
        "tokens_in": run.tokens_in,
        "tokens_out": run.tokens_out,
        "persisted": persisted,
        "dry_run": not persist,
    }
