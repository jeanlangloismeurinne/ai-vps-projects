# Fiche de l'émetteur et sources — `app/modules/emetteurs/`

Contrat **1.1.0** depuis le 2026-11-14 (sources en suspens). Module M1 du plan `roadmap/V3/07-avant-comite.md`. **État : construit et prouvé hors ligne et sur une
base locale le 2026-11-13 ; PAS ENCORE ACCEPTÉ** — l'acceptation se passe sur NVDA et RVMD, sur le VPS
(lignes A13 à A15 de `roadmap/V3/M1-fiche-emetteur.md`, qui porte aussi le tri de l'ancien code).

*Ce que ferait un vrai fonds* : la direction de la recherche tient une fiche par société et la liste
des sources qu'elle tient pour fiables ; chaque admission est datée et motivée ; une source retirée
fait relire ce qui s'appuyait dessus.

## Ce qu'il rend

La **fiche d'un émetteur** (`contrat.Fiche`, version `1.0.0`), lue par une seule fonction :
`contrat.lire_fiche(depot, emetteur)`. Elle dit : l'identifiant maison, la raison sociale, le pays,
les cotations et les références externes (toutes **facultatives**, leur nom est une donnée), où la
société publie, sa spécialité (vide = parcours généraliste), la révision en vigueur avec sa date, son
auteur et son motif — et les **sources admises et révoquées qui valent pour elle** (portée générale,
sa spécialité, elle-même).

Sur une fiche, sans rien lire d'autre : `contrat.qualifier(fiche, adresse, nature)` (cette adresse
est-elle une source admise pour cette nature d'information, à quel niveau, pourquoi) et
`contrat.pieces_a_signaler(fiche, origines)` (les pièces qui s'appuient sur une source révoquée).

## Les gestes

| Geste | Ce qu'il fait | Refuse |
|---|---|---|
| `etablir_fiche` | Ajoute un titre, ou corrige sa fiche : une révision de plus | identifiant, adresse ou genre de lieu mal formé ; pas de motif, de date, de signature ; fiche identique |
| `admettre_source` | Admet un domaine, pour des natures nommées, à un niveau, sur une portée | système sans critère écrit, au-delà du plafond ou hors des natures du critère ; rôle qui utilise les sources ; décision de l'utilisateur déjà rendue |
| `admettre_pages_investisseurs` | Le **système** admet, pour toutes les analyses, les pages de relations investisseurs d'autres sociétés trouvées dans des adresses (reconnues à leur adresse dédiée, préfixes du référentiel) ; signé `systeme:evaluateur_de_sources`, critère `relations_investisseurs_d_une_autre_societe` | rien : rend admise / déjà admise / écartée (l'utilisateur a statué en dernier) |
| `evaluer_source` | Range le jugement de l'évaluateur sur une source inconnue : le code calcule la note (part des « oui » aux questions du référentiel), l'**admet** au seuil (0,80, ≥ 3 publications, critère écrit), la met **en suspens** sinon ; l'évaluation entière part au journal | publication hors de la source, question sans réponse ou sans constat, publication en double ; rôle qui utilise les sources ; source déjà admise ; décision de l'utilisateur déjà rendue |
| `revoquer_source` | Retire une admission — ou **écarte** une source en suspens (aucune pièce à signaler) ; les pièces concernées seront signalées | source ni admise ni en suspens ; rôle qui utilise les sources ; admission faite par l'utilisateur (pour le système) |

Tout le vocabulaire (natures, niveaux, genres de lieu, critères d'admission, rôles qui utilisent les
sources) est une donnée : `referentiel.json`. Les sociétés et les sources sont en base ; la reprise de
ce que l'ancien code portait en constantes est `app/db/seeds/emetteurs_reprise_2026-11-13.json`,
jouée par `tools/emetteurs.sh importer`.

## Invariant → assert garant

| Invariant (ligne d'acceptation) | Contrôle · assert | Test négatif |
|---|---|---|
| Ajouter un titre = un geste, relu tel quel (A1) | `check_emetteurs.py` [A1] | `negatif_emetteurs.sh` |
| Sans référence externe, sans cotation : fiche valide (A2) | `check_emetteurs.py` [A2] | idem |
| Sans kit de spécialité : sources générales + son site (A3) | `check_emetteurs.py` [A3] | idem |
| Une correction est une révision ; les précédentes se relisent (A4) | `check_emetteurs.py` [A4] | idem |
| Une source vaut pour une nature d'information (A5) | `check_emetteurs.py` [A5] | idem |
| Admission datée, motivée, signée ; le système cite son critère (A6) | `check_emetteurs.py` [A6] | idem |
| Celui qui utilise une source ne la qualifie jamais (A7) | `check_emetteurs.py` [A7] | idem |
| La correction de l'utilisateur l'emporte (A8) | `check_emetteurs.py` [A8] | idem |
| Une source révoquée signale ses pièces, et elles seules (A9) | `check_emetteurs.py` [A9] | idem |
| Dans le doute, non admise (A10) | `check_emetteurs.py` [A10] | idem |
| Le chef de dossier s'arrête sans fiche (A11) | `check_emetteurs.py` [A11] | idem |
| Ni réseau ni modèle : bibliothèque standard | `check_emetteurs.py` [A0] | idem |
| Tout tient en base ; registres en ajout seul ; pas d'écrasement (A12) | `check_emetteurs_persist.py` [B0]-[B7] | `negatif_emetteurs_persist.sh` (code et migration 063) |
| L'écran sert la fiche et le journal ; le corps d'un geste ne porte ni auteur ni date (A13) | `check_emetteurs_api.py` [P1]-[P9] | `negatif_emetteurs_api.sh` (exige l'image ; répété sur l'hôte le 2026-11-14 : 8/8) |
| Les pages de relations investisseurs d'une autre société : admises par le système, révocables, jamais rétablies (A16) | `check_emetteurs.py` [A16] ; `check_emetteurs_reprise.py` [R4] | `negatif_emetteurs.sh` |
| Une source inconnue : note calculée, admise au seuil, en suspens dessous ; votre arbitrage tient (A17) | `check_emetteurs.py` [A17] ; `check_emetteurs_persist.py` [B1], [B4] | `negatif_emetteurs.sh` (17 mutations [A17]) ; `negatif_emetteurs_persist.sh` |
| La reprise est à l'identique de l'ancien code, deux écarts voulus nommés (A14) | `check_emetteurs_reprise.py` [R1]-[R5] (**provisoire** : part avec l'ancien code) | — |

## Ce qui n'existe pas encore (dit, pas caché)

- **L'acceptation réelle** (A13-A15) : migration 063 non appliquée en production, reprise non jouée,
  comparaison sur les pièces réelles non faite, écran jamais ouvert contre le vrai service.
- **Le remplacement de l'ancien code** : `websearch._ISSUER_DOMAINS` et ses quatre listes,
  `source_registry._ADMISES` / `_TICKER_SECTEURS` / `qualify` sont toujours là et toujours utilisés
  par l'ancien enchaînement. Ils sont supprimés le jour de l'acceptation.
- **L'évaluateur lui-même** (le modèle qui lit les publications et répond à la grille) : la porte
  est construite (`evaluer_source`, contrat 1.1.0, référentiel 1.2.0), l'évaluateur arrive avec la
  collecte (M2). Seuil, nombre de publications et questions sont des valeurs de départ, en donnée.
- **Le contenu du kit de spécialité** : la fiche porte un nom de spécialité, rien de plus.
- **La reconnaissance au fil de l'eau** des pages de relations investisseurs : le geste existe, mais
  seul l'outil (`tools/emetteurs.sh pages-investisseurs`, sur les pièces déjà collectées) l'appelle.
  La collecte (M2) devra l'appeler sur chaque adresse rencontrée.
- La **date d'un acte** est donnée par l'appelant : l'écran met la date du jour du serveur ; le
  module ne vérifie pas qu'elle est plausible.
- Deux actes simultanés sur le journal : le second est refusé (rang déjà pris) et doit être rejoué ;
  il n'y a pas de reprise automatique.
