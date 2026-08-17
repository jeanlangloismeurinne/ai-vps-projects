---
id: principe-directeur-v2
status: cadre-fondateur
created: 2026-08-11
project: portfolio-tracker
role: >
  Principe directeur de l'Architecture V2. À placer en tête de la consigne unique
  de mise en place V2 (préambule des specs fusionnées). Toute spec, tout ticket,
  toute décision d'implémentation doit s'y conformer — sur le fond (processus
  d'investissement) comme sur la forme (processus de développement).
---

# Principe directeur — Architecture V2

Ce document est la **constitution** de la V2. Il prime sur toute spec de détail :
en cas de contradiction, c'est lui qui tranche. Il définit *comment on conçoit*
(la chaîne UX → agents → données) et *quelles garanties sont non négociables*
(auditabilité, horizon long terme).

---

## 1. Le principe en trois couches

Toute fonctionnalité se conçoit et se construit dans cet ordre :

```
1. UX          → définit le contrat d'affichage (le JSON attendu à l'écran)
2. AGENTS      → logiques métier qui produisent ce JSON (jugement + délégation)
3. DONNÉES     → dérivées du besoin des agents ; alimentent la base de connaissance
                 par flux standards OU par recherche ad hoc d'agents ouvriers
```

**On part toujours de l'écran, jamais de la donnée.** L'UX fixe le contrat ; les
agents s'engagent à le produire ; les données sont exactement celles qu'il faut
pour que les agents tiennent cet engagement — ni plus, ni moins.

---

## 2. Les trois garde-fous (non négociables)

Le principe ci-dessus est un squelette. Il n'est solide qu'avec ces trois
contraintes, qui répondent aux failles identifiées à l'audit du flux
d'investissement.

### G1 — Le schéma JSON est un artefact versionné, source de vérité unique

Le contrat de la couche 1 n'est pas implicite : c'est un **schéma JSON explicite
et versionné** (JSON Schema / Pydantic). Trois consommateurs en dérivent, jamais
l'inverse — et doivent rester synchronisés (règle des « 3 points de
synchronisation ») :

1. **Prompt de l'agent** — le schéma de sortie attendu.
2. **Frontend** — l'affichage et l'édition des champs.
3. **Import / validation backend** — les champs acceptés à l'écriture.

Modifier une structure de données = modifier le schéma versionné, puis répercuter
sur les trois points **dans le même changement**. En omettre un crée une
désynchronisation silencieuse.

### G2 — La logique de décision contraint l'UX, pas l'inverse

« UX-first » vaut pour la **présentation**, jamais pour la **décision**. Les
invariants métier (voir §4) sont définis indépendamment et **contraignent**
l'UX. Un écran ne doit jamais encoder un comportement séduisant mais faux
(ex. vendre un compounder parce que le prix dépasse l'IV haute). Pour tout écran
de décision : d'abord le modèle de décision correct, ensuite l'habillage.

### G3 — Toute donnée entre versionnée et scorée avant usage — y compris l'ad hoc

La donnée de la couche 3 arrive par deux voies :
- **flux standards** (EDGAR, IR, RSS, batch d'ingestion) ;
- **recherche ad hoc** d'agents ouvriers, à la demande d'un agent métier.

Les deux voies obéissent à la même règle : **aucune donnée n'est consommée par un
agent métier avant d'exister comme `knowledge_entry`** — source, `reliability_score`,
`reliability_tier`, timestamp, et **snapshot immuable du contenu au moment de la
décision**. Ad hoc ≠ éphémère. Ad hoc ≠ non tracé. C'est la condition de
l'auditabilité intégrale (principe P1–P4 de la spec V2), et elle impose des
`knowledge_entries` **append-only / versionnées** (on ne mute pas, on supersède).

---

## 3. Architecture d'agents — tiering, cache, batch

### Deux tiers, une interface stricte

| Tier | Modèle par défaut | Rôle | Prix (in/out par M tokens) |
|---|---|---|---|
| **Métier (orchestrateur)** | `claude-opus-4-8` | Jugement, synthèse bull/bear, risk matrix, arbitrage | $5 / $25 |
| **Ouvrier** | `claude-haiku-4-5` | web_search, fetch_url, extraction, classification de matérialité | $1 / $5 |
| *Intermédiaire (option)* | `claude-sonnet-4-6` | Ingestion de gros documents (10-K) si Haiku peine | $3 / $15 |

L'abstraction provider (LiteLLM) reste la règle : changer de modèle = changer une
valeur en DB, pas du code. Les modèles ci-dessus sont les **défauts**, pas un
verrou.

**L'interface orchestrateur → ouvrier est le point critique.** L'agent Opus
n'envoie jamais une consigne vague (« cherche des infos sur NVDA »). Il émet une
**requête structurée** : `query` + schéma de sortie attendu + fiabilité minimale
exigée. L'ouvrier renvoie des `knowledge_entries` scorées, jamais du texte libre.
Garbage in, garbage out : la qualité de la délégation dépend de la précision de la
demande.

### Économie de tokens & arrêt de Pareto (comme un fonds)

Deux principes gouvernent la consommation, au même rang que le tiering :

- **Agent adapté + sous-segmentation.** Chaque tâche va au plus petit modèle qui
  la traite bien ; une tâche lourde est **découpée** en sous-tâches déléguées à des
  ouvriers plutôt que traitée d'un bloc par l'orchestrateur. On ne paie de l'Opus
  que là où il y a du jugement.
- **Arrêt de Pareto sur la recherche.** On cesse de chercher plus d'information dès
  que son **impact marginal sur la décision** devient faible — comme un fonds qui ne
  vise pas l'exhaustivité mais résout les 2-3 incertitudes qui peuvent inverser la
  thèse. Le curator (readiness / incertitudes bloquantes) opérationnalise ce seuil
  d'arrêt.

### Économie d'exécution

- **Prompt caching** pour rendre l'orchestrateur Opus abordable. Le contexte
  réutilisé d'une étape à l'autre (system prompt figé, knowledge entries triées de
  façon déterministe, contexte portefeuille) va en **tête** de prompt ; le volatile
  (la query du tour) en **fin**. Les lectures de cache coûtent ~0,1× l'entrée.
  Interdit absolu en tête de prompt : `datetime.now()`, ID de session, JSON non
  trié — tout invalidateur silencieux du cache.
- **Batch API** pour l'ingestion de masse non latence-sensible (onboarding EDGAR,
  regénération annuelle, ingestion 10-K/10-Q en volume) : **−50 %** sur les tokens.
  Les appels synchrones sont réservés aux analyses on-demand.

---

## 4. Invariants métier (ce que l'UX doit servir, jamais contredire)

Rappel des règles de fond qui contraignent toute UX de décision (cf. audit du
flux) :

- **Horizon ≥ 5 ans.** Valorisation scénarisée (bear/base/bull) + reverse-DCF,
  pas un prix cible à 36 mois.
- **On vend sur dégradation de thèse** (moat, ROIC, allocation du capital,
  gouvernance), **pas sur un seuil de prix mécanique**. Nuance : à chaque revue on
  réévalue si la thèse **valide justifie encore le prix** — si le rendement attendu
  à terme ne compense plus le risque et le coût d'opportunité, on **réduit
  l'exposition même thèse intacte** (arbitrage rendement/risque prospectif, pas
  market-timing). La surévaluation seule = signal de non-renforcement + revue.
