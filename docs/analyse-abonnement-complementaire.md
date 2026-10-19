---
role: >
  Décide quel abonnement complémentaire (~30 €/mois) ajouter à Claude Pro pour que Claude Code
  (orchestrateur CONTROL_SYSTEM) délègue en CLI non interactif. Analyse datée du 2026-10-19.
status: analyse — recommandation, rien d'installé
---

# Abonnement complémentaire à Claude Pro — analyse du 2026-10-19

> **Légende des niveaux de preuve** — **[VPS]** vérifié sur le VPS · **[OFF]** source officielle de
> l'éditeur · **[UTIL]** retour d'utilisateur ou mesure tierce · **[HYP]** hypothèse ou calcul de ma
> part. Toute valeur sur les offres vient d'une recherche web du 2026-10-19. **Aucune ne doit
> être relue de mémoire après cette date** : prix, quotas et modèles ont changé plusieurs fois
> rien qu'en septembre-octobre 2026.

## TL;DR

**Recommandation : ChatGPT Plus (23 € TTC/mois), avec Codex CLI (`codex exec`).** C'est la seule
des trois offres qui réunit à la fois l'autorisation explicite du scénario visé (un orchestrateur
qui appelle le CLI officiel), un modèle de premier plan en code agentique (GPT-6.1 Sol) et une
sortie machine propre (`--json`, `--output-schema`).

- **Google AI Pro est éliminé par les CGU, pas par la qualité.** Google interdit explicitement
  qu'un agent tiers (Claude Code est cité nommément) pilote `agy` avec une connexion grand public,
  et applique cette règle par des suspensions automatiques [OFF].
- **X Subscription Premium (ex-SuperGrok)** est le second choix. Le CLI est déjà installé et
  l'automatisation est explicitement prévue, mais le modèle est nettement plus faible en tâches
  terminal, l'offre a été refondue il y a 7 jours et les premiers abonnés voient leur pool fondre
  en un jour.
- **Ce qui ferait changer d'avis** : un test d'une semaine où le pool hebdomadaire Plus s'épuise
  en moins de 3 jours sur le flux délégué, **ou** un taux d'acceptation sous 60 % (§7).

---

## 1. Audit du VPS (lecture seule)

### 1.1 Comment CONTROL_SYSTEM découpe, route, lance et valide [VPS]

Source : `CLAUDE.md` et `CONTROL_SYSTEM.md` (472 lignes, lus intégralement).

| Étape | Mécanisme réel |
|---|---|
| Découpage | Roadmap figée → **lot de conversation** auto-planifié, découpé par *contexte partagé* ; inventaire d'actions [A]/[C]/[D]/[P] (§3) |
| Routage | Orchestrateur **Opus** (diagnostic, remède, spec, revue) ; worker **Sonnet** via l'outil `Agent` (`model: sonnet`) pour la recherche, la mesure et l'exécution d'une spec écrite (§6, §8) |
| Lancement | Interactif dans le terminal (« reprends le projet X… ») ; la nuit, `/srv/auto-loop/autoloop.sh` (`claude -p`, DeepSeek via `flexproxy.py` → DeepInfra, plafond de budget côté proxy) |
| Validation | Revue fixe en 5 points après délégation (git status, diff, mutations, suite complète, rejeu réel) ; contrat de compte-rendu en 5 rubriques ; vanne de validation de nuit (`/revue-nuit`) |

Conséquence pour le choix : CONTROL_SYSTEM a **déjà** un contrat de délégation (§6), et c'est sa
classe 3, « exécution d'une spec écrite après diagnostic », qu'un CLI externe peut prendre. Le
diagnostic, le remède et la revue restent chez Claude. Ce n'est pas un nouveau protocole à
inventer : c'est un **second exécutant** pour un contrat qui existe déjà.

### 1.2 CLI installés et traces multi-modèles [VPS]

| Outil | État constaté |
|---|---|
| `codex` | **absent** |
| `gemini` / `agy` | **absents** ; aucun `~/.gemini` |
| `grok` | **installé** : Grok Build **1.0.41** (`~/.grok/bin/grok`, lien `/usr/local/bin/grok-build`), connecté en OIDC le 2026-09-26. Les logs disent `subscriptionTier: "Free"` et `paywall_check_no_subscription`. Une seule session, **0 échange réel** (3 messages système). `~/.grok` pèse 352 Mo |
| `/root/grok` | script Python `grok up/down` : redimensionne le VPS Hetzner CX23→CX43 pour lancer `grok-build` dans tmux, puis le redescend. **C'est une idée outillée, pas un usage** : aucune trace d'exécution réussie de Grok Build |
| DeepInfra | **réel** : `flexproxy.py` + boucle de nuit (DeepSeek V4 Flash, ~717 tours dans les transcripts) et clients applicatifs (`assistant-ia`, `newsletter-summary`). La boucle `horizon-scan` est **à l'arrêt** : elle refuse chaque nuit de démarrer tant qu'une branche n'est pas validée (log du 2026-10-18), et le dernier ledger non vide date du 2026-08-28 |
| `gemini-*` dans le code | modèles applicatifs via Dust (`portfolio-tracker`), sans lien avec l'outillage de développement |

