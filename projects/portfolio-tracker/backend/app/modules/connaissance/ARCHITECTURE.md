# Base de connaissance — `app/modules/connaissance/`

Contrat **1.0.0**. Module M3 du plan `roadmap/V3/07-avant-comite.md` ; tri, interface « besoins →
collecte » et acceptation : `roadmap/V3/M3-base-connaissance.md`. **État (2026-11-21) : le lecteur, les
pièces, la recherche par les mots et le pas de lecture sont construits et prouvés hors ligne (société
fictive, communiqué réel) ; le rangement en base (migration 065, `depot_base.py`) est prouvé sur base
jetable — 065 PAS ENCORE APPLIQUÉE en production. À construire : l'écran, les lignes « réel » (K12-K14).**

*Ce que ferait un vrai fonds* : on met le document en lecture une fois pour toutes, lignes numérotées ;
chaque analyste cite sa ligne ; une citation qui ne se retrouve pas mot pour mot n'entre pas au dossier ;
ce que vaut la source, le registre des sources le dit au jour où l'on relit.

## Ce qu'il rend

La **connaissance d'un émetteur** (`contrat.Connaissance`), lue par une seule fonction :
`contrat.lire_connaissance`. Pour chaque document que la collecte (M2) a rangé, sa **lecture** par la
version courante du lecteur — des lignes numérotées, ou une lecture impossible / sans objet, nommée —,
les documents qui attendent leur lecture, et les **pièces**, chacune avec ce que vaut sa source
AUJOURD'HUI (`Valeur`, redemandée à M1 à chaque lecture, jamais rangée). Les lignes d'une lecture se
lisent par `contrat.lire_lignes`.

## Comment c'est construit

```
contrat.py        objets, dépôt (interface + mémoire), lecture, gestes, pas du chef de dossier
coeur.py          mettre en lecture, citer, valeur au jour de la lecture, chercher, le pas
lecteur.py        un document brut → des lignes (bibliothèque standard, aucune règle en dur)
depot_base.py     le rangement en base (tables `connaissance_lectures`, `_lignes`, `_pieces`, migration 065) :
                  ajout seul (la base refuse modification et suppression), une lecture nomme son document
                  de la collecte et une pièce sa lecture par clé étrangère (rien sans origine, par la base)
citation.py       la vérification mot pour mot — DÉTENTEUR UNIQUE (#126, #141), aussi lu par l'ancien
                  code par le contrat (`app/knowledge/citation.py` n'est plus qu'un ré-export)
referentiel.json  la façon de lire (blocs, muets, masques, cellules, décodages), sa version, les raisons
```

- **Une ligne** = un bloc (paragraphe, titre…) ou une ligne de tableau dont chaque cellule s'ouvre sur
  une tabulation (#132) ; une cellule sans lettre ni chiffre se recolle comme imprimée (« $ » et « ( » au
  nombre qui suit, « % » et « ) » à la cellule d'avant — relevé sur un 8-K réel). Ce qui est masqué
  (display:none), les scripts, styles et l'en-tête des données structurées ne sont pas lus.
- **Reproductible** : la version du lecteur fait partie de l'identité d'une lecture ; un lecteur amélioré
  lit à côté, les pièces gardent la leur.
- **Une pièce** porte le texte du DOCUMENT (forme typographique), ses lignes, les dates du document, la
  période du fait quand l'auteur la dit (arbitrage du 2026-11-21), et les autres lignes où le même texte
  figure (la première occurrence est retenue et le dit). Identité : document, lecture, lignes, extrait,
  période — la même pièce citée deux fois est rangée une fois.
- **Chercher** : par les mots (tous), classement par occurrences, puis document le plus récent, puis
  ligne ; gratuit. Par le sens : quand M6/M8 en auront besoin (arbitrage du 2026-11-21).

## Invariant → assert garant

Contrôle : `checks/check_connaissance.py` (49 vérifications le 2026-11-21 ; communiqué réel
`checks/fixtures/connaissance/communique_ex991.htm`) ; test négatif : `checks/negatif_connaissance.sh`
(30 mutations, toutes détectées le 2026-11-21 ; celles de la vérification mot pour mot visent son
détenteur, `citation.py`).

| Ligne | Invariant | Assert |
|---|---|---|
| K0 | Ni réseau, ni base, ni modèle, ni ancien code : bibliothèque standard et contrats | [K0] |
| K1 | Document inconnu, pas encore lu ou illisible → refus nommé ; une pièce nomme son auteur, son document, ses lignes, qui contiennent son extrait | [K1] |
| K2 | Relire ne relit pas ; même lecture deux fois identique ; lecteur amélioré : lecture à côté, pièces inchangées | [K2] |
| K3 | Communiqué réel en lignes citables ; masqué, scripts, en-tête non lus ; bloc dans une cellule ; texte brut ; données structurées « sans objet » ; vide → impossible | [K3] |
| K4 | Texte du document ; court et unique → sa ligne ; ambigu, paraphrase, chiffre changé → refusés par la vérification ; répétition nommée | [K4] |
| K5 | Une pièce rangée une fois ; une autre période = une autre pièce | [K5] |
| K6 | Dates du document, période dite par l'auteur, rien de deviné | [K6] |
| K7 | Valeur relue à la lecture : révocation signalée, non admise marquée, pièce inchangée | [K7] |
| K8 | Tous les mots, classement stable, filtre par genre, recherche vide = rien | [K8] |
| K9 | Pas de lecture : en cours / fait / indisponible sans document ; 0 $ ; ce qui n'en dépend pas avance | [K9] |

Rangement en base : `checks/check_connaissance_persist.py` (mêmes gestes en mémoire et en base,
comparés en entier ; ajout seul ; rien sans origine ; caractère nul ; [K5]) ; test négatif
`checks/negatif_connaissance_persist.sh` (code et migration mutés, sur base jetable).

- **Un caractère nul** dans un document se lit « \ufffd » (lecteur 1.1.0), comme un navigateur : la base
  refuse de ranger un texte qui en contient, et la lecture aurait échoué à chaque passage, sans fin.
- **La mise en lecture** tourne hors de la boucle principale (`asyncio.to_thread`) : la tâche de fond vit
  dans le processus des écrans.

## Ce qui n'existe pas encore (dit, pas caché)

- L'écran, les lignes « réel » (K12-K14).
- Une pièce dont le même texte figure à plusieurs lignes retient la première : le contexte (tableau
  comptable ou retraité) se juge à la relecture, les autres lignes sont nommées.
- Un extrait exact sorti de son contexte (négation dans la phrase voisine) passe (#126).
