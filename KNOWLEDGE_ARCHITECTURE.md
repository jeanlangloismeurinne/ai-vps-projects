# Architecture des bases de connaissance — charte transverse

> Contrat commun à **toutes** les bases de connaissance (KB) du repo, quel que soit leur
> backend (VPS/Postgres, Notion, Nextcloud, mails mailbox.org, web…).
> Lire ce fichier avant de concevoir ou d'implémenter une KB dans un projet.
> Implémentation de référence : `projects/portfolio-tracker/` (Knowledge Platform, pattern Karpathy).

---

## 1. Principe fondateur — séparer le *stockage* de la *recherche*

Deux plans distincts, qu'il ne faut jamais confondre :

```
SYSTÈME DE RÉFÉRENCE            SYSTÈME DE RECHERCHE
(où vit la connaissance)        (comment on la retrouve)
────────────────────────        ────────────────────────
Par projet, dans le backend     UNE couche fédérée unique,
qui lui convient :              ajoutée paresseusement :
 · Postgres/pgvector (pt)        · index `documents` (pgvector)
 · Notion                        · alimenté par des connecteurs
 · Nextcloud (WebDAV)            · recherche exhaustive = requête
 · mailbox.org (IMAP)            · recherche projet = filtre `project=`
 · fichiers Markdown VPS
```

