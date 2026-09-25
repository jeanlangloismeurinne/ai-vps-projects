"""L'ORDRE DU JOUR du comité — les blocs du `ResearchMemo`, DÉRIVÉS et jamais retapés (#46).

POURQUOI CE FICHIER EXISTE
--------------------------
Trois consommateurs ont besoin de la même liste, et chacun était en train de s'en écrire une :

  · `tools/reconcilier_vocabulaires.py` la tenait en dur (`BLOCS = {"business_model": S.BusinessModel,
    …}`) — six noms recopiés à la main ;
  · le pont des définitions doit refuser un `bloc_memo` qui ne désigne aucun bloc réel ;
  · le projecteur (`agents/v2/projection_memo.py`) doit produire UNE rubrique par bloc, toujours les
    six, sans qu'aucune ne puisse manquer en silence.

Trois exemplaires d'accord le jour où on les écrit sont trois exemplaires divergents au correctif
suivant (`feedback_correctif_regle_jumeaux`). La liste vit ici seule, et elle est **dérivée** de
`ResearchMemo.model_fields` : un bloc renommé change le résultat au lieu de le laisser inchangé.

CE QUI SÉPARE UN BLOC D'UN MÉTA-CHAMP, ET POURQUOI ÇA S'ÉCRIT
--------------------------------------------------------------
Un bloc porte de la connaissance sur l'ÉMETTEUR ; un méta-champ porte une propriété du mémo
lui-même. `META_MEMO` les énumère AVEC leur motif, parce que la dérivation seule les distinguerait
par leur forme (`Literal`, `list[...]`) — et une distinction par la forme accepterait en silence un
méta-champ neuf qui se trouverait typé comme un bloc. `check_memo_projete.py` §1 exige que
`BLOCS_MEMO ∪ META_MEMO` recouvre EXACTEMENT `ResearchMemo.model_fields` : un champ neuf qui n'est
ni l'un ni l'autre fait rougir, au lieu de disparaître de l'ordre du jour.

⚠️ CE FICHIER NE PORTE AUCUN SEUIL ET AUCUN DÉCOMPTE. Pas de « 6 » écrit en dur : un mesureur qui
compare un décompte à sa propre constante mesure sa constante (4ᵉ faux vert). Les asserts portent
sur des PROPRIÉTÉS (recouvrement exact, non-vacuité), jamais sur un nombre.
"""
from __future__ import annotations

from typing import get_origin

from .analysis_v2_schemas import ResearchMemo, Strict

__all__ = ["BLOCS_MEMO", "META_MEMO", "feuilles_memo"]

# Les champs du mémo qui ne sont PAS des blocs de connaissance, chacun avec la raison qui l'exclut.
# Énumérés, jamais déduits de leur type : cf. en-tête.
META_MEMO: dict[str, str] = {
    "schema_version": "version du contrat — une propriété du mémo, pas de l'émetteur",
    "posture": "verrou Q2 (aucun verdict dans le mémo) — une propriété du mémo",
    "incertitudes_bloquantes": "transverse aux blocs : une incertitude n'appartient à aucun chapitre",
    # ⚠️ Ce motif disait « idem ». Mesuré par `check_memo_projete` §1 : un renvoi à la ligne d'au
    # dessus n'est pas une raison, c'est l'économie d'une raison — et il se relit comme un oubli.
    "incertitudes_investissables": "transverse aussi, mais pour l'autre moitié du couple : une "
                                   "incertitude qu'on ACCEPTE de porter est une propriété de la "
                                   "thèse, jamais d'un chapitre",
}


def _deriver_blocs() -> dict[str, type]:
    """Les blocs, lus dans le contrat lui-même. Un `get_origin` non nul écarte `Literal[...]` et
    `list[...]` sans jamais les nommer — c'est la forme qui les écarte, et `META_MEMO` qui dit
    pourquoi ils sont hors ordre du jour."""
    out: dict[str, type] = {}
    for nom, champ in ResearchMemo.model_fields.items():
        annotation = champ.annotation
        if get_origin(annotation) is not None:
            continue
        if isinstance(annotation, type) and issubclass(annotation, Strict):
            out[nom] = annotation
    return out


# L'ordre du jour. Dict ordonné comme le contrat déclare ses champs : c'est l'ordre dans lequel le
# comité lit ses chapitres, et il n'a pas à être retrié ailleurs.
BLOCS_MEMO: dict[str, type] = _deriver_blocs()


def feuilles_memo() -> set[str]:
    """Les feuilles du `ResearchMemo` (`bloc.champ`), lues dans le contrat — jamais recopiées.

    `source_entry_refs` est écarté : c'est la référence d'un bloc, pas une connaissance à fonder.
    Déplacée ici depuis `tools/reconcilier_vocabulaires.py` le 2026-09-24 (lot 5) — elle dépendait
    de la liste des blocs, donc elle appartient à son détenteur.
    """
    out: set[str] = set()
    for prefixe, cls in BLOCS_MEMO.items():
        for nom in cls.model_fields:
            if nom == "source_entry_refs":
                continue
            out.add(f"{prefixe}.{nom}")
    return out