### 1.3 Profil de consommation Claude Code [VPS]

Méthode : script Python sur les 211 transcripts `~/.claude/projects/**/*.jsonl` (2026-08-28 →
2026-10-19), dédoublonnés par `message.id`. `ccusage` n'est pas installé ; ces chiffres le
remplacent.

| Indicateur | Valeur |
|---|---|
| Jours actifs | 43 sur 53 |
| Sessions / jour actif | **3,8** |
| Tours modèle / jour actif | **~427** (dont ~30 en sous-agent, soit 7 %) |
| Tokens de sortie / jour actif | ~324 k |
| Contexte lu par tour (session principale) | médiane **130 k**, p90 **331 k**, max 696 k |
| Tokens d'entrée cumulés / jour actif (cache compris) | ~69 M, dont ~66 M en lecture de cache |
| Modèles | Opus 5 / 5.5 / 4.8 ≈ 82 % des tours ; Sonnet ≈ 14 % ; DeepSeek (commande `ds`) ≈ 4 % |
| Délégations `Agent` | **34 au total**, toutes vers Sonnet en `general-purpose` |
| Butées de quota | **12 messages « You've hit your monthly spend limit »** (extra usage plafonné à 5 €/mois, réponse de l'utilisateur), répartis sur 9 jours |
| Outils | Bash 11,6 k (dont tests/checks ~2,0 k, docker exec/logs ~1,8 k, lectures/grep ~2,5 k), Edit 2,8 k, Read 2,0 k, Write 0,6 k |
| Sujet des sessions | 2026-10 : très majoritairement « continue le projet portfolio-tracker » ; le 2026-10-18, trois sessions demandent explicitement « délègue à Sonnet quand c'est pertinent » |

Lecture :
- **Le goulot est le quota Claude, pas le temps humain** : butées répétées, extra usage bridé
  volontairement.
- **Le contexte est lourd** (médiane 130 k) parce qu'une session porte reprise, roadmap, code et
  journaux. Un exécutant externe qui reçoit une spec courte coûte bien moins en contexte que la
  même tâche faite inline. C'est l'argument de fond de la délégation.
- **La part délégable est aujourd'hui sous-exploitée** (7 % des tours en sous-agent), alors que
  CONTROL_SYSTEM §6 la décrit comme rentable depuis le 2026-10-16.
- [HYP] Valorisée au tarif API d'Opus 5.5 (4 $/20 $ par Mtok, lecture de cache 0,20 $, source
  emergent.sh, 2026-10-15), une journée active représente **~30 $** d'équivalent API. Cet ordre de
  grandeur sert d'étalon au §3.

### 1.4 Contraintes d'infrastructure [VPS]

| Contrainte | Constat | Effet sur le choix |
|---|---|---|
| OS | Ubuntu 24.04.4, x86_64 | les trois CLI ont un binaire Linux |
| CPU / RAM | **2 vCPU, 3,7 Go, pas de swap** ; `claude` occupe ~540 Mo, plus une dizaine de conteneurs | un seul exécutant à la fois ; pas de parallélisme local sans rescale (script `/root/grok` réutilisable, CX43) |
| Disque | **2,6 Go libres (93 %)** | installer un binaire (≈100-300 Mo) passe ; vérifier `df` avant (mémoire « Vérifier le disque avant docker pull ») ; prévoir des worktrees éphémères |
| Réseau | UFW actif, seul 22/tcp ouvert ; Tailscale actif | l'auth OAuth sortante fonctionne ; pas de port entrant à ouvrir |
| Auth headless | aucun navigateur sur le VPS | Codex : `codex login --device-auth` ou recopie d'`auth.json` [OFF] ; Grok : navigateur ou `XAI_API_KEY` [OFF] ; agy : URL + code collé [OFF] |
| Secrets | `.env` en 600 hors git, `/root/secrets` en 700 ; le proxy de nuit isole déjà une clé derrière un jeton factice | le jeton OAuth de l'exécutant (`~/.codex/auth.json`) doit rester sous root, hors des worktrees |
| Coolify | dormant depuis le 2026-09-03 ; `docker compose` standalone | aucun impact : l'exécutant tourne sur l'hôte, pas dans un conteneur applicatif |

---

## 2. Les trois offres au 2026-10-19

### 2.1 ChatGPT Plus → Codex CLI

