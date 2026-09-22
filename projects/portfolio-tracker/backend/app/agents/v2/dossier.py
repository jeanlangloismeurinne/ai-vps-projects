"""Le DOSSIER remis à l'analyste — détenteur unique de son assemblage (#46).

CE QUE CE MODULE FERME (mesuré le 2026-09-22, RVMD)
---------------------------------------------------
Le corpus tendu à l'analyste était assemblé **à plat** : les N entries courantes les plus récentes
par `source_date`, tronquées à un plafond. Deux défauts, tous deux mesurés :

  · **le même point instruit plusieurs fois.** `qf_4.endettement_brut_et_net` porte TROIS entries
    courantes (#296 du 12/09, #340 du 19/09, #443 du 21/09), toutes tier A, aucune ne remplaçant
    l'autre — les trois rachats successifs ont empilé. L'analyste recevait trois réponses
    concurrentes à la même question sans rien pour dire laquelle fait foi ;
  · **la troncature choisissait par la date**, donc elle pouvait couper une pièce qui fonde un
    ingrédient tout en gardant trois versions d'un autre. Sur RVMD : 40 retenues sur 57.

Et cette règle d'assemblage n'avait **aucun détenteur** : elle était recopiée à l'identique dans
`tools/acceptation_analyste.py` et `tools/executer_chaine.py`, le second portant le commentaire
« Même plafond que l'autre, et pour la même raison ». Une règle tenue à deux endroits re-diverge au
correctif suivant (`feedback_correctif_regle_jumeaux`) — et ici elle fabriquait en plus la
NON-REPRÉSENTATIVITÉ du corpus de test : c'est l'outil de mesure qui produisait le vrac.

LA CLEF DE REGROUPEMENT N'EST PAS LA LIGNE DE PLAN
---------------------------------------------------
Premier réflexe, et il est faux : regrouper sur le couple (métrique, ancre) de l'ordre de mission.
Mesuré sur les quatre plans RVMD du même framework en version identique (12/09 ×2, 19/09, 21/09) :

    9 ingrédients sur 14 portent QUATRE libellés distincts sur quatre passages ;
    le meilleur cas en porte deux ; aucun n'est stable ; l'ancre dérive aussi (2 à 4 valeurs).

Le traducteur reformule à chaque passage — c'est un modèle, et c'est son droit. Une fiche clefée
là-dessus se scinderait en deux à chaque run : un regroupement qui ne regroupe rien, donc un vrac
déguisé en rangement. Ce qui est STABLE, c'est le point de la liste du comité —
`(framework_id, framework_version, question_id, ingredient_id)` — parce qu'il vient du référentiel
inerte et versionné, jamais d'un modèle. Il est déjà écrit à chaque distribution d'ordre dans
`question_coverage` (#57), et l'assemblage se contente de le LIRE (#29 : la couverture se lit d'un
index, elle ne se demande jamais au modèle).

L'AVEUGLEMENT DU COLLECTEUR RESTE INTACT (#58)
-----------------------------------------------
Ce module lit la question. Il le peut : il est en aval de toute collecte, du côté de celui qui
INSTRUIT le dossier, jamais de celui qui va chercher les pièces. Le collecteur ne l'importe pas et
n'apprend rien de lui.

CE QUE L'ASSEMBLAGE NE FAIT PAS
--------------------------------
Il n'ARCHIVE rien, il n'écrit aucun `superseded_by`, il ne déclare aucune entry périmée. Décider
qu'un fait en remplace un autre est un jugement sémantique, et `knowledge/staleness.py` explique
pourquoi il reste humain. Ici on RANGE : les pièces d'un même point sont mises dans une chemise,
la plus récente devant. Le corpus en base est inchangé, l'historique s'empile, et la seule chose
qui change est ce qu'on tend à lire.

TROIS SORTES DE PIÈCES, JAMAIS DEUX (famille #25 / #44)
--------------------------------------------------------
  · ``en vigueur``  — la pièce la plus récente d'une chemise : elle part au modèle ;
  · ``antérieure``  — une pièce plus ancienne du même point : elle reste en base, elle est COMPTÉE
    et datée dans le bilan, et elle **ne part pas** au modèle. Volontairement : la lui tendre
    reproduirait les trois réponses concurrentes qu'on vient de retirer. Son `id` n'est pas non
    plus annoncé au modèle — un id nommé mais absent du corpus se ferait citer, et le pont refuse
    les citations hors corpus (`frameworks.py`, contrôle B) : on fabriquerait un refus ;
  · ``hors index``  — une pièce courante qu'aucun lien de couverture ne rattache à un point. Sur
    RVMD, 35 des 57 (les faits déterministes du flux EDGAR). Elles ne sont PAS du bruit : les
    écarter ferait lire « indisponible » là où il y a de la donnée
    (`feedback_rendu_est_un_producteur`). Elles suivent les pièces en vigueur, dans la limite du
    plafond.

LE PLAFOND NE PEUT PAS COUPER UNE PIÈCE EN VIGUEUR
---------------------------------------------------
Le plafond existe pour une raison de coût (un dossier entier ferait un prompt de plusieurs
centaines de milliers de tokens), pas de méthode. Il s'applique donc au RESTE, jamais au
porteur : couper une pièce en vigueur ferait lire « le corpus ne fonde pas » là où c'est le budget
qui a tranché — exactement le faux négatif que la troncature par date produisait. Si les pièces en
vigueur dépassent à elles seules le plafond, ce n'est pas un cas à absorber en silence :
`plafond_insuffisant` est vrai, on DIT de combien, et on ne coupe toujours pas.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable, Optional, Sequence

__all__ = [
    "Chemise",
    "Dossier",
    "Lien",
    "assembler_dossier",
    "charger_dossier",
]


# Un lien de couverture, réduit à ce que l'assemblage en utilise. Le framework et sa version ne
# figurent pas ici : l'appelant a déjà restreint la lecture à UN framework en UNE version — les
# mélanger dans une même chemise rangerait sous le même point deux méthodologies différentes.
Lien = tuple[str, str, int]  # (question_id, ingredient_id, entry_id)


@dataclass(frozen=True)
class Chemise:
    """Les pièces d'UN point de la liste du comité, la plus récente devant."""

    question_id: str
    ingredient_id: str
    en_vigueur: int
    anterieures: tuple[int, ...]

    @property
    def profondeur(self) -> int:
        """Combien de versions ce point a accumulées — 1 = une seule collecte."""
        return 1 + len(self.anterieures)


