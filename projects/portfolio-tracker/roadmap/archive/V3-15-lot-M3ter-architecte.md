---
id: spec-lot-m3ter-architecte
status: spec v1 2026-10-22 (Opus) — arbitrages rendus le même jour ; à exécuter par Sonnet APRÈS B4c (fichiers communs)
created: 2026-10-22
project: portfolio-tracker
role: >
  Spec d'EXÉCUTION du lot M3 ter (plan `07-avant-comite.md`, tâche B4d) : les défauts de l'ARCHITECTE SEUL
  relevés par les quatre passages à blanc du 2026-10-22, séparés de ceux du périmètre (B4c). L'architecte
  est le maillon critique (point de départ de la collecte du modèle) : sa robustesse se prouvera ensuite
  sur le banc séquentiel (B4e).
---

# Lot M3 ter — l'architecte voit ce qu'il doit citer, compte chaque programme, et ne plante jamais

> **Ce que ferait un vrai fonds** : l'analyste qui bâtit le classeur a sous les yeux la liste des pièces du
> dossier ; il ne cite que ce qui y figure. Dans un laboratoire, **chaque molécule nommée a sa ligne** et sa
> probabilité de succès, parce que deux molécules n'ont jamais la même ; seule la recherche amont que
> l'émetteur ne nomme pas se regroupe en « plateforme ». La prochaine génération d'un produit vendu n'est
> pas un pari binaire : elle nourrit la croissance de son activité. Une note écrite avant un événement
> majeur se lit comme l'état d'avant, et le dit en tête. Un classeur mal formé est renvoyé à son auteur
> avec le motif, il ne fait pas tomber le bureau.

## 0. Ligne de base (2026-10-22, code DÉPLOYÉ `212af17`, 0,02 $) — à RE-MESURER à l'étape 0

| Passage | Issue | Cause (principe n° 4) | Autres formes touchées |
|---|---|---|---|
| NVDA 1 | refusé deux fois [P4] : `capital_par_point_de_croissance` en `sans_periode` | la fiche se lit par exercice, mais son origine est la REPRISE d'un chiffre unique pluriannuel (qf_3) : rien ne dit au modèle qu'une reprise s'applique à CHAQUE exercice projeté | toute variable reprise d'un encadré |
| NVDA 2 | refusé [S6] : cite « 1370 », numéro d'une RÉPONSE | **les pièces citables sont calculées (`Matiere.pieces_citables`) mais jamais montrées** ; les seuls numéros visibles sont ceux des réponses et de trois notes flash ; l'exemple du prompt cite 101-103 | toutes |
| RVMD 1 | **PLANTE** (`ValidationError` dans `faits_publies.poser_maille`) : bloc estimé sans pièce | un invariant du contrat levé à l'ASSEMBLAGE échappe au chemin « refus nommé → renvoi » | toutes |
| RVMD 2 | proposée, mais six molécules (phase 3 → préclinique) en UN bloc, un seul jalon | le contrat permet qu'un bloc de programmes en couvre plusieurs ; rien ne rapproche les blocs de l'inventaire de `me_7` (8 programmes, chiffre clé `nombre_de_programmes`) | laboratoire, technologie, industriel à programmes |
| RVMD (matière) | me_2, mo_4, se_2 écrites avant l'approbation FDA du 2026-08-26, servies comme résumés courants | la péremption n'est dite que sur la ligne de porte, loin du verbatim | toute société à événement majeur |
| Les quatre | les sorties REFUSÉES ne sont pas conservées : `--sortie` n'écrit qu'en cas de succès | outil | diagnostic impossible |

## 1. Arbitrages (2026-10-22, utilisateur)

- **Une ligne par programme que l'émetteur NOMME individuellement ET dont la réussite est incertaine**
  (essai clinique, autorisation, technologie non prouvée). Une génération suivante d'un produit vendu est
  rattachée à son activité. Seuls les programmes NON nommés (plateforme, recherche amont) se regroupent.
- L'architecte est le maillon critique ; banc séquentiel ensuite (B4e). L'explorateur du dossier est un lot
  à part (B4f) : CE lot ne donne aucun outil à l'architecte.

## 2. Les pièces citables, visibles (cause de NVDA 2)

- `matiere._question_texte` rend, sous chaque réponse, ses pièces : `pièces : #867 (titre, date du fait) ; …`
  — celles de `fondation.cited_entry_ids` et des faits postérieurs, avec leur titre COURT (tronqué à 120
  caractères) et `date_du_fait`/`source_date`. Les comptes et la ventilation portent leur numéro de pièce
  en vigueur s'il existe en base (même à blanc), sinon « pièce publiée à l'écriture » et ils ne sont pas
  citables à blanc.
- Les numéros de RÉPONSE changent de forme dans la matière : `réponse R-1367` (jamais `#`), pour qu'aucun
  numéro de réponse ne ressemble à un numéro de pièce.
- Une section finale « Pièces que tu peux citer » : la liste exacte de `pieces_citables`, triée, avec titre.
  C'est la même liste que [S6] contrôle (un seul détenteur : `Matiere.pieces_citables`).
- L'exemple du prompt garde ses numéros fictifs, mais la consigne dit : « cite UNIQUEMENT des numéros de la
  section "Pièces que tu peux citer" ». Le message de renvoi de [S6] rappelle cette liste.

## 3. Jamais de plantage (cause de RVMD 1)

