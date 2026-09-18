"""Schéma Pydantic versionné de la CARTE D'APPARIEMENT (spec v3 §3.6, maillon 4bis) — convention #67.

Une carte par (ticker × framework × version). Elle répond, pour CET émetteur-là, à une question que
le plan de collecte ne pose pas : « parmi les champs que cette société DÉPOSE RÉELLEMENT, lesquels
répondent à cet ingrédient, et à quel prix ? »

POURQUOI PAR TICKER, ET JAMAIS DANS LE RÉFÉRENTIEL
---------------------------------------------------
La piste « écrire `poste: net_income` à côté de la question du framework » a été envisagée puis
ÉCARTÉE. Le référentiel doit rester applicable à **tout** ticker : y graver un poste us-gaap
enfermerait le cadre dans une juridiction, et il ne vaudrait plus pour un émetteur européen ni pour
une société non cotée — c'est #31 déplacé d'un cran vers le haut.

La mesure du 2026-09-14 le montre sans interprétation : le poste `inventory` est FONDÉ chez NVDA et
MSFT, et ABSENT chez RVMD (27 postes sur 33) — non par défaut de collecte, mais parce qu'une biotech
pré-revenus n'a pas de stocks. Le même ingrédient, la même question, deux appariements différents.
L'appariement est donc une propriété du COUPLE (question × émetteur), et d'aucun des deux seul.

Il se calcule contre l'INVENTAIRE RÉEL (`edgar_facts.fetch_company_facts`), jamais contre une liste
devinée : NVDA dépose 627 concepts `us-gaap`, MSFT 562, RVMD 269, là où le catalogue `POSTES` en
nomme 33. `POSTES` garde son rôle de #61 (les RECETTES de collecte : concepts candidats, flux ou
bilan, choix par fraîcheur #30) mais cesse d'être la FRONTIÈRE.

TROIS ÉTATS, JAMAIS DEUX (#44/#54)
-----------------------------------
  `exact`         — UN champ déposé répond tel quel, sans rien y ajouter ni en retrancher.
  `approximation` — une formule sur N champs déposés, HYPOTHÈSES ÉCRITES.
  `indisponible`  — aucun champ déposé n'y contribue ; la ligne part au web.

La case du milieu est celle qui porte l'information, et c'est elle qui manquait. Aujourd'hui
`qf_1.capital_employe` part au web chercher un nombre que PERSONNE ne publie, alors que NVDA dépose
`Assets`, `CashAndCashEquivalentsAtCarryingValue`, `ShortTermInvestments` et `LiabilitiesCurrent` :
la soustraction est à portée, et elle est en tier A. Sans troisième état, le système n'a le choix
qu'entre mentir (`exact` sur un champ voisin) et renoncer (`indisponible`).

Ce que l'état `approximation` achète n'est pas le nombre : c'est que le lecteur puisse **CONTESTER
L'HYPOTHÈSE**. D'où `formule` et `hypotheses` obligatoires, et jamais facultatifs — une approximation
dont on ne peut pas lire le raisonnement n'est pas une approximation, c'est un `exact` déguisé.

CE QUE CE FICHIER VÉRIFIE, ET CE QU'IL NE PEUT PAS VÉRIFIER (#37)
-----------------------------------------------------------------
Un contrat valide un **objet**, jamais la cohérence entre deux. Tout ce qui demande de connaître un
autre objet — le référentiel des questions, et surtout l'INVENTAIRE réellement déposé par cet
émetteur — vit dans `app/agents/v2/apparieur.py` (`valider_pont_appariement`) :

  ici (Pydantic, un objet)                      | là-bas (pont, contre le RÉEL)
  ----------------------------------------------|------------------------------------------------
  le statut porte EXACTEMENT sa charge          | chaque concept nommé est DÉPOSÉ par CE ticker
  (exact ⟺ 1 concept nu ; approximation ⟺       | la formule ne référence QUE des ingrédients
   formule + hypothèses + `deterministe` ;      |   déclarés — aucun paramètre libre
   indisponible ⟺ motif seul)                   | chaque (question, ingrédient) EXISTE au référentiel
  aucun ingrédient apparié deux fois            | chaque ingrédient ESSENTIEL a une ligne

AUCUN CHAMP DE TIER ICI, ET C'EST LA MÊME FORME QU'AILLEURS (#53/#59)
---------------------------------------------------------------------
Le tier d'un appariement se DÉRIVE (`synthesis_feed.derive_tier_calcul`, convention #67) ; il ne se
déclare pas. Un champ `tier` sur ce contrat serait une invitation permanente à ce que le modèle
qualifie lui-même la fiabilité de ce qu'il vient de proposer. Il est donc ABSENT, et `Strict`
(`extra='forbid'`) rejette à la construction une carte qui tenterait d'en porter un — une doctrine
rendue impossible à violer par construction, jamais gardée par un `if` (même forme que l'actualité
absente de `FrameworkAnswer`, #53, et que le `plancher_tier` absent du plan de collecte, #59).

`deterministe` n'est PAS une exception à cette règle. Ce n'est pas un verdict de fiabilité, c'est un
INGRÉDIENT de la dérivation : il dit s'il a fallu CHOISIR un paramètre pour écrire la formule, ce que
seul l'auteur de la formule sait. Le tier, lui, reste calculé — et la formule est écrite juste à
côté, donc l'affirmation est contestable par le lecteur, ce qu'un tier déclaré n'est jamais.

Cible : pydantic v2 (container backend). Tester en container, **pas** le python hôte (v1).
"""
from __future__ import annotations

