# Comptes — `app/modules/comptes/`

Module M4 du plan `roadmap/V3/07-avant-comite.md`, **pas encore ouvert**. Ouvert au registre le
2026-11-21 avec son seul besoin (M3 §2, point 1) : ce qu'il demande pour ouvrir un dossier, en donnée
dans `referentiel.json` — le dernier rapport annuel et les données comptables structurées qui
l'accompagnent (arbitrage du 2026-11-21). Le reste (trimestriels, exercices antérieurs) sera demandé
par M4 au fil de son travail.

`contrat.besoins_initiaux()` rend ces besoins ; le déclencheur (`app/modules/etude/`) les rassemble
avec ceux des autres modules consommateurs. Garde : `checks/check_etude.py` [K11] (« le besoin réel des
comptes »), rougie par `negatif_etude.sh`.
