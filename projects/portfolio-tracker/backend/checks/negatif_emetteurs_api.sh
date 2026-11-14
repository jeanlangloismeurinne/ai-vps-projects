#!/usr/bin/env bash
# TEST NÉGATIF de `check_emetteurs_api.py` — l'écran du module M1 (ligne A13 de
# `roadmap/V3/M1-fiche-emetteur.md`). Chaque mutation casse une promesse de la route et exige exit≠0
# + FAIL sur l'assert NOMMÉ + bilan atteint (harnais `_negatif.sh`).
#
# Le check dépend de FastAPI et pydantic : il tourne dans l'IMAGE de production (`portfolio-backend`),
# jamais sur l'hôte par défaut. Répétition hors VPS seulement : `HOTE_SI_SANS_CONTENEUR=1 bash …`
# (verdict indicatif : versions de l'hôte).
#   bash checks/negatif_emetteurs_api.sh
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_emetteurs_api.py"
API="app/api/emetteurs_v2.py"

mutations=(
# [P2] le corps d'une fiche accepte un auteur ou une date : ce qui est signé se déclarerait.
"$API¦    model_config = ConfigDict(extra=\"forbid\")¦    model_config = ConfigDict(extra=\"ignore\")¦[P2] le PUT refuse auteur"
# [P3] la fiche est datée d'autre chose que du jour du serveur.
"$API¦motif=corps.motif, le=_aujourdhui(), pays=corps.pays,¦motif=corps.motif, le=\"2001-01-01\", pays=corps.pays,¦[P3] fiche : date du serveur"
# [P4] un émetteur sans fiche est servi comme une fiche vide.
"$API¦            raise HTTPException(status_code=404, detail=f\"Aucune fiche n'existe pour \`{emetteur}\`.\")¦            return {}¦[P4] émetteur sans fiche : 404 qui le nomme"
# [P6] un refus du registre devient une erreur muette du serveur.
"$API¦    return HTTPException(status_code=409, detail=str(e))¦    return HTTPException(status_code=500, detail=\"erreur\")¦[P6] révoquer une source non admise"
# [P5] la révocation perd son motif en route : le registre la refuse.
"$API¦                    auteur=contrat.UTILISATEUR, motif=corps.motif, le=_aujourdhui())¦                    auteur=contrat.UTILISATEUR, motif=\"\", le=_aujourdhui())¦[P5] révoquer rend le rang"
# [P7] une nature d'information inconnue est servie comme une réponse.
"$API¦        raise HTTPException(status_code=422, detail=str(e))¦        return {\"admise\": False}¦[P7] nature inconnue : 422"
# [P8] la route importe l'intérieur du module.
"$API¦from app.modules.emetteurs import contrat¦from app.modules.emetteurs import contrat\nfrom app.modules.emetteurs import regles  # noqa: F401¦[P8] aucun import de \`regles\`"
# [P9] l'état du dossier n'est plus lu chez le chef de dossier.
"$API¦        return lire_etat(d, emetteur).vers_dict()¦        return {}¦[P9] état du dossier vierge"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