- **Trois indicateurs distincts, jamais fusionnés** : qualité/couverture de
  l'information · conviction sur la thèse · marge de sécurité. Pas de
  `confidence_score` global trompeur.
- **Auditabilité reconstructible** : on peut toujours répondre « pourquoi l'agent
  a dit ça » à partir du snapshot figé des sources utilisées.
- **Curator MVDD / readiness / too-hard** préservé : on évalue si on en sait
  assez pour juger, avant de juger.
- **Arrêt de Pareto** : on n'accumule pas l'information pour elle-même ; on s'arrête
  quand une recherche supplémentaire ne changerait probablement pas la décision.

---

## 5. Le même principe gouverne le développement du projet

La chaîne UX → agents → données, et ses garde-fous, ne s'appliquent pas qu'au
produit : ils structurent **comment on le construit**.

1. **On spécifie de l'écran vers la donnée.** Une spec commence par le contrat
   d'affichage (le JSON + son schéma versionné), puis l'agent qui le produit, puis
   les données nécessaires. Une spec qui commence par le schéma de table sans
   écran cible est incomplète.

2. **Le schéma JSON précède le code.** Avant d'implémenter, le schéma versionné
   existe et les 3 points de synchronisation sont identifiés. Un ticket = une
   évolution de contrat cohérente sur les 3 points.

3. **Aucune donnée non tracée dans le code.** Toute écriture dans la base de
   connaissance (flux ou ad hoc) passe par la même porte versionnée/scorée. Pas
   de chemin de contournement, même « temporaire ».

4. **Décision avant habillage.** Pour toute fonctionnalité de décision, la revue
   valide d'abord la conformité aux invariants métier (§4), ensuite l'UX.

5. **Tiering et coût sont des choix de conception, pas d'après-coup.** Chaque
   nouvel agent déclare son tier (métier / ouvrier), son modèle par défaut, et
   s'il passe par batch ou synchrone. Le cache est pensé dès la structure du
   prompt.

6. **Provider-agnostic par défaut.** Tout agent passe par l'abstraction provider.
   Aucun appel direct à un SDK de modèle dans la logique métier.

---

## 6. Test de conformité (à appliquer à chaque spec / PR de la V2)

Une contribution est conforme si elle peut répondre « oui » à tout :

- [ ] Part-elle d'un contrat d'affichage (JSON) avant la donnée ? *(couche 1→3)*
- [ ] Le schéma JSON est-il versionné et synchronisé sur les 3 points ? *(G1)*
- [ ] La logique de décision est-elle définie indépendamment de l'UX et
      conforme aux invariants métier ? *(G2, §4)*
- [ ] Toute donnée utilisée est-elle versionnée + scorée + figée au moment de la
      décision, ad hoc compris ? *(G3)*
- [ ] Chaque agent déclare-t-il tier, modèle, batch/synchrone, et stratégie de
      cache ? *(§3)*
- [ ] Passe-t-elle par l'abstraction provider ? *(§3, §5.6)*

Si une case est « non », la contribution n'est pas prête — quelle que soit la
qualité du reste.
