---
id: 1787559677487
type: feature
status: closed
priority: high
date: 2026-08-24T08:21:17+00:00
closed_at: 2026-08-24T11:45:00+00:00
project: assistant-ia
url: 
milestone: journal-kb
---

## ✨ Feature

**Date** : 24/08/2026 08:21
**URL** : `N/A`

### Description

**Ticket d'assemblage** du chantier `journal-kb` (roadmap §3). Dépend de #1787559677482
(routage), #1787559677483 (client), #1787559677484 (migration), #1787559677485 (classifieur),
#1787559677486 (vault). Ne pas le démarrer avant que les cinq soient fermés.

Brancher la branche 4 du dispatcher (`message parent dans #journal`) sur la chaîne d'ingestion :

```
Message parent #journal
  → classifieur DeepInfra (contexte, nature[], tags[], title)
  → écriture pivot Markdown dans le vault
  → UPSERT dans journal_kb_entries (clé : doc_id ; dédup sur content_hash)
  → accusé de réception Slack en thread sous le message d'origine
```

Points de vigilance :

- **Ordre d'écriture** : Markdown d'abord, index Postgres ensuite. Le Markdown est le pivot ; si
  l'UPSERT échoue, la note n'est pas perdue et l'index peut être reconstruit depuis le vault.
  Si l'écriture Markdown échoue, ne rien insérer en base et le signaler dans le thread.
- **Distinguer une note libre d'autre chose** : la branche 4 ne se déclenche que sur un message
  **parent** de `#journal`. Les réponses en thread (parcours journal v2, ancien journal) sont
  captées plus tôt dans le dispatcher — vérifier explicitement la non-régression.
- **Traitement en tâche de fond** après l'ack (contrainte Slack 3 s) : l'appel DeepInfra prend
  plus de 3 s. Patron `asyncio.create_task` déjà utilisé pour l'import bank-review.
- **Dédup** : si `content_hash` existe déjà, ne pas créer de doublon — répondre « déjà noté ».
- **Accusé Slack** en thread, format roadmap §3 :
  `Noté · professionnel · apprentissage · #management` + lien vers le fichier du vault.
  Si le classifieur a échoué (fallback « à classer ») : `Noté · à classer` — l'utilisateur doit
  voir que la catégorisation n'a pas abouti.
- **Ne jamais faire échouer silencieusement** : toute exception dans la tâche de fond doit produire
  un message en thread, pas seulement un log.

### Vérification attendue

Bout-en-bout réel sur `#journal` : message parent → fichier créé dans le vault, ligne en base,
accusé en thread avec les bonnes catégories. Puis : réponse en thread sur un parcours v2 → toujours
traitée par le journal v2 (non-régression). Puis : même message envoyé deux fois → une seule entrée.

### Notes d'implémentation

Chaîne assemblée dans `app/handlers/journal_kb.py`. La dédup (`content_hash`) est testée **avant**
le classifieur et non après : cela évite à la fois un appel DeepInfra inutile et un fichier orphelin
dans le vault. Ordre d'écriture respecté (Markdown puis Postgres) ; un UPSERT en échec laisse la note
sur disque et le signale explicitement en thread plutôt que de faire croire à un succès.

Défaut corrigé au passage dans `journal_vault` (#1787559677486) : `ensure_vault` faisait échouer toute
l'ingestion si `git init` échouait. Découvert en exécutant les tests sur l'image en production, qui
n'a pas encore `git`. Le module posait déjà la règle inverse pour `_commit` (« une note écrite mais
non committée reste lisible sur disque ») — `git init` est donc passé en best-effort, et `_git`
convertit un git absent en code 127 au lieu d'une exception. Le versionnage est un confort, le
Markdown est la donnée.

Vérification : 22 assertions, dont ligne indexée conforme à l'enveloppe, verbatim préservé, accusé
`Noté · professionnel · decision · #management` + chemin du vault, double envoi → une seule entrée et
aucun fichier orphelin, fallback → `Noté · à classer` avec `contexte` NULL, échec vault → rien en base
+ message en thread, exception inattendue → message en thread (jamais un simple log). Lignes de test
nettoyées (0 restante). Non-régression du journal v2 : les réponses en thread sont interceptées
branche 2 du dispatcher, couverte par les 10 cas de routage de #1787559677482.

⚠️ Reste le bout-en-bout réel sur `#journal` (fichier + ligne + accusé), à faire après déploiement.