| Point | Constat |
|---|---|
| Prix | **23 € TTC/mois** en France, prix fixe en euros, sans formule annuelle [UTIL : promptfacile.fr 2026-10-05, geotoolbox.ai 2026-10-14, cohérent avec 20 $ sur la page OpenAI] |
| Modèles Codex | GPT-6.1 Sol (défaut, sorti le 2026-09-29), GPT-6 Luna, GPT-6 Astra limité. GPT-5.5 retiré de Codex le 2026-10-14 [OFF : developers.openai.com/codex/pricing, 2026-10-18] |
| Limites | **fenêtre glissante de 5 h** + **plafond hebdomadaire non publié**. Messages locaux / 5 h sur Plus : Sol 15-160, Astra 5-45, Luna 350-3 000 (« estimations, pas des limites fixes ») [OFF, même page] |
| Au dépassement | le tour en cours se termine, puis blocage jusqu'au reset, sauf achat de crédits ChatGPT ou bascule sur clé API au tarif API. **Pas de facturation automatique** [OFF] |
| Contexte | 500 k par défaut dans Codex depuis le 2026-10-11, surcoût long contexte retiré pour les abonnés [UTIL : neoteo.com 2026-10-12, d'après DiarioBitcoin] |
| Historique des limites | 5 h retirée en juillet, **rétablie le 2026-08-25** pour Plus [UTIL : TechRepublic 2026-08-26] ; plaintes de fonte en avril 2026 sur Business [UTIL : forum OpenAI 2026-04-04] ; resets offerts début septembre [OFF : help center] |
| Mode non interactif | `codex exec` : sandbox lecture seule par défaut, `--sandbox workspace-write`, `--json` (flux JSONL : `turn.completed`, `turn.failed`, `error`…), `--output-schema` + `-o`, prompt sur stdin (`codex exec -`), `--ephemeral` [OFF : developers.openai.com/codex/noninteractive, 2026-10-16] |
| Auth headless | auth ChatGPT réutilisée par `codex exec` ; procédure CI documentée avec un compte ChatGPT (« advanced ») : déposer `auth.json`, le laisser se rafraîchir sur place. OpenAI recommande la clé API pour l'automatisation, sans interdire l'abonnement [OFF : même page et /codex/auth] |
| CGU / risque de compte | **faible**. L'usage scripté du CLI officiel est documenté par l'éditeur, et le responsable Codex a publiquement approuvé l'usage des abonnements dans des harnais tiers [UTIL : The Register 2026-02-20]. Point d'attention : l'entraînement sur les données est actif par défaut sur Plus, il faut le **désactiver dans les Data Controls** [OFF : help center] |

### 2.2 Google AI Pro → Antigravity CLI (`agy`)

| Point | Constat |
|---|---|
| Prix | **21,99 € TTC/mois** (5 To de stockage inclus) [OFF : one.google.com/intl/fr_fr, relevé le 2026-10-19] |
| CLI | **Gemini CLI ne sert plus les abonnés AI Pro depuis le 2026-06-18**, remplacé par Antigravity CLI `agy` [OFF : Google Developers Blog 2026-05-19]. Jules n'apparaît plus comme surface de développement principale ; tout passe par Antigravity |
| Modèles | Gemini 3.8 Flash (cheval de trait) ; Gemini 3.1 Pro retiré le 2026-10-12 [UTIL : forum Google 2026-10-14] ; **Gemini 4 Argon** ouvert aux Pro payants le 2026-10-15 avec un quota **hebdomadaire seul**, séparé de Flash [UTIL : @antigravity cité par pasqualepillitteri.it 2026-10-16]. Contradiction le 2026-10-14 sur le forum (« Ultra seulement ») : **l'accès Pro à Argon est instable** |
| Limites | « high, generous quota, refreshed every five hours until the weekly limit » ; aucun chiffre publié ; « primarily determined by available capacity » [OFF : antigravity.google/docs/plans] |
| Limites mesurées | très dispersées : un utilisateur fait 5 h continues de Flash 3.8 pour 5 % de l'hebdo [UTIL : Reddit, ~2026-10-15] ; un autre est **verrouillé 51 h après 5 appels**, avec trois compteurs contradictoires [UTIL : forum Google 2026-10-12] ; Argon « vide 5 h en 30-45 min » même sur Ultra [UTIL : Reddit] |
| Au dépassement | blocage, ou crédits IA au tarif Gemini Enterprise [OFF] ; signalé : verrou de **tout le compte**, Flash compris [UTIL] |
| Mode non interactif | `agy -p`, `--output-format json`, `--model`, `--continue` ; échec franc si non authentifié [OFF : docs/cli/headless] |
| CGU / risque de compte | **éliminatoire pour ce scénario**. CGU §6 : utiliser un logiciel tiers pour accéder au service est une violation, avec suspension possible [OFF : antigravity.google/terms]. FAQ : « Wrapping `agy` inside third-party coding agents or applications […] is not supported under consumer plans » [OFF : docs/faq]. Réponse sur le forum officiel (2026-10-07/08) : « we do not support using third-party coding agents (like Codex, **Claude Code**, …) to orchestrate or wrap `agy` under a consumer login. […] can trigger **automated ToS enforcement and account suspension** ». Vagues de bannissements documentées en février, mars et juin 2026 [UTIL : forum Google] |
| Échappatoire | clé API AI Studio (facturée au token). AI Pro inclut 10 $/mois de crédits Cloud [UTIL : bleap.finance] : ~1 M de tokens Argon en sortie, négligeable |

### 2.3 SuperGrok → **X Subscription Premium** (Grok Build)

| Point | Constat |
|---|---|
| Changement d'offre | **SuperGrok n'accepte plus de nouveaux abonnés depuis le 2026-10-12**, remplacé par *The X Subscription* (Grok + Grok Bot + Cursor + X Premium) [OFF : x.ai/news/x-subscription] |
| Palier à ~30 € | **Premium : 30 $/mois HT** (300 $/an), « 4x Plus », annoncé comme reprenant SuperGrok + Cursor Pro + X Premium+ ; promo affichée : **-50 % le premier mois** [OFF : x.ai/pricing, grok.com/plans]. Prix TTC en euros non publié : **~31 € TTC** [HYP : 30 $ ≈ 25,8 € HT + TVA 20 %] |
| Modèle | Grok 4.7 (sorti le 2026-09-21), contexte 500 k [VPS : `models_cache.json` ; OFF : docs.x.ai] |
| Limites | **un seul pool hebdomadaire** partagé par Chat, Imagine, Voice, Build, API, **Grok Bot et Cursor**, sans taille publiée (« multiples de Plus ») [OFF : x.ai/pricing, docs.x.ai/x-subscription/pricing] |
| Limites mesurées | Premium vidé **le premier jour** en usage Cursor + Grok Bot ; 6-7 % de l'hebdo pour deux prompts courts ; Super (100 $) ≈ 2,1 G tokens/mois contre 2,5 G sur l'ancien Cursor Pro+ [UTIL : forum Cursor, 2026-10-13 à 15]. Mesures d'une semaine d'existence, en partie liées à un incident Grok Bot |
| Au dépassement | pause des fonctions payantes, recharge (« top-ups ») ou attente du reset [OFF : FAQ] |
| Mode non interactif | `grok -p`, `--output-format json|streaming-json`, `--json-schema`, `--max-turns`, `--permission-mode`, `--always-approve`, `--prompt-file`, `--worktree` ; ACP pour l'orchestration [VPS : `grok --help` ; OFF : x.ai/news/grok-build-cli « Headless mode (`-p`) allows easily running agents inside scripts and automations »] |
| Auth headless | déjà faite en OIDC sur le VPS [VPS] ; sinon `XAI_API_KEY` (facturée à part) [OFF] |
| CGU / risque de compte | **faible à moyen** : l'automatisation et l'orchestration via ACP sont explicitement promues ; pas d'interdiction trouvée. Opt-out d'entraînement déjà actif sur ce compte (`coding_data_retention_opt_out: true`) [VPS] |

---

## 3. Valeur subventionnée (équivalent API)

Méthode : capacité hebdomadaire estimée × tarifs API publics du même modèle, × 4,3 semaines. Les
tarifs API viennent des sources officielles ou d'agrégateurs datés : GPT-6.1 Sol **2 $/10 $**,
cache 0,10 $ [OFF : openai.com, 2026-09-29] ; Gemini 3.8 Flash **0,75 $/3,75 $** [UTIL :
benchleader] ; Gemini 4 Argon **2 $/10 $** jusqu'au 30/11, puis 4 $/20 $ [UTIL : LiteLLM
2026-10-19] ; Grok 4.7 **2 $/6 $**, cache 0,50 $ [UTIL : OpenRouter, benchlm].

