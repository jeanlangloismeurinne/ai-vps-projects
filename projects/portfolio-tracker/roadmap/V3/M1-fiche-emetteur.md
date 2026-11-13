---
id: m1-fiche-emetteur
status: module en construction (tri fait, acceptation écrite le 2026-11-13, avant le code)
created: 2026-11-13
project: portfolio-tracker
role: >
  Le dossier d'ouverture du module M1 « Fiche de l'émetteur et sources » : le tri de l'ancien code,
  puis l'acceptation, écrite AVANT la construction (charte, points 6 et 7). Part dans
  `roadmap/archive/` le jour où M1 est accepté sur NVDA et RVMD.
---

# M1 — Fiche de l'émetteur et sources

*Ce que ferait un vrai fonds* : la direction de la recherche tient une fiche par société (qui elle
est, où elle publie, sa spécialité) et une liste des sources qu'elle tient pour fiables, chaque
admission datée et motivée. Un analyste n'ajoute pas une source en retouchant un outil : il la fait
inscrire, et une source retirée fait relire ce qui s'appuyait dessus.

## 1. Le tri (charte, point 7)

Inventaire fait le 2026-11-13 par une recherche déléguée, sans base (les valeurs en base restent à
relire sur le VPS : § 4).

| Ce que l'ancien système contient | Où | Décision |
|---|---|---|
| Nom, symbole, place, secteur saisis à la création d'un titre | table `tickers` (`app/api/tickers.py`) | **Repris en donnée** : le nom et le symbole remplissent la fiche à l'identique. La table reste à l'ancien code (V0/V1 s'en servent). |
| Raison sociale et numéro SEC, téléchargés à chaque démarrage et gardés en mémoire ; sans eux l'identité « n'existe pas » | `knowledge/edgar_feed.py` (`identite_de_l_emetteur`, `resolve_cik`) | **Repris en donnée** : le numéro devient une référence externe FACULTATIVE de la fiche. Le téléchargement devient un adaptateur de M2. L'ancien code reste en place jusqu'au tri de M2. |
| Le site de chaque société | `knowledge/websearch.py`, `_ISSUER_DOMAINS` (3 titres écrits dans le code) | **Repris en donnée** (fiche, « où la société publie »). La constante est supprimée à l'acceptation de M1. |
| La reconnaissance d'une page « relations investisseurs » par la forme de l'adresse | `websearch.py`, deux motifs génériques | **Laissé** : la fiche nomme les pages de relations investisseurs ; on ne devine plus. |
| La spécialité d'une société | `knowledge/source_registry.py`, `_TICKER_SECTEURS` (1 titre) | **Repris en donnée** (fiche, « spécialité »). Supprimé à l'acceptation. |
| Quatre publications de biotechnologie admises le 2026-09-05, motif écrit | `source_registry.py`, `_ADMISES` | **Repris en donnée**, à l'identique (date, motif, portée, nature, niveau). Supprimé à l'acceptation. |
| Régulateurs, presse financière, organismes et cabinets d'études tenus pour fiables, sans date ni motif | `websearch.py`, quatre listes | **Repris en donnée**, avec la date et le motif de la reprise. Supprimé à l'acceptation. |
| La règle « une source vaut pour une nature d'information donnée » (#50, #52) | `source_registry.qualify` | **Reprise derrière le contrat** : la règle est réécrite dans le module, l'ancienne fonction est supprimée à l'acceptation. |
| Le stade d'une société (rentable, avant revenus, financière), décidé par le comité | table `ticker_archetypes`, `agents/v2/classement.py` | **Laissé** : c'est une décision du comité, pas une donnée d'identité. Trié avec M6 et M11. |
| Reclassements comptables par société | `knowledge/socle_comptes_emetteurs.yaml` | **Laissé** : trié avec M4. |
| Tables de correspondance nom → symbole, symbole → place, place → devise | `api/thesis_v2.py`, `data_collection/m1_quantitative.py`, `api/tickers.py` | **Laissé** : V0/V1, hors de la reconstruction. |
| Listes de titres de test dans les outils de mesure | `tools/*.py` (17 fichiers) | **Laissé** : outils de l'ancien enchaînement, triés avec leur module. |

Ce que l'ancien système **n'a pas** et que M1 apporte : le pays d'une société cotée ; une
révocation ; un journal des admissions ; une admission faite par le système.