**Règle d'or.** On ne centralise jamais le *stockage*. Chaque projet garde sa connaissance
dans son système naturel. La seule chose mutualisée est un **index de recherche** qui ingère
une *projection normalisée* (l'« enveloppe », §3) de chaque source.

Conséquence directe sur la question « base unique vs une par projet » :

| Niveau | Décision |
|---|---|
| Stockage / système de référence | **Une KB par projet**, schéma métier propre. |
| Recherche / système de retrieval | **Un seul index fédéré**, construit *quand le besoin multi-source apparaît*. |

On ne choisit donc pas entre les deux : on les superpose. « Par projet » devient un simple
filtre sur l'index fédéré, pas un silo.

---

## 2. Le pattern de KB par projet — *LLM Wiki* (Karpathy)

Toute KB de projet suit le **LLM Wiki Pattern** : un wiki cumulatif et persistant, pas un RAG
rejoué à chaque requête. « The wiki is a persistent, compounding artifact » — chaque source
ingérée et chaque synthèse produite densifient le corpus.

Chaque KB implémente **trois opérations** et **quatre artefacts** :

**Opérations**

| Op | Rôle |
|---|---|
| **Ingest** | Traiter une source → extraire → mettre à jour pages + cross-références. |
| **Query** | Rechercher → synthétiser avec citations → archiver les findings de valeur. |
| **Lint** | Health-check périodique : contradictions, entrées périmées, pages orphelines. |

**Artefacts**

1. **Pivot Markdown lisible** — la version humaine (`index.md`, `log.md` append-only, pages).
2. **Index requêtable** — la version agent (Postgres/pgvector, ou l'API de recherche du backend).
3. **Curator / Lint** — le garde-fou qualité.
4. **Schema file** — la config « ce qui compte » pour ce domaine (l'équivalent d'un `CLAUDE.md`
   pour les agents du projet ; ex. `sector_schemas/{secteur}.json` dans portfolio-tracker).

> Le Markdown est le **format pivot** : lisible par un humain *et* ingérable par un LLM.
> Tout backend (Notion, mail, WebDAV) est converti en Markdown + métadonnées à l'ingestion.

---

## 3. Le contrat — l'« enveloppe document » commune (v1)

C'est **la seule contrainte** qui rend la fédération future triviale. Chaque KB doit savoir
**exporter** ses éléments sous cette forme (vue SQL, script d'export, ou connecteur). Le stockage
natif reste libre ; seul l'export est normalisé.

| Champ | Type | Obligatoire | Description |
|---|---|:---:|---|
| `doc_id` | text | ✅ | Identifiant global stable. Format : `{project}:{source}:{local_id}`. |
| `project` | text | ✅ | Slug du projet (ex. `portfolio-tracker`). |
| `source` | text | ✅ | Backend d'origine : `vps_files`·`postgres`·`notion`·`nextcloud`·`mailbox`·`web`·`agent_synthesis`. |
| `uri` | text | ✅ | Pointeur canonique vers l'original (path, URL Notion, WebDAV, `imap://…/{message-id}`, https). |
| `title` | text | ✅ | Titre lisible. |
| `body` | text | ✅ | Contenu **Markdown** (pivot humain). |
| `lang` | text | | Code ISO (`fr`, `en`…). |
| `tags` | text[] | | Étiquettes libres. |
| `entities` | jsonb | | Références normalisées pour le cross-linking (ex. `{"tickers":["NVDA"]}`). |
| `reliability` | numeric(3,2) | | Score 0.00→1.00 (défaut selon `source`, cf. §6). |
| `reliability_tier` | text | | Tier lisible (`A`,`B+`,`C`…). |
| `visibility` | text | ✅ | `public` \| `private` \| `confidential`. **`mailbox` = `private` par défaut.** |
| `created_at` | timestamptz | ✅ | Date de l'original dans son système de référence. |
| `updated_at` | timestamptz | ✅ | Dernière modif de l'original. |
| `ingested_at` | timestamptz | ✅ | Date d'ingestion dans l'index fédéré (posée par le connecteur). |
| `content_hash` | text | ✅ | Hash du `body` — dédup + détection de changement (sync incrémentale). |
| `embedding` | vector | | Calculé **à l'ingestion fédérée**, pas par le projet. |
| `metadata` | jsonb | | Extras spécifiques au projet — **n'entre jamais** dans le contrat, ne le casse jamais. |

Schéma JSON formel : `templates/knowledge-base/envelope.schema.json`.

### Exemple

```json
{
  "doc_id": "portfolio-tracker:postgres:knowledge_entry/8421",
  "project": "portfolio-tracker",
  "source": "postgres",
  "uri": "https://portfolio.jlmvpscode.duckdns.org/knowledge/entry/8421",
  "title": "NVDA — FCF margin 55.3% (EDGAR Q4-2025)",
  "body": "## Fait financier\nRevenue $44.1B (+122% YoY)...",
  "tags": ["nvda", "financials", "edgar"],
  "entities": {"tickers": ["NVDA"]},
  "reliability": 0.95,
  "reliability_tier": "A",
  "visibility": "public",
  "created_at": "2026-08-09T14:32:00Z",
  "updated_at": "2026-08-09T14:32:00Z",
  "ingested_at": "2026-08-10T03:00:00Z",
  "content_hash": "sha256:1f3a…",
  "metadata": {"source_type": "edgar_official", "entry_version": 2}
}
```

---

## 4. La couche fédérée (à construire *plus tard*, pas maintenant)

Quand le besoin de recherche multi-source se matérialise :

- **Techno** : réutiliser `shared-postgres` + `pgvector` — **aucune nouvelle brique**.
  Base dédiée `db_knowledge_federation`, une table `documents` (colonnes = enveloppe §3).
- **Alimentation** : un **connecteur par source** (pull, incrémental via `content_hash`/`updated_at`) :

  | Source | Connecteur |
  |---|---|
  | `postgres` (ex. portfolio-tracker) | Vue SQL `knowledge_federation_export` → copie incrémentale. |
  | `vps_files` | Lecture des `.md` + front-matter → enveloppe. |
  | `notion` | API/MCP Notion → pages → Markdown. |
  | `nextcloud` | WebDAV list+download → extraction texte. |
  | `mailbox` | IMAP → messages → enveloppe (`visibility=private`). |

- **Requête** : recherche exhaustive = `SELECT … ORDER BY embedding <=> :q`; recherche projet =
  même requête `WHERE project = :p`. Les agents citent via `uri`.
- **Confidentialité** : filtrer sur `visibility` selon le contexte d'appel. Les mails
  (`confidential`/`private`) ne remontent jamais dans un contexte public.

> Tant que le besoin n'est pas là, **ne rien construire de la §4**. Seules les §2 et §3
> s'appliquent à chaque nouveau projet dès le départ.

---

## 5. Ce qu'un projet doit garantir pour être « federation-ready »

Checklist à respecter dès la conception d'une KB, même sans fédération active :

- [ ] Sait **exporter l'enveloppe §3** (vue SQL, script, ou connecteur) — au moins les champs obligatoires.
- [ ] `doc_id` et `uri` **stables** (ne changent pas si le contenu est ré-ingéré).
- [ ] **Markdown** comme format de `body`.
- [ ] Déclare son `source` et une `reliability` par défaut (§6).
- [ ] Positionne `visibility` correctement (mail/documents privés → `private`/`confidential`).
- [ ] `content_hash` calculable pour la sync incrémentale.
- [ ] Fournit un **schema file** (« ce qui compte » pour le domaine).

Point d'appui : `templates/knowledge-base/` contient le squelette complet à copier.

---

## 6. Framework de fiabilité (partagé)

Chaque enveloppe porte un `reliability` (0.00→1.00) et un `reliability_tier`. Barème de base
par type de source (repris de portfolio-tracker, extensible par projet dans `metadata.source_type`) :

| Source type | Tier | Score |
|---|:---:|:---:|
| Filing officiel (SEC/EDGAR) | A | 0.95 |
| Document officiel entreprise (IR) | A | 0.90 |
| Régulateur EU (AMF, BaFin) / transcript officiel | A- | 0.85 |
| Presse financière (FT, Bloomberg, Reuters) | B+ | 0.75 |
| Document confidentiel fourni par l'utilisateur | B+ | 0.80 |
| Web source réputée / fourni utilisateur | B | 0.65–0.70 |
| Web générique non classé | C+ | 0.50 |
| Mémoire LLM (pré-entraînement) | C | 0.40 |
| Synthèse d'agent (dérivée) | B- | 0.60 |

Modulation : `-0.05/an` (données financières) ou `-0.02/an` (qualitatif) ; `+0.10` si
cross-validé par 2 sources indépendantes ; `-0.20` si contredit par une source récente.

---

## 7. Résumé en une phrase

**KB verticale par projet** (pivot Markdown + index requêtable + Lint + schema file, façon
Karpathy), stockée dans le backend naturel du projet ; **une seule couche de recherche fédérée**
ajoutée le jour du besoin multi-source ; le seul travail à faire *dès aujourd'hui* pour chaque
projet est de savoir **exporter l'enveloppe document commune (§3)**.