| Offre | Ancre de capacité | Équivalent API / mois (usage maximal réaliste) | Ratio vs prix |
|---|---|---|---|
| ChatGPT Plus | « Codex Quota Observatory » : sur un compte Pro 20×, **1 % = 35,9 M tokens Sol** (cache compris, 2026-09) [UTIL : 1 seul compte] ; Plus ≈ 1/20 de Pro 20× [UTIL : même site, ratio non officiel] ; replay API publié par le site pour Pro 20× : 1 219 $ / 4 semaines (mix Astra rejoué au tarif Sol) | **60-240 $** [HYP : ÷20 linéaire, borne haute en Sol pur]. Fenêtres de 5 h et usage diurne seul : **~40-150 $ réellement consommables** | ×2 à ×7 |
| Google AI Pro | Flash 3.8 : 5 h continues = 5 % de l'hebdo [UTIL : 1 témoignage] ; Argon : quelques tâches par semaine | Flash : **100-400 $** théoriques, mais sur un modèle faible en tâches terminal (§4) ; Argon : **<20 $** | élevé en théorie, sans objet ici (CGU) |
| X Premium | Super (15×) ≈ 2,1 G tokens/mois mesurés dans Cursor → Premium (4×) ≈ **560 M tokens/mois**, très majoritairement en cache [UTIL + HYP] | **~100-400 $** sur le papier ; témoignages de pool vidé en un jour, donc **borne basse non garantie** | ×3 à ×13, fragile |