## 2. L'acceptation (charte, point 6) — écrite avant la construction

Chaque ligne est un fait observable. Les lignes « société fictive » se prouvent sans base ni dépense
(`check_emetteurs.py`, rougi par `negatif_emetteurs.sh`) ; les lignes « base » se prouvent sur une
vraie base (`check_emetteurs_persist.py`) ; les lignes « réel » se passent sur le VPS.

| # | Acceptation | Preuve |
|---|---|---|
| A1 | **Ajouter un titre ne modifie aucun fichier de code.** Une société inconnue du système reçoit une fiche par un seul geste ; elle est relue telle qu'elle a été établie. Aucun nom de société, de pays ou de formulaire dans le code du module. | société fictive ; garde des accès [C7] |
| A2 | **Une société sans numéro SEC a une fiche valide**, et aussi une société non cotée, sans symbole ni place. Une référence externe est toujours facultative. | société fictive |
| A3 | **La fiche passe SANS kit de spécialité** : ses sources admises sont alors les sources générales et son propre site. Avec une spécialité, celles de la spécialité s'ajoutent. | société fictive |
| A4 | **Une fiche se corrige sans s'effacer** : chaque correction est une révision nouvelle, datée, motivée, signée ; les précédentes se relisent. | société fictive ; base (table sans modification ni suppression) |
| A5 | **Une source vaut pour une nature d'information** : admise pour l'interprétation, elle ne l'est pas pour une mesure chiffrée. | société fictive |
| A6 | **Toute admission est datée, motivée, et dit qui l'a faite.** Une admission du système cite le critère écrit qu'il applique ; sans critère, elle est refusée. | société fictive |
| A7 | **Celui qui utilise une source ne la qualifie jamais** : une admission proposée par un rôle qui collecte ou analyse est refusée. | société fictive |
| A8 | **Votre correction l'emporte** : une source que vous révoquez ne peut pas être réadmise par le système ; une source que vous avez admise ne peut pas être révoquée par lui. | société fictive |
| A9 | **Une source révoquée signale les pièces qui s'y appuient**, avec la date et le motif de la révocation — et elles seules : une pièce fondée sur une autre nature d'information, ou sur une source toujours admise, n'est pas signalée. | société fictive |
| A10 | **Dans le doute, la source n'est pas admise** : une adresse inconnue, illisible ou hors de la portée de l'admission reste au niveau le plus bas, et le motif le dit. | société fictive |
| A11 | **Le chef de dossier s'arrête tant que la fiche n'existe pas**, en nommant l'acte attendu ; il repart quand elle existe. | société fictive |
| A12 | **Tout tient en base** : fiches et journal des sources se rangent et se relisent à l'identique ; ni l'un ni l'autre ne se modifie ni ne se supprime. L'état d'un dossier du chef de dossier se range aussi, et deux écritures concurrentes ne s'écrasent pas. | base |
| A13 | **L'écran** montre la fiche, ses révisions, les sources admises et révoquées avec date, auteur et motif, et permet de corriger, d'admettre et de révoquer. | réel |
| A14 | **NVDA et RVMD** : la reprise remplit leurs fiches à l'identique de ce que le code dit aujourd'hui. Sur les adresses des pièces déjà collectées, la qualification par le module rend le même niveau que l'ancien code ; chaque écart est listé et expliqué. | réel (`tools/emetteurs.sh comparer`) |
| A15 | **Rien d'autre ne casse** : la suite complète reste verte ; les trois constantes reprises sont supprimées et l'ancien code lit la fiche. | réel |

## 3. Ce que M1 ne fait pas (dit, pas caché)

- **L'évaluation d'une source inconnue par un modèle.** M1 construit la porte (critères écrits,
  rôle de l'évaluateur, journal, révocation) et les admissions que le code sait motiver seul. Le
  premier évaluateur qui lit une source nouvelle arrive avec la collecte (M2) et passe par cette
  porte. D'ici là, une source inconnue n'est pas admise.
- **Le kit de spécialité** : la fiche porte le nom de la spécialité ; le contenu du kit (moteurs
  types, questions propres, étalons) est écrit par les modules qui s'en servent.
- **Le stade de la société** : décision du comité, hors de la fiche.

## 4. À faire sur le VPS

Tenu à jour dans `00-REPRISE.md`, section « À vérifier sur le VPS ».
