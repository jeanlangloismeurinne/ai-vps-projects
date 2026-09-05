---
project: newsletter-summary
updated: 2026-09-05
role: >
  Prompt de reprise du digest matinal de newsletters. État : en production, digest 8h quotidien,
  rendu HTML à enveloppe déterministe. Aucun chantier en cours — un 360° est proposé.
---

# Prompt de reprise — newsletter-summary

> **Roadmap active : aucune.**

**Carte de l'archive** : le récit des lots livrés est dans `00-REPRISE-ARCHIVE.md`. Le seul fait
réutilisable ailleurs est en `DECISIONS.md` **#2**. L'état stable du projet — flux, endpoints,
variables, sécurité, commande de déploiement — est dans le **`README.md`**, seul détenteur : ce
fichier ne le redit pas.

## État

En production. Newsletters transférées → inbound Resend → PostgreSQL ; digest quotidien à 8h
(Europe/Paris) résumé par DeepInfra, un appel par mail, envoyé via **comms-gateway** (le projet ne
détient aucune clé de provider). Le rendu HTML des cartes a son enveloppe produite **côté code**
depuis le 2026-09-04 : l'imbrication de cartes est impossible par construction.

**Corrigé le 2026-09-05 — le digest se mangeait lui-même.** Une seule URL de webhook reçoit tous
les événements Resend, entrants comme sortants : les `email.sent` / `delivered` / `opened` du
digest qu'on venait d'envoyer étaient stockés comme des newsletters à résumer. Une ligne fantôme
par jour, corps vide, ressortie le lendemain en carte vide dont l'en-tête affichait le sujet de la
veille. C'est ce qu'on voyait le 05/09 : objet « 2 newsletter(s) », en-tête de première carte
« 8 newsletter(s) — Friday 04 », un seul vrai bloc. `resend.is_inbound_event` trie désormais sur
liste blanche, gardé par `checks/check_webhook_event_filter.py`. Les 4 lignes fantômes déjà en
base sont passées en `status='ignored'` (marquées, pas supprimées).

Ce n'était **pas** une régression du correctif d'imbrication du 2026-09-04, qui tient.

Déploiement : ce projet reste **hors** de `infrastructure/compose-deploy.sh` (comme `kb-viewer`).
La commande est dans le `README.md` § Déploiement.

## Reste à faire / dettes ouvertes

- **Le rendu d'un digest de 5 à 8 mails n'a toujours pas été observé.** Celui du 05/09 n'avait
  qu'un seul vrai bloc (l'autre était le fantôme), et la file de demain n'en contient qu'un
  (Euractiv, id 29). Restent à constater sur un vrai lot : la séparation entre cartes et le
  respect des 600 mots sur des mails variés. Surveiller les WARNING `finish_reason=length`.
  ⚠️ **La cause du non-observé, jusqu'ici, était le fantôme lui-même** : il gonflait le compte
  annoncé, ce qui donnait l'illusion d'un digest fourni.
- **Le corps d'un mail arrivé trop tôt n'est pas rapatriable** : le 05/09 à 08:00, trois tentatives
  `GET /v1/inbound/email/{id}` ont rendu 404 (« pas encore indexé »). La ligne reste alors
  metadata-only et produit une carte « Corps non reçu ». Aucun re-essai différé n'existe — à
  traiter si le cas se répète sur un vrai mail (le 05/09, c'était le fantôme).
- **Domaine d'envoi Resend non vérifié** → le gateway tourne en `RESEND_DEV_MODE=1`, tous les
  envois sont forcés vers `RESEND_DEV_TO`. **Le digest ne part donc pas à son vrai destinataire.**
  Sortir du mode dev une fois un domaine vérifié dans resend.com/domains (avec DNS). Blocage
  hors-code, partagé avec comms-gateway.
- **Code mort** : `SUMMARIZATION_PROMPT` et `summarize()` (`app/prompts.py`, `app/summarizer.py`)
  ne sont jamais appelés — seul `summarize_html` l'est. Les retirer, ou constater qu'ils servent
  de repli avant de les garder.
- **Repli « Option A »** : si le HTML produit par le modèle s'avère trop incohérent dans les
  clients mail, basculer sur une coquille HTML entièrement côté code (CSS inline, cartes
  uniformes, contenu échappé), DeepSeek ne produisant plus que du texte. Décidé comme repli, pas
  comme cible — ne l'ouvrir que si la première dette ci-dessus vire au rouge.
- **Fédération KB** : `kb_documents` est déjà à l'enveloppe `KNOWLEDGE_ARCHITECTURE.md` §3.
  Brancher le connecteur `mailbox` → `db_knowledge_federation` le jour où une recherche
  multi-source est réellement demandée, jamais par anticipation.

## Où démarrer

Aucune roadmap n'est inscrite : proposer le diagnostic 360° (`CONTROL_SYSTEM.md` §4) et attendre
le choix de l'utilisateur. Ne pas ouvrir « Option A » de soi-même — c'est un repli conditionné.