Rapportés à l'étalon §1.3 (~30 $ d'équivalent API par jour actif sur Claude, soit ~1 000 $/mois),
**chaque option ajoute de l'ordre de +5 à +15 % de capacité brute**. Le gain réel dépend surtout de
la part de travail **qui peut sortir de Claude sans devoir être refaite** (§5).

**Risque de resserrement** :

| Offre | Signaux | Risque |
|---|---|---|
| OpenAI | fenêtre de 5 h retirée puis rétablie (juil. → 25/08) ; plafond hebdo non publié ; modèles retirés tous les 1-2 mois ; mais baisses de prix API (GPT-6 Sol -50 %) et resets offerts | **moyen** |
| Google | Gemini CLI supprimé (06/2026), modèles retirés d'un coup (12/10), accès Argon qui varie d'un jour à l'autre, quotas qui dépendent explicitement de la « capacity », tarif d'Argon doublé au 01/12, plaintes récurrentes depuis mars | **élevé** |
| xAI | offre refondue il y a 7 jours, pool désormais partagé avec Cursor et Bot, tailles jamais publiées, premiers retours de fonte | **élevé** |

---

## 4. Qualité en développement

Les benchmarks se contredisent selon le harnais utilisé : seuls les écarts importants comptent.
Terminal-Bench 4.0 est le plus proche du travail de ce VPS (shell, déploiement, débogage en
terminal).

| Modèle (offre) | Terminal-Bench 4.0 | Autres indicateurs | Source / date |
|---|---|---|---|
| **Claude Opus 5.5** (référence) | **64,9-66,4 %** (1ᵉʳ) | SWE-bench Pro 89,9 % (éditeur) | benchlm 2026-10-15/16 |
| **GPT-6.1 Sol** (Plus) | **54-56 %** max effort (Vals 55,0, AA 56,1) | DeepSWE 75,2 % (éditeur) ; AA Intelligence 52 vs Opus 5.5 58 | benchleader 2026-10-19, emergent 2026-09-30 |
| **Gemini 4 Argon** (Pro, quota hebdo) | 57,4 % (éditeur) | DeepSWE 77,9 % (éditeur), 1ᵉʳ du Vals Index | dealntech 2026-10-13 |
| **Gemini 3.8 Flash** (Pro, cheval de trait) | **~19-20 %** | DeepSWE 73,8 % ; TB 2.1 89 % (saturé) | tbench.ai, benchleader |
| **Grok 4.7** (X Premium) | **28,8 % (Vals) - 38 % (benchlm)** | Vals Index 55,0 vs Sonnet 5.5 67,0 ; SRE Bench 3,8 % vs 30 % | vals.ai, benchlm 2026-10-16 |

Retours de terrain [UTIL] :
- **Flash 3.8** : « wandered around the codebase for minutes », « garbage for coding » (Reddit et
  forum Google, 2026-10).
- **Argon** : jugé excellent en audit et détection de bugs, mais dévoreur de quota.
- **GPT-6.1 Sol** : présenté comme « near-Astra » ; c'est le modèle par défaut de Codex.
- **Grok 4.7** : peu de retours qualitatifs, et ceux qui existent portent sur la consommation du
  pool, pas sur la qualité du code.

### Complémentarité avec Claude

| Type de tâche (ce VPS) | GPT-6.1 Sol | Grok 4.7 | Gemini 3.8 Flash / Argon |
|---|---|---|---|
| Exécution d'une spec écrite (Python/FastAPI, checks) | **≈ équivalent** à Sonnet | moins bon | Flash moins bon ; Argon ≈ |
| Mesure / ligne de base (lancer, relever, ne pas conclure) | ≈ | ≈ (rapide, peu cher) | Flash ≈ |
| **Revue croisée d'un diff** (second regard, détection de bugs) | **bon**, et utile parce que d'une autre famille de modèles | moyen | Argon très bon d'après les retours, mais quota |
| Débogage en terminal / déploiement | ≈, un cran sous Opus | nettement moins bon | Flash nettement moins bon |
| Diagnostic, choix du remède, arbitrage métier | **reste chez Claude** (CONTROL_SYSTEM §6) | idem | idem |
| Long contexte (gros fichiers de reprise) | 500 k | 500 k | 1 M |

---

## 5. Ce qu'on peut déléguer dans CONTROL_SYSTEM, et le gain attendu

