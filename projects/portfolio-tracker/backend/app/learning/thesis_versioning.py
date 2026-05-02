# TODO (Priorité 3) : Implémenter le version control des thèses.
# Quand Régime 3 révise des hypothèses :
# 1. Archiver la version actuelle (is_current = FALSE, invalidated_at = NOW())
# 2. Créer une nouvelle version (version + 1) avec les paramètres révisés
# 3. Les hypothèses originales (H1-H7 de la thèse v1) restent immuables
# Cf. spec section 20.

async def archive_and_create_new_version(position_id: str, revised_data: dict):
    raise NotImplementedError("Version control des thèses non encore implémenté — priorité 3")
