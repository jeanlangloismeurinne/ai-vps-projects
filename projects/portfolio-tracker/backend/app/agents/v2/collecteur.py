"""L'AGENT 2 de la chaîne de collecte — le COLLECTEUR, et son AIGUILLEUR (spec v3 §3.6, lot 2c).

Le traducteur (agent 1) a produit un plan : une ligne par ingrédient. Ici on l'exécute. Deux rôles,
et c'est leur SÉPARATION qui rend le principe 2 vrai par construction :

  · le COLLECTEUR reçoit UNE ligne « aveugle » — une métrique, une source, une ancre, un ticker — et
    **ne connaît pas la question**. L'entry qu'il écrit ne PEUT donc pas porter de vocabulaire de
    framework : il n'en a jamais vu. Le principe « l'entry ne nomme aucun framework » n'est plus une
    discipline d'écriture, c'est une conséquence du flux ;
  · l'AIGUILLEUR tient le plan, donc il SAIT à quelle (question, ingrédient) chaque ligne répond. Quand
    le collecteur rend une entry, l'aiguilleur écrit le lien de couverture. **La couverture devient un
    sous-produit déterministe du dispatch, pas une prétention de modèle** — un modèle ne peut plus
    déclarer couvrir ce qu'il ne couvre pas (#57, la couverture est une propriété de la RELATION).

TROIS ÉTATS, JAMAIS DEUX (#44/#54) — et aucune ligne ne disparaît en silence :
  · `traduit` + collecte réussie → un LienCouverture (→ `question_coverage`) ;
  · `inobtenable` → un MandatCollecte (→ `framework_mandates`), JAMAIS exécuté (le traducteur a déjà
    dit qu'aucune source ne le produit) ;
  · `traduit` + collecte échouée → un MandatCollecte AUSSI, motivé par l'échec. Une source pressentie
    qui ne rend rien n'est pas un trou : c'est un mandat. La confondre avec un succès vide serait le
    mode de panne #25 (un échec de recherche n'est jamais un résultat vide).

LA FRONTIÈRE DÉTERMINISTE, ÉPROUVÉE SANS RÉSEAU. `aiguiller_plan` est une orchestration PURE :
l'exécution réelle d'une ligne (EDGAR / web / futur connecteur) est un **exécuteur injecté**
(`collecter: LigneAveugle -> ResultatCollecte`), câblé plus tard sur `edgar_feed` / le `search-worker`.
On éprouve ici la logique d'aiguillage — question-aveuglement, couverture déterministe, trois états —
avec un exécuteur factice, avant tout appel réseau (`feedback_frontiere_gratuite_avant_depense_modele`).

⚠️ La PERSISTANCE (`question_coverage` existe déjà ; `framework_mandates` viendra en migration 039)
est hors de ce module : `aiguiller_plan` RETOURNE les liens et mandats, il ne les écrit pas. Un
sous-produit déterministe se recalcule ; le figer trop tôt rejouerait le défaut du corpus qui ne
vieillit pas (#53).
"""
from __future__ import annotations

from typing import Callable, Optional

from pydantic import Field, model_validator

from app.contracts.analysis_v2_schemas import Strict
from app.contracts.collection_plan_schema import CollectionPlan, CollectionPlanItem

__all__ = [
    "LigneAveugle",
    "ResultatCollecte",
    "LienCouverture",
    "MandatCollecte",
    "ResultatAiguillage",
    "ligne_aveugle",
    "aiguiller_plan",
]


class LigneAveugle(Strict):
    """Ce que le COLLECTEUR voit — et RIEN d'autre. Pas de `question_id`, pas d'`ingredient_id`, pas
    de framework : l'exécuteur ne peut pas savoir à quelle question il répond, donc l'entry qu'il
    écrit ne peut pas porter de vocabulaire de framework. C'est le principe 2 rendu structurel."""
    ticker_id: str = Field(min_length=1)
    metrique: str = Field(min_length=3)
    source_pressentie: str = Field(min_length=3)
    ancre: str = Field(min_length=5)


class ResultatCollecte(Strict):
    """Ce que l'exécuteur rend pour une ligne : SOIT une entry produite (`entry_id`), SOIT un échec
    motivé (`echec`) — jamais les deux, jamais aucun. Un échec de collecte est une information, pas
    un vide (#25) : il devra devenir un mandat, pas disparaître."""
    entry_id: Optional[int] = None
    echec: Optional[str] = Field(default=None, min_length=3)

    @model_validator(mode="after")
    def _exactement_un(self):
        if (self.entry_id is None) == (self.echec is None):
            raise ValueError(
                "ResultatCollecte porte SOIT `entry_id` SOIT `echec`, jamais les deux ni aucun : "
                "une collecte a réussi (une entry) ou échoué (un motif), pas un état intermédiaire")
        return self


