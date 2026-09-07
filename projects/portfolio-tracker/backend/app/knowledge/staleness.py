"""Balayage de péremption — un RAPPORT, jamais un `superseded_by`.

Le trou fermé ici (2026-09-05)
------------------------------
`superseded_by` existe, il est filtré par toutes les requêtes… et **rien ne le peuple** quand un
événement postérieur contredit un fait antérieur. Sur RVMD, quatre entries actives **tier A**
disaient « aucun produit approuvé pour la vente commerciale » / « les seules entrées de trésorerie
proviennent de financements » alors que la FDA avait approuvé RASONQUE le 2026-08-26. Aucune n'est
fausse : chacune est fidèle à sa source et correctement datée. Elles sont **périmées** — et la
porte de complétude (#29), qui compte les champs *couverts*, est structurellement **aveugle à la
péremption** : elle aurait conclu à un socle prêt.

Pourquoi ce module n'écrit rien
-------------------------------
Décider qu'un fait est remplacé est un **jugement sémantique**. L'automatiser reviendrait à donner
au modèle (ou pire, à une heuristique de dates) une voix sur ce que le corpus affirme — exactement
le desserrage refusé en #29 et dans `feedback_optional_schema_gate`. Le module produit donc une
**liste à re-vérifier**, ordonnée et motivée ; la décision reste humaine, et son point d'atterrissage
est `superseded_by` (ou `is_outdated`) écrit à la main.

Trois états, encore (#25/#44)
-----------------------------
Une entry active est classée :

  • ``suspecte``      — `source_date` STRICTEMENT antérieure à l'événement matériel le plus récent ;
  • ``posterieure``   — datée à/après l'événement : elle a pu en tenir compte ;
  • ``non_datee``     — `source_date IS NULL` : sa fraîcheur est **indéterminable**, ce qui n'est
    pas la même chose que fraîche. La ranger avec les `posterieure` fabriquerait du silence.

Et le rapport lui-même a un état : si le flux des événements est injoignable, il rend
``indeterminable`` avec **zéro suspecte**, en le DISANT. Un rapport vide pour cause de panne se
lirait « rien à re-vérifier » — une mesure incomplète qui écrase de la vérité (leçon §13 du
`CHANTIER_OUTILLAGE_DEV.md`).

La règle de classement ne vit PAS ici (F15, 2026-09-05)
-------------------------------------------------------
Ces trois classes sont le vocabulaire du RAPPORT ; la règle qui décide laquelle s'applique est
l'axe `actualité` (`knowledge/actualite.py`), détenteur unique depuis la capacité 3. Ce module
traduit, il ne recalcule pas.

Le motif est une mesure, pas une préférence de style. Tant que la partition était écrite ici, la
branche « aucun événement matériel » rangeait l'entry non datée dans `posterieures` **et** dans
`non_datees` : trois classes totalisant 4 entries pour 3 actives, et l'entry sans date comptée
parmi les fraîches — c'est-à-dire exactement ce que la docstring ci-dessus interdit. Le défaut
n'était visible ni au diff ni dans la suite de checks ; il est sorti en exécutant le producteur et
en lisant sa sortie en texte. Une règle recopiée re-diverge de sa doctrine au premier branchement.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.knowledge.actualite import classe_rapport, etat_actualite
from app.knowledge.material_events import (
    ITEM_LABELS,
    MaterialEventLookup,
    material_anchor_for_ticker,
)

logger = logging.getLogger(__name__)

# Longueur de l'extrait de `content` rapporté. Assez pour juger sans relire la base, trop court
# pour que le rapport devienne le corpus.
_EXTRAIT = 240


async def _entries_actives(conn, ticker_id: str) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        """
        SELECT id, title, content, covers, source_type, source_url, source_date,
               fiscal_period, reliability_tier, entry_type, requires_human_review
          FROM knowledge_entries
         WHERE ticker_id = $1
           AND superseded_by IS NULL
           AND COALESCE(is_deleted, FALSE) = FALSE
         ORDER BY source_date DESC NULLS LAST, id
        """,
        ticker_id,
    )
    return [dict(r) for r in rows]


def _resume_entry(row: dict[str, Any], act) -> dict[str, Any]:
    """Résumé d'une entry pour le rapport. L'écart au seuil est LU sur l'axe, jamais recalculé ici :
    c'est la même soustraction, et deux sites qui la font sont deux sites à corriger (#46)."""
    contenu = (row.get("content") or "").strip().replace("\n", " ")
    ecart = act.jours_avant_evenement if act is not None else None
    return {
        "id": row["id"],
        "titre": row.get("title"),
        "covers": list(row.get("covers") or []),
        "source_type": row.get("source_type"),
        "source_url": row.get("source_url"),
        "source_date": row["source_date"].isoformat() if row.get("source_date") else None,
        "fiscal_period": row.get("fiscal_period"),
        "tier": row.get("reliability_tier"),
        "entry_type": row.get("entry_type"),
        "requires_human_review": row.get("requires_human_review"),
        "jours_avant_evenement": ecart,
        # L'axe est reporté TEL QUEL à côté du vocabulaire du rapport : le lecteur voit sur quelle
        # règle la classe repose, et un futur consommateur (capacité 4) n'a pas à la redériver.
        "actualite": act.etat if act is not None else None,
        "motif_actualite": act.motif if act is not None else None,
        "extrait": contenu[:_EXTRAIT] + ("…" if len(contenu) > _EXTRAIT else ""),
    }


