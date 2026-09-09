"""
Schéma Pydantic versionné du contrat de FRAMEWORK (spec v3 §2.4) — lot 1 du chantier v3.

Un objet par (ticker × framework × question × analyste). C'est **le** nouveau contrat de la v3 :
il remplace, comme sortie d'analyse, la grille fermée de 19 champs (`MVDD_SPEC`) que le lot 3
supprime.

CE QUE CE FICHIER VÉRIFIE, ET CE QU'IL NE PEUT PAS VÉRIFIER
-----------------------------------------------------------
Un contrat valide un **objet**, jamais la cohérence entre deux (convention #37). Tout ce qui
demande de connaître le corpus, la question, ou les autres réponses vit dans
`app/agents/v2/frameworks.py` (`valider_pont_framework_answer`) et lève `FrameworkAnswerRefused` :

  ici (Pydantic)                            | là-bas (pont, en Python)
  ------------------------------------------|-------------------------------------------------
  le statut porte EXACTEMENT ses blocs       | la question existe dans le framework
  une approximation est complète             | les entries citées ont été RÉELLEMENT fournies
  une approximation est une `interpretation` | le rang est bien celui que les tiers cités dérivent
  un renvoi porte son mandat                 | le rang atteint le plancher de la question
  un gap nomme la question qu'il comble      | un substitut pointe une réponse d'une AUTRE question

LES TROIS AXES, ET POURQUOI L'ACTUALITÉ N'EST PAS UN CHAMP DE `FrameworkAnswer`
------------------------------------------------------------------------------
La doctrine des trois axes (conventions #50/#51/#53) se lit **dans la forme de ce fichier** :

  • **fiabilité** — propriété de la SOURCE : `fondation.rang_derive`, stocké.
  • **nature** — propriété de l'ASSERTION : `fondation.nature_effective`, stocké.
  • **actualité** — propriété de la RELATION fait ↔ ancre : **absent de `Fondation`**, et présent
    seulement sur `FondationServie`, produit à la LECTURE.

`FrameworkAnswer` est ce que l'analyste émet et ce que la table persiste ; `FrameworkAnswerServie`
est ce que le GET rend. Le premier hérite de `Strict` (`extra='forbid'`) : un payload qui porterait
un `actualite` est **rejeté à la construction**, pas ignoré. C'est la convention #53 rendue
impossible à violer par construction plutôt que gardée par un `if` — persister l'actualité
reproduirait littéralement la cause n°2 du diagnostic #50 (un corpus dont le score est arrêté à
l'écriture ne vieillit jamais, donc ne peut pas signaler qu'il a vieilli).

DEUX ÉCARTS ASSUMÉS AVEC LE JSON DE LA SPEC §2.4, TOUS DEUX PLUS STRICTS
------------------------------------------------------------------------
1. `manager.controles.honnetete_approximation` a **trois** valeurs (`ok|ko|sans_objet`) là où la
   spec en écrit deux. Sur une réponse qui n'approxime pas, « l'approximation est-elle honnête ? »
   n'a pas d'objet : la répondre `ok` serait un vert vrai sur zéro ligne — le 1er des quatre faux
   verts, et le mode de panne que #44/#53/#55 nomment à chaque fois (l'indécidable est un troisième
   état, compté à part et NOMMÉ, jamais un repli sur l'un des deux autres). L'équivalence
   `honnetete_approximation == 'sans_objet' ⟺ statut != 'approxime'` est un invariant, donc le
   troisième état ne peut pas servir d'échappatoire.
2. `analyste` n'est pas dans le JSON de la spec. §3.4 écrit le contrat pour **N > 1** analystes dès
   maintenant ; sans porteur de l'identité du répondant, deux réponses à une même question sont
   indiscernables, et le correctif naturel le jour venu serait de les moyenner — ce que §3.4
   interdit explicitement (un score composite reproduirait la cause n°1 de #50).

Cible : pydantic v2 (container backend 2.13.4). Tester en container, **pas** le python hôte (v1).
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import Field, model_validator

from .analysis_v2_schemas import Strict, Tier
from .readiness_report_schema import GapItem

__all__ = [
    "FRAMEWORK_SCHEMA_VERSION", "STATUTS", "Statut",
    "Reponse", "Fondation", "FondationServie", "Approximation", "SansObjet",
    "ControlesManager", "ManagerVerdict", "FrameworkAnswer", "FrameworkAnswerServie",
    "FrameworkMandate", "COLONNES_DENORMALISEES",
]

# Contrat NEUF, versionné avec le chantier qui le crée. Il ne bouscule pas `SCHEMA_VERSION`
# ("v2.0.0") des 4 JSON d'analyse : bumper celui-là forcerait les 3 points de synchro (#19) et
# l'exemple JSON des 12 prompts en base (#39) pour un contrat qui n'existait pas encore.
FRAMEWORK_SCHEMA_VERSION = "v3.0.0"

# Vocabulaire FERMÉ des statuts (spec §2.4). Il n'y a pas de statut par défaut, et surtout pas de
# cinquième état « partiellement répondu » : chacun des quatre commande des blocs distincts.
STATUTS = ("repondu", "approxime", "sans_objet", "non_fondable")
Statut = Literal["repondu", "approxime", "sans_objet", "non_fondable"]

# Vocabulaire de l'axe `nature` — celui des ENTRIES (migration 034, convention #51), pas celui des
# natures attendues d'un champ. Les deux ne se dérivent jamais l'un de l'autre.
NatureEntry = Literal["mesure", "evenement", "interpretation"]


class Reponse(Strict):
    """La réponse elle-même. `verbatim` est ce qu'un lecteur lit ; le reste rend la réponse
    comparable entre dossiers (spec §7, niveau 2)."""
    verbatim: str = Field(min_length=1)
    valeur: Optional[float] = None
    unite: Optional[str] = Field(default=None, min_length=1)
    # `sens` n'a PAS de vocabulaire fermé ici : la spec n'en fixe aucun (elle montre « eleve »), et
    # en inventer un au lot 1 serait induire le contrat de ce que le code fera — le 1er piège de
    # §12. Il se fermera au lot 2, quand les 13 questions diront ce que « sens » veut dire pour
    # chacune.
    sens: Optional[str] = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _un_nombre_porte_son_unite(self):
        # Un montant sans unité n'est pas imprécis, il est illisible : 15,99 lus « 0,0 » ont coûté
        # la convention #46, et un ratio sans unité se lit indifféremment en points ou en pourcents.
        if self.valeur is not None and not self.unite:
            raise ValueError("`reponse.valeur` sans `reponse.unite` : un nombre nu n'est pas une "
                             "réponse (#45/#46 — une grandeur porte son unité)")
        return self


class Fondation(Strict):
    """Ce qui fonde la réponse — les DEUX axes qui se stockent (#50).

    Pas de champ `actualite` : c'est une propriété de la relation fait ↔ ancre, calculée à la
    lecture (#53). Elle vit sur `FondationServie`, et seulement là.
    """
    cited_entry_ids: list[int] = Field(min_length=1)
    # DÉRIVÉ, jamais déclaré (règle transverse 7, §3.5). Le pont vérifie qu'il vaut bien ce que les
    # tiers réels des entries citées commandent — un rang auto-déclaré est un rang faux.
    rang_derive: Tier
    nature_effective: NatureEntry


class FondationServie(Fondation):
    """`Fondation` + l'axe recalculé À LA LECTURE. Jamais persistée, jamais acceptée en entrée.

    Produite par `frameworks.servir_answer()`, qui appelle la fonction de production
    (`knowledge.actualite.etat_actualite_entry`) — jamais une seconde porte.
    """
    actualite: Literal["courante", "perimee", "indeterminable"]
    motif_actualite: str = Field(min_length=1)


class Approximation(Strict):
    """Le bloc que `statut='approxime'` rend obligatoire, et qui EST le contrôle ③ du manager.

    Les quatre champs sont requis : une estimation dont la méthode, les ingrédients, les hypothèses
    ou le sens d'erreur manquent se lit exactement comme une mesure. C'est déjà ce que la consigne
    de production exige (`synthesis_feed._CONSIGNE_LACUNES` : « assortie de son sens d'erreur et de
    ses hypothèses ») ; le contrat cesse de le demander poliment.
    """
    methode: str = Field(min_length=1)
    ingredients_entry_ids: list[int] = Field(min_length=1)
    hypotheses_explicites: list[str] = Field(min_length=1)
    sensibilite: str = Field(min_length=1)


class SansObjet(Strict):
    """Le hors-sujet est un SIGNAL, pas une panne (spec §2.1) — mais un `sans_objet` sans motif est
    un trou déguisé (contrôle ① du manager)."""
    motif: str = Field(min_length=1)
    substitut_applique: Optional[str] = Field(default=None, min_length=1)
    substitut_answer_id: Optional[int] = None
    # Déclaration EXPLICITE, sans défaut : « qf_1 sur une pré-revenus n'a pas de substitut, c'est
    # la RÉPONSE » (§4.1.3) doit s'écrire, pas s'obtenir en omettant un champ.
    aucun_substitut: bool

    @model_validator(mode="after")
    def _substitut_ou_declaration(self):
        if self.aucun_substitut and self.substitut_applique:
            raise ValueError("`aucun_substitut=True` et un `substitut_applique` : il faut choisir")
        if not self.aucun_substitut and not self.substitut_applique:
            raise ValueError("un `sans_objet` désigne un substitut OU déclare qu'il n'y en a pas "
                             "(`aucun_substitut=True`) — le silence n'est pas une option (§2.4)")
        if self.substitut_answer_id is not None and not self.substitut_applique:
            raise ValueError("`substitut_answer_id` sans `substitut_applique` : une réponse de "
                             "substitution qui ne nomme pas le substitut n'est pas traçable")
        return self


class ControlesManager(Strict):
    """Les 4 contrôles de §3.2. Aucun ne demande un jugement d'investissement ; chacun a une
    réponse mécanique. `honnetete_approximation` porte un troisième état — cf. l'écart n°1 en
    en-tête de module."""
    completude: Literal["ok", "ko"]
    fondation: Literal["ok", "ko"]
    honnetete_approximation: Literal["ok", "ko", "sans_objet"]
    non_substitution: Literal["ok", "ko"]

    def kos(self) -> list[str]:
        return [n for n in ("completude", "fondation", "honnetete_approximation", "non_substitution")
                if getattr(self, n) == "ko"]


class ManagerVerdict(Strict):
    """Le manager acquitte ou renvoie — il ne réécrit pas la réponse et ne promeut jamais un rang
    (§3.3). C'est pourquoi ce bloc ne porte AUCUN champ de réponse ni de rang : il n'a pas où
    écrire une correction, donc il ne peut pas en écrire une."""
    verdict: Literal["acquitte", "renvoye"]
    controles: ControlesManager
    motif: str = Field(min_length=1)
    mandat_de_recherche_id: Optional[int] = None

    @model_validator(mode="after")
    def _un_renvoi_produit_quelque_chose(self):
        kos = self.controles.kos()
        if self.verdict == "renvoye":
            if self.mandat_de_recherche_id is None:
                raise ValueError("un renvoi sans `mandat_de_recherche_id` est un renvoi qui ne "
                                 "produit rien — c'est l'Écart B de §0.5, que la v3 ferme")
            if not kos:
                raise ValueError("renvoi avec les 4 contrôles au vert : le motif du renvoi doit "
                                 "être un contrôle `ko`, pas une opinion sur l'entreprise (§3.2)")
        else:
            if kos:
                raise ValueError(f"acquittement malgré {kos} en `ko` : un manager qui acquitte ce "
                                 "qu'il vient de refuser n'a plus d'autorité (§3.2)")
            if self.mandat_de_recherche_id is not None:
                raise ValueError("un acquittement ne porte pas de mandat de recherche")
        return self


class FrameworkAnswer(Strict):
    """La réponse d'UN analyste à UNE question d'UN framework, pour UN émetteur.

    Append-only et versionnée au lot 3 (A1, comme `knowledge_entries`) : une réponse corrigée ne se
    met pas à jour, elle supersede.
    """
    schema_version: Literal["v3.0.0"] = "v3.0.0"
    framework_id: str = Field(min_length=1)
    question_id: str = Field(min_length=1)
    ticker_id: str = Field(min_length=1)
    analyste: str = Field(min_length=1)      # §3.4 : N ≥ 1, deux réponses ne se moyennent JAMAIS
    statut: Statut

    reponse: Optional[Reponse] = None
    fondation: Optional[Fondation] = None
    approximation: Optional[Approximation] = None
    sans_objet: Optional[SansObjet] = None
    gap: Optional[GapItem] = None            # détenteur unique du couple manque ↔ remède (#54)
    manager: Optional[ManagerVerdict] = None  # None = pas encore passée au manager

    @model_validator(mode="after")
    def _le_statut_porte_exactement_ses_blocs(self):
        """Chaque statut commande ses blocs, et INTERDIT les autres.

        L'interdiction compte autant que l'obligation : c'est elle qui empêche un `non_fondable` de
        porter quand même une `reponse` (entry #190 — un ROIC publié pour une société sans revenus)
        et un `sans_objet` de servir le substitut comme réponse à la question d'origine (contrôle ④
        de §3.2, le seul qui aurait attrapé #190 et #191).
        """
        requis: dict[str, tuple[str, ...]] = {
            "repondu":      ("reponse", "fondation"),
            "approxime":    ("reponse", "fondation", "approximation"),
            "sans_objet":   ("sans_objet",),
            "non_fondable": ("gap",),
        }
        # `fondation` est TOLÉRÉE sur un `sans_objet` : les entries qui prouvent que la question n'a
        # pas d'objet (« aucun revenu ») sont une fondation légitime de ce hors-sujet.
        tolere: dict[str, tuple[str, ...]] = {"sans_objet": ("fondation",)}
        tous = ("reponse", "fondation", "approximation", "sans_objet", "gap")

        attendus = requis[self.statut]
        manquants = [b for b in attendus if getattr(self, b) is None]
        if manquants:
            raise ValueError(f"statut `{self.statut}` sans {manquants} : "
                             f"il exige {list(attendus)} (spec §2.4)")
        interdits = [b for b in tous
                     if b not in attendus and b not in tolere.get(self.statut, ())
                     and getattr(self, b) is not None]
        if interdits:
            raise ValueError(f"statut `{self.statut}` porte {interdits}, qui ne lui appartiennent "
                             f"pas — un statut qui publie les blocs d'un autre est exactement la "
                             f"non-substitution que le contrôle ④ interdit")

        # ④ NON-SUBSTITUTION, moitié intra-objet : une approximation ne se présente jamais comme une
        # mesure. `nature` est FORCÉE à `interpretation` (règle de rang, spec §1.5) — le rang, lui,
        # est vérifié par le pont, qui seul connaît les tiers réels des entries citées.
        if self.statut == "approxime" and self.fondation.nature_effective != "interpretation":
            raise ValueError(
                f"approximation de nature `{self.fondation.nature_effective}` : une estimation est "
                "une `interpretation`, jamais une `mesure` (règle de rang, §1.5). C'est le contrôle "
                "④ : une approximation présentée comme une mesure est le défaut de l'entry #190.")

        # Un gap qui ne nomme pas la question qu'il comble n'est pas rouvrable : il faudrait deviner
        # ce qu'on doit aller chercher. `champs_cibles` porte le grain question (spec §6).
        if self.statut == "non_fondable" and self.question_id not in self.gap.champs_cibles:
            raise ValueError(
                f"le gap de `{self.question_id}` ne le nomme pas dans `champs_cibles` "
                f"({self.gap.champs_cibles}) : un manque qui ne dit pas ce qu'il comble ne produit "
                "aucun mandat exécutable")

        # ⚠️ L'équivalence, pas l'implication : `sans_objet` sur une approximation laisserait un
        # contrôle ③ muet là où il est le plus utile, et `ok` sur une non-approximation serait un
        # vert vrai sur zéro ligne.
        if self.manager is not None:
            vaut_sans_objet = self.manager.controles.honnetete_approximation == "sans_objet"
            if vaut_sans_objet != (self.statut != "approxime"):
                raise ValueError(
                    f"`honnetete_approximation` = "
                    f"`{self.manager.controles.honnetete_approximation}` sur un statut "
                    f"`{self.statut}` : ce contrôle vaut `sans_objet` si et seulement si la réponse "
                    "n'approxime pas (cf. écart n°1 de l'en-tête)")
        return self


class FrameworkAnswerServie(FrameworkAnswer):
    """Ce que le GET rend : la réponse persistée + l'axe `actualite` RECALCULÉ.

    Même schéma que la readiness depuis la capacité 4 (#54) : le GET rejoue la moitié déterministe
    sur une copie, sans rien écrire. Un GET qui servirait la ligne stockée telle quelle servirait le
    verdict d'avant l'événement matériel — c'est le faux vert que la capacité 4 a mis une journée à
    voir.
    """
    fondation: Optional[FondationServie] = None


class FrameworkMandate(Strict):
    """Le mandat de recherche — ce qu'un renvoi PRODUIT (§3.1), et ce qui ferme l'Écart B.

    Émis par un renvoi du manager **ou** par l'action « renvoyer » du comité (§8.2) : un seul canal,
    deux émetteurs. Consommé par le `search-worker`.
    """
    schema_version: Literal["v3.0.0"] = "v3.0.0"
    framework_id: str = Field(min_length=1)
    question_id: str = Field(min_length=1)
    ticker_id: str = Field(min_length=1)
    origine: Literal["manager_renvoi", "comite"]
    motif: str = Field(min_length=1)
    # Le mandat EXÉCUTABLE, pas un mot-clef : c'est ce qui remplace les sacs de mots-clefs français
    # de `SYNTHESIS_TARGETS` (§5.1). Il descend du `mandat_gabarit` de la question, instancié par
    # l'archétype (§4.2.3 : l'archétype change le mandat, jamais le contrat).
    mandat: str = Field(min_length=1)
    etat: Literal["ouvert", "servi", "abandonne"]

    statut_avant: Optional[Statut] = None
    statut_apres: Optional[Statut] = None
    consomme_at: Optional[datetime] = None
    entry_ids_produits: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def _un_etat_porte_exactement_sa_trace(self):
        if self.etat == "ouvert":
            sales = [n for n in ("statut_apres", "consomme_at") if getattr(self, n) is not None]
            if sales or self.entry_ids_produits:
                raise ValueError(f"mandat `ouvert` portant déjà {sales or 'des entries produites'} :"
                                 " un mandat non consommé n'a pas de suite")
        elif self.etat == "servi":
            manquants = [n for n in ("statut_avant", "statut_apres", "consomme_at")
                         if getattr(self, n) is None]
            if manquants:
                raise ValueError(
                    f"mandat `servi` sans {manquants} : sans l'avant ET l'après, on ne peut pas "
                    "dire si la boucle comité → collecte a changé quoi que ce soit (T8)")
            # ⚠️ `statut_apres == statut_avant` est LICITE : une recherche qui ne trouve rien laisse
            # la question `non_fondable`, et c'est une information — pas une violation. C'est T8, en
            # face, qui exige qu'AU MOINS UN mandat ait fait bouger un statut.
        else:  # abandonne
            if self.statut_apres is not None:
                raise ValueError("mandat `abandonne` portant un `statut_apres` : un abandon ne "
                                 "conclut rien sur la question")
        return self


# ── Les colonnes que la table `framework_answers` devra porter (migration 036, lot 3) ─────────
# DÉTENTEUR UNIQUE du nom de chaque colonne dénormalisée et du chemin du contrat dont elle est la
# projection. Même rôle que `monitoring._colonnes_routeur` : ce qu'un LECTEUR (le test
# d'acceptation, la porte, l'écran) doit pouvoir lire sans reparser le JSON.
#
# ⚠️ Il existe parce que le test d'acceptation du lot 0 a été écrit AVANT ce contrat, avec sa propre
# nomenclature devinée (`framework`, `rang_degrade`, `methode_approximation`, `ingredients`,
# `motif`). Deux nomenclatures d'accord restent deux nomenclatures (#46) : le jour où le lot 3
# nommerait ses colonnes d'après le contrat, T3 et T4 liraient `None` pour toujours et resteraient
# rouges pour la MAUVAISE raison — ou pire, T3 virerait au vert sur zéro ligne. La table est
# importée par `tools/acceptation_frameworks.py`, et `check_framework_contract.py` §6 vérifie que
# chaque chemin résout dans le contrat.
COLONNES_DENORMALISEES: dict[str, str] = {
    "framework":             "framework_id",
    "question_id":           "question_id",
    "ticker_id":             "ticker_id",
    "analyste":              "analyste",
    "statut":                "statut",
    "cited_entry_ids":       "fondation.cited_entry_ids",
    "rang_degrade":          "fondation.rang_derive",
    "methode_approximation": "approximation.methode",
    "ingredients":           "approximation.ingredients_entry_ids",
    "motif":                 "sans_objet.motif",
}