from typing import Annotated, Literal, Optional

from pydantic import Field, model_validator

from .analysis_v2_schemas import Strict
from .formule_grammaire import GRAMMAIRE_ADMISE, FormuleInexecutable, analyser_formule

__all__ = [
    "APPARIEMENT_SCHEMA_VERSION",
    "STATUTS_APPARIEMENT",
    "ConceptDepose",
    "HypotheseEcrite",
    "TermeWeb",
    "AppariementItem",
    "AppariementCarte",
]

# Les contraintes portent sur l'ÉLÉMENT, pas sur la liste. Une `list[str]` dont on ne vérifie que la
# longueur accepte `[""]` — la liste est non vide, donc `if not hypotheses` la laisse passer, et la
# garde « une approximation s'explique » devient un test de présence de crochets. C'est la forme de
# faux vert que `feedback_test_negatif_trois_faux_verts` nomme `all()` sur une liste vide, prise par
# l'autre bout : une liste non vide d'éléments vides.
ConceptDepose = Annotated[str, Field(min_length=2, pattern=r"^[A-Za-z][A-Za-z0-9]*$")]
HypotheseEcrite = Annotated[str, Field(min_length=15)]   # une hypothèse se conteste : elle doit s'énoncer
TermeWeb = Annotated[str, Field(min_length=5)]     # un terme se cherche : il doit se nommer

# Même version que les autres contrats du chantier v3 (définition, réponse, plan de collecte) : ils
# naissent de la même spec et se lisent ensemble. Les désynchroniser créerait deux horloges.
APPARIEMENT_SCHEMA_VERSION = "v3.0.0"

# Les trois états de #67. Contrairement au plan de collecte, dont le troisième état (`omis`) est
# l'ABSENCE de ligne, les trois états d'un appariement sont bien trois valeurs de `statut` : une
# carte dit ce qu'on a trouvé POUR CHAQUE ingrédient, y compris « rien de déposé ». Le mode de panne
# de l'omission reste gardé — par le pont, comme pour le plan.
STATUTS_APPARIEMENT = ("exact", "approximation", "indisponible")


