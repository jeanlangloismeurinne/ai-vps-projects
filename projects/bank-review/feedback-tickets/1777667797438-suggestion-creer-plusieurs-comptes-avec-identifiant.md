---
id: 1777667797438
type: suggestion
status: open
date: 2026-05-01T20:36:37.438586
project: bank-review
url: slack://#features-bank-review
priority: medium
needs_clarification: true
---

## 💡 Suggestion

**Date** : 01/05/2026 20:36
**URL** : `slack://#features-bank-review`

### Description

creer plusieurs comptes avec identifiant / mot de passe pour accéder au service, chacun avec sa base de données, ses règles, etc. Bref une instance de l’outil pour chaque utilisateur. Réfléchissions à la meilleure façon de faire ça en termes d’architecture car la situation pourrait se reproduire pour d’autres services au-delà de bank review.

### Questions avant implémentation

**Q1** : Combien d’utilisateurs envisages-tu à court terme — 2 à 5 personnes de confiance, ou une vraie plateforme ouverte à des inconnus ? Ça détermine si on fait du multi-tenant dans la même instance (schémas PostgreSQL isolés) ou plusieurs instances Coolify séparées.
**R1** : Commençons par des personnes de confiance. Mais je veux des bases de données isolées par utilisateur.

**Q2** : Veux-tu une session dédiée de design d’architecture avant toute implémentation, ou je peux définir un plan et créer les tickets directement dans le prochain brief ?
**R2** : J’aimerais une session design d’architecture lors du prochain échange pour qu’on valide ensemble les choix techniques et que tu définisses le plan et les tickets ensuite.