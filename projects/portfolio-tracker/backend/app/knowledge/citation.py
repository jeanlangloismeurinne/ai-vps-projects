"""
La citation littérale — DÉTENTEUR UNIQUE de « ce passage figure-t-il mot pour mot dans ce texte ? » (#90, #126).

Deux lecteurs : la note flash (#90 — chaque type d'événement se cite par un passage du dépôt) et le
collecteur web (#126 — une fiche de lecture porte des extraits du document, vérifiés contre le texte que
les outils ont réellement rapporté). Une règle recopiée re-diverge au correctif suivant (#46) : la
normalisation vit ici, et seulement ici.

La normalisation est MINIMALE : forme Unicode, guillemets et tirets typographiques, espaces, casse.
Rien d'autre — une paraphrase, une traduction, un chiffre arrondi ne doivent pas passer.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable, Optional

_GUILLEMETS = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"',
                             "–": "-", "—": "-", " ": " "})

# Un extrait plus court ne prouve rien : « revenue » figure dans tout document financier. Le seuil
# exige au moins un bout de phrase — ce qui rend l'extrait discriminant sans exiger une phrase entière.
EXTRAIT_MIN_CARS = 20


def normaliser(texte: str) -> str:
    """Forme comparable d'un texte. Cf. docstring du module : rien au-delà de la typographie."""
    t = unicodedata.normalize("NFKC", texte).translate(_GUILLEMETS)
    return re.sub(r"\s+", " ", t).strip().casefold()


def extrait_introuvable(extraits: Iterable[str], textes: Iterable[str]) -> Optional[str]:
    """Le PREMIER extrait qui ne figure mot pour mot dans aucun des `textes`, ou None si tous y sont.

    Rend l'extrait fautif, jamais un booléen : un refus qui ne dit pas sur quoi condamne le producteur
    à deviner (#63/#78). Sans texte de référence, tout extrait est introuvable — on ne vérifie pas
    contre rien.
    """
    corpus = [normaliser(t) for t in textes if t]
    for e in extraits:
        n = normaliser(e)
        if not any(n in c for c in corpus):
            return e
    return None
