---
status: tickets-created
---

# Roadmap — Base de connaissance du journal (Obsidian + index Postgres)

> Origine : ticket #1787211986144 (feature, high). Reformulé en séance du 2026-08-20.
> Charte de référence : `KNOWLEDGE_ARCHITECTURE.md` (racine du repo).
> Statut : **direction à défricher** — implémentation après validation de la décision ouverte (§6).

---

## 1. Besoin (reformulé avec l'utilisateur)

Écrire en **langage naturel dans le fil journal** (Slack `#journal`) des idées ou apprentissages,
et que le système :

1. **catégorise** automatiquement l'entrée (axes fixes + tags libres) via une API externe DeepInfra ;
2. **l'enregistre** dans une base de connaissance **lisible par l'utilisateur mais non éditable
   par lui** (c'est l'agent qui écrit et maintient) ;
3. reste **exploitable par d'autres agents** plus tard.

Aujourd'hui, seuls les **parcours d'apprentissage structurés** vivent en base (journal v2).
Il faut une couche KB générale qui accueille aussi les retours libres.

## 2. Décision d'architecture — pas Notion, mais LLM Wiki (charte §2)

L'utilisateur propose **Obsidian comme UI + fichiers Markdown de référence liés à une base de
données sur le VPS**. C'est *précisément* le patron imposé par la charte :

| Artefact charte (§2) | Implémentation journal |
|---|---|
| **Pivot Markdown lisible** | Vault Obsidian : un fichier `.md` par entrée (lecture humaine). |
| **Index requêtable** | Table Postgres sur `db_assistant` (déjà réservée, cf. CLAUDE.md racine). pgvector **plus tard**. |
| **Curator / Lint** | Health-check périodique (contradictions, doublons) — phase ultérieure avec fichier ticket à créer pour s’en souvenir. |
| **Schema file** | Fichier de config de la taxonomie (« ce qui compte » pour ce domaine). |

> On ne duplique pas *deux stockages de vérité* : le **Markdown est le pivot** (source lisible),
> Postgres est l'**index** dérivé (requête, dédup, export enveloppe). C'est conforme à la règle
> d'or de la charte (§1) : un système de référence + un système de recherche superposés, pas deux silos.

## 3. Flux d'ingestion (opération *Ingest*, charte §2)

```
Message #journal (langage naturel)
        │  on_message (slack_app.py) détecte une entrée « note libre »
        ▼
DeepInfra — Llama 3.1 8B Instruct  (endpoint OpenAI-compatible)
        │  classification à schéma contraint → JSON {categorie, sous_type, tags[]}
        ▼
Écriture pivot Markdown  ──►  vault/<AAAA>/<AAAA-MM-JJ>-<slug>.md  (front-matter + corps)
        │
        └──►  UPSERT dans Postgres  (index requêtable + champs enveloppe §3)
        ▼
Confirmation Slack en thread : « Noté · personnel · apprentissage · #management »
```

- Le déclenchement se greffe sur le `on_message` existant (`app/slack_app.py`) qui gère déjà le
  « fil journal ». Distinguer une **note libre** d'une réponse à un parcours v2 (déjà routé).
- L'appel DeepInfra est **strictement une classification** : température basse, sortie JSON
  validée contre le schéma. Pas de reformulation du texte utilisateur (on garde son verbatim).
- L’agent d’organisation de la base de connaissance pourra créer de nouveaux tags, réorganiser les notes, etc.

## 4. Taxonomie (schema file du domaine)

Extrait du ticket : axes fixes **× ** tags libres.

```yaml
# categories.schema.yaml (proposition)
axes:
  contexte:   [personnel, professionnel]      # obligatoire
  nature:     [idee, apprentissage, note de lecture, etc]           # obligatoire, 0..n, vocabulaire fermé entretenu par l’agent d’organisation de la base de connaissance
tags_libres:  [management, politique, vacances, restaurant,...]   # 0..n, vocabulaire ouvert
```

