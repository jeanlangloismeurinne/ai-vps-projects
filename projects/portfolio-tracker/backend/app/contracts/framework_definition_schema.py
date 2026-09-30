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

from typing import Annotated, Literal, Optional

from pydantic import Field, model_validator

from .analysis_v2_schemas import Strict, Tier

__all__ = [
    "FRAMEWORK_DEFINITION_SCHEMA_VERSION",
    "MODES_ARCHETYPE", "PLANCHERS_DESSERRES", "PORTEES_EVENEMENT",
    "TypeEvenement", "IngredientRequis", "ChiffreCleDeclare", "VariableArchetype", "QuestionDefinition", "FrameworkDefinition",
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


# Ce qu'un type d'événement rouvre (#89). Voir le catalogue `types_evenement` de `frameworks.yaml`.
PORTEES_EVENEMENT = ("questions_declarees", "toutes", "aucune")


class TypeEvenement(Strict):
    """Un type d'événement publié par l'émetteur, et sa PORTÉE.

    `toutes` existe pour les événements qui changent l'objet même de l'analyse (périmètre,
    existentiel) ou qu'on n'a pas encore lus (`a_qualifier`) : les faire lister par chaque question
    ferait qu'une question oubliée resterait « à jour » après une fusion. `aucune` existe pour les
    dépôts de pure forme — nommés, pour qu'un dépôt reconnu ne se confonde jamais avec un dépôt
    inconnu (qui, lui, est `a_qualifier`)."""
    id: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    libelle: str = Field(min_length=20)
    portee: Literal["questions_declarees", "toutes", "aucune"]
    # D'OÙ VIENT L'ÉVÉNEMENT (#93, arbitrage A du 2026-09-28). `emetteur` : un fait que l'émetteur
    # publie lui-même — le seul que la note flash lit. `exterieur` : un fait survenu chez un
    # concurrent ou dans le secteur (approbation d'un rival, réforme des prix) — un vrai fonds relit
    # la partie concurrence du dossier sans attendre que l'émetteur en parle. REQUIS, sans défaut :
    # une origine omise ferait proposer un événement de concurrent au lecteur d'un 8-K de l'émetteur.
    origine: Literal["emetteur", "exterieur"]

    @model_validator(mode="after")
    def _un_evenement_exterieur_rouvre_des_questions_nommees(self):
        # Un fait chez un concurrent ne change pas l'entreprise analysée (portée `toutes` serait une
        # relecture complète du dossier pour la décision d'un tiers), et un type extérieur qui ne
        # rouvrirait rien (`aucune`) n'aurait pas de raison d'être déclaré.
        if self.origine == "exterieur" and self.portee != "questions_declarees":
            raise ValueError(
                f"`{self.id}` est un événement extérieur de portée `{self.portee}` : un fait survenu "
                f"chez un concurrent ou dans le secteur rouvre les questions qui le déclarent, "
                f"jamais tout le dossier, et jamais rien")
        return self


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
    # `repris_de` (#99, capacité 4 bis) : l'ingrédient EST le chiffre déjà instruit par ces questions
    # d'une autre méthodologie — un seul chiffre par dossier (#95). Il ne se collecte JAMAIS (le
    # traducteur ne le voit pas, le pont du plan refuse sa ligne) ; la valorisation le reprend de la
    # réponse qui tient, ou, si la question est sans objet pour ce titre, du modèle de l'entreprise
    # (arbitrage « option c » du 2026-09-29). Vide = un ingrédient ordinaire, à collecter.
    repris_de: list[Annotated[str, Field(pattern=r"^[a-z]{2}_[0-9]+$")]] = Field(default_factory=list)

    @model_validator(mode="after")
    def _reprise_sans_doublon(self):
        if len(set(self.repris_de)) != len(self.repris_de):
            raise ValueError(f"ingrédient `{self.id}` : `repris_de` contient un doublon")
        return self


class ChiffreCleDeclare(Strict):
    """Un chiffre de l'ENCADRÉ DE CHIFFRES CLÉS que toute réponse à la question doit rendre (4 bis,
    instruit avec l'utilisateur le 2026-09-29).

    Comme un vrai fonds : la note d'analyste se clôt par un encadré au format maison — valeur, unité,
    période —, et c'est LUI que relit le modèle de valorisation, jamais la prose. Le chiffre est
    déclaré ici, en DONNÉES : l'analyste ne choisit ni ce qu'il chiffre, ni l'unité (un coût du capital
    rendu en points par l'un et en fraction par l'autre ferait deux chiffres, #95).
    """
    id: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    libelle: str = Field(min_length=10)
    unite: str = Field(min_length=1)     # « % », « M$ », « mois », « années », « points/an »
    periode: str = Field(min_length=3)   # « moyenne 5 ans », « dernier exercice », « à la date du bilan »
    # `calcul` (#101) : le chiffre SE CALCULE à partir des autres chiffres de la même question (dette
    # nette = dette brute − trésorerie ; autonomie = trésorerie ÷ consommation × 12). C'est le CODE qui
    # le calcule, jamais le modèle (arbitrage #95 : « le calcul n'est pas fait par le modèle ») — mesuré
    # le 2026-09-29 : laissé au modèle, la dette nette de RVMD sortait à −328 M$, la valeur de l'EXEMPLE
    # du prompt, au lieu de −3 450,5. Grammaire fermée de `formule_grammaire` (#72), sans décalage
    # d'exercice ; les noms référencés sont un invariant RELATIONNEL (pont du référentiel, [T]).
    calcul: Optional[str] = Field(default=None, min_length=3)
    # `le_plus_eleve_de` (#105) : le chiffre RETIENT le plus élevé de plusieurs chiffres relevés de la
    # même question, dans la même unité — la règle de PRUDENCE d'un fonds (arbitrage du 2026-09-30 : la
    # consommation de trésorerie retenue pour l'autonomie est la plus forte du constaté et de la
    # prévision de la direction ; sinon le comité se fonde sur une prévision optimiste, ce qui fausse
    # toute société en accélération). Calculé par le code comme `calcul`, jamais par le modèle. Hors de
    # la grammaire de formules à dessein : elle est partagée avec l'appariement (#72), qui n'a que
    # faire d'un maximum.
    le_plus_eleve_de: list[Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$")]] = Field(default_factory=list)
    # `facultatif` (#105) : un chiffre RELEVÉ que le dossier peut ne pas établir sans rien bloquer (la
    # prévision de la direction). Dans `le_plus_eleve_de`, un terme facultatif absent est SAUTÉ en le
    # disant ; un terme obligatoire absent rend le chiffre retenu non établi (on ne retient pas une
    # prévision faute du constaté).
    facultatif: bool = False

    @property
    def calcule_par_le_systeme(self) -> bool:
        """Vrai si le CODE établit ce chiffre (formule ou règle de prudence) : il n'est pas demandé au
        modèle, et une ligne fournie pour lui est écartée (#101). DÉTENTEUR UNIQUE de la distinction
        relevé / calculé, lue par le référentiel, le pont, l'analyste et `completer_encadre` (#46)."""
        return self.calcul is not None or bool(self.le_plus_eleve_de)

    @model_validator(mode="after")
    def _une_seule_facon_d_etre_etabli(self):
        if self.calcul is not None and self.le_plus_eleve_de:
            raise ValueError(f"chiffre `{self.id}` : `calcul` ET `le_plus_eleve_de` — un chiffre s'établit "
                             "d'une seule façon")
        if self.le_plus_eleve_de and (len(self.le_plus_eleve_de) < 2
                                      or len(set(self.le_plus_eleve_de)) != len(self.le_plus_eleve_de)):
            raise ValueError(f"chiffre `{self.id}` : `le_plus_eleve_de` compare au moins deux chiffres "
                             "distincts")
        if self.facultatif and self.calcule_par_le_systeme:
            raise ValueError(f"chiffre `{self.id}` : seul un chiffre RELEVÉ peut être facultatif — un chiffre "
                             "calculé s'établit ou dit pourquoi il ne s'établit pas")
        return self

    @model_validator(mode="after")
    def _le_calcul_est_une_formule(self):
        if self.calcul is not None:
            from app.contracts.formule_grammaire import FormuleInexecutable, analyser_formule
            try:
                analyser_formule(self.calcul)
            except FormuleInexecutable as e:
                raise ValueError(f"chiffre `{self.id}` : `calcul` hors de la grammaire fermée — {e}") from e
        return self


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
    # Les types d'événement qui ROUVRENT la question (#89) — REQUIS, sans défaut : créer un framework,
    # c'est décider ce qui rouvre chacune de ses questions (arbitrage du 2026-09-26). Un défaut vide
    # rendrait « rien ne la rouvre » indiscernable de « on a oublié de le déclarer », et la question
    # resterait à jour après n'importe quel communiqué. Les types de portée `toutes` n'ont pas à y
    # figurer ; leur appartenance au catalogue est un invariant RELATIONNEL (pont, [Q]).
    rouverte_par: list[str] = Field(min_length=1)
    sens_admis: list[str] = Field(min_length=2)
    ingredients_requis: list[IngredientRequis] = Field(min_length=1)
    variables_par_archetype: dict[str, VariableArchetype] = Field(min_length=1)
    # L'encadré de chiffres clés (4 bis) — REQUIS, sans défaut, et une liste VIDE est une réponse :
    # « se_4 ne rend AUCUN chiffre (une position dans le cycle) » doit s'écrire. Un défaut vide rendrait
    # « cette question ne se chiffre pas » indiscernable de « on a oublié de déclarer ses chiffres », et
    # la valorisation n'aurait rien à reprendre sans que rien ne le dise (`feedback_optional_schema_gate`).
    chiffres_cles: list[ChiffreCleDeclare]

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
        chiffres = [c.id for c in self.chiffres_cles]
        if len(set(chiffres)) != len(chiffres):
            raise ValueError(f"{self.id} : deux chiffres clés portent le même id — {sorted(chiffres)}")
        if len(set(self.rouverte_par)) != len(self.rouverte_par):
            raise ValueError(f"{self.id} : `rouverte_par` contient un doublon")
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
    # Le bloc du `ResearchMemo` que ce framework PROJETTE (§6, lot 5). REQUIS, jamais optionnel :
    # `Optional` ici rendrait « ce framework ne projette rien » indiscernable de « on a oublié de le
    # déclarer », et le mémo sortirait une rubrique « pas de méthodologie approuvée » sur un sujet
    # pourtant instruit (`feedback_optional_schema_gate` — un desserrage à chaud est un trou
    # silencieux).
    #
    # ⚠️ IL EXISTE PARCE QUE `chemin_indexation` NE PEUT PAS EN TENIR LIEU. L'invariant [N] du pont
    # force la racine du chemin à être l'id du framework : `qualite_financiere.*` vit donc dans
    # l'espace de noms du FRAMEWORK, jamais dans celui du mémo. Sans ce champ, le seul lien possible
    # serait la coïncidence de noms (appeler un framework `financials`) — un alias de plus, et
    # §0.3 rouvert.
    #
    # Le contrat ne vérifie PAS que ce bloc existe : il valide un objet, jamais la cohérence entre
    # deux (#37). C'est l'invariant relationnel [O] de `frameworks._valider_pont_definitions`, qui
    # confronte la valeur à `contracts.memo_blocs.BLOCS_MEMO`.
    bloc_memo: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
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
                f"qu'un lien de `question_coverage` désignera (§6, #57) : partagé, il rend deux "
                f"questions indiscernables pour l'index, et la porte de complétude en comptera "
                f"une pour deux"
            )
        return self


class FrameworksFile(Strict):
    """Le fichier entier. `archetypes` y est déclaré UNE fois : c'est le détenteur, et chaque
    question doit couvrir exactement cette liste — vérifié par le pont, pas ici (#37)."""
    schema_version: str = Field(min_length=1)
    archetypes: list[str] = Field(min_length=1)
    # La version du CATALOGUE D'ÉVÉNEMENTS, distincte de celle des méthodologies (#90) : une note flash
    # est la lecture d'un dépôt contre CE catalogue. Corriger un libellé d'événement ne change aucune
    # question ; le faire sous `schema_version` invaliderait toutes les réponses pour relire un 8-K.
    types_evenement_version: str = Field(min_length=1)
    types_evenement: list[TypeEvenement] = Field(min_length=1)
    frameworks: list[FrameworkDefinition] = Field(min_length=1)

    @model_validator(mode="after")
    def _les_archetypes_sont_distincts(self):
        if len(set(self.archetypes)) != len(self.archetypes):
            raise ValueError("`archetypes` contient un doublon")
        ids = [t.id for t in self.types_evenement]
        if len(set(ids)) != len(ids):
            raise ValueError("`types_evenement` contient un doublon")
        return self