def _partition(entries: list[dict[str, Any]], lookup: MaterialEventLookup
               ) -> dict[str, list[dict[str, Any]]]:
    """Range les entries dans les trois classes du rapport, via l'axe `actualité`.

    Une entry tombe dans EXACTEMENT une classe — c'est ce que garantit le passage par un état
    unique. La version précédente évaluait deux prédicats indépendants et pouvait donc en placer
    une dans deux classes (F15).
    """
    classes: dict[str, list[dict[str, Any]]] = {
        "suspectes": [], "posterieures": [], "non_datees": [],
    }
    for r in entries:
        act = etat_actualite(source_date=r.get("source_date"), ancre=lookup)
        classes[classe_rapport(act.etat)].append(_resume_entry(r, act))
    return classes


def _motif(lookup: MaterialEventLookup) -> str:
    """Phrase qui dit POURQUOI ces entries sont suspectes — le rapport doit être lisible seul."""
    evt = lookup.event
    if evt is None:
        return ""
    items = ", ".join(
        f"{i} ({ITEM_LABELS.get(i, 'non répertorié')})" for i in evt.items_substantiels
    )
    base = (
        f"Un événement matériel est survenu le {evt.event_date.isoformat()} "
        f"({evt.form}, déposé le {evt.filing_date.isoformat()})"
    )
    if items:
        base += f" — items {items}"
    return (
        base + ". Les entries ci-dessous sont ANTÉRIEURES : elles restent exactes à leur date, "
        "mais peuvent décrire un état révolu. À re-vérifier, pas à supprimer."
    )


async def balayage_peremption(conn, ticker_id: str) -> dict[str, Any]:
    """Rapport de péremption pour un émetteur. **N'écrit rien en base.**

    Le seuil est la date de l'ÉVÉNEMENT (`reportDate`), pas celle du dépôt : le monde change quand
    le fait se produit. La date de dépôt est rapportée à côté pour que le délai reste lisible.
    """
    lookup = await material_anchor_for_ticker(conn, ticker_id)
    entries = await _entries_actives(conn, ticker_id)
    total = len(entries)

    if lookup.status == "unavailable":
        return {
            "ticker_id": ticker_id,
            "statut": "indeterminable",
            "raison": lookup.raison,
            "ecrit_en_base": False,
            "entries_actives": total,
            "seuil": None,
            "evenement": None,
            "suspectes": [],
            "posterieures": [],
            "non_datees": [],
            "avertissement": (
                "Le flux des événements matériels est injoignable : ZÉRO suspecte ici ne signifie "
                "PAS que rien n'est périmé, seulement que le balayage n'a pas pu être fait."
            ),
        }

    if lookup.status == "none":
        return {
            "ticker_id": ticker_id,
            "statut": "aucun_evenement",
            "ecrit_en_base": False,
            "entries_actives": total,
            "seuil": None,
            "evenement": None,
            # ⚠️ Partition par l'AXE, pas par deux prédicats indépendants : une entry non datée
            # reste `non_datee` même quand aucun événement n'existe. La classer `posterieure`
            # (« elle a pu en tenir compte ») serait un silence — il n'y a rien dont elle aurait
            # pu tenir compte, et surtout on ignore de quand elle date. C'était F15.
            **_partition(entries, lookup),
            "avertissement": (
                "Cet émetteur n'a publié aucun 8-K/6-K : aucun événement matériel ne peut périmer "
                "le corpus. Les dépôts périodiques restent couverts par l'ancre du search-worker."
            ),
        }

    evt = lookup.event
    assert evt is not None
    seuil = evt.event_date

    classes = _partition(entries, lookup)
    suspectes = classes["suspectes"]
    posterieures = classes["posterieures"]
    non_datees = classes["non_datees"]

    # Le plus ancien d'abord : l'écart au seuil est l'ordre de suspicion le plus honnête dont on
    # dispose sans juger le CONTENU (ce que ce module s'interdit).
    suspectes.sort(key=lambda e: (-(e["jours_avant_evenement"] or 0), e["id"]))

    return {
        "ticker_id": ticker_id,
        "statut": "balaye",
        "ecrit_en_base": False,
        "entries_actives": total,
        "seuil": seuil.isoformat(),
        "motif": _motif(lookup),
        "evenement": {
            "form": evt.form,
            "event_date": evt.event_date.isoformat(),
            "filing_date": evt.filing_date.isoformat(),
            "items": list(evt.items),
            "items_libelles": evt.libelle_items(),
            "url": evt.url,
        },
        "evenements_recents": [
            {"form": e.form, "event_date": e.event_date.isoformat(),
             "filing_date": e.filing_date.isoformat(), "items": list(e.items),
             "items_libelles": e.libelle_items(), "url": e.url}
            for e in lookup.recents
        ],
        "suspectes": suspectes,
        "posterieures": posterieures,
        "non_datees": non_datees,
        "champs_touches": sorted(
            {c for e in suspectes for c in e["covers"]}
        ),
    }
