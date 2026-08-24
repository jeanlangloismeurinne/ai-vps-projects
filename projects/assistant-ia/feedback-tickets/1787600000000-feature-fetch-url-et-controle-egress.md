---
id: 1787600000000
type: feature
status: open
priority: medium
date: 2026-08-24T19:00:00+00:00
project: assistant-ia
url: 
milestone: agent-outillage-v1.1
---

## ✨ Feature

**Date** : 24/08/2026 19:00
**URL** : `N/A`

### Description

Outil `fetch_url` (`effect: read`, `taints_context: true`, `egress: public_web`) — récupérer le
contenu d'une URL choisie par le modèle. Détaché de `#1787579840506` le 2026-08-24, parce que c'est
le seul outil du chantier qui ouvre une **surface SSRF** (roadmap `agent-outillage.md` §4).

**Dépend de** `#1787579840505` et `#1787579840506` (le cadre et le taint éprouvés en usage réel).

### Le défaut à corriger au portage — bloquant

`_fetch_url_direct` (`portfolio-tracker/backend/app/knowledge/websearch.py:361`) fait
`client.get(url)` avec `follow_redirects=True` et **aucune validation de schéma ni d'adresse**.

Sans conséquence dans portfolio-tracker, où les URL proviennent des résultats de recherche. Ici, le
modèle choisit l'URL — et une page web tainte peut lui en suggérer une. Chemins ouverts depuis ce
VPS :

| Cible | Ce qu'elle expose |
|---|---|
| `http://localhost:8000` | **API Coolify** — déploiements, variables d'env, secrets |
| `http://shared-postgres:5432`, `http://shared-redis:6379` | services internes `infra-net` |
| `http://169.254.169.254` | métadonnées cloud |
| `file://`, `gopher://` | lecture locale / protocoles détournés |

C'est le risque dominant du chantier. Aucune règle d'autorisation applicative ne le couvre : c'est
une lecture, jamais une écriture.

### Politique d'egress — condition d'entrée de l'outil

`fetch_url` n'est pas livrable sans elle. À implémenter comme une fonction réutilisable, désignée
par le champ `egress` du manifeste (`#1787579840503`), applicable à tout futur outil sortant.

- Schémas `http` / `https` **exclusivement**.
- Résolution DNS **puis** vérification de l'IP obtenue : refus de loopback, privé (RFC1918),
  link-local, multicast, réservé, IPv6 équivalents (`::1`, `fc00::/7`, `fe80::/10`).
- **Revalidation à chaque redirection.** Une 302 vers `127.0.0.1` est le contournement classique de
  ce contrôle — `follow_redirects=True` sans revalidation ne vaut rien.
- Refus des hostnames internes (`shared-postgres`, `shared-redis`, `coolify`, `*.internal`, noms de
  services Docker).
- Timeout, plafond de taille de réponse, plafond de caractères réinjectés.
- Refus explicite et tracé, jamais un résultat vide (leçon SearXNG).

### Vérification attendue

- `http://localhost:8000`, `http://127.0.0.1`, `http://169.254.169.254`, `http://shared-postgres`,
  `file:///etc/passwd` → refusés, tracés dans `agent_tool_calls`.
- **Test de redirection** : une URL publique contrôlée redirigeant vers `127.0.0.1` est refusée à
  l'étape de redirection. Ce test est le cœur du ticket.
- Un domaine public normal fonctionne et son contenu est borné.
- Le domaine récupéré alimente `taint_sources` — une écriture dans le même tour bascule en
  `ConfirmerAvant` avec la source affichée.
- Test lancé **dans le container** (les cibles internes n'existent pas depuis l'hôte de la même
  façon).

### Notes d'implémentation
