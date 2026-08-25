---
id: 1787600247614
type: feature
status: closed
priority: high
date: 2026-08-24T19:37:27Z
closed_at: 2026-08-25T07:15:00Z
project: assistant-ia
url:
milestone: kb-visualisation
---

## ✨ Feature

**Date** : 24/08/2026 19:37
**URL** : `N/A`

### Description

Rendre le conteneur Obsidian (ticket `1787600247613`) **scale-to-zero** (arrêté ≈ 0 RAM au repos,
réveillé à la demande) et l'exposer derrière Traefik **avec authentification**
(`roadmap/kb-visualisation-obsidian.md` §3-4, §7).

**1. Sablier** — middleware Traefik qui démarre le conteneur à la 1re requête, affiche une page
d'attente pendant le boot, puis proxifie ; l'arrête après un délai d'inactivité.
- Déployer Sablier (conteneur) avec accès au **socket Docker** (start/stop). Isoler si possible via
  un **docker-socket-proxy** limité aux actions containers start/stop/inspect (réduire la surface —
  cf. §7 roadmap : le socket Docker est un privilège à assumer).
- Stratégie : **dynamic** (page d'attente auto-refresh) — meilleure UX qu'une requête suspendue
  pour un boot KasmVNC de 15-30 s. Page d'attente thématisée « démarrage d'Obsidian… ».
- `sessionDuration` (inactivité) : ex. **10 min**. Le WebSocket KasmVNC maintient la session tant
  que l'onglet est ouvert → pas d'arrêt en pleine consultation ; l'inactivité démarre à la
  fermeture.

**2. Traefik** — labels sur le conteneur Obsidian (via Coolify custom labels, cf. mémoire
`feedback_traefik_multi_network` pour la méthode d'ajout de labels Traefik en base64) :
- router sur `obsidian.jlmvpscode.duckdns.org`, TLS ;
- middleware Sablier + middleware **auth** (basic auth Traefik au minimum, ou l'auth de la gateway
  existante si elle couvre ce host) ;
- si le conteneur est sur plusieurs réseaux, fixer `traefik.docker.network=coolify`
  (leçon `feedback_traefik_multi_network`).

**3. Auth — non négociable** : le vault contient un journal `private`. L'URL ne doit **jamais** être
joignable sans authentification. Vérifier explicitement : requête non authentifiée → 401, pas de
fuite du bureau.

**4. Vérif RAM** : conteneur arrêté au repos (`docker ps` ne le liste pas / status exited) ; 1er
accès → démarrage + page d'attente → bureau ; après 10 min sans activité → conteneur arrêté à
nouveau.

### Vérification attendue

- Au repos : `docker ps` ne montre pas Obsidian ; RAM rendue.
- `curl` non authentifié sur le host → 401 (auth active), conteneur **non** démarré par une requête
  non autorisée si possible (ordre des middlewares : auth avant Sablier).
- Accès authentifié à froid → page d'attente puis bureau Obsidian (~15-30 s).
- Session active maintenue tant que l'onglet KasmVNC est ouvert ; arrêt automatique ~10 min après
  fermeture.
- UFW : port interne en DENY externe ; seul Traefik expose le host.

### Notes d'implémentation

**Fermé le 2026-08-25 — SUPERSEDED par le pivot Quartz.** Le scale-to-zero (Sablier + socket-proxy)
visait à neutraliser la RAM d'un bureau KasmVNC lourd. Avec le viewer statique Quartz, l'empreinte
permanente est un `nginx:alpine` (~10 MB RAM) → **scale-to-zero sans objet**.

Ce qui a été conservé de ce ticket (l'exigence réelle) : **auth non négociable + TLS**. Réalisé via
le **coolify-proxy** (edge) : middleware Traefik `basicauth` (hash dans `docker-compose.override.yml`,
gitignored) + cert Let's Encrypt. Vérifié : `http→302 https`, `https sans auth → 401`,
`https avec auth → 200`, cert LE valide. Host : `kb.jlmvpscode.duckdns.org`. Le POC KasmVNC complet
(Traefik dédié + plugin Sablier + tecnativa socket-proxy restreint `CONTAINERS/POST`) a été monté et
validé côté plan de contrôle avant l'abandon — réutilisable si retour à Obsidian après upgrade box.