class LienCouverture(Strict):
    """Un lien couverture — les EXACTES colonnes de `question_coverage` (§6, migration 036). Écrit
    par l'aiguilleur, jamais par le modèle : la couverture est un sous-produit du dispatch."""
    framework_id: str = Field(min_length=1)
    framework_version: str = Field(min_length=1)
    question_id: str = Field(min_length=1)
    ingredient_id: str = Field(min_length=1)
    entry_id: int


class MandatCollecte(Strict):
    """Un mandat de recherche ouvert — un ingrédient qu'on n'a PAS pu ranger, mais NOMMÉ (jamais un
    trou). Deux origines distinctes, parce qu'elles appellent des suites différentes (#54)."""
    framework_id: str = Field(min_length=1)
    framework_version: str = Field(min_length=1)
    question_id: str = Field(min_length=1)
    ingredient_id: str = Field(min_length=1)
    motif: str = Field(min_length=3)
    origine: str  # "inobtenable" (le traducteur savait) | "echec_collecte" (la source a déçu)

    @model_validator(mode="after")
    def _origine_connue(self):
        if self.origine not in ("inobtenable", "echec_collecte"):
            raise ValueError(
                f"origine `{self.origine}` inconnue : un mandat vient SOIT du plan (`inobtenable`), "
                "SOIT d'une collecte qui a échoué (`echec_collecte`) — pas d'une troisième cause muette")
        return self


class ResultatAiguillage(Strict):
    """Le bilan d'un plan aiguillé : ce qui a été couvert, ce qui part en mandat. Invariant central
    (vérifié) : chaque ligne du plan produit EXACTEMENT un lien OU un mandat — aucune ne s'évapore."""
    liens: list[LienCouverture] = Field(default_factory=list)
    mandats: list[MandatCollecte] = Field(default_factory=list)
    lignes_vues: int = 0


def ligne_aveugle(item: CollectionPlanItem, ticker_id: str) -> LigneAveugle:
    """Construit l'entrée AVEUGLE du collecteur depuis une ligne `traduit`. C'est ICI que la question
    est retirée : `question_id`/`ingredient_id` ne sont pas recopiés. Défensif — appeler sur une
    ligne `inobtenable` (sans métrique) est un bug d'aiguillage, pas un cas d'usage."""
    if item.statut != "traduit":
        raise ValueError(
            f"ligne_aveugle sur une ligne `{item.statut}` : seule une ligne traduite a une métrique, "
            "une source et une ancre à collecter")
    return LigneAveugle(
        ticker_id=ticker_id,
        metrique=item.metrique,          # type: ignore[arg-type]  — non-None garanti par le contrat
        source_pressentie=item.source_pressentie,  # type: ignore[arg-type]
        ancre=item.ancre,                # type: ignore[arg-type]
    )


def aiguiller_plan(
    plan: CollectionPlan,
    *,
    collecter: Callable[[LigneAveugle], ResultatCollecte],
) -> ResultatAiguillage:
    """Exécute un plan, ligne par ligne, via l'exécuteur `collecter` (question-AVEUGLE, injecté).

    Le collecteur ne reçoit qu'une `LigneAveugle` ; c'est l'aiguilleur qui, connaissant le plan,
    rattache l'entry produite à sa (question, ingrédient) dans un `LienCouverture`. Rien n'est écrit
    en base : on rend les liens et les mandats (cf. en-tête).
    """
    res = ResultatAiguillage(lignes_vues=len(plan.items))
    for item in plan.items:
        cle = dict(framework_id=plan.framework_id, framework_version=plan.framework_version,
                   question_id=item.question_id, ingredient_id=item.ingredient_id)
        if item.statut == "inobtenable":
            # Le traducteur a déjà tranché : aucune source. On n'exécute pas, on ouvre le mandat.
            res.mandats.append(MandatCollecte(**cle, motif=item.motif, origine="inobtenable"))  # type: ignore[arg-type]
            continue

        rc = collecter(ligne_aveugle(item, plan.ticker_id))
        if rc.entry_id is not None:
            res.liens.append(LienCouverture(**cle, entry_id=rc.entry_id))
        else:
            # Une source pressentie qui ne rend rien devient un mandat MOTIVÉ, jamais un silence (#25).
            res.mandats.append(MandatCollecte(**cle, motif=rc.echec, origine="echec_collecte"))  # type: ignore[arg-type]
    return res