@dataclass(frozen=True)
class Dossier:
    """Ce qu'on tend à l'analyste, et ce qu'on a laissé dehors — les deux, toujours."""

    entries: dict[int, dict[str, Any]]
    chemises: tuple[Chemise, ...]
    hors_index_retenues: tuple[int, ...]
    laissees_dehors: tuple[int, ...]
    total_courantes: int
    plafond: int
    plafond_insuffisant: bool
    # Date de COLLECTE de toutes les pièces, y compris celles qui ne partent pas — les antérieures
    # sont absentes d'`entries` par construction, et c'est justement leur date de collecte qu'il
    # faut pour repérer une datation hétérogène. Vide si l'appelant n'a pas chargé `created_at`.
    collecte: dict[int, Any]

    @property
    def anterieures_ecartees(self) -> tuple[int, ...]:
        """Les versions antérieures, DÉDOUBLONNÉES.

        Une même pièce peut être antérieure sur deux points à la fois (mesuré : #300 l'est sous
        qf_4 et sous qf_7). La compter deux fois ferait lire « 10 versions écartées » là où il y en
        a 9 — un décompte de rendu qui se lit comme une propriété du corpus.
        """
        return tuple(sorted({i for ch in self.chemises for i in ch.anterieures}))

    @property
    def datation_suspecte(self) -> tuple[Chemise, ...]:
        """Chemises où la pièce en vigueur a été COLLECTÉE avant une de ses antérieures.

        Le signal d'une datation hétérogène, pas d'une erreur d'ordre. Mesuré sur RVMD le
        2026-09-22 : `qf_4.endettement_brut_et_net` sert #296 (`source_date` 2026-09-01, ramassée
        le 12/09) en écartant #443 (`source_date` 2026-06-30, ramassée le 21/09) — les trois pièces
        de la chemise affirment pourtant le MÊME fait. La cause est en amont : `edgar_feed` date une
        entry à la clôture de période (`period_end`), le chemin narratif à ce que le modèle déclare.
        Deux horloges dans la même chemise.

        Ce module ne tranche pas ce conflit — il n'a pas de quoi. Il le NOMME, parce qu'un
        assemblage qui choisit en silence entre deux dates incomparables fabrique un « en vigueur »
        qui n'est l'avis de personne. Le remède est à la production des entries, pas ici.

        Indécidable sans `created_at` : si l'appelant ne l'a pas chargé, le silence serait un
        « rien à signaler ». On rend donc un tuple vide **uniquement** quand l'information est là et
        qu'il n'y a rien ; `datation_mesurable` dit lequel des deux cas on est.
        """
        if not self.datation_mesurable:
            return ()
        suspectes = []
        for ch in self.chemises:
            vig = self.collecte.get(ch.en_vigueur)
            if vig is None:
                continue
            if any(self.collecte.get(a) is not None and self.collecte[a] > vig
                   for a in ch.anterieures):
                suspectes.append(ch)
        return tuple(suspectes)

    @property
    def datation_mesurable(self) -> bool:
        """`created_at` a-t-il été chargé ? Sans lui, la datation suspecte est INDÉTERMINABLE."""
        return bool(self.collecte)

    def bilan(self) -> str:
        """Le bilan se LIT — son absence est un échec, jamais un zéro rassurant.

        Il nomme les trois sorties séparément parce qu'elles n'ont pas le même remède : une chemise
        profonde est un rachat qui a empilé (normal), une pièce laissée dehors est un plafond qui a
        mordu (budget), un plafond insuffisant est une conception à revoir.
        """
        profondes = [c for c in self.chemises if c.profondeur > 1]
        lignes = [
            f"dossier : {len(self.entries)} pièce(s) remise(s) sur {self.total_courantes} "
            f"courante(s) · plafond {self.plafond}",
            f"  · {len(self.chemises)} chemise(s) — un point instruit chacune",
            f"  · {len(self.hors_index_retenues)} pièce(s) hors index retenue(s)",
            f"  · {len(self.anterieures_ecartees)} version(s) antérieure(s) gardée(s) en base, "
            f"non remise(s) : {list(self.anterieures_ecartees) or 'aucune'}",
            f"  · {len(self.laissees_dehors)} pièce(s) laissée(s) dehors par le plafond",
        ]
        if profondes:
            detail = ", ".join(
                f"{c.question_id}.{c.ingredient_id}×{c.profondeur}" for c in profondes
            )
            lignes.append(f"  · chemises à plusieurs versions : {detail}")
        if not self.datation_mesurable:
            lignes.append(
                "  · datation hétérogène : INDÉTERMINABLE (`created_at` non chargé) — "
                "ce n'est pas « rien à signaler »"
            )
        elif self.datation_suspecte:
            detail = ", ".join(
                f"{c.question_id}.{c.ingredient_id}" for c in self.datation_suspecte
            )
            lignes.append(
                f"  ⚠️ {len(self.datation_suspecte)} chemise(s) à DATATION HÉTÉROGÈNE — la pièce en "
                f"vigueur a été collectée AVANT une antérieure : {detail}. Deux horloges dans la "
                f"même chemise (clôture de période vs date déclarée) ; le remède est à la "
                f"production des entries, pas à l'assemblage."
            )
        if self.plafond_insuffisant:
            lignes.append(
                f"  ⚠️ PLAFOND INSUFFISANT — {len(self.chemises)} pièce(s) en vigueur pour un "
                f"plafond de {self.plafond} : aucune n'a été coupée, le plafond est le problème."
            )
        return "\n".join(lignes)