class AppariementItem(Strict):
    """L'appariement d'UN ingrédient chez CET émetteur : quel(s) champ(s) déposé(s) y répondent, et
    sous quelles hypothèses.

    `question_id` + `ingredient_id` désignent le couple du référentiel, comme dans
    `CollectionPlanItem` — et pour la même raison : un `ingredient_id` nu (`resultat_net`) peut
    exister sous deux questions, c'est le couple qui lève l'ambiguïté.
    """
    question_id: str = Field(min_length=1, pattern=r"^[a-z]{2}_[0-9]+$")
    ingredient_id: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    statut: Literal["exact", "approximation", "indisponible"]

    # Les concepts `us-gaap` RÉELLEMENT déposés par cet émetteur. Le pont vérifie l'appartenance à
    # l'inventaire ; ici on ne garde que la forme (un nom XBRL est en CamelCase, sans espace).
    #
    # Ce ne sont PAS des postes du catalogue `POSTES` : ce sont les étiquettes brutes du dépôt. Le
    # catalogue est une liste de 33 recettes écrites à la main ; l'émetteur en dépose entre 269 et
    # 627. Nommer ici un poste de catalogue plutôt qu'un concept déposé reviendrait à re-rétrécir la
    # fenêtre que ce maillon existe pour ouvrir.
    concepts: list[ConceptDepose] = Field(
        default_factory=list,
        description="Concepts us-gaap déposés par CET émetteur qui contribuent à l'ingrédient.")

    # Présents SI ET SEULEMENT SI `approximation`.
    # ⚠️ Depuis le maillon 4, ce champ est EXÉCUTÉ, plus seulement lu : `appariement_feed` l'évalue
    # sur les points déposés pour produire le fait. Sa FORME est donc contrainte
    # (`formule_grammaire.analyser_formule`), et le refus emprunte le tour de réparation déjà en
    # place — une prose ne dégrade plus la lisibilité, elle rend la ligne incollectable.
    formule: Optional[str] = Field(
        default=None, min_length=3,
        description="L'expression de calcul, écrite avec les noms de concepts et RIEN d'autre — "
                    "'Assets - LiabilitiesCurrent - CashAndCashEquivalentsAtCarryingValue'. "
                    f"Grammaire admise : {GRAMMAIRE_ADMISE}.")
    hypotheses: list[HypotheseEcrite] = Field(
        default_factory=list,
        description="Ce que la formule SUPPOSE, en clair, pour que le lecteur puisse le contester — "
                    "'les titres de placement court terme sont assimilés à de la trésorerie'.")
    deterministe: Optional[bool] = Field(
        default=None,
        description="La formule est-elle FERMÉE (aucun paramètre à choisir) ? Discriminant unique "
                    "de la règle de tier #67 — voir `derive_tier_calcul`.")

    # Facultatif, et seulement sur une `approximation`. Un terme du calcul que le dépôt ne porte pas
    # et qu'il faut aller chercher ailleurs. C'est le RÔLE DU WEB tranché en #67 : chercher un terme
    # MANQUANT DU CALCUL, et non « caler une hypothèse ». La recherche cesse d'être ce qu'on fait
    # après avoir échoué — elle devient un ingrédient, et fait basculer le calcul dans la branche
    # « ingrédients mixtes » de la règle de tier.
    termes_web: list[TermeWeb] = Field(
        default_factory=list,
        description="Termes du calcul absents du dépôt, à collecter sur le web.")

    # Présent SI ET SEULEMENT SI `indisponible`. Même longueur minimale que `motif` d'une ligne de
    # plan inobtenable, et pour la même raison : « rien de déposé » sans dire pourquoi est un trou
    # déguisé. Ici le motif a une charge de plus — il doit tenir face à un inventaire de plusieurs
    # centaines de concepts, donc dire ce qu'on y a cherché.
    motif: Optional[str] = Field(default=None, min_length=20)

    @model_validator(mode="after")
    def _le_statut_porte_exactement_sa_charge(self):
        # Même forme que `CollectionPlanItem._le_statut_porte_exactement_sa_charge` : le statut n'est
        # pas un libellé, il DÉCIDE des champs présents. C'est ici que les trois états cessent d'être
        # une intention de spec pour devenir une contrainte.
        if self.statut == "exact":
            # UN concept, et un seul. « Exact » veut dire qu'on relève le nombre et que c'est fini :
            # deux concepts, c'est déjà une addition — donc une approximation, qui doit s'expliquer.
            if len(self.concepts) != 1:
                raise ValueError(
                    f"statut='exact' avec {len(self.concepts)} concept(s) : un appariement exact est "
                    "UN champ qu'on recopie tel quel. Zéro, c'est `indisponible` ; deux ou plus, "
                    "c'est un calcul, donc `approximation` avec ses hypothèses écrites")
            # ⚠️ `deterministe` se teste `is not None`, JAMAIS par vérité : `False` est falsy, et un
            # `exact` portant `deterministe=False` traverserait un `if val` sans être vu. Le champ
            # est un booléen à trois valeurs utiles (vrai / faux / absent) ; le confondre avec sa
            # valeur de vérité rendrait la garde aveugle à exactement la moitié des cas.
            porte = [nom for nom, val in (("formule", self.formule),
                                          ("hypotheses", self.hypotheses),
                                          ("termes_web", self.termes_web),
                                          ("motif", self.motif)) if val]
            if self.deterministe is not None:
                porte.append("deterministe")
            if porte:
                raise ValueError(
                    f"statut='exact' porte {porte} : s'il faut une formule, une hypothèse, un terme "
                    "web ou un motif, le champ ne répond pas COMPLÈTEMENT et EXACTEMENT — c'est une "
                    "`approximation` ou un `indisponible`, et le déclarer exact fait passer un "
                    "raisonnement pour un relevé")

        elif self.statut == "approximation":
            # Au moins un concept DÉPOSÉ. Une approximation qui ne repose sur rien de déposé n'est
            # pas une approximation : c'est une recherche web, donc `indisponible`. Le web apporte un
            # terme MANQUANT du calcul (#67) — il ne fournit pas le calcul entier.
            if not self.concepts:
                raise ValueError(
                    "statut='approximation' sans aucun concept déposé : une approximation est une "
                    "formule sur des champs que l'émetteur PUBLIE, dont le web complète au plus un "
                    "terme manquant. Sans aucun ancrage dans le dépôt, c'est `indisponible`")
            manquants = [nom for nom, val in (("formule", self.formule),
                                              ("hypotheses", self.hypotheses)) if not val]
            if manquants:
                raise ValueError(
                    f"statut='approximation' mais {manquants} absent(s) : ce que l'état "
                    "`approximation` achète, c'est que le lecteur puisse CONTESTER le raisonnement. "
                    "Sans formule lisible ni hypothèse écrite, c'est un `exact` déguisé")
            if self.deterministe is None:
                raise ValueError(
                    "statut='approximation' sans `deterministe` : c'est le discriminant UNIQUE de la "
                    "règle de tier (#67) — une formule fermée hérite du plus faible ingrédient, une "
                    "formule qui demande de CHOISIR un paramètre descend d'un cran. Sans lui, le "
                    "tier ne se dérive pas, et il faudrait le déclarer")
            if self.motif:
                raise ValueError(
                    "statut='approximation' porte un `motif` : le motif est la raison d'une "
                    "absence ; une approximation a une formule, pas une excuse")
            # La FORME de la formule, et c'est ici qu'elle se garde — pas dans le prompt (maillon 4).
            # Depuis que `appariement_feed` l'évalue, une formule en prose n'est plus une approximation
            # « moins lisible » : c'est une ligne qui repart au web chercher un nombre que l'émetteur
            # dépose, sous un log de repli qui ressemble à un cas nominal. Le remède par prompt a été
            # mesuré à un passage sur deux (00-REPRISE, 2026-09-18) ; celui-ci ne peut pas se desserrer
            # par reformulation (#59).
            try:
                analyser_formule(self.formule)
            except FormuleInexecutable as e:
                raise ValueError(
                    f"statut='approximation' avec une formule INEXÉCUTABLE — {e}") from e

        else:  # indisponible
            if not self.motif:
                raise ValueError(
                    "statut='indisponible' sans `motif` : l'inventaire de cet émetteur compte des "
                    "centaines de concepts, donc « rien ne répond » demande de dire ce qu'on y a "
                    "cherché. Sans motif, c'est un trou déguisé (#44/#54) — et il se relira comme "
                    "une absence chez l'émetteur")
            porte = [nom for nom, val in (("concepts", self.concepts),
                                          ("formule", self.formule),
                                          ("hypotheses", self.hypotheses),
                                          ("termes_web", self.termes_web)) if val]
            if self.deterministe is not None:  # `False` est falsy — cf. la note du cas `exact`
                porte.append("deterministe")
            if porte:
                raise ValueError(
                    f"statut='indisponible' porte {porte} : si un champ déposé y contribue, "
                    "l'ingrédient n'est pas indisponible — il est `exact` ou `approximation`. Les "
                    "deux ensemble sont une carte qui se contredit (mode de panne #44)")
        return self


