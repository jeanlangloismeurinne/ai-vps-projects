---
project: exploration-science
updated: 2026-10-19
role: >
  Reprise de l'Explorateur de systèmes. V2 planifiée le 2026-10-19 (roadmap/v2.md, contrat QUALITY_BAR.md). Phase 0 (prototype) construite et validée jusqu'au jalon 5 bis ;
  le jalon 6 (aperçu déployable + finitions iPad) est livré mais pas encore déployé ni essayé sur iPad.
  Phase 1 (générateur) amorcée en parallèle : socle reproductible multi-API livré, essai manuel réussi,
  restent les runs API réels (VPS) puis le banc de non-régression.
---

# Prompt de reprise — exploration-science

> **Roadmap active : `roadmap/v2.md`** — capacité en cours : §2 (schémas, à soumettre). Contrat d'acceptation : `QUALITY_BAR.md`.
> En parallèle, inchangés : jalon 6 de la Phase 0 (essai iPad, tests utilisateurs — hors de l'agent) et `roadmap/phase1-generator.md` (prochaine : §3, banc de non-régression).

Lire d'abord `CLAUDE.md` du projet, puis `docs/SPEC.md` (source de vérité). Historique détaillé (jalons 1 à 6, essais, choix d'implémentation) : `00-REPRISE-ARCHIVE.md` (instantané du 2026-10-11, à interroger par `grep`).

## V2 — décidée le 2026-10-19

**Pourquoi.** Les prototypes de rendu (A à G, puis M « maquette », dans `prototypes/render/`) restent très loin de l'image visée par l'utilisateur : `docs/v2-reference-starlink.png`, une île en vue d'oiseau avec maisons, stations sol, satellites, faisceaux et Terre courbe.
Deux autres références montrent le rendu attendu **plus près**, à l'échelle d'un site : `docs/v2-reference-zoom-crossdock.jpg` et `docs/v2-reference-zoom-warehouse.jpg` (plateforme logistique en vue isométrique). On y voit :
- des objets détaillés et lisibles (camions, chariots élévateurs, palettes, quais) ;
- une palette claire et peu saturée, avec un bleu d'accent ;
- des ombres douces et un sol neutre, l'objet sélectionné mis en évidence ;
- des repères posés dans la scène.

Seule la 3D compte. Les panneaux 2D par-dessus seront conçus plus tard. La cause : on cherchait un rendu que le générateur refasse à chaque question, à coût nul, entièrement calculé. Ce rendu-là demande des modèles détaillés, une lumière précalculée et une direction artistique, ce qui suppose de construire une fois et de soigner.

