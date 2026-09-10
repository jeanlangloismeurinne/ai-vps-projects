"""Le corpus tel qu'il était AVANT la 036 — détenteur unique du pointeur et de l'avertissement.

POURQUOI CE FICHIER EXISTE
---------------------------
Cinq mesureurs ponctuels (`mesure_conflits_capacite5`, `qualif_couples_capacite5`,
`ligne_de_base_frameworks`, `reconcilier_vocabulaires`, `mesure_ingredients_capacite5`) ont produit
des chiffres qui sont aujourd'hui cités dans les décisions du projet — c'est le cas de « 8 postes
servent 4 des 33 ingrédients essentiels, 3 ne répondent à aucune » (#58). Ces chiffres ont été
mesurés sur un corpus qui portait `covers`, `is_deleted` et les six autres colonnes que la 036 a
retirées.

La 036 n'a rien détruit : elle a déplacé les 15 tables V2 vers le schéma `archive_v2` par
`SET SCHEMA`. Le corpus mesuré existe donc encore, à l'identique, à cette adresse. Y pointer ces
outils les garde **rejouables**, ce qui est la seule façon de vérifier une affirmation citée
plutôt que de la croire (`feedback_verifier_contre_api_reelle`). Les réécrire sur le schéma
`public` en aurait fait autre chose : un mesureur réécrit entre deux mesures ne mesure plus rien.

⚠️ CE QU'ILS NE MESURENT PLUS
------------------------------
L'ÉTAT COURANT. `archive_v2` est figé au 2026-09-10 : ces outils rendront éternellement les mêmes
nombres, et c'est exactement ce qu'on leur demande. Lire l'un d'eux comme une photographie du
corpus vivant serait le mode de panne de `feedback_corpus_sans_horloge` — un fait juste à sa date,
décrivant un monde révolu. Chacun l'imprime en tête de sa sortie, par `bandeau()`, plutôt que de le
laisser dans une docstring que personne ne relit au moment de lire les nombres.

Un mesureur de l'état COURANT ne s'écrit pas ici : il se pose sur `public`, sans colonne retirée.
"""
from __future__ import annotations

SCHEMA = "archive_v2"

# Les mesureurs interpolent ce nom dans leur SQL. Il n'est pas paramétrable : leur corpus n'est
# pas un choix d'exécution, c'est ce qui définit ce qu'ils mesurent.
ENTRIES = f"{SCHEMA}.knowledge_entries"

AVERTISSEMENT = (
    f"⚠️ MESURE HISTORIQUE — corpus `{ENTRIES}`, figé par la migration 036 au 2026-09-10.\n"
    "   Ces nombres sont ceux qui ont fondé les décisions du projet ; ils ne décrivent PAS l'état\n"
    "   courant de la base et ne bougeront plus. Pour l'état courant, écrire un mesureur sur\n"
    "   `public`, qui ne porte plus les colonnes retirées."
)


def bandeau() -> str:
    """L'avertissement, à imprimer AVANT les nombres — jamais après, ni seulement en docstring."""
    return f"{AVERTISSEMENT}\n"