Les classes viennent de CONTROL_SYSTEM §6. Les parts sont des **[HYP]** calées sur le profil §1.3 ;
elles sont faites pour être réfutées par le test du §7.

| Classe CONTROL_SYSTEM | Exemples sur ce VPS | Délégable à Codex (Sol) | à Grok 4.7 | Part du volume Claude actuel |
|---|---|---|---|---|
| 3. Exécution d'une spec écrite après diagnostic | correctif portfolio-tracker spécifié (fichiers, règle, mutations), boilerplate, migrations, nouveaux `check_*.py` | **oui** | oui, avec plus de reprises | ~15-25 % |
| 2. Mesure / ligne de base, « faits seulement » | rejeu à blanc, inventaire de journaux, décompte en base, `docker exec … grep` | oui (sandbox à régler) | oui | ~5-10 % |
| 1. Recherche | « où X est défini », balayage de N fichiers | oui, mais le gain est faible (un filtre shell suffit souvent) | oui | ~2-5 % |
| Revue croisée **comme signal** (pas comme décision) | `codex exec` sur le diff avant la revue fixe en 5 points | **oui, valeur ajoutée propre** | moyen | nouveau |
| Boucle de nuit | remplacer DeepSeek dans `autoloop.sh` | possible plus tard ; entre en concurrence avec le quota diurne ; la vanne de validation bloque de toute façon | possible | hors périmètre de la semaine de test |
| Diagnostic, remède, revue, déploiement à privilège | — | **non** (§6 + « un sous-agent ne négocie jamais de permissions ») | non | — |

**Ordre de grandeur des tâches absorbées hors quota Claude** [HYP] :

| Offre | Tâches absorbées | Raisonnement |
|---|---|---|
| ChatGPT Plus | **15-25 %** | ~40 % de volume délégable × ~60-70 % d'acceptation sans reprise × plafond hebdo Plus. La revue reste chez Claude et coûte environ 10-20 % de la tâche inline. Gain net estimé de **+10 à +20 %** de capacité de développement |
| X Premium | **5-12 %** | même volume, mais acceptation plus basse sur les tâches terminal et pool incertain |
| Google AI Pro | **0 % dans le scénario demandé** | CGU. Hors orchestration, usage manuel séparé possible, mais ce n'est pas l'objectif |

---

## 6. Tableau comparatif

