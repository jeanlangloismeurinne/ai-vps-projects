"""La datation d'une pièce — DEUX dates nommées, `source_date` DÉRIVÉE (#79).

Pourquoi deux colonnes au lieu d'une
------------------------------------
`source_date` est la colonne sur laquelle les machines trient : c'est elle qui élit la pièce « en
vigueur » dans `dossier._rang`, elle qui nourrit l'axe `actualite` (#53), elle qui décote l'âge dans
`compute_reliability`. Jusqu'ici elle était **déclarée** — par le modèle au search-worker, par le
producteur déterministe ailleurs — et une seule case accueillait deux dates qui ne sont pas la même
chose : la date du FAIT et la date du DOCUMENT qui le rapporte.

Mesuré sur RVMD avant d'écrire une ligne (#78 : la difficulté se remesure) :

  • #307 — « Au 2026-06-30 : trésorerie + titres 3 937,97 M$ », `source_date` = **2026-08-05**
    (le dépôt du 10-Q). La pièce bat #444, le même bilan lu en XBRL et daté du fait. L'analyste
    reçoit le commentaire, le chiffre reste en base.
  • #309 — « six mois clos le **2025**-06-30 : −416,2 M$ », `source_date` = **2026-08-05**. C'est la
    colonne COMPARATIVE du 10-Q : le chiffre de l'an dernier porte le tampon le plus frais du
    dossier. Mode de panne de #48, en clair.
  • #296 — « Au 2026-06-30 (déposé le 2026-08-05) », `source_date` = **2026-09-01**, une date qui
    n'apparaît NULLE PART dans la pièce. Ni le fait, ni le dépôt : le tampon du greffier au moment
    du classement. Ce n'est plus un problème de fraîcheur, c'est un problème de traçabilité — la
    ligne ne peut plus être rapprochée de sa source.

21 des 54 entries courantes datées de RVMD portent cette forme, et 6 des 8 chemises à plusieurs
versions élisent une pièce collectée AVANT celle qu'elle bat.

Ce que ce module change, et ce qu'il ne change pas
--------------------------------------------------
Il ne muscle aucune garde. Une garde vérifie la structure et la relation, jamais le SENS (#68) :
aucun code ne peut regarder `source_date = 2026-08-05` et savoir si c'est le fait ou le papier —
les deux sont des dates plausibles, structurellement indiscernables. La réponse est donc de changer
la **FORME** de la réponse : deux cases nommées rendent la confusion inexprimable au lieu de la
rendre surveillée. Le modèle écrivait DÉJÀ les deux dates dans sa prose (« Au 2026-06-30 (10-Q
déposé le 2026-08-05) ») — il ne lui manquait pas la connaissance, il lui manquait la case.

Et `source_date` cesse d'être reçue : elle est CALCULÉE ici, à partir de la portée et des deux
dates, exactement comme `nature` est dérivée au guichet depuis la 034 (#51/#78). Les lecteurs
(`_rang`, `actualite`, `compute_reliability`) ne changent pas d'une ligne : la colonne existe
toujours, elle a seulement cessé de mentir.

Le vocabulaire est FERMÉ — trois états, jamais deux (#25/#44/#54)
-----------------------------------------------------------------
  • ``constatee``    — la pièce affirme ce qui A ÉTÉ. Elle fait foi à la date du FAIT.
  • ``prospective``  — la pièce affirme ce qui EST ATTENDU (guidance, plan, consensus). Elle fait
    foi à la date de son ANNONCE : une guidance émise le 5 août est une information du 5 août, pas
    une information de l'exercice qu'elle vise. La période visée devient un ATTRIBUT de la pièce
    (`periode_visee`), pas sa fraîcheur — et c'est précisément ce qui rendra possible la
    confrontation ultérieure du réalisé à l'annoncé (module « qualité des prévisions », backlog).
  • ``indatable``    — la pièce n'affirme rien de datable (description d'un modèle d'affaires, d'une
    gouvernance, d'un cadre réglementaire stable). `source_date` est NULL, donc l'axe `actualite`
    rend ``indeterminable`` et la pièce **perd toute élection de fraîcheur**. C'est voulu : perdre
    faute de date est honnête, gagner sur la date d'une page ne l'est pas.

Il n'y a pas de quatrième état et pas de défaut. Une entry dont la portée n'est pas déclarée est
REJETÉE au guichet ; en base, `portee_temporelle IS NULL` désigne les lignes ANTÉRIEURES à la
migration 045 — un quatrième cas qui est un constat d'héritage, pas un état du vocabulaire.

Convention de bornage (#42/#48)
-------------------------------
Un poste de BILAN est daté d'un INSTANT, un FLUX d'un EXERCICE. Les deux entrent dans
`date_du_fait` sous la même convention : **la borne de FIN**. « Six mois clos le 2025-06-30 » donne
`date_du_fait = 2025-06-30`. C'est ce qui rend flux et stocks comparables sur une colonne unique
sans que l'un n'écrase l'autre — et c'est aussi ce qui fait que #309 cesse d'être le fait le plus
frais du dossier pour devenir ce qu'il est : un chiffre d'il y a un an.

Ce que ce module NE fait PAS
----------------------------
Il ne vérifie pas `date_du_document` contre l'index des dépôts EDGAR. Ce serait un contrôle juste,
et il rendrait la porte d'écriture DÉPENDANTE DU RÉSEAU : une panne d'EDGAR se lirait « date
invérifiable », donc, sous la moindre tolérance, « date acceptée » — une panne réseau qui produit
la phrase rassurante (#49). Le rapprochement est un travail de LECTURE, il est nommé en résiduel.

Il n'extrait aucune date depuis la prose. « Quelle date cette phrase affirme-t-elle ? » n'est pas un
vocabulaire fermé, donc ce n'est pas dérivable ; c'est pour cette raison que les pièces héritées
sont RE-COLLECTÉES et non backfillées par modèle (arbitrage du 2026-09-22 : à l'initialisation, on
rachète tout).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

# Vocabulaire FERMÉ de la portée temporelle. Hors de cette liste, rien n'existe : pas de défaut,
# pas de « probablement constatée ».
PORTEES: frozenset[str] = frozenset({"constatee", "prospective", "indatable"})


class DatationInvalide(ValueError):
    """Violation STRUCTURELLE de la datation — toujours décidable sans lire le sens du contenu.

    Distincte de `ValueError` nue pour que le guichet puisse la journaliser comme un refus de
    forme, et pour qu'une garde négative puisse asserter le TYPE de l'échec et pas seulement le
    fait qu'il y en ait eu un.
    """


@dataclass(frozen=True)
class Datation:
    """Ce qu'une pièce déclare de son propre temps. `source_date` n'en fait PAS partie : elle en
    découle (`source_date()`), et c'est toute la raison d'être de ce type.

    `motif` n'est obligatoire que pour ``indatable`` : dire « cette pièce n'a pas de date » sans
    dire pourquoi est un silence, et un silence se lit plus tard comme une propriété du sujet
    (`feedback_rendu_est_un_producteur`).
    """

    portee: str
    date_du_document: Optional[date] = None
    date_du_fait: Optional[date] = None
    periode_visee: Optional[date] = None   # borne de FIN de la période annoncée (prospective)
    motif: Optional[str] = None

    def __post_init__(self) -> None:
        valider(self)

    def source_date(self) -> Optional[date]:
        """La date qui fait foi — DÉRIVÉE, jamais déclarée.

        C'est la seule fonction que les écrivains doivent appeler. Elle est pure : rejouable sur
        n'importe quelle ligne à n'importe quel instant, comme `derive_nature`.
        """
        if self.portee == "constatee":
            return self.date_du_fait
        if self.portee == "prospective":
            return self.date_du_document
        return None  # indatable : l'absence est le résultat, pas un échec


def valider(d: Datation) -> None:
    """Gardes DÉCIDABLES — structure et relation entre champs, jamais sens du contenu (#68).

    Chaque règle porte son propre message nommé : une garde qui échoue doit dire LAQUELLE, sinon
    une mutation de test vire au rouge sans qu'on sache si c'est la bonne (`feedback_test_negatif_trois_faux_verts`).
    """
    if d.portee not in PORTEES:
        raise DatationInvalide(
            f"portee_temporelle {d.portee!r} hors vocabulaire fermé {sorted(PORTEES)} — "
            "il n'y a pas d'état par défaut"
        )

    if d.portee == "constatee":
        if d.date_du_fait is None:
            raise DatationInvalide(
                "constatee exige `date_du_fait` : une pièce qui affirme ce qui a été dit QUAND. "
                "Si la date du fait est inconnue, la portée est `indatable`, pas `constatee` "
                "datée du document"
            )
        if d.date_du_document is None:
            raise DatationInvalide("constatee exige `date_du_document` : un constat vient d'un document")
        if d.date_du_fait > d.date_du_document:
            raise DatationInvalide(
                f"constatee : date_du_fait {d.date_du_fait} POSTÉRIEURE à date_du_document "
                f"{d.date_du_document} — un document ne constate pas l'avenir. Une affirmation "
                "portant au-delà du document est `prospective`"
            )
        if d.periode_visee is not None:
            raise DatationInvalide(
                "constatee ne porte pas `periode_visee` : la période visée qualifie une ANNONCE, "
                "pas un constat (exclusivité du vocabulaire, #54)"
            )

    elif d.portee == "prospective":
        if d.date_du_document is None:
            raise DatationInvalide(
                "prospective exige `date_du_document` : une prévision fait foi à la date de son "
                "ANNONCE, donc l'annonce doit être datée"
            )
        if d.periode_visee is None:
            raise DatationInvalide(
                "prospective exige `periode_visee` (borne de fin) : sans elle, le réalisé ne "
                "pourra jamais être confronté à l'annoncé"
            )
        if d.periode_visee <= d.date_du_document:
            raise DatationInvalide(
                f"prospective : periode_visee {d.periode_visee} n'est pas postérieure à "
                f"date_du_document {d.date_du_document} — ce qui est déjà clos au moment de "
                "l'annonce est un constat, pas une prévision"
            )
        if d.date_du_fait is not None:
            raise DatationInvalide(
                "prospective ne porte pas `date_du_fait` : il n'y a pas encore de fait "
                "(exclusivité du vocabulaire, #54)"
            )

    else:  # indatable
        if d.date_du_fait is not None or d.periode_visee is not None:
            raise DatationInvalide(
                "indatable ne porte ni `date_du_fait` ni `periode_visee` : déclarer l'un des deux "
                "contredit la portée déclarée"
            )
        if not (d.motif or "").strip():
            raise DatationInvalide(
                "indatable exige un `motif` qui NOMME pourquoi la pièce n'est pas datable — "
                "une absence muette se relit comme une propriété du sujet"
            )


def constatee(*, date_du_fait: date, date_du_document: date) -> Datation:
    """Raccourci pour le cas nominal — l'écrasante majorité des pièces d'un dossier."""
    return Datation(portee="constatee", date_du_fait=date_du_fait, date_du_document=date_du_document)


def prospective(*, date_du_document: date, periode_visee: date) -> Datation:
    return Datation(portee="prospective", date_du_document=date_du_document, periode_visee=periode_visee)


def indatable(*, motif: str, date_du_document: Optional[date] = None) -> Datation:
    return Datation(portee="indatable", date_du_document=date_du_document, motif=motif)
