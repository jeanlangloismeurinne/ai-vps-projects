# DECISIONS — assistant-ia

> Système de référence des **faits durables** : gotchas réutilisables et « pourquoi » d'architecture.
> Versionné, greppable. La mémoire agent n'en est qu'un cache. Un fait porteur vit **ici**, pas
> uniquement dans un résumé de session (qui scrolle hors de vue) ni dans la mémoire (point-in-time).

## LLM / DeepInfra

- **DeepInfra refuse `response_format: json_schema` pour Llama 3.1 8B-Turbo → HTTP 405.**
  Conséquences observées : double appel (405 puis fallback `json_object`), vocabulaire fermé non
  respecté, cardinalité non honorée. **Correctif** : utiliser un modèle qui supporte `json_schema`
  (`DeepSeek-V4-Flash`) + vocabulaire en **`enum`** (toujours dérivé de `categories.schema.yaml`).
  Garder la validation Python : seul garde-fou si l'appel retombe sur `json_object`.
- **`Meta-Llama-3.1-8B-Instruct` est déprécié chez DeepInfra depuis le 2026-07-16.** Ne pas s'y
  reposer ; préférer la variante supportée retenue ci-dessus.
- **Vérifier contre l'API réelle.** Un correctif de prompt/schéma ne tient pas tant qu'il n'a pas
  tourné contre le vrai modèle : le 405 ci-dessus était **invisible en test** et trouvé seulement en
  appelant DeepInfra. Corollaire de pilotage : front-loader un spike contre la dépendance externe
  avant de bâtir des tickets qui la présument.
- **Clé DeepInfra** : celle utilisée a été **empruntée** à portfolio-tracker (copiée chiffrée dans
  Coolify). ⚠️ En générer une propre à assistant-ia.

## Bases de connaissance

- **Fédération KB : on ne construit pas** (tickets `1787559677490/491` fermés `wont-do-for-now`).
  `KNOWLEDGE_ARCHITECTURE.md` §4 (charte transverse) l'emporte sur une roadmap projet. Aucune
  requête multi-source formelle → besoin supposé, pas constaté. L'export « enveloppe commune » étant
  livré, la décision est réversible. **Condition de réouverture** : une requête traversant deux
  sources réellement formulée.

---
_Historique détaillé des sessions : `git log` + `roadmap/archive/`._
