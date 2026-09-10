"""Contrat des DÉFINITIONS de framework (chantier v3, lot 2) — ce qui valide `frameworks.yaml`.

À ne pas confondre avec `framework_answer_schema`, qui valide une RÉPONSE. Ici on valide la
**question** : ce qu'elle demande, à quel rang, et comment elle s'instancie par archétype. Les deux
contrats se rencontrent dans le pont (`agents/v2/frameworks.py`), jamais dans un import croisé.

CE QUE CE CONTRAT REFUSE, ET POURQUOI CHAQUE REFUS EXISTE
---------------------------------------------------------
Une définition de question peut être formellement bien formée et ne rien demander. C'est le mode de
panne le plus coûteux du chantier, parce qu'il produit un VERT :

  · une question **sans ingrédient essentiel** est satisfaite par le corpus vide. Sa couverture sort
    à 100 % le jour où on la mesure, et le framework paraît fondé sur rien ;
  · une question dont `variables_par_archetype` **omet un archétype** est muette sur cet archétype ;
    l'agent choisira alors entre fabriquer une réponse et échouer, et l'expérience du chantier dit
    qu'il fabrique (entry #190, §0.2). L'indécidable se déclare, il ne s'omet pas (#44/#53/#55) ;
  · un `sans_objet` **sans motif** est un trou déguisé, et un `sans_objet` qui ne dit ni son
    substitut ni son absence de substitut laisse le lecteur conclure à une panne ;
  · un **plancher desserré sans motif** est un desserrage tacite — exactement
    `feedback_optional_schema_gate` : on desserre à chaud, et le trou reste ouvert sans trace.

⚠️ CE QUE CE CONTRAT NE VÉRIFIE PAS, ET C'EST VOULU (#37). Un contrat valide un objet, jamais la
cohérence entre deux. L'unicité des `question_id` entre frameworks, l'existence de la question
visée par un `substitut_question_id`, et l'accord avec les vocabulaires détenus ailleurs
(`common.NATURES`, `common.TIER_ORDER`) sont des invariants RELATIONNELS : ils vivent dans
`frameworks.load_frameworks()` et lèvent `FrameworkDefinitionRefused`.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field, model_validator

from .analysis_v2_schemas import Strict, Tier

__all__ = [
    "FRAMEWORK_DEFINITION_SCHEMA_VERSION",
    "MODES_ARCHETYPE", "PLANCHERS_DESSERRES",
    "IngredientRequis", "VariableArchetype", "QuestionDefinition", "FrameworkDefinition",
    "FrameworksFile",
]

# Même version que le contrat de réponse : les deux naissent du même chantier et se lisent
# ensemble. Les désynchroniser créerait deux horloges pour une seule spec.
FRAMEWORK_DEFINITION_SCHEMA_VERSION = "v3.0.0"

MODES_ARCHETYPE = ("variable", "sans_objet")

# Tiers pour lesquels un `motif_plancher` devient OBLIGATOIRE. §4.2.2 desserre `mo_1/3/4/5` à B
# parce que, sur un champ d'interprétation, un dépôt réglementaire est du boilerplate malgré son
# tier A (#50). Ce desserrage est légitime — mais il doit s'ÉCRIRE. Un plancher bas sans motif ne
# se distingue pas d'un oubli, et c'est par des oublis que les plafonds descendent.
PLANCHERS_DESSERRES = ("B", "B-", "C+", "C")


class IngredientRequis(Strict):
    """Ce dont la question a besoin, en SUBSTANCE ÉCONOMIQUE — jamais une entry du corpus.

    Le `libelle` est ce qui descendra au `search-worker` comme mandat (§4.1.2) : il remplace les
    sacs de mots-clefs français de `SYNTHESIS_TARGETS`. Il est donc écrit pour être cherché, pas
    pour être coché.
    """
    id: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    libelle: str = Field(min_length=20)
    # `essentiel` : son absence rend la question NON FONDABLE, elle ne la dégrade pas. C'est ce qui
    # sépare une lacune (qui produit un mandat) d'une réponse faible (qui produit un affichage).
    essentiel: bool


class VariableArchetype(Strict):
    """Comment la question s'instancie pour un archétype — ou pourquoi elle n'a pas d'objet.

    Les archétypes sont une VARIABLE de la question, jamais un framework séparé (§4.1.3). On
    n'ouvrira un framework par archétype que sur le critère de déclenchement de §9.3.
    """
    mode: Literal["variable", "sans_objet"]
    variable: Optional[str] = Field(default=None, min_length=10)
    motif_gabarit: Optional[str] = Field(default=None, min_length=20)
    substitut_question_id: Optional[str] = Field(default=None, min_length=1)
    aucun_substitut: bool = False

    @model_validator(mode="after")
    def _le_mode_porte_exactement_sa_charge(self):
        if self.mode == "variable":
            if not self.variable:
                raise ValueError(
                    "mode='variable' sans `variable` : la question serait déclarée applicable "
                    "sans dire à quoi elle s'applique"
                )
            if self.motif_gabarit or self.substitut_question_id or self.aucun_substitut:
                raise ValueError(
                    "mode='variable' porte une trace de hors-sujet (motif_gabarit / substitut) : "
                    "un archétype est soit couvert, soit sans objet, jamais les deux"
                )
        else:  # sans_objet
            if self.variable:
                raise ValueError("mode='sans_objet' porte une `variable` : contradiction")
            if not self.motif_gabarit:
                raise ValueError(
                    "mode='sans_objet' sans motif : un hors-sujet sans motif est un trou déguisé "
                    "(contrôle ① du manager)"
                )
            # XOR strict, repris de `SansObjet` du contrat de réponse : « pas de substitut » doit
            # s'ÉCRIRE, jamais s'obtenir en omettant un champ (§4.1.3).
            if bool(self.substitut_question_id) == bool(self.aucun_substitut):
                raise ValueError(
                    "un `sans_objet` déclare SOIT un `substitut_question_id`, SOIT "
                    "`aucun_substitut: true` — jamais les deux, jamais aucun des deux"
                )
        # ⚠️ Le motif est un GABARIT : il énonce une propriété de l'ARCHÉTYPE, valable pour tout
        # émetteur (#31). Un motif qui nommerait un émetteur serait une dispense déguisée ; c'est
        # `check_frameworks_definitions.py` qui le vérifie, sur la liste réelle des tickers.
        return self


class QuestionDefinition(Strict):
    """Une question universelle. Les six propriétés de §2.3, aucune facultative par accident."""
    id: str = Field(min_length=1, pattern=r"^[a-z]{2}_[0-9]+$")
    # Énoncé en substance économique. La longueur minimale n'est pas décorative : « ROIC ? » passe
    # un `min_length=1`, et c'est précisément l'énoncé que §2.3 interdit.
    enonce: str = Field(min_length=30)
    chemin_indexation: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
    nature_attendue: Literal["mesure", "evenement", "interpretation"]
    plancher_tier: Tier
    motif_plancher: Optional[str] = Field(default=None, min_length=20)
    actualite_bloquante: bool
    sens_admis: list[str] = Field(min_length=2)
    ingredients_requis: list[IngredientRequis] = Field(min_length=1)
    variables_par_archetype: dict[str, VariableArchetype] = Field(min_length=1)

    @model_validator(mode="after")
    def _une_question_demande_quelque_chose(self):
        if not any(i.essentiel for i in self.ingredients_requis):
            raise ValueError(
                f"{self.id} n'a aucun ingrédient essentiel : sa couverture serait satisfaite par "
                f"le corpus vide, donc mesurée à 100 % le jour où on la mesure"
            )
        ids = [i.id for i in self.ingredients_requis]
        if len(set(ids)) != len(ids):
            raise ValueError(f"{self.id} : deux ingrédients portent le même id — {sorted(ids)}")
        if len(set(self.sens_admis)) != len(self.sens_admis):
            raise ValueError(f"{self.id} : `sens_admis` contient un doublon")
        if self.plancher_tier in PLANCHERS_DESSERRES and not self.motif_plancher:
            raise ValueError(
                f"{self.id} : plancher {self.plancher_tier} sans `motif_plancher`. Un desserrage "
                f"se DÉCLARE (§4.2.2) ; tacite, il ne se distingue pas d'un oubli"
            )
        # L'inverse aussi : un motif de desserrage sur un plancher qui n'est pas desserré est un
        # motif orphelin, et il survivra au prochain resserrage en prétendant l'expliquer.
        if self.plancher_tier not in PLANCHERS_DESSERRES and self.motif_plancher:
            raise ValueError(
                f"{self.id} : `motif_plancher` sur un plancher {self.plancher_tier} non desserré"
            )
        return self


class FrameworkDefinition(Strict):
    """Les 7 parties de §2.2. `sortie` n'en est pas une ici : le contrat de sortie est
    `FrameworkAnswer`, détenu par `framework_answer_schema` et jamais recopié (#46)."""
    id: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    libelle: str = Field(min_length=3)
    etape_benchmark: int = Field(ge=1, le=8)
    methodologie: str = Field(min_length=40)
    nature_dominante: Literal["mesure", "evenement", "interpretation"]
    questions: list[QuestionDefinition] = Field(min_length=1)

    @model_validator(mode="after")
    def _les_questions_sont_distinctes(self):
        ids = [q.id for q in self.questions]
        if len(set(ids)) != len(ids):
            raise ValueError(f"{self.id} : deux questions portent le même id — {sorted(ids)}")
        chemins = [q.chemin_indexation for q in self.questions]
        if len(set(chemins)) != len(chemins):
            raise ValueError(
                f"{self.id} : deux questions partagent un chemin d'indexation. Le chemin est ce "
                f"que `covers` désignera (§6) : partagé, il rend deux questions indiscernables "
                f"pour l'index, et la porte de complétude en comptera une pour deux"
            )
        return self


class FrameworksFile(Strict):
    """Le fichier entier. `archetypes` y est déclaré UNE fois : c'est le détenteur, et chaque
    question doit couvrir exactement cette liste — vérifié par le pont, pas ici (#37)."""
    schema_version: str = Field(min_length=1)
    archetypes: list[str] = Field(min_length=1)
    frameworks: list[FrameworkDefinition] = Field(min_length=1)

    @model_validator(mode="after")
    def _les_archetypes_sont_distincts(self):
        if len(set(self.archetypes)) != len(self.archetypes):
            raise ValueError("`archetypes` contient un doublon")
        return self
