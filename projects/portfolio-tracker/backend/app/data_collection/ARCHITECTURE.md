# `data_collection/` — ⚠️ LEGACY V0/V1

> **Ce module est hérité de V0/V1. Ne pas le confondre avec les feeds V2/V3 de `knowledge/`.**

## Rôle

Le **DataService** historique : accès aux données de marché (yfinance EOD + FMP fondamentaux + FRED
macro) pour la boucle V1. `data_service.py` est le **seul point d'accès** aux données marché
(convention #8) — ne jamais appeler `collect_quantitative()` directement.

| Fichier | Rôle |
|---|---|
| `data_service.py` | Point d'accès unique (cache Redis, `get_m1`/`refresh_m1`) |
| `m1_quantitative.py` · `m2_events.py` · `m3_qualitative.py` · `m4_macro.py` | Collecteurs V0/V1 par régime |
| `assembler.py` · `data_cache.py` | Assemblage + cache |

## Rapport avec la V3

- **Aucune extension V3 ici.** Une nouvelle **source de données** au sens V3 s'ajoute dans
  `knowledge/` (feed déterministe + `store_knowledge` + `source_registry`), **pas** ici — voir
  `app/knowledge/ARCHITECTURE.md`.
- Ce module reste **actif en production** pour la boucle V1 (schedulers, DataService). Il n'est pas
  gardé par la suite `checks/` V2/V3 : toute modification est de la **vigilance manuelle**.
