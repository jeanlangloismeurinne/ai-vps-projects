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
- Ce module reste **actif en production** pour la boucle V1 (schedulers, DataService). Hors de la
  garde ci-dessous, toute modification reste de la **vigilance manuelle**.

## Gardes

| Garantie | Garde |
|---|---|
| Le cours coté et sa date : un non-nombre est une ABSENCE, une séance vide n'est pas une séance, et la mesure est datée du dernier FAIT (#81) | `check_cours_cote.py` + `negatif_cours_cote.sh` |
| La même garantie tenue sur le CHEMIN RÉEL : un `refresh_m1` contre le vrai fournisseur, jusqu'à l'écriture PostgreSQL, ne laisse passer aucun non fini (#81) | `check_cours_cote_live.py` (hors `run_all.sh` : réseau ouvert + clé fournisseur + écriture DB) |

Ce que cette garde tient, et pourquoi elle est née dans un module « legacy » : le 2026-09-23, le
fournisseur a rendu 251 séances dont la dernière avait un `Close` vide — sur les trois titres à la
fois, donc le fournisseur et non le titre. Les quatre variations de la fiche se terminant toutes au
dernier cours, elles sont tombées ensemble, en `NaN` : une non-valeur qui a la **forme** d'un
nombre, qui est **vraie** au sens booléen, et que PostgreSQL refuse — l'écriture du cache m1 cassait
donc **après** que l'appel réseau avait été payé (6 producteurs déterministes en échec). Les gardes
d'alors testaient la FORME du cadre (`len(hist) < days`), jamais la VALEUR des cours aux bornes.

Trois règles en sont sorties, chacune à **détenteur unique** (#46) : `fini` (un non-nombre est une
absence, `0.0` traverse), `serie_cotee` (une séance sans cours n'est pas une séance) et
`_assainir_non_finis` — le **filet** posé sur la porte de la convention #8, qui garantit qu'aucun
champ *futur* n'injectera un non-nombre sans qu'on le sache. Voir `CLAUDE.md` § #81.