def _rang(entry: dict[str, Any]) -> tuple[int, int, int]:
    """Ordre de fraîcheur d'une pièce : la plus récente d'abord, non datée en dernier. Croissant.

    ⚠️ La clef est `source_date` — ce que la pièce DIT du monde — et non `created_at`, la date à
    laquelle on l'a ramassée. Trier par la collecte ferait passer devant un rachat qui rapporte un
    document plus VIEUX, et l'appellerait « en vigueur ». Une entry non datée ne peut pas prétendre
    être la plus récente : sa fraîcheur est indéterminable, ce qui n'est pas la même chose que
    fraîche (même raison qu'en `knowledge/staleness.py`).

    ⚠️ **Les ordinaux sont NIÉS, et c'est load-bearing.** Écrite avec la date nue, cette clef trie
    en ordre CROISSANT : elle élit la plus ANCIENNE « en vigueur » et range les récentes en
    antérieures. Mesuré sur RVMD le 2026-09-22 avant correctif — `qf_4.lignes_de_credit_non_tirees`
    servait une pièce du 2025-06-30 en écartant celle du 2026-08-05. Aucun contrôle ne pouvait le
    voir : la fonction rendait un dossier bien formé, de la bonne taille, avec une pièce par point.
    C'est la LECTURE du dossier en texte qui l'a montrée — pas le code de sortie
    (`feedback_rendu_est_un_producteur`). D'où l'invariant d'ordre asserté en §3 de
    `checks/check_dossier.py`, qui mord sur une inversion de signe.
    """
    d: Optional[date] = entry.get("source_date")
    return (0 if d is not None else 1, -d.toordinal() if d is not None else 0, -int(entry["id"]))


