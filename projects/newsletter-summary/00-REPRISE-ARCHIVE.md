---
project: newsletter-summary
role: >
  Récit du travail livré, sorti du 00-REPRISE.md le 2026-09-05 en appliquant CONTROL_SYSTEM.md §5.
  Jamais chargé en session — greppable seulement.
---

# Archive — newsletter-summary

Ce que ce fichier contient : le **récit** des lots livrés. Ce qu'il ne contient pas, et où c'est
parti :

- les faits **durables et réutilisables ailleurs** → `DECISIONS.md` (#2 : l'enveloppe HTML produite
  par un LLM se déséquilibre à la troncature) ;
- l'**état stable du projet** (flux, endpoints, variables, sécurité, déploiement) → `README.md`,
  qui en est le détenteur unique ;
- les **dettes encore ouvertes** → section « Reste à faire » du `00-REPRISE.md`, qui ne bouge pas
  à l'archivage.

---

## 2026-09-04 — Cartes déterministes, anti-troncature, plein écran mobile

**Cause racine sur le digest du 04/09** (7 newsletters) : le modèle dépassait la consigne de
600 mots (~1200 produits) et la sortie était **coupée à `max_tokens=2500`** → 5 blocs sur 7
tronqués (Euractiv « Le Rapporteur » coupé net) ET un `<div>` non fermé → **la carte suivante
s'imbriquait dans la précédente** (Geopolitechs id21 dans Euractiv id20). Un seul bug expliquait
les trois symptômes qu'on lisait comme trois pannes distinctes.

Corrigé et déployé (`docker compose up -d --build`, health OK, un seul conteneur) :

- `digest.py` : ouverture/fermeture de carte **+ en-tête (expéditeur/sujet) rendus déterministes
  côté code**. Le modèle ne produit plus que le corps. `_sanitize_inner` déballe un `<div>`
  enveloppant éventuel, coupe une balise finale tronquée et **équilibre les `<div>`** →
  imbrication impossible par construction (vérifié : les 5 blocs cassés du 04/09 re-wrappés sont
  tous équilibrés ; document global 45/45).
- Marges latérales de l'enveloppe et du bloc blanc à 0 (plein écran mobile), padding interne des
  cartes conservé.
- `summarizer.py` : `max_tokens` 2500 → **4000** ; invariants « corps seul » et « 600 mots »
  doublés dans le message système, donc garantis même si le prompt est réédité depuis le Hub.
- `deepinfra_client.py` : WARNING si `finish_reason=length`.
- **Prompt actif V4** (id=5, table `prompt_versions`, append-only) : « corps seul, 600 mots
  strict ». Rollback par le menu déroulant du Hub. Défaut de `config.py` aligné.
- **Vérification contre le vrai modèle** (email id27, 73k caractères en entrée, sans envoi ni
  changement de statut) : sortie de **520 mots**, zéro `<div>` émis par le modèle, carte équilibrée
  3/3.

## 2026-09-03 — Migration Coolify → docker compose

**Rien n'a changé dans ce projet** : il était déjà une stack `docker compose` standalone, ce qui
lui a évité tout coût de migration. Ce qui a changé est en face : le Hub n'est plus une app
Coolify, donc `NEWSLETTER_URL` / `NEWSLETTER_API_TOKEN` se posent dans `projects/hub/.env` et non
plus dans l'UI Coolify.

⚠️ Cette entrée portait une **justification fausse**, corrigée le 2026-09-05 : elle expliquait
qu'il fallait reconstruire le Hub « parce que c'est un Next.js dont les variables sont figées dans
le bundle au build ». Le Hub est une app **FastAPI/uvicorn** (`projects/hub/Dockerfile`) et lit
ses variables au **runtime** via `env_file`. La conclusion « rebuild, pas restart » restait juste,
mais pour une autre raison : le `docker-compose.yml` du Hub fait `build: .`, donc `app/` est
**dans l'image** — un changement de code exige un rebuild. Conservé ici comme faux-ami : une
consigne juste peut survivre des mois sur un raisonnement faux, et personne ne la teste tant
qu'elle donne le bon résultat.

## Antérieur — mise en place

Flux inbound Resend → PostgreSQL, digest 8h APScheduler, un appel DeepInfra par mail, garanties
« français » et « sans publicité » portées par le message système (donc insensibles aux éditions
du prompt), séparation des cartes garantie côté code, KB des résumés au format enveloppe
`KNOWLEDGE_ARCHITECTURE.md` §3, éditeur de prompt versionné dans le Hub. L'état durable de tout
ceci est décrit par le `README.md` — il n'est pas redit ici.
