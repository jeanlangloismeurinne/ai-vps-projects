#!/usr/bin/env bash
# TEST NÉGATIF de `check_etude_api.py` — l'écran de la société mise à l'étude (M2 B12, M3 K12). Chaque
# mutation casse une promesse de la route ou de la vue et exige exit≠0 + FAIL sur l'assert NOMMÉ +
# bilan atteint (harnais `_negatif.sh`). Le check dépend de FastAPI : il tourne dans l'IMAGE.
#   bash checks/negatif_etude_api.sh
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_etude_api.py"
API="app/api/etude_v2.py"
COEUR="app/modules/etude/coeur.py"
REF="app/modules/etude/referentiel.json"

mutations=(
# [E1] la vue ne sert plus la collecte.
"$API¦            \"collecte\": await R.vue_ecran(monde.recueil, emetteur),¦            \"collecte\": {},¦[E1] ni collecte ni lecture"
# [E2] le corps de la mise à l'étude accepte un auteur : ce qui est signé se déclarerait.
"$API¦    motif: str¦    motif: str\n    par: str = \"\"\n    le: str = \"\"¦[E2] un corps qui porte par est refusé"
# [E2] l'étude est signée d'un autre que l'utilisateur.
"$API¦par=T.UTILISATEUR, motif=corps.motif¦par=\"gerant\", motif=corps.motif¦[E2] l'étude est signée de l'utilisateur"
# [E2] l'étude est datée d'autre chose que du jour du serveur.
"$API¦motif=corps.motif, le=_aujourdhui())¦motif=corps.motif, le=\"2001-01-01\")¦[E2] l'étude est signée de l'utilisateur"
# [E3] l'acte reste dans le vocabulaire du chef de dossier.
"$REF¦\"lecture:collecte\": \"Valider¦\"lecture:autre\": \"Valider¦[E3] l'acte qui vous revient : en mots de gérant"
# [E3] les attentes perdent leur libellé.
"$COEUR¦            x[\"libelle\"] = libelle_acte(x[\"cle\"], x[\"acte\"]) if x[\"acte\"] else \"\"¦            x[\"libelle\"] = \"\"¦[E3] chaque attente d'un acte porte son libellé"
# [E3] le journal des passages n'est plus servi le plus récent d'abord.
"$COEUR¦        \"passages\": list(reversed(passages))¦        \"passages\": list(passages)¦[E3] les passages qui ont fait quelque chose"
# [E4] un geste refusé devient une erreur muette du serveur.
"$API¦            raise HTTPException(status_code=409, detail=str(e))¦            raise HTTPException(status_code=500, detail=\"erreur\")¦[E4] acte non attendu : 409"
# [E4] l'acte enregistré n'est plus celui que vous avez envoyé.
"$API¦T.enregistrer_acte(m, emetteur, corps.cle,¦T.enregistrer_acte(m, emetteur, \"lecture:collecte\",¦[E4] acte non attendu : 409"
# [E6] la lecture des lignes n'est plus bornée.
"$API¦        fin = debut + LIGNES_MAX - 1¦        fin = None¦[E6] les lignes d'un document lu se lisent, bornées"
# [E6] un document sans lecture en lignes est servi comme s'il en avait.
"$API¦if l.empreinte == empreinte and l.statut == K.LUE), None)¦if l.empreinte == empreinte), None)¦[E6] un document sans lecture en lignes : 404"
# [E7] la route importe l'intérieur d'un module.
"$API¦from app.modules.etude import contrat as T¦from app.modules.etude import contrat as T\nfrom app.modules.etude import coeur  # noqa: F401¦[E7] seuls les \`contrat\` sont importés"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