- Toute erreur de contrat levée APRÈS la réponse du modèle (assemblage : `poser_maille`, `_poser_entete`,
  validation de `Architecture`) devient un refus NOMMÉ qui suit le chemin du renvoi (une fois), puis
  `ArchitectureRefusee`. Seule une panne d'infrastructure (réseau, base) reste une exception.
- `tools/architecte.py --sortie` écrit aussi les sorties REFUSÉES (`<sortie>.refus1.json`,
  `.refus2.json` : la sortie brute du modèle et le motif), pour que tout refus se lise.

## 4. Une ligne par programme nommé (cause de RVMD 2)

- Contrat `architecture-1.3.0` : `Bloc.programmes: list[str]` — REQUIS si `statut == "en_developpement"`,
  interdit sinon : les noms des programmes couverts, recopiés tels que `me_7` les écrit.
  `Bloc.plateforme: bool = False` : un bloc plateforme regroupe des programmes NON nommés (`programmes` vide,
  `nombre_de_programmes_non_nommes: int ≥ 1` requis).
- `ArchitecteSortie.inventaire_des_programmes: list[{programme, traitement, bloc, motif}]` : pour CHAQUE
  programme que nomme la réponse de `me_7`, ce que l'architecte en fait — `bloc` (sa ligne propre),
  `rattache` (génération suivante d'un produit vendu : le bloc d'activité qui le porte, motif ≥ 20),
  `extension` (activité annoncée), `hors_modele` (motif ≥ 20 : abandonné, immatériel…).
- Contrôles :
  - **[S13]** un bloc non plateforme couvre UN seul programme ;
  - **[S14]** chaque nom de `programmes` et de l'inventaire figure LITTÉRALEMENT dans le verbatim de `me_7`
    (comparaison sur le texte du dossier, jamais sur une liste écrite dans le code) ; chaque entrée
    `bloc`/`rattache`/`extension` désigne un bloc existant du bon statut ; chaque bloc `en_developpement`
    non plateforme apparaît dans l'inventaire ;
  - **[S15]** le nombre d'entrées de l'inventaire est ≥ au chiffre clé `nombre_de_programmes` de `me_7`
    quand il est établi (sinon : signal « inventaire non chiffré »).
- Signal inchangé : deux programmes au même prochain jalon à la même échéance.
- Ce qui n'est PAS contrôlé (dit au comité) : qu'un programme ait été OUBLIÉ alors que `me_7` le nomme sans
  le compter. Le banc (B4e) le mesurera ; l'explorateur (B4f) le réduira.

## 5. La période des variables reprises (cause de NVDA 1)

- Le rendu des fiches dit, pour une fiche `exercice` : « une cellule par période listée (historiques
  et/ou projetées) ; une valeur reprise d'un encadré (chiffre unique) s'applique à CHAQUE exercice
  projeté » ; pour `sans_periode` : « une seule cellule, sans période ».
- Le message de renvoi de [P4] nomme les périodes attendues.

## 6. La péremption au pied du verbatim

- Dans la matière, une réponse dont l'actualité n'est pas `courante` porte, AVANT son verbatim :
  « ⚠ écrite avant <fait daté> : à lire comme l'état au <date> ; le fait postérieur dit : <résumé de la note
  flash> ». Lu dans la même source que la ligne de porte (pas de second calcul).

## 7. Gardes

- **Fixture copiée du réel** : `mesures/2026-10-22/` reçoit les quatre sorties du 2026-10-22 (la sortie
  proposée de RVMD 2 ; les refusées reconstituées par un rejeu à blanc à l'étape 0, puisqu'elles n'ont pas
  été gardées). RVMD 2 doit être refusé par [S13] ; sa correction (une ligne par molécule) doit passer.
- Cas fictifs (aucun nom réel) : laboratoire à 6 programmes nommés + plateforme (passe ; regroupé → [S13]) ;
  société technologique dont la génération suivante est `rattache` (passe ; en bloc sans risque propre :
  admis, c'est un choix, mais l'inventaire doit le dire) ; programme inventé absent de `me_7` → [S14] ;
  inventaire plus court que `nombre_de_programmes` → [S15] ; bloc estimé sans pièce → refus NOMMÉ puis
  renvoi (plus de plantage) ; pièce citée hors liste → [S6] avec la liste dans le motif.
- `negatif_architecte.sh` : une mutation par règle neuve, motif unique, assert nommé.
- Réplicabilité : grep des noms réels dans le code, le prompt, l'exemple → 0.
- Suite ENTIÈRE.

## 8. Étapes et ce que Sonnet rend à Opus

0. Rejouer `architecte.sh NVDA` et `RVMD --hors-porte` À BLANC deux fois chacun avec le code courant
   (~0,02 $) et GARDER les sorties refusées (correctif §3 de l'outil d'abord, si nécessaire) ;
   `--matiere-seule` : taille de la matière.
1. §3 (plantage → refus), §2, §5, §6 ; contrat 1.3.0 et §4 ; prompt et exemple ; checks, cas fictifs,
   négatifs.
2. Suite ; bilan par `grep -E`.
3. Rejouer les quatre passages à blanc (~0,02 $) : rendre chaque issue, les motifs de refus, et pour RVMD
   l'inventaire des programmes et les blocs.
4. Rendre : fichiers ; écarts et pourquoi ; négatifs ; suite ; matière avant/après ; ce qui n'a PAS été
   exécuté. Ne pas committer, ne pas déployer, aucun `--ecrire`.
