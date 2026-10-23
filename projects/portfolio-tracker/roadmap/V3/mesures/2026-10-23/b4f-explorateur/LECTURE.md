# B4f étape 4 — lecture des passages à blanc en mode `explorateur` (Opus, 2026-10-23)

V4-Pro, `max_iterations_explorateur` = 8. Coût : NVDA 0,4292 $ (7 tentatives), RVMD 0,4517 $ (8) — ×1,5 l'estimation.
Les pièces ouvertes ne sont PAS connues pour ces deux passages : l'outil ne rendait pas le journal
d'exploration (corrigé après coup, succès ET refus — à relire au prochain passage).

## NVDA — accepté (`nvda.txt`, `nvda.json`)
- Vera Rubin RATTACHÉE à Data Center (« génération suivante, mêmes clients ») — juste (était ligne propre dans `apres-143/`).
- Vera CPU : ligne propre (juste) mais `programme/en_developpement` avec `probabilite_de_succes` — FAUX, la pièce #1004
  (~20 Md$ de revenus CPU) est CITÉE par le bloc. Motif : « extension d'indication » → le vocabulaire de #143 est
  pharmaceutique et l'activité vendue n'a pas de case. Défaut de CONSIGNE, pas d'information.
- IA souveraine : encore `extension_annoncee`, pièce #1012 CITÉE (« AI factory Vera Rubin… » = clients de Data Center).
  Défaut de CONSIGNE/MODÈLE : la pièce est là, le classement ne suit pas.
- Hugging Face (acquisition annoncée, non conclue) en extension annoncée : défendable.

## RVMD — refusé [S15] après renvoi (`rvmd.txt`, `rvmd.json.refus{1,2}.json`)
- Le modèle applique #143 : daraxonrasib a une ligne par indication (PDAC 1L, adjuvant) + RASONQUE vendu en activité.
  Mais les deux entrées s'appellent « daraxonrasib » → [S14] (1er tour) puis [S15] « 6 présents dans me_7 pour 5 ».
  Conflit de GRANULARITÉ : #143 compte par indication, `me_7` (#2624) et [S14]/[S15] par nom de molécule. C'est le
  point différé « une extension d'indication = un élément de `me_7` » (réponse de l'utilisateur : après B4f).
- Molécules perdues par #2624 (RMC-0708, RMC-8839 ; essais RASolve 301) NON retrouvées, alors que #1546 (22 663 car.,
  citée par 7 blocs) les nomme : au-delà de 6 000 caractères, `ouvrir_piece` rend les passages pertinents, et le modèle
  n'a jamais demandé « pipeline ». Ouverte ou non : inconnu (journal non rendu).
- `demandes_de_recherche` rendues, pertinentes (taille et concurrence des marchés PDAC 2L, 1L, adjuvant, NSCLC…).

## Ce que l'ouverture des pièces règle seule
Peu : Vera Rubin (peut-être aussi le modèle). Les deux erreurs de sens NVDA restantes ont leur pièce sous les yeux →
consigne. RVMD bute sur la granularité → contrat `me_7`/[S14]/[S15]. Les deux corrections différées sont donc les
prochaines ; l'explorateur reste à `aucun` par défaut.
