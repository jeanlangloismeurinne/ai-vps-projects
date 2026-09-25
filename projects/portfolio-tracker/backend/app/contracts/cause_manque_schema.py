"""La CAUSE d'un manque de collecte — pourquoi le système n'a pas pu obtenir une information
(chantier v3, lot 6 maillon 2 — migration 047).

ARBITRAGE DU COMITÉ (2026-09-25, n°3)
-------------------------------------
Un dossier complet est l'état NORMAL : le système va lui-même chercher ce qui manque avant de
présenter le dossier. Quand il n'y arrive pas, l'utilisateur veut le savoir EN TÊTE, avec ce qui
manque et **pourquoi le système n'a pas pu l'obtenir** — « recherche épuisée, source indisponible,
question sans source possible ». Ce vocabulaire EST cette phrase, mot pour mot.

Ce que ferait un vrai fonds : l'analyste qui rend un dossier incomplet dit au comité « je n'ai pas
trouvé » (la donnée n'est pas publiée), « je n'ai pas pu accéder » (base de données en panne,
temps épuisé — ça se relance) ou « ça n'existe pas pour cette société » (question à reformuler).
Les trois appellent trois suites différentes ; les confondre, c'est relancer une recherche qui ne
peut rien donner, ou abandonner une donnée qu'une simple relance aurait ramenée.

DÉTENTEUR DE LA CAUSE = LE PRODUCTEUR DE L'ÉCHEC, JAMAIS LE LECTEUR
-------------------------------------------------------------------
La cause est déclarée par l'exécuteur au moment où il échoue (`collecte_executor`) — c'est le seul
endroit qui SAIT si le search-worker a répondu « rien » ou s'il a été coupé par le chien de garde.
La relire après coup dans la prose du motif serait un jumeau du producteur, divergent au premier
motif reformulé (`feedback_correctif_regle_jumeaux`). Le motif reste la prose pour l'humain ; la
cause est la structure pour l'écran.
"""
from __future__ import annotations

from typing import Literal

# L'exécuteur a TENTÉ la ligne et elle a échoué : il sait lequel des deux.
CauseEchecCollecte = Literal[
    "recherche_epuisee",      # la source a été lue, la donnée n'y est pas publiée
    "source_indisponible",    # la source n'a pas pu être lue (panne, temps épuisé) : à relancer
]

# Un mandat du collecteur porte l'une des trois. La troisième ne vient pas d'un échec : c'est le
# traducteur qui a su, AVANT toute collecte, qu'aucune source ne produit l'ingrédient (`inobtenable`).
CauseManqueCollecte = Literal[
    "recherche_epuisee",
    "source_indisponible",
    "sans_source_possible",
]

CAUSE_INOBTENABLE: CauseManqueCollecte = "sans_source_possible"