class AppariementCarte(Strict):
    """La carte entière pour un (ticker × framework × version).

    `dernier_depot_vu` est ce qui rend la carte RÉVISABLE plutôt que définitive. Une société mûrit et
    se met à déposer des ingrédients qu'elle ne déposait pas : RVMD ne publie ni `Revenues`, ni
    `InventoryNet`, ni `AccountsReceivableNetCurrent` — ce n'est pas un trou de collecte, c'est une
    biotech pré-revenus, et son produit approuvé par la FDA en août 2026 fera apparaître ces trois
    champs au premier trimestre de commercialisation. Une carte figée continuerait alors de router
    vers le web des ingrédients devenus tier A, en silence.

    D'où la mécanique tranchée en #67, qui est exactement celle de #54
    (`_apply_deterministic_overrides`) : la carte est PERSISTÉE avec le dépôt le plus récent qu'elle
    a vu, et sa validité est REVÉRIFIÉE À LA LECTURE. Un `indisponible` établi sur un inventaire de
    269 concepts ne vaut rien contre un inventaire qui en compte 272 ; c'est le point de LECTURE qui
    doit s'en apercevoir, jamais un travail de fond qu'on espère avoir relancé
    (`feedback_controle_au_point_de_lecture`).
    """
    ticker_id: str = Field(min_length=1)
    framework_id: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    framework_version: str = Field(min_length=1)
    dernier_depot_vu: str = Field(
        min_length=10,
        description="La date du point le plus récent de l'inventaire au moment du calcul "
                    "(ISO). La carte se recalcule dès qu'un dépôt plus récent apparaît.")
    items: list[AppariementItem] = Field(min_length=1)

    @model_validator(mode="after")
    def _un_ingredient_n_est_apparie_qu_une_fois(self):
        couples = [(it.question_id, it.ingredient_id) for it in self.items]
        if len(set(couples)) != len(couples):
            vus: set[tuple[str, str]] = set()
            doublons = sorted({c for c in couples if c in vus or vus.add(c)})
            raise ValueError(
                f"un même couple (question, ingrédient) est apparié plusieurs fois : {doublons}. "
                "Un ingrédient n'a qu'un meilleur appariement ; deux lignes, c'est un aval qui "
                "choisira la première rencontrée — et un `exact` doublé d'un `indisponible` est une "
                "contradiction sur ce que cet émetteur publie")
        return self
