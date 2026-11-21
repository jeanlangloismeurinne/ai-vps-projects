"""La citation littérale — RÉ-EXPORT. Le détenteur unique est désormais le module M3 « Base de
connaissance » (`app/modules/connaissance/citation.py`), qui l'expose par son contrat : l'ancien code
ne lit d'un module que son contrat (garde [C5]). Ce fichier garde les imports de la note flash et du
collecteur tels quels jusqu'à leur retrait ; aucune règle ne vit ici (#46).
"""
from app.modules.connaissance.contrat import (  # noqa: F401
    CONTEXTE_MAX_CARS,
    EXTRAIT_MIN_CARS,
    etablir_extraits,
    extrait_introuvable,
    normaliser,
)
