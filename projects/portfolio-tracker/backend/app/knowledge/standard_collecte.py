"""
Le STANDARD DE COLLECTE d'une pièce — détenteur unique de « cette pièce a-t-elle été écrite au standard
courant ? » (#127, arbitrage de l'utilisateur du 2026-10-15).

Ce que ferait un fonds : pendant la mise au point de la méthode, il ne réécrit pas ses dossiers à chaque
règle nouvelle ; il DATE chaque note par le standard sous lequel elle a été instruite, et refait tout le
dossier une fois la méthode figée (ici : le premier passage du test A11). Une note d'un standard antérieur
reste affichée, marquée « à refaire au standard courant » — et on ne remonte jamais son fil pour en tirer
une erreur à corriger : elle est provisoire par définition.

Le standard courant est celui de #126 : une fiche tirée d'un document porte ses extraits littéraux,
vérifiés. Une pièce est AU STANDARD si elle n'est pas une fiche de document rédigée par le collecteur, ou si
elle en est une à extraits :
  · produite par le CODE — un producteur déterministe (socle, comptes EDGAR, ratios, cours, taux de base,
    appariement) pose toujours `content_structured.metric` ; aucune fiche du collecteur n'en porte
    (mesuré le 2026-10-15 sur toute la base ; depuis #126, impossible par construction : les valeurs
    structurées du collecteur partent avec sa lecture) ;
  · lecture d'un dépôt, texte déposé tel quel (`lecture_du_depot`, #106) ;
  · pas une fiche de document : synthèse ou lecture d'agent (`agent_synthesis`), aveu de mémoire
    (`llm_memory`) — leur rang dit déjà ce qu'elles valent ;
  · fiche du collecteur dont le texte est composé de ses extraits (`PREFIXE_FICHE`).
Tout le reste est une fiche du collecteur au standard ANTÉRIEUR.

Recalculé à la LECTURE, jamais stocké (#53) : la marque disparaît d'elle-même quand la note est refaite.
"""
from __future__ import annotations

from typing import Iterable, Optional

# Le début du texte d'une fiche à extraits, composé par le worker (#126). Détenteur unique : le worker
# l'écrit, ce module le reconnaît.
PREFIXE_FICHE = "Extraits littéraux du document"
STANDARD_COURANT = "fiches à extraits littéraux vérifiés (#126, 2026-10-15)"
# Ce que la règle lit d'une ligne de `knowledge_entries`, à ajouter aux SELECT de ses lecteurs.
COLONNES_SQL = "tags, content_structured->>'metric' AS metric, left(content, 80) AS debut_contenu"

_SANS_DOCUMENT = frozenset({"agent_synthesis", "llm_memory"})


def piece_au_standard(*, source_type: Optional[str], tags: Optional[Iterable[str]],
                      metric: Optional[str], debut_contenu: Optional[str]) -> bool:
    """True si la pièce est au standard courant ; False = fiche du collecteur au standard antérieur."""
    if source_type in _SANS_DOCUMENT:
        return True
    if metric:
        return True
    if "lecture_du_depot" in (tags or ()):
        return True
    return (debut_contenu or "").startswith(PREFIXE_FICHE)
