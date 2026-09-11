"""Schéma Pydantic versionné du PLAN DE COLLECTE (spec v3 §3.6) — lot 2c du chantier v3.

Un plan par (ticker × framework × version). C'est la sortie de l'**agent 1, le traducteur** : il
reçoit les questions applicables (archétype, §4.1.3) et le ticker, et rend UNE LIGNE PAR INGRÉDIENT
requis, dans le vocabulaire du framework. Le plan est ensuite lu par l'**agent 2, le collecteur**,
qui n'en voit qu'une ligne à la fois et NE CONNAÎT PAS la question.

POURQUOI LE PLAN EST UN OBJET CONTRÔLÉ, PAS UNE SUGGESTION
----------------------------------------------------------
« Une question sans réponse doit rester diagnosticable : mauvais plan, ou mauvaise collecte ? »
(§3.6). Cette phrase n'a de sens que si le plan est un objet persisté et relisable — d'où ce
contrat. Un agent unique qui traduirait ET collecterait fusionnerait les deux défauts en un verdict
opaque, exactement la panne de `curator.py` aujourd'hui (un champ absent ne s'y distingue pas d'un
champ que le modèle a décidé de ne plus exiger).

CE QUE CE FICHIER VÉRIFIE, ET CE QU'IL NE PEUT PAS VÉRIFIER (#37)
-----------------------------------------------------------------
Un contrat valide un **objet**, jamais la cohérence entre deux. Tout ce qui demande de connaître le
RÉFÉRENTIEL (les questions, leurs ingrédients, l'archétype applicable) vit dans
`app/agents/v2/frameworks.py` (`valider_pont_collection_plan`) et lève `CollectionPlanRefused` :

  ici (Pydantic, un objet)                   | là-bas (pont, contre le référentiel)
  -------------------------------------------|-------------------------------------------------
  le statut porte EXACTEMENT sa charge        | chaque (question, ingrédient) EXISTE au référentiel
  (traduit ⟺ métrique+source+ancre ;          | l'archétype est l'un des archétypes DÉCLARÉS
   inobtenable ⟺ motif seul)                  | CHAQUE ingrédient ESSENTIEL d'une question
  aucun ingrédient référencé deux fois        |   applicable a une ligne — une OMISSION = plan REFUSÉ
                                              | une ligne `inobtenable` devient un mandat ouvert

LE TROISIÈME ÉTAT N'EST PAS UNE VALEUR DE `statut`, ET C'EST VOULU (#44/#54)
----------------------------------------------------------------------------
Le §3.6 nomme trois états : `traduit`, `inobtenable`, et `omis`. Seuls les deux premiers sont des
lignes — `omis` est l'ABSENCE de ligne pour un ingrédient. Il ne peut donc pas être une valeur de
`statut` : une valeur `omis` serait une ligne, donc l'ingrédient ne serait pas omis. L'omission d'un
ingrédient essentiel est le mode de panne que toute la v3 combat (il produit un VERT : couverture à
100 % sur ce qui reste) ; elle se constate en confrontant le plan au référentiel — c'est-à-dire dans
le pont, pas ici. Ce que ce contrat garantit, c'est qu'une ligne PRÉSENTE est complète.

CE QUE LE TRADUCTEUR NE PEUT PAS PORTER, ET POURQUOI C'EST UNE ABSENCE DE CHAMP (#59, §3.6)
-------------------------------------------------------------------------------------------
Le traducteur dit **où chercher**, jamais **combien de preuve suffit**. `plancher_tier`,
`nature_attendue` et `essentiel` viennent du framework et de lui seul (écart V2 de l'audit, qui vise
le levier `RESSERRER` de `curator.py`). Ils sont donc **absents de ce contrat** : `Strict`
(`extra='forbid'`) rejette à la construction un plan qui tenterait de les porter. C'est la même
forme que l'actualité absente de `FrameworkAnswer` (#53) — une doctrine rendue impossible à violer
par construction, pas gardée par un `if`.

De même, un plan ne DÉGRADE jamais un tier de source selon l'émetteur : l'inégalité d'un 10-K entre
RVMD et MSFT est de l'ACTUALITÉ, pas de la fiabilité (#59). Le traducteur NOMME l'ancre (`ancre`),
et l'actualité reste calculée à la lecture. Il n'y a donc aucun champ de tier ni de score ici.

Cible : pydantic v2 (container backend). Tester en container, **pas** le python hôte (v1).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field, model_validator

from .analysis_v2_schemas import Strict

__all__ = [
    "COLLECTION_PLAN_SCHEMA_VERSION",
    "STATUTS_LIGNE",
    "CollectionPlanItem",
    "CollectionPlan",
]

# Même version que les deux autres contrats du chantier v3 (définition et réponse) : les trois
# naissent de la même spec et se lisent ensemble. Les désynchroniser créerait deux horloges.
COLLECTION_PLAN_SCHEMA_VERSION = "v3.0.0"

# Les deux statuts d'une LIGNE. `omis` n'y figure pas : c'est l'absence de ligne (cf. en-tête).
STATUTS_LIGNE = ("traduit", "inobtenable")


class CollectionPlanItem(Strict):
    """Une ligne de plan : ce qu'on cherche pour UN ingrédient, et où — ou pourquoi c'est hors de
    portée. Le collecteur en recevra une à la fois, sans jamais voir la question.

    `question_id` + `ingredient_id` désignent le couple du référentiel (§6, `question_coverage` a
    exactement ces deux colonnes). On ne les fond PAS en une seule chaîne : un même `ingredient_id`
    nu (`resultat_net`) peut exister sous deux questions, et c'est le couple qui lève l'ambiguïté.
    """
    question_id: str = Field(min_length=1, pattern=r"^[a-z]{2}_[0-9]+$")
    ingredient_id: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    statut: Literal["traduit", "inobtenable"]

    # Présents SI ET SEULEMENT SI `traduit`. Optionnels ici pour que `inobtenable` puisse les
    # omettre ; le validateur ci-dessous impose leur présence exacte selon le statut. La longueur
    # minimale n'est pas décorative : une `metrique` vide passerait un `min_length=1` et laisserait
    # le collecteur sans rien à chercher.
    metrique: Optional[str] = Field(
        default=None, min_length=3,
        description="Comment CETTE entreprise-là nomme l'ingrédient — 'free cash flow' pour MSFT, "
                    "'cash burn trimestriel hors milestone' pour une biotech pré-revenus.")
    source_pressentie: Optional[str] = Field(
        default=None, min_length=3,
        description="Où chercher D'ABORD — '10-Q', 'communiqués + call trimestriel'.")
    ancre: Optional[str] = Field(
        default=None, min_length=5,
        description="L'ÉVÉNEMENT par rapport auquel le fait sera daté (#59) — 'clôture du "
                    "trimestre', 'dernière lecture clinique'. Nommer l'ancre, jamais dégrader un tier.")

    # Présent SI ET SEULEMENT SI `inobtenable`. Une ligne inobtenable devient un mandat ouvert qui
    # NOMME l'ingrédient (§3.6) — jamais un trou. Le motif est ce que le mandat portera ; il doit
    # EXPLIQUER, comme un `motif_plancher` (même longueur minimale) : « aucune source connue ne le
    # produit » sans dire pourquoi est un trou déguisé.
    motif: Optional[str] = Field(default=None, min_length=20)

    @model_validator(mode="after")
    def _le_statut_porte_exactement_sa_charge(self):
        # Même forme que `VariableArchetype._le_mode_porte_exactement_sa_charge` : le statut n'est
        # pas un simple libellé, il DÉCIDE des champs présents. Un `traduit` sans source, ou un
        # `inobtenable` qui porte quand même une métrique, est une ligne qui se contredit.
        cherche = (self.metrique, self.source_pressentie, self.ancre)
        if self.statut == "traduit":
            manquants = [nom for nom, val in
                         (("metrique", self.metrique),
                          ("source_pressentie", self.source_pressentie),
                          ("ancre", self.ancre)) if not val]
            if manquants:
                raise ValueError(
                    f"statut='traduit' mais {manquants} absent(s) : une ligne traduite dit QUOI "
                    "chercher, OÙ, et par rapport à QUELLE ancre — sinon le collecteur reçoit un "
                    "ordre vide")
            if self.motif:
                raise ValueError(
                    "statut='traduit' porte un `motif` : le motif est la raison d'une "
                    "impossibilité ; une ligne traduite n'en a pas")
        else:  # inobtenable
            if not self.motif:
                raise ValueError(
                    "statut='inobtenable' sans `motif` : une ligne inobtenable devient un mandat "
                    "ouvert qui doit dire POURQUOI aucune source connue ne la produit — sans motif, "
                    "c'est un trou déguisé (#44/#54)")
            porte = [nom for nom, val in
                     (("metrique", self.metrique),
                      ("source_pressentie", self.source_pressentie),
                      ("ancre", self.ancre)) if val]
            if porte:
                raise ValueError(
                    f"statut='inobtenable' porte {porte} : si l'ingrédient a une métrique, une "
                    "source et une ancre, il est traduit, pas inobtenable — les deux états "
                    "s'excluent (mode de panne #44)")
        _ = cherche  # explicite : les trois champs de recherche vont ensemble ou pas du tout
        return self


class CollectionPlan(Strict):
    """Le plan entier pour un (ticker × framework × version × archétype).

    Le plan est DATÉ et VERSIONNÉ comme tout le reste (§3.6) : le corpus EDGAR de RVMD ne vaut pas
    la même chose en janvier et après une lecture clinique. La date de génération est portée par la
    table `collection_plans` (grain `(ticker_id, framework_id, framework_version)`), pas par ce
    contrat — un contrat valide un contenu, l'horodatage est un fait d'écriture.

    `archetype` n'est PAS un `Literal` figé : la liste des archétypes est détenue par le référentiel
    (`frameworks.yaml`, §4.1.3) et le pont vérifie l'appartenance. Le figer ici recopierait le
    vocabulaire d'un autre détenteur (#46), et il divergerait au premier archétype ajouté.
    """
    ticker_id: str = Field(min_length=1)
    framework_id: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    framework_version: str = Field(min_length=1)
    archetype: str = Field(min_length=1)
    items: list[CollectionPlanItem] = Field(min_length=1)

    @model_validator(mode="after")
    def _un_ingredient_n_est_planifie_qu_une_fois(self):
        couples = [(it.question_id, it.ingredient_id) for it in self.items]
        if len(set(couples)) != len(couples):
            vus: set[tuple[str, str]] = set()
            doublons = sorted({c for c in couples if c in vus or vus.add(c)})
            raise ValueError(
                f"un même couple (question, ingrédient) est planifié plusieurs fois : {doublons}. "
                "Deux lignes pour un ingrédient, c'est un aiguilleur qui ne saura pas laquelle "
                "relier à `question_coverage` ; et un `traduit` + un `inobtenable` sur le même "
                "ingrédient est une contradiction sur ce qu'on sait chercher")
        return self