Le classifieur renvoie `contexte`, `nature` + une liste de `tags` libres.
Le schema file est **versionné** et sert de prompt de cadrage au modèle.

## 5. Contrat federation-ready (charte §3, obligatoire dès le départ)

Chaque entrée doit savoir s'exporter en **enveloppe document commune**. Mapping :

| Champ enveloppe | Valeur journal |
|---|---|
| `doc_id` | `assistant-ia:vps_files:journal/<slug>` (stable). |
| `project` | `assistant-ia`. |
| `source` | `vps_files`. |
| `uri` | chemin canonique du `.md` dans le vault. |
| `title` | 1re ligne / résumé court. |
| `body` | corps Markdown (verbatim + éventuel résumé). |
| `tags` | tags libres + axes. |
| `visibility` | **`private`** (journal personnel) par défaut. |
| `created_at` / `updated_at` | date d'écriture / dernière modif. |
| `content_hash` | hash du `body` (dédup + sync incrémentale). |

Le titre est généré par un appel à l’API si possible commun avec la création des tags car le contenu en entrée est le même. 
L'export (vue SQL ou script) est livré **dès la v1**, même sans couche fédérée active
(checklist charte §5). La fédération (§4) est construite dès maintenant.

## 6. ⚠️ Décision ouverte à valider — exposition du vault Obsidian

Obsidian est une app locale qui lit un dossier de `.md`. Le vault vit sur le VPS ; comment
l'utilisateur le lit-il en Obsidian (en lecture, l'agent écrivant) ?

| Option | Description | Note |
|---|---|---|
| **A. Sync Nextcloud (WebDAV)** | Le vault = un dossier Nextcloud (backend déjà cité par la charte). L'utilisateur le synchronise en Obsidian via le plugin « Remotely Save » ou le client Nextcloud. | **Recommandé** : réutilise l'infra existante, sync bidi possible mais on garde l'écriture agent uniquement. |
| **B. Dépôt git** | Le vault = un repo git ; l'utilisateur clone et ouvre en Obsidian, `git pull` pour rafraîchir. | Simple, versionné nativement, mais friction de pull manuel. |
| **C. Rendu web read-only** | Pas d'Obsidian : une page web d'assistant-ia rend le vault (liens, tags). | Écarte la demande explicite « Obsidian comme UI ». |

→ ~~**Décidé : option A (Nextcloud WebDAV)**~~ — **révisé le 2026-08-24 : option B (dépôt git)**.

> **Motif de la révision** : il n'y a **aucun Nextcloud sur le VPS** (`docker ps` : aucun container).
> L'option A supposait une infra qui n'existe pas et aurait ajouté un chantier de déploiement complet
> en amont de la KB. L'option B ne demande rien : le vault est un dossier de `.md` avec `git init`,
> commit automatique après chaque écriture, clone + `pull` côté utilisateur pour Obsidian.
> Le format du vault et le code d'écriture sont **identiques** dans les deux options — un passage
> ultérieur à Nextcloud ne toucherait que la couche de synchronisation.
> Les garde-fous de §6.1 (chemin non dérivé d'un input, append-only, pas de suppression récursive)
> restent valables et sont repris tels quels dans le ticket vault.

### 6.1 Isolation Nextcloud (conservé pour un éventuel retour à l'option A)

L'utilisateur exige que la sync **ne puisse rien toucher d'autre** dans son Nextcloud. Cloisonnement :

- **Compte de service dédié** `journal-agent` (≠ compte perso). En WebDAV chaque compte est confiné
  à son namespace `…/remote.php/dav/files/journal-agent/` → l'agent ne voit pas les fichiers perso.
- L'agent s'authentifie via un **app password** Nextcloud (révocable indépendamment, ne divulgue
  pas le mot de passe du compte). Stocké en variable d'env Coolify : `NEXTCLOUD_WEBDAV_URL`,
  `NEXTCLOUD_USER`, `NEXTCLOUD_APP_PASSWORD`.
- Le **vault vit dans le compte de service** ; il est **partagé en lecture seule** vers le compte
  perso de l'utilisateur (son Obsidian lit, l'agent écrit).
