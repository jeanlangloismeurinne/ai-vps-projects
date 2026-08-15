---
id: 1777667877640
type: suggestion
status: closed
date: 2026-05-01T20:37:57.640470
project: bank-review
url: slack://#features-bank-review
priority: medium
needs_clarification: true
closed_at: 2026-08-15T00:00:00Z
---

## 💡 Suggestion

**Date** : 01/05/2026 20:37
**URL** : `slack://#features-bank-review`

### Description

gérer plusieurs formats de fichiers d’entrée en fonction des banques. Aujourd’hui le format est celui de Bourso Bank. Je veux que l’utilisateur puisse uploader un fichier de compte issu de sa banque et utiliser Claude Haïku pour faire un mapping entre le format du fichier uploadé et le format de traitement existant dans l’outil. L’utilisateur rentre le nom de la banque correspondant au fichier. Il est possible qu’il y ait plusieurs formats de fichier par banque, tu peux tout enregistrer dans supprimer d’anciens formats.

### Questions avant implémentation

**Q1** : Quelle est la prochaine banque à supporter en priorité ? Si tu peux fournir un fichier CSV/Excel exemple (même anonymisé), ça permettra de valider le mapping Claude immédiatement.
**R1** : Ce sera la société générale mais je n’ai pas encore le fichier. Je veux faire un appel à Claude Haïku pour faire le mapping entre le format existant et le nouveau format. Minimise le nombre de tokens dans l’appel API (donc n’envoie ps tout le fichier)

**Q2** : Les formats détectés par Claude doivent-ils être mémorisés en base (pour ne pas re-mapper à chaque import d’un même format), ou le mapping peut se faire à la volée à chaque import ?
**R2** : Oui, je veux que le système vérifie s’il existe un mapping existant qui correspond aux headers du tableau qui est transmis. Si oui, il l’utilise. Si non, il créé un nouveau format en demandant de déclarer le nom de la banque et il l’enregistre avec la date du jour.