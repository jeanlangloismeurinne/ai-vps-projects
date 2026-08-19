# Template — base de connaissance de projet

Squelette à copier pour doter un nouveau projet d'une KB conforme à la charte
`../../KNOWLEDGE_ARCHITECTURE.md`. Objectif : que la KB soit **federation-ready** dès le départ,
sans construire la couche fédérée tant que le besoin multi-source n'existe pas.

## Contenu du template

| Fichier | Rôle |
|---|---|
| `envelope.schema.json` | Schéma JSON formel de l'« enveloppe document commune » (le contrat). |
| `schema-file.example.json` | Squelette du *schema file* Karpathy (« ce qui compte » pour le domaine). |
| `federation_export.example.sql` | Vue SQL projetant une KB Postgres → colonnes de l'enveloppe. |
| `knowledge/index.md` | Catalogue auto-maintenu des entrées, par catégorie. |
| `knowledge/log.md` | Journal append-only des Ingest / Query / Lint. |

## Instancier pour un nouveau projet

1. Copier `knowledge/` dans le repo du projet (`projects/<projet>/knowledge/`).
2. Choisir le backend de stockage (Postgres/pgvector, Notion, Nextcloud, fichiers…). Le stockage
   natif est libre — **seul l'export de l'enveloppe est imposé**.
3. Créer le *schema file* du domaine à partir de `schema-file.example.json`.
4. Implémenter l'export enveloppe :
   - backend **Postgres** → adapter `federation_export.example.sql` en vue `knowledge_federation_export` ;
   - autre backend → écrire un petit connecteur/exporteur qui produit du JSON conforme à `envelope.schema.json`.
5. Cocher la checklist « federation-ready » de la charte (§5).
6. Documenter la KB dans le `CLAUDE.md` du projet (backend, source, visibilité par défaut, chemin de l'export).

## Ne PAS faire maintenant

- Ne pas monter la base `db_knowledge_federation` ni les connecteurs cross-source tant qu'un
  besoin de recherche multi-projet n'est pas réel (charte §4). Poser l'export suffit.