def assembler_dossier(
    *,
    entries: dict[int, dict[str, Any]],
    liens: Iterable[Lien],
    plafond: int,
    total_courantes: Optional[int] = None,
) -> Dossier:
    """Range les pièces par point instruit, la plus récente devant, puis joint le reste. PUR.

    `entries` est le corpus COURANT du ticker, `{id: {id, source_date, ...}}`. `liens` est ce que
    `question_coverage` dit du rattachement point ↔ pièce, restreint à UN framework en UNE version.

    Un lien qui pointe une entry absente d'`entries` est ignoré, pas fatal : l'index couvre aussi
    des entries supersédées ou d'un autre ticker, et un lien mort ne doit pas vider le dossier.
    Une chemise dont AUCUNE pièce n'est présente n'existe pas — elle ne se fabrique pas vide.

    `total_courantes` sert à dire la troncature quand l'appelant a compté le dossier complet avant
    d'en charger une partie. Absent, il vaut `len(entries)`.
    """
    if plafond < 1:
        raise ValueError(
            f"plafond={plafond} : un dossier vide n'est pas une mesure, c'est une panne (#25)"
        )

    par_point: dict[tuple[str, str], list[int]] = {}
    for question_id, ingredient_id, entry_id in liens:
        if entry_id not in entries:
            continue
        par_point.setdefault((question_id, ingredient_id), []).append(entry_id)

    chemises: list[Chemise] = []
    for (question_id, ingredient_id), ids in sorted(par_point.items()):
        # `dict.fromkeys` plutôt que `set` : l'index peut porter deux fois le même lien, et on veut
        # un ordre déterministe avant le tri par fraîcheur.
        uniques = sorted(dict.fromkeys(ids), key=lambda i: _rang(entries[i]))
        chemises.append(
            Chemise(
                question_id=question_id,
                ingredient_id=ingredient_id,
                en_vigueur=uniques[0],
                anterieures=tuple(uniques[1:]),
            )
        )

    # Une même pièce peut être en vigueur sur DEUX points (mesuré : `lignes_de_credit_non_tirees`
    # est réclamé par qf_4 et par qf_7, et une seule entry les couvre). Elle ne compte qu'une fois
    # dans le dossier, mais elle ouvre bien deux chemises.
    en_vigueur: list[int] = list(dict.fromkeys(c.en_vigueur for c in chemises))
    rattachees = {i for c in chemises for i in (c.en_vigueur, *c.anterieures)}
    hors_index = sorted(
        (i for i in entries if i not in rattachees), key=lambda i: _rang(entries[i])
    )

    plafond_insuffisant = len(en_vigueur) > plafond
    place_restante = max(0, plafond - len(en_vigueur))
    hors_index_retenues = tuple(hors_index[:place_restante])

    retenues = list(dict.fromkeys([*en_vigueur, *hors_index_retenues]))
    laissees_dehors = tuple(sorted(set(entries) - set(retenues)))

    return Dossier(
        entries={i: entries[i] for i in retenues},
        chemises=tuple(chemises),
        hors_index_retenues=hors_index_retenues,
        laissees_dehors=laissees_dehors,
        total_courantes=int(total_courantes if total_courantes is not None else len(entries)),
        plafond=plafond,
        plafond_insuffisant=plafond_insuffisant,
        collecte={i: e["created_at"] for i, e in entries.items() if e.get("created_at") is not None},
    )


_SQL_ENTRIES = """
    SELECT id, title, content, source_type, source_date, reliability_tier, nature, created_at
      FROM knowledge_entries
     WHERE ticker_id = $1 AND superseded_by IS NULL
"""

_SQL_LIENS = """
    SELECT qc.question_id, qc.ingredient_id, qc.entry_id
      FROM question_coverage qc
      JOIN knowledge_entries e ON e.id = qc.entry_id
     WHERE qc.framework_id = $1 AND qc.framework_version = $2
       AND e.ticker_id = $3 AND e.superseded_by IS NULL
"""


async def charger_dossier(
    conn,
    *,
    ticker_id: str,
    framework_id: str,
    framework_version: str,
    plafond: int,
) -> Dossier:
    """Lit le corpus courant et l'index de couverture, puis délègue l'assemblage à la fonction pure.

    ⚠️ Le corpus est chargé ENTIER, sans `LIMIT` : c'est l'assemblage qui tranche, et il ne peut pas
    trancher juste sur un échantillon que la base a déjà écrémé par la date. Un `LIMIT` ici
    rétablirait exactement le défaut que ce module ferme, une couche plus bas et hors de portée des
    gardes.
    """
    rows = await conn.fetch(_SQL_ENTRIES, ticker_id)
    entries = {r["id"]: dict(r) for r in rows}
    liens_rows = await conn.fetch(_SQL_LIENS, framework_id, framework_version, ticker_id)
    liens: Sequence[Lien] = [
        (r["question_id"], r["ingredient_id"], r["entry_id"]) for r in liens_rows
    ]
    return assembler_dossier(entries=entries, liens=liens, plafond=plafond)
