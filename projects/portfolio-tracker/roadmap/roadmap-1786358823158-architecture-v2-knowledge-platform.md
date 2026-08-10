---
id: roadmap-1786358823158
status: spec-ready
created: 2026-08-09T00:00:00.000000
project: portfolio-tracker
---

## Architecture V2 — Knowledge Platform & Flux d'investissement professionnel

### Direction / Feature (utilisateur)

Refonte architecturale complète du système d'analyse d'investissement :
- Abstraction provider (Dust comme provider parmi d'autres, via LiteLLM)
- Base de connaissance auditables par entreprise (sources tracées, fiabilité scorée)
- Pipeline d'ingestion de données structurées et non structurées (EDGAR, IR, web search, upload)
- Les agents font des recherches web et stockent ce qu'ils trouvent
- Toute information utilisée dans une analyse est traçable — y compris la mémoire des LLMs
- Flux bull/bear indépendants + synthèse en matrice de risques
- Confiance dans le système = traçabilité intégrale des bases de décision

---

## Spec générée

---

## 1. Vision et principes

### 1.1 Ce qu'on construit

Un **système d'intelligence d'investissement** composé de trois couches :

```
┌─────────────────────────────────────────────────┐
│  PORTFOLIO TRACKER  (existant, évolue)          │
│  Frontend Next.js — pages analyse, thèse, suivi │
└──────────────────────┬──────────────────────────┘
                       │ consomme
┌──────────────────────▼──────────────────────────┐
│  AGENT LAYER  (refonte)                         │
│  Abstraction LiteLLM — bull, bear, thesis,      │
│  monitoring — provider-agnostic                 │
└──────────────────────┬──────────────────────────┘
                       │ interroge
┌──────────────────────▼──────────────────────────┐
│  KNOWLEDGE PLATFORM  (nouveau)                  │
│  Ingestion + stockage + fiabilité + RAG         │
│  Toute information tracée, scorée, auditable    │
└─────────────────────────────────────────────────┘
```

### 1.2 Principes non négociables

**P1 — Traçabilité intégrale**
Chaque information utilisée dans une analyse est enregistrée en base avec : source, date, type, score de fiabilité, note explicative. Aucune analyse ne repose sur une donnée non tracée.

**P2 — La mémoire LLM est une source comme les autres**
Si un agent utilise une connaissance issue de son pré-entraînement (non sourcée à un document), il crée une entrée `source_type = 'llm_memory'` avec une note "information issue du modèle, non vérifiée, à confirmer". L'utilisateur peut la consulter et la marquer comme validée ou obsolète.

**P3 — Provider-agnostic**
Le système ne parle pas à Dust, OpenAI ou Anthropic directement. Il parle à une interface abstraite. Dust reste disponible comme provider. Changer de provider = changer une valeur en DB, pas du code.

**P4 — Auditabilité des analyses**
Chaque analyse (bull case, bear case, thèse) enregistre les IDs des knowledge entries qui ont été utilisées. On peut reconstruire pourquoi l'agent a dit ce qu'il a dit.

**P5 — Fiabilité graduée, jamais binaire**
Une information n'est pas "fiable" ou "non fiable". Elle a un score (0.0-1.0) et une note explicite sur ce score. Les analyses agrègent les scores des sources utilisées pour produire un `confidence_score` global de l'analyse.

---

## 2. Architecture de la couche agents (provider-agnostic)

### 2.1 L'abstraction provider

**Fichier** : `backend/app/agents/providers/`

```python
# base.py
from typing import Protocol, AsyncIterator

class AgentMessage(TypedDict):
    role: str   # 'system' | 'user' | 'assistant'
    content: str

class AgentResponse(TypedDict):
    content: str
    model: str
    provider: str
    tokens_input: int
    tokens_output: int
    cost_usd: float
    conversation_id: str | None  # pour providers avec mémoire gérée (Dust)

class AgentProvider(Protocol):
    async def complete(
        self,
        messages: list[AgentMessage],
        model: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict] | None = None,
    ) -> AgentResponse: ...

    async def stream(
        self,
        messages: list[AgentMessage],
        model: str,
        **kwargs,
    ) -> AsyncIterator[str]: ...
```

**Implémentations** :

```
providers/
  litellm_provider.py   ← wrappeur LiteLLM (Anthropic, OpenAI, Gemini, Ollama...)
  dust_provider.py      ← wrappeur DustClient existant (migration transparente)
  __init__.py           ← factory get_provider(name: str) -> AgentProvider
```

La factory lit la config depuis la DB :
```sql
-- agent_prompts étendu
ALTER TABLE agent_prompts
  ADD COLUMN provider    TEXT NOT NULL DEFAULT 'dust',   -- 'dust' | 'litellm'
  ADD COLUMN model       TEXT,    -- ex: 'anthropic/claude-sonnet-4-6', 'gemini/gemini-2.5-flash'
  ADD COLUMN tools_json  JSONB;   -- définitions d'outils disponibles pour cet agent
```

Changer `bull-agent` de Dust vers Anthropic direct = `PATCH /admin/agents/bull-agent` avec `{"provider": "litellm", "model": "anthropic/claude-sonnet-4-6"}`. Rien d'autre ne change.

### 2.2 Les outils (tools) disponibles pour les agents

Les agents disposent de tools standardisés, disponibles quel que soit le provider :

| Tool | Description | Stockage résultat |
|---|---|---|
| `web_search(query, max_results)` | Recherche web via Brave Search API (gratuit 2000 req/mois) ou SearXNG self-hosted | `knowledge_entries` + `source_type='web_search'` |
| `fetch_url(url, extract_mode)` | Fetch et extraction texte d'une URL | `knowledge_documents` + extraction → `knowledge_entries` |
| `query_knowledge(ticker_id, query, limit)` | RAG sur pgvector pour la base de connaissance | aucun (lecture seule) |
| `store_knowledge(entry)` | Crée une knowledge_entry (y compris `llm_memory`) | `knowledge_entries` |

**Implémentation** : `backend/app/agents/tools/` — chaque tool est une fonction Python async appelée par le runtime agent quand l'agent émet un `tool_use`.

Côté LiteLLM : tool_use natif (format OpenAI function calling, supporté par Claude, GPT, Gemini).
Côté Dust : les tools sont des actions Dust configurées dans l'agent Dust.

### 2.3 Registre des agents V2

| Agent | Rôle | Provider défaut | Modèle défaut | Tools |
|---|---|---|---|---|
| `bull-agent` | Meilleur argument POUR | litellm | claude-sonnet-4-6 | web_search, fetch_url, query_knowledge, store_knowledge |
| `bear-agent` | Meilleur argument CONTRE | litellm | claude-sonnet-4-6 | web_search, fetch_url, query_knowledge, store_knowledge |
| `thesis-agent` | Synthèse bull+bear → thèse + risk matrix | litellm | claude-sonnet-4-6 | query_knowledge |
| `monitoring-agent` | Suivi thèse modes 1-6 | litellm | modes 1/2/4/5: gemini-flash, modes 3/6: sonnet | web_search, query_knowledge, store_knowledge |
| `ingestion-agent` | Extraction connaissance depuis documents | litellm | gemini-flash (volume) | store_knowledge |

Les agents Dust existants (opportunity-agent, thesis-agent V1, monitoring-agent V1) restent actifs tant que `provider = 'dust'` dans `agent_prompts`. La migration est progressive par agent.

---

## 3. Architecture de la base de connaissance (Knowledge Platform)

### 3.1 Principe général

La knowledge base est la **mémoire externe commune à tous les agents**. Elle est :
- Stockée en base de données (PostgreSQL + pgvector)
- Accessible via le tool `query_knowledge` (RAG sémantique)
- Entièrement auditable via le frontend (`/knowledge`)
- Indépendante des providers d'agents

Toute information qui influence une analyse doit exister dans cette base. C'est la règle centrale du système.

### 3.2 Structure de la knowledge base

```
/knowledge/                              ← dans le repo Git, synchronisé avec la DB
  companies/
    {ticker_id}/
      profile.md                         ← profil entreprise (auto-généré + éditable)
      financials.md                      ← historique financier 10 ans (auto-mis à jour)
      competitive.md                     ← analyse concurrentielle (agents + notes user)
      management.md                      ← équipe dirigeante, track record (agents + user)
      documents/
        {date}-{type}-{slug}.txt         ← texte extrait des documents sources
  sectors/
    {sector_slug}.md                     ← connaissance sectorielle (existant: IT_Services.json)
  macro/
    market_temperature.md               ← contexte macro (FRED, Buffett indicator, CAPE)
```

Les fichiers Markdown sont la version lisible par l'humain. La DB est la version requêtable par les agents. Les deux sont synchronisés par le pipeline d'ingestion.

### 3.3 Le score de fiabilité — framework détaillé

Chaque knowledge entry a un `reliability_score` (0.0 → 1.0) et un `reliability_tier`.

| Source type | Tier | Score de base | Justification |
|---|---|---|---|
| `edgar_official` | A | 0.95 | Filing SEC officiel, données auditées |
| `company_ir_official` | A | 0.90 | Document officiel de l'entreprise (rapport annuel, press release) |
| `earnings_transcript_official` | A- | 0.85 | Transcription officielle — contient forward-looking statements non audités |
| `regulator_filing_eu` | A- | 0.85 | AMF, BaFin — officiel mais moins structuré qu'EDGAR |
| `financial_press` | B+ | 0.75 | FT, Bloomberg, Reuters — journalisme de qualité mais interprétation |
| `web_search_reputable` | B | 0.65 | Source identifiée et réputée (site entreprise, media reconnu) |
| `web_search_generic` | C+ | 0.50 | Source web non classifiée |
| `llm_memory` | C | 0.40 | Mémoire du modèle pré-entraîné — cutoff connu, peut être obsolète |
| `user_provided` | B | 0.70 | Fourni par l'utilisateur — considéré de bonne foi, non vérifié |
| `user_provided_confidential` | B+ | 0.80 | Document confidentiel fourni par l'utilisateur (investor update) — données primaires |
| `agent_synthesis` | B- | 0.60 | Synthèse produite par un agent — dérivée de sources, non originale |

**Modulation du score** :
- Âge de l'information : `-0.05` par an pour les données financières, `-0.02` par an pour les données qualitatives stables
- Cross-validation : `+0.10` si la même information est confirmée par deux sources indépendantes
- Contradiction : `-0.20` si une autre source récente dit le contraire (flag `has_conflict`)

### 3.4 La règle de la mémoire LLM

Quand un agent génère une affirmation basée sur sa connaissance interne (pas sur un document récupéré), il **doit** appeler `store_knowledge` avec :

```json
{
  "entry_type": "llm_memory",
  "source_type": "llm_memory",
  "content": "LVMH détient environ 75 maisons de luxe réparties sur 6 secteurs d'activité, avec une part significative du chiffre d'affaires réalisée en Asie-Pacifique.",
  "reliability_score": 0.40,
  "reliability_note": "Information issue du pré-entraînement du modèle (cutoff août 2025). Peut ne pas refléter la situation actuelle. À vérifier contre le rapport annuel le plus récent.",
  "requires_human_review": true,
  "model_cutoff": "2025-08"
}
```

Ces entrées apparaissent dans le frontend avec un badge "⚠ Mémoire modèle — à vérifier". L'utilisateur peut les marquer comme "Confirmé" ou "Obsolète / incorrect".

L'objectif est double :
1. L'utilisateur voit exactement ce que le modèle "invente" vs. ce qu'il a trouvé
2. Au fil du temps, les entrées validées constituent un corpus de connaissance fiable

---

## 4. Pipeline d'ingestion des données

### 4.1 Vue d'ensemble

Trois modes d'ingestion, chacun alimentant les mêmes tables :

```
Mode A — Automatisé (scheduler)
  EDGAR (US)          → knowledge_documents → knowledge_entries
  IR scraping (EU)    → knowledge_documents → knowledge_entries
  News / RSS          → knowledge_entries (direct, sans document intermédiaire)

Mode B — Agent on-demand (pendant une analyse)
  web_search tool     → knowledge_entries (source_type='web_search')
  fetch_url tool      → knowledge_documents + knowledge_entries
  store_knowledge     → knowledge_entries (source_type='llm_memory' ou 'agent_synthesis')

Mode C — Manuel (Admin UI)
  Upload PDF          → knowledge_documents → ingestion-agent → knowledge_entries
  Saisie URL          → fetch_url → knowledge_documents → ingestion-agent → knowledge_entries
  Formulaire structuré → knowledge_entries (source_type='user_provided')
  Données confidentielles → knowledge_documents (is_confidential=true) → knowledge_entries
```

### 4.2 Sources par type d'entreprise

#### US public companies

| Source | Données | Fréquence | API / méthode |
|---|---|---|---|
| SEC EDGAR | 10-K, 10-Q, 8-K, DEF14A, ex-99 (earnings press release) | À publication (webhook ou polling) | `edgar` Python package (gratuit, officiel) |
| EDGAR company facts | Financials XBRL structurés sur 10+ ans | À onboarding + annuel | `https://data.sec.gov/api/xbrl/companyfacts/{cik}.json` — gratuit, officiel, JSON structuré |
| yfinance | Prix, valorisation, métriques courantes, short interest, insider % | Cache 4h (existant) | Existant dans DataService |
| macrotrends.net | Historique financier formaté 10 ans | À onboarding | Scraping HTML (fragile mais suffisant pour bootstrap) |

L'API EDGAR Company Facts est la clé : elle retourne 10+ ans de données financières XBRL structurées, gratuitement, sans scraping. C'est la source de référence pour les US.

#### EU large caps (CAP, LVMH, etc.)

| Source | Données | Fréquence | API / méthode |
|---|---|---|---|
| Site IR de l'entreprise | Communiqués de résultats, présentations, rapports annuels | Trimestriel | Scraper spécifique par entreprise (fragile, maintenance requise) |
| AMF BDIF | Documents de référence officiels (PDF) | Annuel | Scraping amf-france.org/BDIF |
| Euronext | Données prix, volumes | Via yfinance (suffisant) | Existant |
| Factset / Refinitiv | Non disponible sans abonnement | — | Hors scope |

**Stratégie EU pragmatique** :
- Scrapers spécifiques pour les 5-10 entreprises EU les plus suivies (maintenance acceptable)
- Fallback systématique : upload manuel via Admin quand le scraper échoue
- Flag `scraper_health: ok | degraded | broken` par entreprise en DB
- Alert Slack si un scraper EU n'a pas produit de nouveau document depuis > 120 jours

#### Startups (US ou EU, non cotées)

| Source | Données | Fréquence | API / méthode |
|---|---|---|---|
| Crunchbase free API | Funding rounds, investisseurs, équipe, date fondation | À onboarding + trimestriel | API Crunchbase (free: 200 req/mois) |
| PitchBook (si accès) | Valorisations, comparables | — | Non disponible sans abonnement |
| LinkedIn (limité) | Taille équipe, croissance effectif | Mensuel | Scraping limité (fragile) |
| Presse tech | Annonces levées, partenariats, recrutements | Quotidien | RSS TechCrunch, Sifted, TheInformation |
| Documents confidentiels | Investor updates, cap table, KPIs | Sur réception | Upload manuel Admin, `is_confidential = true` |

### 4.3 Processus d'onboarding d'un nouveau ticker

Déclencheur : `POST /tickers` → le backend lance automatiquement le pipeline d'onboarding en background.

```
1. Identifier le type : public_us | public_eu | private
   → basé sur tickers.exchange ou préfixe id (PRIV-)

2. Si public_us :
   a. Chercher le CIK EDGAR (API SEC search par ticker symbol)
   b. Fetch EDGAR Company Facts → historique financier XBRL complet
   c. Fetch derniers 4 filings (10-K + 10-Q les plus récents)
   d. Extraire textes → knowledge_documents
   e. Lancer ingestion-agent sur chaque document → knowledge_entries
   f. Créer profile.md + financials.md dans /knowledge/companies/{ticker}/

3. Si public_eu :
   a. Lancer scraper IR (si disponible pour cette entreprise)
   b. Fallback : web_search "[company] annual report [year] PDF investor relations"
   c. Fetch macrotrends.net pour historique financier 10 ans
   d. Créer knowledge_documents + knowledge_entries
   e. Flag Admin : "Vérifier scraper EU pour {ticker}"

4. Si private :
   a. Crunchbase lookup (par nom d'entreprise)
   b. Créer profil minimal depuis Crunchbase
   c. Flag Admin : "Compléter le profil manuellement pour {ticker}"

5. Pour tous :
   a. News monitoring bootstrap (10 derniers articles Google News)
   b. Créer les fichiers Markdown dans /knowledge/companies/{ticker}/
   c. Générer embeddings pgvector pour tous les knowledge_entries créés
   d. Envoyer notification Slack : "Onboarding {ticker} terminé — {n} knowledge entries créées"
```

### 4.4 Processus de mise à jour périodique

```
Quotidien (7h00) :
  Pour chaque ticker watchlist + portfolio :
    → News monitoring : Google News RSS + web_search si signal fort
    → Matérialité scorée : ignorer si score < 0.3, stocker si score >= 0.3
    → Pour private : chercher mentions presse tech

Trimestriel (J+2 après date earnings connue) :
  Pour chaque ticker portfolio :
    → US : fetch nouveau 10-Q et ex-99 depuis EDGAR
    → EU : lancer scraper IR + tentative fetch transcript
    → Lancer ingestion-agent sur nouveaux documents
    → Mettre à jour financials.md
    → Invalider knowledge_entries financières de la période précédente

Annuel (mois de clôture fiscal) :
  Pour chaque ticker portfolio :
    → US : fetch 10-K complet depuis EDGAR
    → EU : fetch rapport annuel (scraper + fallback web_search PDF)
    → Lancer ingestion-agent complet
    → Regénérer profile.md + financials.md + competitive.md
    → Invalider anciens embeddings → regénérer
```

### 4.5 L'ingestion-agent

Un agent dédié à l'extraction de connaissance depuis les documents bruts.

**Input** : texte brut d'un document (extrait de PDF ou HTML)
**Output** : liste de `knowledge_entries` structurées

Prompt structurant :
```
Tu es un extracteur de connaissance financière.
À partir du document fourni :
1. Extrais les faits chiffrés clés (revenus, marges, ROIC, dette, guidance)
2. Extrais les déclarations qualitatives importantes (stratégie, concurrence, risques)
3. Pour chaque fait : précise le contexte (période, segment, devise)
4. Évalue la fiabilité de chaque fait dans le contexte du document source
5. Si tu fais des inférences qui vont au-delà du texte, marque-les comme 'agent_synthesis'

Format : une knowledge_entry par fait / déclaration. Maximum 20 entries par document.
```

**Modèle** : `gemini-flash` (volume, coût) pour les extractions de routine. `sonnet` pour les documents complexes (10-K complets, proxy statements).

---

## 5. Le nouveau flux d'analyse — bull/bear/synthèse

### 5.1 Vue d'ensemble

```
[WATCHLIST] ticker ajouté → onboarding pipeline
     ↓
[PRÉ-ANALYSE] lecture knowledge base existante
     ↓ utilisateur décide de lancer une analyse
[BULL CASE]   bull-agent (contexte isolé, sans bear)
     ↓         ↓ stocke ses recherches en knowledge_entries
[BEAR CASE]   bear-agent (contexte isolé, sans bull)
     ↓         ↓ stocke ses recherches en knowledge_entries
[SYNTHÈSE]    thesis-agent reçoit bull + bear + knowledge entries utilisées
     ↓
[RISK MATRIX] matrice de risques — cœur du document de thèse
     ↓ pré-mortem auto-généré depuis risk matrix
[VALIDATION]  utilisateur acquitte risk matrix → position créée
     ↓
[MONITORING]  modes 1-6, enrichi par knowledge platform
```

### 5.2 Le bull-agent

**Isolation** : le bull-agent ne voit jamais le résultat du bear-agent. Il reçoit :
- Les knowledge_entries du ticker (résultats du RAG sémantique sur sa query initiale)
- Le contexte portefeuille actuel (pour évaluer le coût d'opportunité)
- La température de marché

**Prompt structurant (extrait)** :
```
Tu es un analyste d'investissement dont la mission est de construire le cas
d'investissement le plus solide possible POUR cette entreprise.

Tu dois :
1. Identifier les 3-5 forces structurelles qui rendent ce business exceptionnel
2. Construire un scénario de valorisation à 5 ans avec des hypothèses explicites
3. Identifier les catalyseurs qui pourraient accélérer la création de valeur
4. Te prononcer sur un prix cible et un horizon avec une conviction chiffrée

Règle : tout fait que tu utilises doit provenir soit des knowledge entries fournies,
soit d'une recherche web que tu effectues maintenant (outil web_search).
Tu ne peux PAS utiliser ta mémoire sans créer une entrée llm_memory.

À la fin, liste les IDs des knowledge_entries que tu as utilisées.
```

**Output — `bull_case_json`** :
```json
{
  "forces_structurelles": [
    {"titre": "Switching costs quasi-impossibles", "explication": "...", "source_entry_ids": [42, 67]},
    {"titre": "ROIC > 20% depuis 8 ans", "explication": "...", "source_entry_ids": [15, 16, 17]}
  ],
  "valorisation": {
    "methode": "FCF yield normalisé + croissance 12% sur 5 ans + exit multiple 22x",
    "prix_cible": 145,
    "horizon_mois": 36,
    "assumptions": {"croissance_revenue": 0.12, "expansion_marge_fcf": 0.02, "multiple_sortie": 22}
  },
  "catalyseurs": ["lancement produit IA Q4 2026", "expansion Allemagne 2027"],
  "conviction": 7,
  "knowledge_entries_used": [15, 16, 17, 42, 67, 89],
  "confidence_score": 0.72
}
```

`confidence_score` = moyenne pondérée des `reliability_score` des entries utilisées.

### 5.3 Le bear-agent

**Isolation** : le bear-agent ne voit pas le bull case. Il reçoit les mêmes données brutes.

**Prompt structurant (extrait)** :
```
Tu es un analyste short-seller dont la mission est de construire le meilleur
argument CONTRE cet investissement.

Tu dois :
1. Identifier les risques structurels que le marché sous-estime
2. Trouver les failles dans la thèse bull conventionnelle sur cette entreprise
3. Construire un scénario de destruction de valeur plausible à 3 ans
4. Évaluer la probabilité que cette entreprise sous-performe son secteur

Tu as l'autorisation d'être pessimiste mais tu dois rester factuel.
Aucune affirmation sans source tracée ou entrée llm_memory.
```

**Output — `bear_case_json`** :
```json
{
  "risques_structurels": [
    {
      "titre": "Concurrence cloud native en accélération",
      "explication": "...",
      "probabilite": 0.45,
      "impact": "fort",
      "horizon": "2-3 ans",
      "source_entry_ids": [23, 91]
    }
  ],
  "scenario_adverse": {
    "description": "...",
    "prix_cible_bear": 65,
    "perte_potentielle_pct": -40,
    "declencheurs": ["perte contrat Fortune 500", "récession IT 2027"]
  },
  "failles_bull_conventionnel": ["Le ROIC élevé est partiellement comptable (capitalisation R&D)", "..."],
  "conviction_negative": 6,
  "knowledge_entries_used": [23, 91, 44],
  "confidence_score": 0.68
}
```

### 5.4 La synthèse et la matrice de risques

Le thesis-agent (mode synthesis) reçoit les deux outputs + toutes les knowledge_entries utilisées.

**Output — `risk_matrix_json`** :
```json
{
  "verdict": "PROCEED_AVEC_CONDITIONS",
  "rationale": "Business de qualité avec moat défendable. Le risque cloud native est réel mais horizon 3+ ans. Prix actuel offre une marge de sécurité limitée — convient pour une entrée fractionnée.",
  
  "risques_acceptes": [
    {
      "risque": "Concurrence cloud native",
      "probabilite": 0.45,
      "impact": "fort",
      "reversible": false,
      "reponse_si_materialise": "Sortir si perte de part de marché > 3pts sur 2 trimestres consécutifs",
      "couvert_par_hypothese": "H3"
    },
    {
      "risque": "Récession IT compressant les budgets",
      "probabilite": 0.30,
      "impact": "moyen",
      "reversible": true,
      "reponse_si_materialise": "Maintenir — impact cyclique, thèse long terme intacte",
      "couvert_par_hypothese": "H5"
    }
  ],
  
  "conditions_entree": ["Prix < 115 pour marge de sécurité > 10%", "Confirmer tendance ROIC Q3 2026"],
  
  "position_sizing": {
    "pct_recommande": 4.5,
    "pct_max": 7.0,
    "justification": "Conviction 7/10, risque cloud non négligeable, marché chaud — sizing conservateur"
  },

  "pre_mortem": [
    "Scénario 1 : un concurrent cloud lance une offre à -40% du prix — notre pricing power disparaît en 18 mois",
    "Scénario 2 : le CFO révèle en Q3 que la croissance était boostée par des one-timers",
    "Scénario 3 : récession sévère → les clients repoussent les renouvellements → churn +5pts"
  ],
  
  "confidence_score_global": 0.71,
  "sources_summary": {
    "tier_A": 12,
    "tier_B": 8,
    "tier_C_llm_memory": 3,
    "total_entries": 23
  }
}
```

**Ce que l'utilisateur voit** : la risk matrix est le document central affiché sur la page d'analyse. Chaque risque a un bouton "Je comprends et j'accepte ce risque". L'utilisateur ne peut pas valider une thèse sans avoir acquitté chaque risque de la matrice.

---

## 6. Schéma de base de données — tables nouvelles et modifiées

### 6.1 Tables nouvelles

```sql
-- Migration 023_v2_knowledge_platform.sql

-- Documents bruts (avant extraction)
CREATE TABLE knowledge_documents (
    id                  SERIAL PRIMARY KEY,
    ticker_id           TEXT REFERENCES tickers(id),
    doc_type            TEXT NOT NULL,  -- '10-K'|'10-Q'|'8-K'|'earnings_call'|'annual_report'
                                        -- |'press_release'|'investor_day'|'news'|'investor_update'
    title               TEXT,
    source_url          TEXT,
    source_type         TEXT NOT NULL,  -- 'edgar'|'ir_scrape'|'web_search'|'user_upload'|'rss'
    content_raw         TEXT,           -- texte extrait (peut être long)
    content_hash        TEXT,           -- SHA256 pour déduplication
    published_date      DATE,
    fiscal_period       TEXT,           -- 'Q4-2025'|'FY-2025'
    is_confidential     BOOL NOT NULL DEFAULT FALSE,
    language            TEXT DEFAULT 'en',
    processing_status   TEXT DEFAULT 'pending',  -- 'pending'|'processing'|'done'|'failed'
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Entrées de connaissance atomiques (le cœur du système)
CREATE TABLE knowledge_entries (
    id                  SERIAL PRIMARY KEY,
    ticker_id           TEXT REFERENCES tickers(id),  -- null = connaissance sectorielle/macro
    document_id         INT REFERENCES knowledge_documents(id),  -- null si source directe
    entry_type          TEXT NOT NULL,  -- 'fact_financial'|'fact_qualitative'|'event'
                                        -- |'quote'|'analysis'|'risk'|'llm_memory'
    content             TEXT NOT NULL,  -- le fait, formulé en langage naturel
    content_structured  JSONB,          -- version structurée si applicable (ex: {metric, value, period})
    source_type         TEXT NOT NULL,  -- cf. framework fiabilité section 3.3
    source_url          TEXT,
    source_date         DATE,
    fiscal_period       TEXT,           -- période couverte par cette information
    reliability_score   FLOAT NOT NULL CHECK (reliability_score BETWEEN 0.0 AND 1.0),
    reliability_tier    TEXT NOT NULL,  -- 'A'|'A-'|'B+'|'B'|'B-'|'C+'|'C'
    reliability_note    TEXT,           -- pourquoi ce score
    has_conflict        BOOL DEFAULT FALSE,   -- une autre source dit le contraire
    conflict_entry_id   INT REFERENCES knowledge_entries(id),
    requires_human_review BOOL DEFAULT FALSE,
    reviewed_by_user    BOOL DEFAULT FALSE,
    last_reviewed_at    TIMESTAMPTZ,
    model_cutoff        TEXT,           -- ex: '2025-08' pour les llm_memory
    embedding           vector(1536),   -- pgvector — dimension selon modèle d'embedding
    is_outdated         BOOL DEFAULT FALSE,  -- marqué obsolète par mise à jour plus récente
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour performances
CREATE INDEX idx_knowledge_entries_ticker ON knowledge_entries(ticker_id);
CREATE INDEX idx_knowledge_entries_type ON knowledge_entries(entry_type);
CREATE INDEX idx_knowledge_entries_review ON knowledge_entries(requires_human_review) WHERE requires_human_review = TRUE;
CREATE INDEX idx_knowledge_entries_embedding ON knowledge_entries USING ivfflat (embedding vector_cosine_ops);

-- Scraper EU — configuration et santé
CREATE TABLE eu_ir_scrapers (
    id              SERIAL PRIMARY KEY,
    ticker_id       TEXT REFERENCES tickers(id),
    scraper_url     TEXT NOT NULL,      -- URL de la page IR à scraper
    scraper_config  JSONB,              -- sélecteurs CSS, regex, etc.
    scraper_health  TEXT DEFAULT 'ok',  -- 'ok'|'degraded'|'broken'
    last_success_at TIMESTAMPTZ,
    last_error      TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Tables analyses (bull/bear/synthesis)
CREATE TABLE investment_analyses (
    id                      SERIAL PRIMARY KEY,
    ticker_id               TEXT REFERENCES tickers(id),
    analysis_type           TEXT NOT NULL,  -- 'bull'|'bear'|'synthesis'
    bull_analysis_id        INT REFERENCES investment_analyses(id),  -- pour synthesis
    bear_analysis_id        INT REFERENCES investment_analyses(id),  -- pour synthesis
    result_json             JSONB NOT NULL,
    knowledge_entry_ids     INT[] NOT NULL DEFAULT '{}',  -- traçabilité
    confidence_score        FLOAT,
    provider_used           TEXT,
    model_used              TEXT,
    cost_usd                FLOAT,
    tokens_input            INT,
    tokens_output           INT,
    status                  TEXT DEFAULT 'completed',
    created_at              TIMESTAMPTZ DEFAULT NOW()
);
```

### 6.2 Tables modifiées

```sql
-- agent_prompts — ajout provider + model + tools
ALTER TABLE agent_prompts
    ADD COLUMN provider     TEXT NOT NULL DEFAULT 'dust',
    ADD COLUMN model        TEXT,
    ADD COLUMN tools_json   JSONB DEFAULT '[]';

-- theses — lien avec l'analyse bull/bear
ALTER TABLE theses
    ADD COLUMN synthesis_analysis_id  INT REFERENCES investment_analyses(id),
    ADD COLUMN pre_mortem_acked       BOOL DEFAULT FALSE,
    ADD COLUMN risk_matrix_acked      BOOL DEFAULT FALSE,  -- tous les risques acquittés
    ADD COLUMN position_sizing_pct    FLOAT,
    ADD COLUMN conditions_entree      JSONB DEFAULT '{}';

-- tickers — flag ingestion pipeline
ALTER TABLE tickers
    ADD COLUMN ingestion_status   TEXT DEFAULT 'pending',  -- 'pending'|'running'|'done'|'failed'
    ADD COLUMN ingestion_done_at  TIMESTAMPTZ,
    ADD COLUMN has_eu_scraper     BOOL DEFAULT FALSE,
    ADD COLUMN edgar_cik          TEXT;  -- CIK EDGAR pour les tickers US
```

---

## 7. API REST nouvelles

```
# Knowledge Documents
GET    /knowledge/{ticker_id}/documents              Liste documents par ticker
POST   /knowledge/{ticker_id}/documents              Upload document (PDF ou URL)
GET    /knowledge/{ticker_id}/documents/{id}         Détail + statut extraction
DELETE /knowledge/{ticker_id}/documents/{id}         Supprimer

# Knowledge Entries
GET    /knowledge/{ticker_id}/entries                Liste avec filtres (type, tier, review_required)
POST   /knowledge/{ticker_id}/entries                Créer entrée manuelle
PATCH  /knowledge/{ticker_id}/entries/{id}           Modifier (contenu, fiabilité, marquer reviewed)
DELETE /knowledge/{ticker_id}/entries/{id}           Supprimer
POST   /knowledge/{ticker_id}/entries/{id}/confirm   Marquer reviewed_by_user=true
POST   /knowledge/{ticker_id}/entries/{id}/flag      Marquer obsolète ou en conflit

# Knowledge Query (pour les agents et le frontend)
POST   /knowledge/query                              RAG sémantique {ticker_id, query, limit, min_reliability}

# Ingestion Pipeline
POST   /admin/ingestion/{ticker_id}/trigger          Relancer pipeline onboarding
GET    /admin/ingestion/status                       État de tous les pipelines actifs
GET    /admin/scrapers/eu                            Liste scrapers EU + santé

# Analyses bull/bear
POST   /tickers/{ticker_id}/analyses                 Lancer bull ou bear {type: 'bull'|'bear'}
GET    /tickers/{ticker_id}/analyses                 Liste analyses
GET    /tickers/{ticker_id}/analyses/{id}            Détail + entries utilisées
POST   /tickers/{ticker_id}/analyses/synthesis       Synthèse depuis bull_id + bear_id

# Thèse — modifications
POST   /theses/{id}/ack-risk/{risk_index}            Acquitter un risque de la matrice
POST   /theses/{id}/ack-pre-mortem                   Acquitter le pré-mortem
```

---

## 8. Frontend — nouvelles pages et composants

### 8.1 Nouvelle section `/knowledge/{ticker_id}`

La page de connaissance d'une entreprise — l'interface "Obsidian-like" dans le web app.

**Onglets** :
- **Profil** : profile.md rendu en HTML (éditable en Markdown inline)
- **Financiers** : financials.md — historique 10 ans avec graphiques
- **Concurrence** : competitive.md
- **Documents** : liste des knowledge_documents avec statut d'extraction
- **Entrées** : tableau des knowledge_entries avec filtres (tier, type, à vérifier, obsolètes)
- **À vérifier** : entrées `requires_human_review = true` — boutons Confirmer / Obsolète

### 8.2 Nouvelle page `/ticker/{id}/analyse`

Remplace la page `/ticker/{id}/opportunity/new`.

Layout 3 colonnes :
- Col 1 (gauche) : knowledge base du ticker — entrées utilisées, score de confiance global
- Col 2 (centre) : chat avec l'agent actif (bull ou bear selon le mode)
- Col 3 (droite) : résultat en cours de construction (bull_case_json ou bear_case_json)

**Séquence UX** :
1. "Lancer le bull case" → chat avec bull-agent
2. "Lancer le bear case" → chat avec bear-agent (onglet séparé, contexte isolé)
3. "Synthétiser" → thesis-agent produit risk_matrix → affichage de la matrice
4. Pour chaque risque : bouton "J'accepte ce risque" (obligatoire avant validation)
5. "Valider et créer la thèse" → POST /theses

### 8.3 Nouveau composant `RiskMatrixPanel.js`

Affiche la risk_matrix_json :
- Tableau des risques (probabilité, impact, réversible, réponse)
- Checkbox "J'accepte ce risque" par ligne
- Barre de progression "X/Y risques acquittés"
- Score de confiance global avec détail (X entrées Tier A, Y entrées Tier B, Z mémoire LLM)
- Bouton "Valider" activé seulement quand tous les risques sont acquittés

### 8.4 Nouveau composant `KnowledgeAuditPanel.js`

Panneau latéral sur les pages d'analyse et de thèse.

Affiche :
- Les knowledge_entries utilisées par l'analyse avec leur tier et reliability_score
- Un score de confiance agrégé (moyenne pondérée)
- Les entrées `llm_memory` en surbrillance avec lien "Vérifier"
- Les entrées en conflit (flag `has_conflict`)

---

## 9. Ce qui ne change pas

- **Système de monitoring** (modes 1-5) : inchangé fonctionnellement. La seule évolution est que le contexte injecté inclura les knowledge_entries pertinentes (RAG) au lieu des seules données yfinance.
- **Page portfolio** : inchangée.
- **Page calendrier** : inchangée.
- **Page admin** : étendue (nouveaux champs provider/model sur les agents, état des scrapers EU, pipeline ingestion).
- **Les thèses existantes** (NVDA, CAP, TSLA) : non migrées vers le nouveau flux. Leur monitoring continue normalement. La knowledge base s'enrichit progressivement pour ces entreprises en background.
- **Tables V0** : inchangées.

---

## 10. Plan de migration

### Phase 1 — Foundation knowledge platform (sans toucher au flux existant)

1. Migration DB `023_v2_knowledge_platform.sql`
2. Pipeline ingestion EDGAR pour tickers US en portefeuille (NVDA en priorité)
3. `ingestion-agent` + extraction → knowledge_entries
4. Frontend `/knowledge/{ticker_id}` — lecture seule
5. Système de scoring fiabilité + détection `llm_memory`

**Livrable** : la knowledge base existe et est navigable. Les analyses existantes ne changent pas.

### Phase 2 — Abstraction provider (LiteLLM)

1. Installer LiteLLM dans le backend
2. Implémenter `litellm_provider.py` + `dust_provider.py`
3. Modifier les agents V1 pour passer par la factory provider
4. Tests : même résultat avec provider='dust' vs provider='litellm'
5. Migrer monitoring-agent vers litellm (le moins risqué)

**Livrable** : les agents peuvent switcher de provider via l'Admin. Dust reste le défaut.

### Phase 3 — Bull/Bear flow

1. Créer `bull-agent` et `bear-agent` dans `agent_prompts` (provider=litellm)
2. Backend : `POST /tickers/{id}/analyses` + table `investment_analyses`
3. Frontend : page `/ticker/{id}/analyse` (remplace opportunity)
4. `RiskMatrixPanel.js` + acquittement des risques
5. Modifier thesis-agent pour accepter synthesis_analysis_id en input

**Livrable** : nouveau flux d'analyse disponible en parallèle de l'ancien (opt-in par ticker).

### Phase 4 — Web search + store_knowledge en agents

1. Implémenter tools `web_search`, `fetch_url`, `store_knowledge`
2. Brave Search API (gratuit 2000 req/mois) ou SearXNG self-hosted
3. Prompt bull/bear mis à jour pour utiliser les tools
4. `KnowledgeAuditPanel.js` côté frontend

**Livrable** : les agents enrichissent la knowledge base pendant leurs analyses.

### Phase 5 — EU scrapers + startups

1. Scrapers IR pour CAP et LVMH (premiers)
2. Crunchbase integration pour startups
3. Upload manuel confidentiel (Admin)
4. Health monitoring des scrapers EU

---

## 11. Décisions architecturales et leurs justifications

| Décision | Alternative considérée | Raison du choix |
|---|---|---|
| LiteLLM pour abstraction provider | Custom wrapper maison | LiteLLM gère déjà 100+ providers, retry, fallback, logging. Ne pas réinventer. |
| pgvector pour RAG | Pinecone, Weaviate, Qdrant | Déjà sur shared-postgres. Zéro nouveau service, zéro coût additionnel, données locales. |
| EDGAR Company Facts API pour US | yfinance seul, FMP | Officiel, gratuit, JSON structuré, 10+ ans. Supérieur à toute alternative gratuite. |
| knowledge_entries comme table centrale | Fichiers uniquement, graph DB | SQL est queryable, indexable, auditable. pgvector pour le sémantique. Pas de nouveau service. |
| Deux agents séparés bull/bear | Un seul agent avec deux modes | Isolation garantie de l'ancrage cognitif. Impossible autrement. |
| Markdown dans Git pour les fichiers knowledge | JSON en DB uniquement | Lisibilité humaine + versioning git + editabilité manuelle sans interface. Complément de la DB. |
| Brave Search API pour web search | Google Custom Search, SearXNG | 2000 req/mois gratuit. SearXNG self-hosted pour monter en volume sans coût. |

---

## 12. Questions ouvertes et décisions futures

**Q1 — Modèle d'embedding**
Pour générer les embeddings pgvector (`vector(1536)`), quel modèle ? Options :
- `text-embedding-3-small` (OpenAI) : $0.02/1M tokens — très bon
- `voyage-finance-2` (Voyage AI) : spécialisé finance, meilleur pour notre use case, ~$0.06/1M tokens
- `nomic-embed-text` (Ollama, local) : gratuit, légèrement moins bon
Recommandation : `text-embedding-3-small` pour commencer, migrer vers voyage-finance si la qualité du RAG est insuffisante.

**Q2 — Volume des knowledge_entries**
Sur 20 entreprises suivies, 3 ans de documents, ~20 entries par document :
→ ~5000-10000 entries. pgvector tient très bien. Pas de problème de scale pour longtemps.

**Q3 — Confidentialité des documents startup**
Les documents marqués `is_confidential = true` sont-ils accessibles aux agents ou uniquement à l'utilisateur ? Recommandation : accessibles aux agents (ils sont sur le même serveur privé), mais non exposés via les API publiques et non inclus dans les exports.

**Q4 — Validation du bull/bear par l'utilisateur**
L'utilisateur doit-il pouvoir modifier le bull case ou le bear case manuellement avant la synthèse, ou est-ce que les résultats agents sont figés ? Recommandation : modifier manuellement (comme `brief_json` sur la Page 3 actuelle) — l'utilisateur peut corriger une erreur de l'agent.

---

### Tickets créés

*(à créer lors de la session d'implémentation — par phase)*
