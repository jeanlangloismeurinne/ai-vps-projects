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

from datetime import date
from typing import Annotated, Literal, Optional

from pydantic import Field, model_validator

from .analysis_v2_schemas import Strict, Tier

__all__ = [
    "FRAMEWORK_DEFINITION_SCHEMA_VERSION",
    "MODES_ARCHETYPE", "PLANCHERS_DESSERRES", "PORTEES_EVENEMENT",
    "TypeEvenement", "IngredientRequis", "ParametreDuFonds", "ChiffreCleDeclare", "VariableArchetype", "QuestionDefinition", "FrameworkDefinition",
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
    # CE QUE LE FAIT RECOMMANDE AU COMITÉ (#139, arbitrage du 2026-10-18) : par archétype en vigueur,
    # l'archétype vers lequel reclasser l'émetteur (« premier produit autorisé » : pre_revenus → rentable).
    # Une RECOMMANDATION affichée au dossier, jamais un reclassement : le comité reclasse ou maintient.
    # Optionnel : la plupart des faits ne changent pas la grille. Cohérence avec `archetypes` : pont [W].
    reclasse: Optional[dict[str, str]] = None

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
        if self.reclasse is not None and self.origine != "emetteur":
            raise ValueError(
                f"`{self.id}` recommande un reclassement mais est d'origine `{self.origine}` : la "
                f"décision d'un concurrent ne change pas le stade de l'émetteur analysé")
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
    # `depuis_le_socle` (arbitrage du 2026-10-04 — « toutes les questions financières s'intègrent à un
    # P&L reconstitué ») : l'ingrédient est une ligne des COMPTES RECONSTITUÉS de l'émetteur (le socle
    # des comptes, une pièce jointe d'office au dossier des frameworks qui le lisent). Il ne se collecte
    # JAMAIS ligne à ligne : le socle le porte déjà, bouclé avec le reste des comptes ; une seconde
    # collecte ferait deux chiffres pour un même poste — exactement les défauts #104/#112.
    depuis_le_socle: bool = False
    # `duree_de_vie` / `cadence` (règle de fraîcheur, arbitrages du 2026-10-16, `roadmap/V3/
    # 06-regle-fraicheur.md`) : combien de temps une pièce qui fonde cet ingrédient reste valable.
    # REQUIS, sans défaut — comme `rouverte_par`, une absence rendrait « valable pour toujours »
    # indiscernable de « on a oublié ». Un CHIFFRE COURANT est remplacé par les comptes suivants ; un
    # HISTORIQUE ne vieillit pas, il se COMPLÈTE de la période nouvelle ; une DESCRIPTION ANNUELLE cède
    # au document annuel suivant ; un JUGEMENT n'a pas de durée propre (seuls les faits qui rouvrent la
    # question le touchent). Deux mécanismes déjà arbitrés ferment la liste : `reprise` (hérite de la
    # réponse reprise, #99 — ⟺ `repris_de`) et `au_cours_du_jour` (recalculé à la lecture au dernier
    # cours coté daté, option 1 du 28/09). La `cadence` (trimestrielle / annuelle : celle du document
    # qui publie usuellement l'ingrédient) n'existe que pour un chiffre courant ou un historique.
    duree_de_vie: Literal["chiffre_courant", "historique", "description_annuelle", "jugement", "reprise",
                          "au_cours_du_jour"]
    cadence: Optional[Literal["trimestrielle", "annuelle"]] = None

    @model_validator(mode="after")
    def _reprise_sans_doublon(self):
        if len(set(self.repris_de)) != len(self.repris_de):
            raise ValueError(f"ingrédient `{self.id}` : `repris_de` contient un doublon")
        if self.repris_de and self.depuis_le_socle:
            raise ValueError(f"ingrédient `{self.id}` : repris d'une autre question ET lu dans le socle — "
                             "un ingrédient a une seule origine")
        if (self.duree_de_vie == "reprise") != bool(self.repris_de):
            raise ValueError(f"ingrédient `{self.id}` : la durée de vie `reprise` va avec `repris_de`, et "
                             "seulement avec lui (un ingrédient repris hérite de la réponse qu'il reprend)")
        a_cadence = self.duree_de_vie in DUREES_A_CADENCE
        if self.depuis_le_socle and not a_cadence:
            raise ValueError(f"ingrédient `{self.id}` : lu dans le socle des comptes, c'est un chiffre — sa "
                             f"durée de vie est un chiffre courant ou un historique, pas `{self.duree_de_vie}`")
        if a_cadence and self.cadence is None:
            raise ValueError(f"ingrédient `{self.id}` : un {self.duree_de_vie} porte sa `cadence` "
                             "(trimestrielle ou annuelle) — c'est elle qui dit quelle publication le prolonge")
        if not a_cadence and self.cadence is not None:
            raise ValueError(f"ingrédient `{self.id}` : `cadence` sans objet pour la durée de vie "
                             f"`{self.duree_de_vie}`")
        return self


# Détenteur unique : les durées de vie qu'une publication périodique prolonge (et qui portent donc une
# cadence) — lu par le contrat et, à la lecture, par la règle de fraîcheur.
DUREES_A_CADENCE = ("chiffre_courant", "historique")


class ChiffreDuSocle(Strict):
    """Un chiffre de l'encadré LU dans les comptes reconstitués (arbitrage du 2026-10-04 : « repris du
    socle »). Comme un fonds : le modèle des comptes est la seule source des chiffres, l'analyste juge
    et commente ; il ne recopie pas (RVMD qf_7 recopiait « 1,22 Md$ » pour 1 223,03 M$).

    Deux formes, exclusives :
      · un MONTANT — `formule` : formule fermée (`formule_grammaire`) sur des LIGNES du gabarit maison
        (leur existence est un invariant relationnel, vérifié par le pont du référentiel, [U]), lue à
        une `periode` du vocabulaire fermé de `socle_comptes.PERIODES_DE_CHIFFRE` ;
      · un RATIO MAISON — `ratio` : l'identifiant d'une définition de `ratios_maison.RATIOS` (rendement
        du capital sur cinq exercices, conversion en trésorerie…), qui porte sa propre fenêtre
        d'exercices ; son existence et son unité sont vérifiées par le pont du référentiel ([U])."""
    formule: Optional[str] = Field(default=None, min_length=3)
    periode: Optional[Literal["dernier_bilan", "douze_mois", "dernier_exercice"]] = None
    ratio: Optional[str] = Field(default=None, pattern=r"^[a-z][a-z0-9_]*$")

    @model_validator(mode="after")
    def _formule_fermee(self):
        if (self.formule is None) == (self.ratio is None):
            raise ValueError("`socle` porte une `formule` (un montant) OU un `ratio` maison, exactement l'un des "
                             "deux")
        if self.ratio is not None and self.periode is not None:
            raise ValueError(f"`socle.ratio` {self.ratio} porte sa propre fenêtre d'exercices : pas de `periode`")
        if self.formule is not None:
            if self.periode is None:
                raise ValueError("`socle.formule` sans `periode` : un montant du socle se lit à une date")
            from app.contracts.formule_grammaire import FormuleInexecutable, analyser_formule
            try:
                analyser_formule(self.formule)
            except FormuleInexecutable as e:
                raise ValueError(f"`socle.formule` hors de la grammaire fermée — {e}") from e
        return self


class ParametreDuFonds(Strict):
    """Une DÉCISION DU FONDS, commune à tout le portefeuille (#137 point 10) : le comité la fixe, la date
    et la revoit à échéance. Ce n'est pas une pièce — jamais collectée, jamais citée : l'encadré la reçoit
    du code. Comme un fonds : le taux exigé est une décision maison, la cohérence entre titres prime sur
    la précision, et une estimation de tiers n'est qu'un point de comparaison."""
    valeur: float
    unite: str = Field(min_length=1)
    decide_le: date
    revoir_avant: date
    decision: str = Field(min_length=20)   # qui l'a décidée, et pourquoi — lu par le comité

    @model_validator(mode="after")
    def _une_revue_suit_la_decision(self):
        if self.revoir_avant <= self.decide_le:
            raise ValueError(f"décision du fonds : revue au {self.revoir_avant} avant ou le jour de la décision "
                             f"({self.decide_le})")
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
    # `socle` (2026-10-04) : le chiffre est LU dans les comptes reconstitués, par le code.
    socle: Optional[ChiffreDuSocle] = None
    # `parametre_du_fonds` (#137 point 10) : le chiffre EST une décision du fonds (`parametres_du_fonds`
    # du référentiel), posée par le code — le taux exigé de qf_1. Son existence et son unité sont un
    # invariant RELATIONNEL (pont du référentiel, [W]).
    parametre_du_fonds: Optional[str] = Field(default=None, pattern=r"^[a-z][a-z0-9_]*$")
    # `non_significatif_si_negatif` (2026-10-12) : les termes d'un CALCUL dont le signe négatif rend le
    # résultat non significatif — la pratique d'un analyste crédit, qui écrit « n.s. » plutôt qu'une
    # couverture des intérêts de −27,4 fois quand l'entreprise perd de l'argent en exploitation (RVMD :
    # −1 627 M$ sur douze mois). Déclaré par chiffre, jamais généralisé : une marge négative, elle, est un
    # niveau. Prolonge #44 (le dénominateur négatif) aux numérateurs NOMMÉS.
    non_significatif_si_negatif: list[Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$")]] = Field(
        default_factory=list)

    @property
    def calcule_par_le_systeme(self) -> bool:
        """Vrai si le CODE établit ce chiffre (formule, règle de prudence, lecture du socle ou décision du
        fonds) : il n'est
        pas demandé au modèle, et une ligne fournie pour lui est écartée (#101). DÉTENTEUR UNIQUE de la
        distinction relevé / calculé, lue par le référentiel, le pont, l'analyste et `completer_encadre`
        (#46)."""
        return (self.calcul is not None or bool(self.le_plus_eleve_de) or self.socle is not None
                or self.parametre_du_fonds is not None)

    @model_validator(mode="after")
    def _une_seule_facon_d_etre_etabli(self):
        if sum((self.calcul is not None, bool(self.le_plus_eleve_de), self.socle is not None,
                self.parametre_du_fonds is not None)) > 1:
            raise ValueError(f"chiffre `{self.id}` : deux façons d'être établi (calcul, le plus élevé de, "
                             "socle, décision du fonds) — un chiffre s'établit d'une seule façon")
        if self.socle is not None and self.socle.formule is not None and self.unite != "M$":
            raise ValueError(f"chiffre `{self.id}` : un montant lu dans le socle est en M$ (unité déclarée "
                             f"{self.unite!r}) — un ratio est un RATIO MAISON (`socle.ratio`), défini une fois")
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
        if self.non_significatif_si_negatif:
            if self.calcul is None:
                raise ValueError(f"chiffre `{self.id}` : `non_significatif_si_negatif` ne vaut que pour un chiffre "
                                 "CALCULÉ (`calcul`)")
            from app.contracts.formule_grammaire import noms_de_la_formule
            hors = sorted(set(self.non_significatif_si_negatif) - noms_de_la_formule(self.calcul))
            if hors:
                raise ValueError(f"chiffre `{self.id}` : `non_significatif_si_negatif` nomme {hors}, absents de "
                                 f"son calcul « {self.calcul} » — la règle ne s'appliquerait jamais")
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


# #139 ter — le verdict d'une question dont le chiffre qui le porte est non significatif (« n.s. »).
SENS_NON_SIGNIFICATIF = "non_significatif"


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
    # #139 ter — LE VERDICT EST LA LECTURE D'UN SEUL CHIFFRE : `sens_lu_sur` nomme ce chiffre de l'encadré
    # (lu dans les comptes reconstitués). Comme une note d'analyse : quand la cellule porte « n.s. », la
    # case verdict aussi ; quand elle est vide, il n'y a pas de verdict. Le sens `non_significatif` est
    # alors au vocabulaire, et SEUL le code l'écrit (le chiffre est non significatif) ; un chiffre qui
    # manque n'admet aucun verdict. Mesuré RVMD qf_3/qf_5 (2026-10-18) : texte « non mesurable », verdict
    # « en érosion » — inventé, il changeait d'un passage à l'autre. Optionnel : la plupart des verdicts
    # se fondent sur plusieurs éléments (qf_1 « détruit de la valeur » tient sur les pertes).
    sens_lu_sur: Optional[str] = Field(default=None, pattern=r"^[a-z][a-z0-9_]*$")

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
        if self.sens_lu_sur is not None:
            lu = next((c for c in self.chiffres_cles if c.id == self.sens_lu_sur), None)
            if lu is None or lu.socle is None:
                raise ValueError(
                    f"{self.id} : `sens_lu_sur` = {self.sens_lu_sur!r} doit nommer un chiffre de l'encadré "
                    "lu dans les comptes reconstitués — c'est le code qui en établit l'issue")
        if (self.sens_lu_sur is not None) != (SENS_NON_SIGNIFICATIF in self.sens_admis):
            raise ValueError(
                f"{self.id} : le sens `{SENS_NON_SIGNIFICATIF}` va avec `sens_lu_sur` — sans chiffre qui "
                "porte le verdict, personne ne peut établir qu'il est non significatif")
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
    # `lit_le_socle` (2026-10-04) : le dossier de ce framework porte d'office les COMPTES RECONSTITUÉS de
    # l'émetteur (une pièce, `socle_feed`). REQUIS, sans défaut : « ce framework ne lit pas les comptes »
    # ne doit pas se confondre avec « on a oublié de le dire » (`feedback_optional_schema_gate`). Un
    # framework qui ne le lit pas ne voit pas les comptes : chaque framework ne lit que ses sujets (#108).
    lit_le_socle: bool
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


# Les deux sens d'une révision de prévision (§14 de `roadmap/V3/06-regle-fraicheur.md`).
SENS_REVISION = ("hausse", "baisse")


class CausesProbables(Strict):
    """Ce qu'un chiffre révisé dans UN sens peut vouloir dire quand le communiqué ne dit pas pourquoi :
    les CAUSES probables (chacune dérive son type `surprise_<cause>`) et les types qui s'y AJOUTENT
    (une baisse du chiffre d'affaires peut venir d'une décision réglementaire)."""
    causes: list[str] = Field(min_length=1)
    types: list[str]


class ChiffreRevisable(Strict):
    """Une ligne de la TABLE DES CAUSES DE RÉVISION (validée par l'utilisateur le 2026-10-16) : un
    chiffre que la direction peut réviser, les mots par lesquels un communiqué le NOMME (lus dans la
    phrase, en minuscules — la vérification de la déclaration du lecteur), et ses causes probables par
    sens. Ce que ferait un vrai fonds : devant une prévision relevée sans explication, l'analyste rouvre
    tous les chapitres que les causes PLAUSIBLES de ce chiffre touchent, pas un seul par convention."""
    id: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    libelle: str = Field(min_length=5)
    termes: list[Annotated[str, Field(min_length=2)]] = Field(min_length=1)
    hausse: CausesProbables
    baisse: CausesProbables

    @model_validator(mode="after")
    def _des_termes_en_minuscules(self):
        if any(t != t.lower() for t in self.termes):
            raise ValueError(f"`{self.id}.termes` : en minuscules (la phrase est lue en minuscules — un "
                             "terme en majuscules ne serait jamais trouvé)")
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
    # L'INTERRUPTEUR du rappel (#125, principe fondateur n° 3) : True = un passage dont le rappel a été
    # VÉRIFIÉ ne rouvre rien (ordre 1) ; False = tout type cité rouvre, rappel ou non (ordre 0, la règle
    # d'avant). Requis, sans défaut. Lu à la LECTURE des notes : le basculer ne demande aucune relecture.
    rappels_ecartes: bool
    # L'INTERRUPTEUR de la règle de fraîcheur par durée de vie (2026-10-16, `06-regle-fraicheur.md`,
    # principe fondateur n° 3) : True = chaque pièce citée est jugée dans la durée de vie de
    # l'ingrédient qu'elle fonde (ordre 1) ; False = ORDRE 0, la règle d'avant (la réponse a l'âge de sa
    # pièce la plus ancienne, tout fait qui rouvre la question la périme). Requis, sans défaut ; lu à la
    # LECTURE, rien n'est stocké : le basculer ne demande aucune réécriture.
    fraicheur_par_duree_de_vie: bool
    # L'INTERRUPTEUR de la fraîcheur SUJET PAR SUJET (point 15, arbitrage du 2026-10-17, #137 ; principe
    # fondateur n° 3), lu seulement sous `fraicheur_par_duree_de_vie` : True = sur un même ingrédient, seule
    # la pièce la plus RÉCENTE juge la fraîcheur, les plus anciennes sont du contexte (ordre 1) ; False =
    # chaque pièce est jugée seule (ordre 0 : une pièce remplacée citée en contexte périme la réponse).
    # Requis, sans défaut ; lu à la LECTURE : le basculer ne demande aucune réécriture.
    fraicheur_par_sujet: bool
    types_evenement: list[TypeEvenement] = Field(min_length=1)
    # La TABLE DES CAUSES DE RÉVISION (§14 de `06-regle-fraicheur.md`, catalogue 1.6.0) : quand un
    # communiqué révise une prévision SANS dire pourquoi, le code rouvre l'union des types des causes
    # probables du chiffre révisé, dans le sens révisé. Requise, sans défaut : sans elle, une révision
    # sans cause ne rouvrirait rien de vérifiable. Sa cohérence avec le catalogue est un invariant
    # RELATIONNEL (pont, [S] de `frameworks.py`).
    revisions_de_prevision: list[ChiffreRevisable] = Field(min_length=1)
    # Les DÉCISIONS DU FONDS (#137 point 10) — ce que le comité fixe pour tout le portefeuille (le taux
    # exigé). Requises, sans défaut : un taux absent laisserait chaque analyse chercher le sien.
    parametres_du_fonds: dict[Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$")], ParametreDuFonds] = Field(
        min_length=1)
    frameworks: list[FrameworkDefinition] = Field(min_length=1)

    @model_validator(mode="after")
    def _les_archetypes_sont_distincts(self):
        if len(set(self.archetypes)) != len(self.archetypes):
            raise ValueError("`archetypes` contient un doublon")
        ids = [t.id for t in self.types_evenement]
        if len(set(ids)) != len(ids):
            raise ValueError("`types_evenement` contient un doublon")
        return self
