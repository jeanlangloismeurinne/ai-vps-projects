# kb-viewer — viewer statique de la base de connaissance

Viewer web de la KB (vault `/storage/journal-vault`) via **Quartz** (site statique), servi par
`nginx:alpine` derrière le coolify-proxy, protégé par **basic-auth** (le journal est `private`).
Chantier : `projects/assistant-ia/roadmap/kb-visualisation-obsidian.md` (Sprint 2).

## Pourquoi Quartz (et pas Obsidian réel)

Décision initiale = « Obsidian réel en conteneur KasmVNC ». **Abandonnée le 2026-08-25** : l'image
`linuxserver/obsidian` pèse **5,18 GB** (bureau distant complet) et la tirer a saturé le disque
(box 38 GB, ~5,6 GB libres) → risque prod. RAM aussi tendue. Quartz produit un site statique
(~50 MB, nginx ~10 MB RAM). **Trade-off** : on perd le filtrage interactif Bases/Dataview ; on garde
graphe, backlinks, recherche, lecture des notes. Détails : `assistant-ia/DECISIONS.md`.

## Architecture

```
vault (RO) ──build.sh (conteneur node éphémère, sandbox)──▶ volume kb_public ──▶ nginx:alpine
                                                                                  ▲ coolify-proxy (TLS LE + basic-auth)
timer systemd (10 min) ──▶ build.sh    # rafraîchit le site quand l'agent met à jour le vault
```

- `quartz/` (gitignored) : reconstruit par `setup.sh` (clone Quartz v4.5.1 épinglé + notre config).
- Le build tourne dans un conteneur `node:22` **éphémère** : les scripts npm de Quartz (code externe)
  sont sandboxés, jamais exécutés sur l'hôte. `node_modules` est mis en cache dans `quartz/`.
- Auth : middleware Traefik `basicauth` porté par `docker-compose.override.yml` (généré par
  `gen-auth.sh` depuis `.env`, **gitignored** — le hash n'est jamais committé).

## Installation / exploitation

```bash
./setup.sh                       # clone Quartz + applique la config
cp .env.example .env             # renseigner KB_AUTH_USER / KB_AUTH_PASSWORD
./gen-auth.sh                    # génère docker-compose.override.yml (basic-auth)
./build.sh                       # 1er build (npm install + génération) → volume kb_public
docker compose up -d             # démarre nginx (routé par coolify-proxy)

# Rafraîchissement automatique (nécessite les droits systemd) :
systemctl enable --now kb-viewer-build.timer      # unités déjà écrites dans /etc/systemd/system/
# à défaut, refresh manuel : ./build.sh
```

- URL : https://kb.jlmvpscode.duckdns.org  (401 sans auth, 200 avec).
- Sous-domaine `kb.*` (et non `obsidian.*`) : le viewer n'est plus Obsidian.

## Vérifications (Sprint 2)

- `curl http://kb.…` → 302 vers https.
- `curl https://kb.…/Accueil` sans auth → **401** (basic-auth avant gzip, pas de fuite).
- avec auth → **200**, cert Let's Encrypt valide, rendu Quartz (graphe, recherche, thèmes).
- Empreinte : nginx `mem_limit 32m` ; build transitoire ~2 s ; aucun conteneur lourd permanent.
