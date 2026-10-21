# Procédure — recentrage

**But** : réécrire `CAP.md` en replanifiant **à rebours depuis le jalon actif**, jamais en
prolongeant la liste précédente. C'est la question « liste les étapes restantes pour arriver
à *{capacité}* », systématisée.

## Quand
- **Début de session** (après lecture de `CAP.md`) — si `CAP.md` date d'avant le dernier lot
  du journal, ou si un déclencheur ci-dessous est vrai.
- **Après une compaction du contexte** — c'est le moment où le cap se perd.
- **Jalon atteint** (validé par l'utilisateur sur démonstration du scénario).
- **Changement** de mission, de principe ou de jalon (`changement.md`).
- **Coupe-circuit**, lu dans le journal de lots : 3 lots consécutifs sans avancée du jalon,
  ou plus de 2 lots sur le même bug.

## Comment
1. Relire `MISSION.md` (valeur, P0, principes) et la capacité du jalon actif dans la roadmap
   (scénario, acceptation). **Ne pas relire l'ancienne liste d'étapes de `CAP.md`.**
2. Partir du scénario : « pour que l'utilisateur puisse faire *ça*, que doit-il exister qui
   n'existe pas encore ? » Remonter jusqu'à l'état actuel du code (vérifié, pas supposé).
3. **Triage des bugs et idées en cours** : un bug n'est traité maintenant que s'il **bloque le
   scénario du jalon actif**. Sinon → ticket (`feedback-tickets/`) et ligne « Hors cap ».
4. Réécrire `CAP.md` (≤ 15 lignes, gabarit `templates/CAP.md`).
5. Si le coupe-circuit a déclenché : le dire à l'utilisateur en une ligne, avec la cause lue
   dans le journal (bug récurrent ? jalon trop gros ? spec ambiguë ?) — et proposer, pas
   appliquer, le remède (redécouper le jalon, escalader une décision).

## Choisir le jalon suivant (jalon atteint)
« Quelle capacité rapproche le plus l'utilisateur du modèle de référence ? » — parmi les
capacités restantes de la roadmap. Si aucune ne le fait, c'est la roadmap qui est à revoir
(proposer à l'utilisateur), pas le jalon à inventer.