**Planifiée le 2026-10-19 (session 1)** → `roadmap/v2.md`, sous contrat `QUALITY_BAR.md` (fourni par l'utilisateur). Décisions :
- v0 = **une scène Starlink restreinte mais aboutie** (maison, antenne, satellite, station sol), style illustration isométrique éditoriale sur socle ; la photo de référence reste une référence de contenu.
- **Aucune API externe** (génération 3D/image) : tout par Blender scripté (`bpy` 5.2.2 par pip, Cycles CPU — la session n'a pas de GPU). La piste image→3D (Tripo ≈ 0,30 $, Meshy ≈ 0,60 $ par objet, relevés le 2026-10-19) est écartée pour la v0.
- **Pile React + React Three Fiber**, entrée `v2.html` à côté du prototype (dérogation validée au « pas de framework UI »).
- Règle de récit (utilisateur) : toujours le système global avant l'objet — testée en §7.
- Les prototypes `prototypes/render/` ne servent pas de base (non lus par la session 1).

Règles du projet inchangées : toute modification de schéma est soumise à l'utilisateur, et `docs/SPEC.md` n'est modifiée qu'après validation.

## Jalons Phase 0
- [x] 1. Schémas et exemples de contenu — format `0.2` (2026-10-10)
- [x] 2. Moteur, scène de test, caméra contrainte (2026-10-10)
- [x] 3. Niveau 1 Starlink complet, avec le Play (2026-10-10)
- [x] 4. Plongée vers les niveaux 2 et 3, lentille Ondes, curseurs (validé 2026-10-11)
- [x] 5. Scène de contrôle ciel bleu, sans changer le format (2026-10-11)
- [x] 5 bis. Termes explorables cliquables + nœud principe `wave-interference` (2026-10-11)
- [ ] 6. Aperçu statique déployable (ordinateur + iPad Safari) et finitions de la Phase 0 — **déployé le 2026-10-13 (derrière le login du hub), reste l'essai sur iPad**. Acceptation : `https://explorer.jlmvpscode.duckdns.org/` répond 200 en HTTPS, la visite Starlink se joue de bout en bout sur ordinateur et sur un vrai iPad (gestes, fluidité), `?node=blue-sky` et `?node=wave-interference` s'ouvrent.
- Sortie de Phase 0 (spec) : tests concluants auprès d'une dizaine de personnes (adultes et enfants), puis **gel du format v1**.

## État en bref
- **Contenu** : 5 nœuds (`content/nodes/`) — `starlink-terminal` (m) → `starlink-phased-array` (cm) → `starlink-radiating-element` (mm), `blue-sky` (système), `wave-interference` (principe, Wikidata Q136980). Chacun : scène, textes FR sur 3 niveaux, `sources.json`. Catalogue : 17 composants, 3 simulateurs (`phased-array-wave`, `orbital-pass`, `rayleigh-scattering`), 1 lentille (`waves`), tous implémentés.
- **Format** : `0.2`, inchangé depuis le jalon 1 hors ajouts validés (`node.summaryKey`, convention « y vers le haut, sol en y = 0 » écrite dans la description du schéma).
- **Moteur** (`engine/src/`) : cœur sans logique de sujet (`core/`), plugins (`plugins/`), lecteur Play (`play/`), interface DOM (`ui/`). Budget de détail testé par scène, résolution adaptative, `?perf` (i/s, rapport de pixels, triangles), `?node=<id>`. En dev, `window.xs` pilote l'app (captures Playwright).
- **Tests** : 116 Vitest (`npm test`) + 20 pytest du générateur. Page de revue : `npm run review` (5 nœuds, 0 erreur).
- **Déploiement** : `Dockerfile` (Vite → nginx), `deploy/nginx.conf`, `docker-compose.yml` (conteneur `exploration-science`, `explorer.jlmvpscode.duckdns.org`, sans `.env`), entrée dans `infrastructure/compose-deploy.sh`. **En ligne depuis le 2026-10-13, protégé par le login global du hub** : middleware Traefik `xsauth` (forwardAuth → `homepage:8000/auth/verify`, qui valide le cookie `hub_session`) ; sans session, 302 vers `jlmvpscode.duckdns.org/login?next=<url>` puis retour. La sonde de déploiement attend donc **302**. Carte « Explorateur de systèmes » sur la page d'accueil du hub. Si le hub tombe, l'explorer est inaccessible.
- **Aperçu en ligne** : https://claude.ai/artifact/1vtLmqzT4kfUU7j3q33FLo (version 10 = jalon 6 + sources vérifiées, 2026-10-13). Republier : `npm run build`, copier `dist/assets` (js, css, woff2) + page sans `<html>` vers le scratchpad, même URL, en supprimant les anciens fichiers hachés.
- **Sources** : vérifiées le 2026-10-11 (≈ 35 pages ouvertes, ≈ 15 ajoutées) via le connecteur **Parallel** (`mcp__Parallel_Search__web_fetch` / `web_search`, à charger par ToolSearch) — WebFetch et curl restent bloqués dans la session cloud.

## Générateur (Phase 1, `generator/`)
- Principe : **le générateur est du code qui appelle une API**. Une réponse écrite dans Claude Code passe par l'exécuteur `manual` et le run est marqué `reproducible: false`.
- Exécuteurs : `api` (fournisseur du profil), `manual` (écrit `request.md` + empreinte, attend `response.txt`, refuse une réponse à une demande périmée), `replay` (rejoue un run, refuse si l'empreinte diffère). Un appel déjà enregistré n'est jamais repayé.
- **Profils** (`generator/profiles.toml`) : fournisseur, modèle, paramètres, prix, `api_key_env`, `prompt_variant` (`prompts/<variante>/` remplace fichier par fichier). Les réglages hors secrets entrent dans l'empreinte. Profils : `anthropic-opus` (référence, défaut) et `deepinfra-deepseek-v4.1-flash` (vérifié à la source : identifiant, prix Standard 0,20 / 0,60 / 0,006 $ par M, `reasoning_effort = "high"`, `temperature = 1.0`, coût lu dans `usage.estimated_cost`).
- **Fournisseurs** (`xs_generator/providers.py`), même contrat Request → Response : `AnthropicProvider` (SDK officiel, streaming, réflexion adaptative, effort, prompt système en cache, repli serveur `fallbacks: "default"`) ; `OpenAICompatibleProvider` (SDK `openai` sur `base_url`, mode JSON, troncature = erreur). Ajouter une API = une classe + un profil.
- Étape `node` : prompts `generator/prompts/node.*.md`, sortie validée par `scripts/validate-node.ts` (même validateur que les tests), 2 réparations au plus. Journal des runs committé dans `generator/runs/`.
- **Essai §2** (`generator/runs/2026-10-11-phased-array-manual`, manuel à l'aveugle) : valide après 1 réparation, rejoué à l'identique, joué dans le moteur sans erreur ; même structure que la référence, mais ~1,7× plus de mots. Il ne se rejoue plus avec le code actuel (enregistré avant les profils, prompt modifié depuis).
- **Enseignements pour le gel du format v1** (à trancher avec les tests) : une seule durée d'étape pour les 3 niveaux ; le réseau dessiné ne suit pas d/λ et rien ne montre la ligne calculée ; `antenna-element-array` sans `cutaway` (puces invisibles) ; aucun texte ne peut dépendre de l'état de la lentille.
- Lancer sur le VPS, depuis `projects/exploration-science` (clés dans `generator/.env`, chmod 600 : `ANTHROPIC_API_KEY`, `DEEPINFRA_API_KEY`) :
  `python3 -m venv .venv && .venv/bin/pip install -e generator && npm ci`
  `.venv/bin/python -m xs_generator node --id starlink-phased-array --question "Comment le réseau d'antennes de Starlink oriente-t-il son faisceau ?" --parent starlink-terminal:phased-array --sources content/nodes/starlink-phased-array/sources.json --runner api --profile <anthropic-opus | deepinfra-deepseek-v4.1-flash>`

## Pièges connus
- V2 : `npm run assets` (Blender, `art/.venv` : `python3 -m venv art/.venv && art/.venv/bin/pip install -r art/requirements.txt`), `npm run check:assets [-- --determinism]`, `npm run capture [-- --formats … --only …]`. Les messages `ERROR Draco/MeshOptimizer is not available` de `bpy` sont sans effet (compression faite par gltf-transform). Ne jamais utiliser les `preset` d'environnement de drei (HDRI téléchargées) ni Draco (décodeur sur CDN).
- Lentille Ondes : le shader travaille en unités de scène (`position * uSize`), sinon il ne marche qu'à l'échelle 1 m.
- `engine/src/content/validation.ts` reste sans import relatif : la page de revue et `validate-node.ts` le lancent sous Node sans bundler (règle dupliquée `derivedTextKey`, testée).
- Clés de texte : minuscules uniquement (`derived.steering-angle-deg`, pas `derived.steeringAngleDeg`).
- Générateur : SDK `anthropic` 1.x et `openai` 3.x reposent sur `httpx2` (tests : `import httpx2 as httpx`) ; URL Anthropic épinglée (`XS_ANTHROPIC_BASE_URL` pour la changer) car la session de dev exporte un `ANTHROPIC_BASE_URL` ; un nom de profil TOML qui contient un point s'écrit entre guillemets.
- Ne pas lancer `pkill -f vite` dans une commande qui contient elle-même « vite » : la commande se tue.

## Décisions récentes (2026-10-11)
- **Starlink niveaux 2 et 3 : on garde le modèle simplifié.** Les démontages publiés décrivent une réalité différente (voir Reste à faire) ; le principe enseigné ne change pas, le contenu le dira comme une représentation d'école.
- Docker compose (et plus Coolify) pour tout déploiement : spec et `CLAUDE.md` corrigés.
- Générateur multi-API avec Anthropic pour référence ; DeepInfra / DeepSeek V4.1 Flash comme premier challenger.

## Reste à faire / dettes ouvertes
- **Rendu immersif : remplacé par la V2** (section en tête). Les prototypes `prototypes/render/` et les pages de comparaison (A/B/C https://claude.ai/artifact/UUEhsdGwK6kiPs5mY5yh6X ; D/E/F/G https://claude.ai/artifact/NCjzcU9zWWcQvnZV1QHr8C ; M https://claude.ai/artifact/2EYMUwTaxJJafeVSzdAeJV) restent comme trace, à ne pas reprendre comme base.
- **Essai iPad** (déployé le 2026-10-13 ; se connecter d'abord au hub) : avec `?perf` (viser ≥ 55 i/s, rapport de pixels ≥ 1,5) : gestes et fluidité seulement vérifiés en émulation.
- **Runs API réels** (roadmap §2) : `anthropic-opus` puis `deepinfra-deepseek-v4.1-flash` sur `starlink-phased-array`, depuis le VPS (clés à poser). Donnent le coût réel par nœud.
- **Banc de non-régression** (roadmap §3), puis socle backend (§4) et étapes amont (§5).
- **Modèle simplifié Starlink à rendre explicite** (décision ci-dessus) : ajouter dans les textes de `starlink-radiating-element` (et la description de l'élément) une phrase disant que la pastille carrée sur substrat est une représentation d'école ; noter dans les `sources.json` concernés que la simplification est assumée. Écarts relevés : puces de formation de faisceau (scène 64 ; sources secondaires 20 grandes + 640 petites, ou 80 + 640), éléments (1 200 estimé ; 1 280 avec éléments factices de bord), alimentation (« sonde » ; démontage : couplage par fente — `play.stack`, `intro.cutaway`), structure (pastilles rondes empilées, grille hexagonale, cavités d'air ; nous : pastille carrée sur εr ≈ 3 — `intro.arrival`, `intro.cutaway`, `entity.element.description`, `play.resonance`). Rien trouvé sur l'espacement des éléments, la permittivité ni l'épaisseur du substrat. Les éléments sont modélisés comme des sources ponctuelles.
- **Ciel bleu, corrections proposées, en attente de l'accord de l'utilisateur** (mécaniques, textes inchangés) : τ(550 nm) = 0,09707 (Bodhaine, tableau 3) au lieu de 0,0973 (`sources.json` + `TAU_550` du simulateur + tests) ; hauteur d'échelle 8,4 km (utexas) au lieu de 8 km ; molécules ≈ 0,35 nm (rapport ≈ 1 400) au lieu de 0,3 nm.
- Sources non ouvertes : `metoffice-sunset` (404), `iau-2015-b3` (ADS), `adi-phased-array-2` (403), `tuberlin-ula` (menu seul), `kasten-young-1989` (formule vérifiée dans le code pvlib, article non ouvert) ; `hackaday-teardown` et `wyman-2013` remplacées par des pages ouvertes.
- `_KNOWN_PROJECTS` (`projects/assistant-ia/app/slack_app.py`) n'a pas `exploration-science` : à ajouter au prochain déploiement d'assistant-ia si on veut `/feature` sur ce projet.
- Termes vers des nœuds pas encore écrits (`rayleigh-scattering`, `visible-spectrum`, `circular-orbit`…) : soulignés, non cliquables. Wikidata de la diffusion Rayleigh : Q193709, pour le futur nœud principe.
- Page de revue : publication bloquée depuis le jalon 4 (l'outil la prend pour une page « artifact-pr-review ») ; la version en ligne (https://claude.ai/artifact/9TpKGxucXtCtH5uMRcBGPo) date du jalon 3.
- Plongée = vol + fondu + coupe, pas de morphing géométrique : la continuité tient au même composant affiché de part et d'autre.
- Passages orbitaux : direction et culmination fixées par le plugin ; un passage non zénithal demanderait des paramètres au catalogue (à soumettre).
- `blue-sky` : éclairage de scène resté sur `daylight` (sol clair au coucher, seule la lumière du Soleil change de couleur) ; plan « ciel vu du dehors » avec barre d'échelle à 100 m alors que le dôme n'est pas à l'échelle ; diffusion simple seulement (pas de diffusion multiple ni d'ozone), l'horizon blanchit moins que le vrai.
- Format de scène v1 : à figer après les tests utilisateurs (critère de sortie de Phase 0), en tenant compte des enseignements de l'essai de génération.

## Où démarrer
0. **V2 : `roadmap/v2.md` §2** (schémas soumis à l'utilisateur), puis §3 scène de référence itérée sur captures.
1. Si l'utilisateur a déployé ou posé les clés : vérifier le déploiement / lancer les runs API et comparer les deux profils.
2. Sinon : **roadmap Phase 1 §3, banc de non-régression** (autonome, ne dépend ni du VPS ni des tests).
3. En petit lot : rendre explicite le modèle simplifié Starlink ; appliquer les corrections ciel bleu si l'utilisateur les accepte.
Après tout changement de contenu : `npm test` et `npm run review`.