- **Garde-fous code** : URL WebDAV fixée au dossier vault (jamais de chemin dérivé d'un input
  utilisateur), écritures **append-only** par entrée, **pas de suppression récursive**. Le pire cas
  reste confiné au vault, révocable en un clic.

## 7. Config DeepInfra (commune avec le ticket #2)

- API OpenAI-compatible : `https://api.deepinfra.com/v1/openai`.
- Modèle classif : `meta-llama/Meta-Llama-3.1-8B-Instruct` (≈ $0.03/Mtok).
- Nouvelle variable d'env Coolify : `DEEPINFRA_API_KEY` (+ `DEEPINFRA_BASE_URL` défaut ci-dessus).
- Client dédié : `app/services/deepinfra_client.py` (réutilisé par les deux tickets).

## 8. Tickets d'implémentation — **créés le 2026-08-24**

Prérequis partagé avec le chantier agent (à faire en premier) :

| ID | Ticket | Complexité |
|---|---|---|
| `1787559677482` | **Routage `on_message`** — accepter les messages parents (`slack_app.py:42` fait `if not thread_ts: return`, donc une note libre n'arrive jamais) | complexe |

Chantier `milestone: journal-kb` (`feedback-tickets/journal/`) :

| ID | Ticket | Complexité |
|---|---|---|
| `1787559677483` | **Client DeepInfra** — portage de `portfolio-tracker/backend/app/agents/providers/deepinfra_provider.py` (existe déjà, ne pas réécrire) | simple |
| `1787559677484` | **Migration index Postgres** — `009_journal_kb.sql` (pas `003` : le dossier va déjà jusqu'à 008) | simple |
| `1787559677485` | **Taxonomie + classifieur** — `categories.schema.yaml` + sortie JSON validée, titre dans le même appel | moyen |
| `1787559677486` | **Vault git + writer Markdown** — option B (cf. §6 révisé) | moyen |
| `1787559677487` | **Ingest** — assemblage : note libre → MD + upsert + accusé thread | complexe, couplé |
| `1787559677488` | **Export enveloppe** — vue `knowledge_federation_export` + `reliability` | simple |

Couche fédérée (`milestone: knowledge-federation`, `feedback-tickets/`) :

| ID | Ticket | Note |
|---|---|---|
| `1787559677490` | Base `db_knowledge_federation` + pgvector | ❌ fermé `wont-do-for-now` (2026-08-24) |
| `1787559677491` | Connecteurs (pull incrémental) | ❌ fermé avec le précédent |

> ✅ **Tranché le 2026-08-24 : la fédération n'est PAS construite.** La §5 de ce document
> (« la fédération est construite dès maintenant ») est **caduque** : elle contredisait
> `KNOWLEDGE_ARCHITECTURE.md` §4, charte transverse qui l'emporte sur une roadmap de projet.
> Motif retenu : aucune requête traversant deux sources n'a encore été formulée — le besoin
> était supposé, pas constaté. L'export « enveloppe commune » (#1787559677488) étant livré,
> la décision reste réversible à faible coût.
>
> **Ne pas rouvrir ce débat sans une requête multi-source réelle.** Détail de l'arbitrage et
> condition de réouverture : `feedback-tickets/1787559677490-feature-base-federation-pgvector.md`.

Phase ultérieure (hors v1) :

| ID | Ticket | Milestone |
|---|---|---|
| `1787559677489` | **Curator / Lint** — contradictions, doublons, dérive de taxonomie, désync vault↔index | `journal-kb-v2` |

pgvector : couvert par la couche fédérée (`1787559677490`).