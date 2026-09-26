---
id: reprise-strategic-intelligence
status: prompt-de-reprise
created: 2026-09-26
updated: 2026-09-26
project: strategic-intelligence
---

# strategic-intelligence — reprise

## État (2026-09-26)

**Phase : spécification consolidée, aucun code.** Remplace `horizon-scan` (archivé).

- La spec d'origine (v1) a été analysée puis **supprimée du dépôt** ; archive (zip), analyse et vrais mandats
  de départ dans `prive/` (gitignoré, contenu sensible — ne pas lire sans demande).
- **`spec-v2/` : spécification de référence**, un fichier détenteur par sujet (`spec-v2/README.md`),
  toutes les décisions dans `spec-v2/DECISIONS.md`. Schéma `03-SCHEMA.sql` validé sur un Postgres 16
  + pgvector jetable (62 tables) ; tous les YAML de `config-exemple/` se chargent.

## Roadmap active

`spec-v2/06-ROADMAP.md` — prochain jalon : **lot 0 (noyau)**, démarré avec
`spec-v2/08-PROMPT-DEMARRAGE.md`.

## Reste à faire / dettes ouvertes

- Prérequis avant le lot 1 : **agrandir le VPS** (≥ 8 Go RAM, disque) — constat 2026-09-26 :
  2 vCPU, 3 Go, 5,4 Go libres (D16).
- Chantier `newsletter-summary` (alias `forward`, `veille@` / `terrain@`) : `spec-v2/07`, avant L1-05.
- Prérequis externes de `comms-gateway` : domaine Resend vérifié, app Slack — non bloquants
  (mode dev), mais aucune livraison réelle du brief tant qu'ils ne sont pas levés.
- Modèle LLM DeepInfra « économique » à choisir au lot 1 après essai (`settings.yml`).
- Gabarit TED volontairement incomplet : à finaliser contre l'API réelle (L1-06).
- Acteurs de départ du pack : placeholders ; termes d’identité : réglage `noyau.identity_terms` à saisir dans l’interface.
- Contenu sensible jamais versionné (D18) : mandats, questions, relations, identité → base ou `prive/`.
- Informations attendues de l'utilisateur : liste dans la conversation du 2026-09-26 (identité, périmètre
  exact, acteurs, mandats réels, newsletters, adresses terrain@, VPS, Resend/Slack).
