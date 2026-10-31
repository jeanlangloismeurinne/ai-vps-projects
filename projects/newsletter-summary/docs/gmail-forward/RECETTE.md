# Recette

## A. Faite en local (faux script, contrat rejoué)

| Lot | Commande | Résultat 2026-10-31 |
| --- | --- | --- |
| Script Apps Script (harnais Node) | `apps-script/test` | 31/31 ; 28/28 mutations rouges |
| Backend (G0–G17) | `checks/check_gmail_rules.py` (via `checks/run_all.sh`) | vert ; 24/24 mutations rouges (`checks/mutations.py`) |
| Pages Hub (H1–H10) | `hub/checks/check_gmail_pages.py` | vert ; 16/16 mutations rouges (`hub/checks/mutations_gmail.py`) |

Limite : le faux script rejoue le contrat de la spec, pas Gmail. Il ne prouve pas que Gmail se comporte ainsi.

## B. À faire par vous, sur un compte Gmail de TEST (pas le compte réel)

Suivre `TUTORIEL.md`, puis constater et noter ci-dessous le résultat réel.

| # | Hypothèse | Test | Résultat |
| --- | --- | --- | --- |
| 6 | `gmail.settings.basic` suffit (lister adresses, créer filtre + transfert, supprimer) | `authorize`, puis ping et liste des adresses | |
| 7 | `criteria.from` accepte `@domaine.tld` | règle domaine entier, mail réel de ce domaine transféré | |
| 8 | URL anonyme sans connexion Google ; délai d'un appel | ping depuis le Hub ; noter la durée | |
| 9 | Quotas Apps Script et limites Gmail | noter ce que l'écran Exécutions et Gmail indiquent | |
| 10 | Forme des erreurs Gmail (`removeFilter_`) | supprimer un filtre déjà supprimé à la main | |
| — | `negatedQuery` accepte `from:(@a OR @b)`, et sa longueur avec un `DENY_FROM` long | règle sans expéditeur, mail d'un domaine refusé | |
| — | Tests de sécurité du script (tableau « Script » de `SPEC.md`) | un par un, y compris `panic()` | |
| — | Cycle complet : créer, modifier, désactiver, réactiver, supprimer | filtre Gmail cohérent à chaque étape + journal | |
| — | Utilisation sur téléphone | formulaire et liste sans zoom horizontal | |
| — | `.resend.app` accepté par 3–4 vraies newsletters | s'y abonner avec l'alias, vérifier la réception | |

## C. Mise en service (hors périmètre de ce chantier)

Compte réel : à décider après B. Contenu initial de `DENY_FROM` à fournir par vous.