| | **ChatGPT Plus (Codex)** | **Google AI Pro (agy)** | **X Premium (Grok Build)** |
|---|---|---|---|
| Prix TTC | **23 €** [OFF/UTIL] | 21,99 € [OFF] | ~31 € [HYP] (-50 % le 1ᵉʳ mois) |
| Quota réel utile / mois | 5 h + hebdo non publié ; ~40-150 $ équivalent API consommables | Flash généreux mais erratique ; Argon quelques tâches/semaine | pool hebdo partagé, non publié ; témoignages de fonte en 1 jour |
| Valeur API équivalente | 60-240 $ | 100-400 $ (Flash) | 100-400 $ (papier) |
| Qualité code (TB 4.0) | **~55 %** | Flash ~20 % / Argon ~57 % | ~29-38 % |
| Friction d'intégration VPS | faible : binaire, `--device-auth`, `--json`, `--output-schema` | faible techniquement | **la plus faible** : déjà installé et connecté |
| Risque CGU | **faible** (scripté documenté par l'éditeur) | **rédhibitoire** (orchestration par Claude Code interdite nommément, enforcement automatique) | faible à moyen |
| Risque de dégradation de l'offre | moyen | élevé | élevé |
| Données | désactiver l'entraînement (Data Controls) | « Interactions » relues par des humains sauf opt-out | opt-out déjà actif |

---

## 7. Recommandation et plan de test d'une semaine

### Recommandation unique : **ChatGPT Plus + Codex CLI**

Pourquoi lui et pas un autre : c'est la seule offre où les trois conditions sont vraies en même
temps.
1. Le scénario exact (Claude Code appelle un CLI) est permis.
2. Le modèle est assez bon pour que la revue en 5 points ne tourne pas à la réécriture.
3. Le contrat de sortie est machine-lisible.

**Conditions qui feraient changer d'avis** :
- **Pool Plus épuisé en moins de 3 jours** sur le flux délégué de la semaine de test → passer à X
  Premium. Son pool est peut-être plus gros en tokens, et l'outil est déjà installé ; le tester
  sur la même grille.
- **Taux d'acceptation sous 60 %**, ou revue Claude qui coûte plus de 40 % de l'inline → la
  délégation ne paie pas. Mieux vaut alors mettre les 23 € dans le passage à un plan Claude
  supérieur ou dans l'extra usage.
- **Google publie une autorisation explicite** d'orchestration de `agy` par un agent tiers sous
  abonnement → réévaluer AI Pro : Argon est le meilleur des trois sur le papier.
- OpenAI **retire la fenêtre de 5 h** ou **publie le plafond hebdo** → recalculer le §3.

### Plan de test (7 jours)

**J0 — installation** (à faire par l'orchestrateur ; rien n'est installé aujourd'hui)
1. `df -h /` (≥ 1 Go libre exigé) ; installer Codex CLI (binaire officiel) ; `codex --version`.
2. `codex login --device-auth` ; ChatGPT → Data Controls → **désactiver l'entraînement**.
3. Test négatif du wrapper (§8) : un prompt qui doit dépasser le timeout → exit 124 nommé ; une
   auth retirée → exit « auth ». Un wrapper qui n'a jamais rougi n'est pas éprouvé.

**J1-J6 — 15 à 25 tâches réelles, tirées de l'inventaire en cours (portfolio-tracker d'abord)**
- Répartition visée : ~60 % classe 3 (spec écrite), ~25 % mesures, ~15 % revues croisées de diff.
- 3 tâches en **A/B** : même spec à Codex et à un sous-agent Sonnet, pour comparer qualité et
  coût de revue.
- Pour chaque tâche, une ligne de ledger (produite par le wrapper) :

| Mesure | Comment |
|---|---|
| Quota consommé | `/status` (5 h et hebdo, en %) avant et après ; tokens de `turn.completed` (`--json`) |
| Réussite | verdict de la revue en 5 points : **accepté tel quel / reprise mineure / rejeté** |
| Temps de validation | tours et tokens Claude consacrés à la revue (transcript), et temps mur |
| Coût évité | estimation des tokens Claude qu'aurait demandé la tâche inline (tâches A/B pour calibrer) |
| Incidents | timeout, quota, auth, fichier parasite (`git status`) |

**J7 — décision**, sur trois seuils écrits **avant** le test :
- acceptation (tel quel + reprise mineure) ≥ 60 % ;
- pool hebdo Plus non épuisé avant J5 au rythme du test ;
- coût de revue ≤ 30 % de l'inline estimé.

Si les trois passent : garder, puis inscrire la règle de routage dans CONTROL_SYSTEM §6/§8 (un
ajout d'une ligne, et la suppression de ce qui devient faux). Sinon, appliquer la bascule prévue
plus haut.

---

## 8. Esquisse du wrapper CLI (non installé)

Principes, tirés des règles déjà en vigueur sur ce VPS :
- **Borné par unité** (« un blocage est un état muet ») : timeout interne → échec nommé, jamais
  une attente silencieuse.
- **Un seul binaire à autoriser** : le `timeout` vit *dans* le script. Sinon la règle de
  permission `Bash(delegate:*)` est neutralisée (« règles de permission = préfixes »).
- **Travail en worktree jetable** : l'exécutant ne commite jamais ; Claude relit le diff (revue en
  5 points).
- **Pas de secret dans l'environnement** de l'exécutant ; `auth.json` reste sous root, hors du
  worktree.
- **Sortie au format du contrat de CONTROL_SYSTEM §6** (5 rubriques), imposée par `--output-schema`.
- **Ledger JSONL** ; code de sortie = bilan reconnaissable (« un bilan se reconnaît à sa forme »).

```bash
#!/usr/bin/env bash
# infrastructure/delegate.sh <engine> <repo> <spec.md> [timeout_s]
# engine : codex (défaut) | grok. Une ligne de bilan en dernière sortie :
#   DELEGATE: ok|timeout|quota|auth|error — <worktree> — <tokens in/out>
set -uo pipefail
ENGINE="${1:?}"; REPO="${2:?}"; SPEC="${3:?}"; T="${4:-1800}"
ID="$(date +%Y%m%dT%H%M%S)-$ENGINE"
WT="/srv/delegate/wt/$ID"; OUT="/srv/delegate/runs/$ID"; mkdir -p "$OUT"
git -C "$REPO" worktree add -q --detach "$WT" HEAD || { echo "DELEGATE: error — worktree"; exit 5; }

case "$ENGINE" in
  codex) timeout --kill-after=30 "$T" env -i HOME="$HOME" PATH="$PATH" \
           codex exec --ephemeral --sandbox workspace-write --cd "$WT" \
             --json --output-schema /srv/delegate/report.schema.json -o "$OUT/report.json" \
             - < "$SPEC" > "$OUT/events.jsonl" 2> "$OUT/stderr.log" ;;
  grok)  timeout --kill-after=30 "$T" env -i HOME="$HOME" PATH="$PATH" \
           grok -p "$(cat "$SPEC")" --cwd "$WT" --output-format json \
             --json-schema "$(cat /srv/delegate/report.schema.json)" \
             --permission-mode acceptEdits --max-turns 60 --no-subagents \
             > "$OUT/report.json" 2> "$OUT/stderr.log" ;;
esac
rc=$?
status=ok
[ $rc -eq 124 ] && status=timeout
grep -qiE 'usage limit|rate limit|quota' "$OUT/stderr.log" "$OUT/events.jsonl" 2>/dev/null && status=quota
grep -qiE 'not logged in|authentication required|401' "$OUT/stderr.log" 2>/dev/null && status=auth
[ $rc -ne 0 ] && [ "$status" = ok ] && status=error
git -C "$WT" diff --stat HEAD > "$OUT/diffstat.txt"
# ledger : une ligne par appel, lue par la revue du matin / le test J7
python3 /srv/delegate/ledger.py "$ID" "$ENGINE" "$status" "$rc" "$OUT" >> /srv/delegate/ledger.jsonl
echo "DELEGATE: $status — $WT — $(tail -1 /srv/delegate/ledger.jsonl | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("tokens","?"))')"
case $status in ok) exit 0;; timeout) exit 124;; quota) exit 3;; auth) exit 4;; *) exit 1;; esac
```

`report.schema.json` impose les 5 rubriques du contrat worker (interprétation, fichiers modifiés,
décisions, vérification lancée et résultat, ambiguïtés tranchées). Côté Claude, l'appel est un
simple `Bash` avec `run_in_background`, suivi de la revue en 5 points sur `$WT`. Le nettoyage
(`git worktree remove`) se fait après la revue, jamais avant.

À vérifier lors de l'installation, avant de figer ce script :
- noms exacts des flags de la version installée (`codex exec --help`, `grok --help`) ;
- texte réel des erreurs de quota et d'auth, à capturer une fois puis à mettre dans les `grep` ;
- comportement de `env -i` vis-à-vis du stockage des credentials.

---

## Sources (consultées le 2026-10-19)

**OpenAI**
- [OFF] developers.openai.com/codex/pricing — limites Plus, tarifs en crédits, dépassement (page datée 2026-10-18)
- [OFF] developers.openai.com/codex/noninteractive — `codex exec`, `--json`, `--output-schema`, auth CI (2026-10-16)
- [OFF] developers.openai.com/codex/auth — stockage d'`auth.json`, API key vs ChatGPT
- [OFF] help.openai.com/en/articles/11369540 — dépassement, entraînement sur les données Plus
- [OFF] openai.com/index/introducing-gpt-6-1-sol — tarifs API GPT-6.1 Sol (2026-09-29)
- [UTIL] techrepublic.com — rétablissement de la fenêtre de 5 h (2026-08-26)
- [UTIL] promptfacile.fr (2026-10-05), geotoolbox.ai (2026-10-14) — 23 € TTC en France
- [UTIL] codex-quota.manetli.com — mesures de quota sur un compte Pro 20× (données au 2026-10-15)
- [UTIL] community.openai.com « Codex Rate Limits Discussion Thread » (2026-04-04)
- [UTIL] theregister.com — position d'OpenAI sur les harnais tiers (2026-02-20)

**Google**
- [OFF] one.google.com/intl/fr_fr/about/google-ai-plans — 21,99 €/mois
- [OFF] antigravity.google/docs/plans, /docs/cli/headless, /docs/cli/install, /docs/faq, /terms
- [OFF] developers.googleblog.com — transition Gemini CLI → Antigravity CLI (2026-05-19)
- [OFF/UTIL] discuss.ai.google.dev — t/187241 (2026-10-08, orchestration par Claude Code non supportée), t/188232 (2026-10-12, verrou après 5 appels), t/131424 (2026-03-12, bannissements)
- [UTIL] pasqualepillitteri.it — quota Argon hebdo pour Pro (2026-10-16)
- [UTIL] reddit r/google_antigravity — retours sur Flash 3.8 et Argon (~2026-10-15)

**xAI**
- [OFF] x.ai/news/x-subscription (2026-10-12), x.ai/pricing, grok.com/plans
- [OFF] docs.x.ai/x-subscription/pricing (2026-10-11), docs.x.ai/grok/faq (2026-10-10), docs.x.ai/build/overview
- [OFF] x.ai/news/grok-build-cli — mode headless
- [UTIL] forum.cursor.com « Introducing The X Subscription » — pool vidé en un jour, ~2,1 G tokens sur Super (2026-10-13 à 15)

**Benchmarks et tarifs API**
- [UTIL] benchleader.com (GPT-6.1 Sol, Gemini 3.8 Flash, données au 2026-10-19)
- [UTIL] benchlm.ai (Terminal-Bench 4.0 au 2026-10-15 ; Opus 5.5 vs Grok 4.7 au 2026-10-16)
- [UTIL] vals.ai (Sonnet 5.5 vs Grok 4.7)
- [UTIL] dealntech.com (Argon, 2026-10-13)
- [UTIL] emergent.sh (2026-09-30 et 2026-10-15)
- [UTIL] models.litellm.ai (Argon, 2026-10-19)
- [UTIL] openrouter.ai (Grok 4.7)
