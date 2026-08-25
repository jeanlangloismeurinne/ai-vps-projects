---
id: 1787600247615
type: feature
status: closed
priority: medium
date: 2026-08-24T19:37:27Z
project: assistant-ia
url:
milestone: kb-visualisation
closed_at: 2026-08-25T00:00:00Z
---

## ✨ Feature

**Date** : 24/08/2026 19:37
**URL** : `N/A`

### Description

Documenter l'accès à la visualisation KB et l'exposer dans l'UI, une fois le viewer déployé
(tickets `1787600247613` + `1787600247614`). Suit le « Workflow de déploiement production » de
`CLAUDE.md` (mettre à jour la landing avant déploiement).

**1. Landing page** — `_LANDING_HTML` dans `app/main.py` :
- ajouter une section / un lien vers `https://obsidian.jlmvpscode.duckdns.org` (« Base de
  connaissance — vue Obsidian ») ;
- mentionner que c'est en lecture seule et qu'un 1er accès peut prendre ~15-30 s (cold start
  scale-to-zero) — évite l'impression de page cassée.

**2. README du vault** — aligner le `_README` généré par `journal_vault.py` (et/ou la note
`Accueil.md` du ticket `1787600247612`) : mentionner l'accès web Obsidian en plus du `git clone`
existant. Ne pas dupliquer le message « écrit par l'agent, ne pas éditer ».

**3. CLAUDE.md** (racine et/ou projet) : consigner l'URL, le fait que le viewer est scale-to-zero
(Sablier), le montage RO, et que le vault est partagé journal + tasks. Une ou deux lignes, pas plus.

### Vérification attendue

- La landing affiche le lien vers Obsidian avec la note de latence.
- Le README/Accueil mentionne les deux voies d'accès (web + git clone).
- CLAUDE.md consigne l'URL et le mode scale-to-zero.

### Notes d'implémentation

Livré **après pivot Quartz** (cf. Sprint 2 / DECISIONS.md) : les hypothèses Obsidian +
scale-to-zero du ticket sont **caduques**. URL réelle = `kb.jlmvpscode.duckdns.org` (pas
`obsidian.…`), nginx **permanent** (aucun cold start à documenter), lecture seule + basic-auth.

1. **Landing** (`app/main.py`, section « Base de connaissance ») : bouton `Explorer le vault →` +
   lien inline vers `kb.jlmvpscode.duckdns.org` + note lecture seule / protégé par mot de passe.
   Aucune note de latence (nginx permanent, sans objet).
2. **README vault** (`services/journal_vault.py`, `_README`) : section « Consulter le vault » à deux
   voies — en ligne (Quartz, lecture seule) **et** `git clone` existant. Message « écrit par
   l'agent » non dupliqué (déjà en tête).
3. **Accueil.md** (`services/kb_schema_notes.py`) : pointeur README mis à jour (accès en ligne + clone).
4. **CLAUDE.md** : racine déjà détaillée (entrée `kb-viewer`, écrite au pivot) ; ajout d'une section
   « Base de connaissance — visualisation en ligne » dans le CLAUDE.md **projet** (URL + vault
   partagé + renvoi racine/README).

Vérification : `python -m py_compile` OK sur les 3 modules touchés. Rendu HTML/Markdown = strings
statiques (pas de logique). Latence/scale-to-zero du ticket : sans objet (nginx permanent).
