---
id: reprise-strategic-intelligence
status: prompt-de-reprise
created: 2026-09-26
updated: 2026-09-26
project: strategic-intelligence
---

# strategic-intelligence — reprise

## État (2026-09-26)

**Phase : spécification complète, prête à implémenter, aucun code.** Remplace `horizon-scan` (archivé).

- La spec d'origine (v1) a été analysée puis **supprimée du dépôt** ; archive (zip), analyse et vrais mandats
  de départ dans `prive/` (gitignoré, contenu sensible — ne pas lire sans demande).
- **`spec-v2/` : spécification de référence**, un fichier détenteur par sujet (`spec-v2/README.md`),
  toutes les décisions dans `spec-v2/DECISIONS.md`. Schéma `03-SCHEMA.sql` validé sur un Postgres 16
  + pgvector jetable (62 tables) ; tous les YAML de `config-exemple/` se chargent.

## Roadmap active

`spec-v2/06-ROADMAP.md` — prochain jalon : **lot 0 (noyau)**, démarré avec
`spec-v2/08-PROMPT-DEMARRAGE.md`.

## Reste à faire / dettes ouvertes

- **Utilisateur** : agrandir le VPS (≥ 8 Go RAM, disque) avant le lot 1 (D16) ; valider `prive/identite.yml`,
  `prive/acteurs-spatial.yml` ; mandats réels paramétrés après la V0 (proposition : `prive/demarrage-mandats.yml`) ;
  compte EPO OPS au début du lot 3 (l'agent le demande) ; atelier scénarios au lot 4.
- Secrets : clés DeepInfra et Exa vérifiées le 2026-09-26, dans `.env` (600, gitignoré) et
  `/root/secrets/strategic-intelligence.env` ; importées dans le coffre au premier démarrage (D28).
- Phase de test V0 sur DeepInfra ; bascule vers une API sécurisée prévue, par configuration seulement (D5).
- Chantier `newsletter-summary` (action `forward`, alias `veille+spatial` / `terrain+spatial`) : `spec-v2/07`, L1-05.
- `comms-gateway` : sans domaine Resend vérifié, courriel vers l'adresse du compte Resend ; alertes Slack
  (`strategic-intelligence-space`) en attente de l'app Slack du gateway.
- Gabarit TED volontairement incomplet (L1-06) ; support du format de sortie structuré de DeepSeek-V4-Flash
  à vérifier au lot 1.
- Contenu sensible jamais versionné (D18) : `prive/` (gitignoré) — ne le lire que sur demande.
