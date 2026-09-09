"""Ligne de base du chantier v3 — les 6 mesures de la spec §9.1, REQUÊTÉES et non recopiées.

POURQUOI CE FICHIER EXISTE
--------------------------
« La ligne de base est une mesure, pas un souvenir » (`feedback_ligne_de_base_est_une_mesure`). Sur
ce chantier, elle a déjà changé le lot **trois fois de suite** : la capacité 4 visait le mauvais
émetteur, la capacité 5 a visé deux fois un mécanisme sans matière. Chaque fois, le lot avait été
découpé sur des chiffres remémorés au lieu d'être requêtés.

Ce script n'assert PRESQUE rien et c'est délibéré : il ÉTABLIT l'état de départ, il ne juge pas.
Les jugements sont dans `tools/acceptation_frameworks.py` (T1-T8). Ce qu'il assert, ce sont
uniquement les conditions sans lesquelles ses propres nombres seraient faux — un corpus vide rendrait
« 0 orpheline » et « 0 lacune » avec le même aplomb (#47/#49).

CE QU'IL N'ÉCRIT PAS
--------------------
Rien. Aucun UPDATE, aucun INSERT. Il lit le corpus courant et deux contrats.

DÉTENTEURS UNIQUES (#46) — aucune règle n'est ré-implémentée ici :
  · les deux vocabulaires et leur écart      → `tools.reconcilier_vocabulaires`
  · les cibles de synthèse et leurs planchers → `knowledge.synthesis_feed.SYNTHESIS_TARGETS`
  · la matrice de traçabilité benchmark → étape → champ → le benchmark lui-même, PARSÉ
    (`/roadmap/benchmark-methodologies-decision-investissement.md`, Partie E)

Usage (réseau `coolify` pour la base, `/roadmap` monté en lecture seule) :

    bash tools/ligne_de_base_frameworks.sh
"""
from __future__ import annotations

import asyncio
import os
import pathlib
import re
import sys
from typing import Any

from app.agents.v2.common import MVDD_FIELD_PATHS
from app.db.database import close_pool, get_db_session, init_pool
from app.knowledge.synthesis_feed import SYNTHESIS_TARGETS

from tools.reconcilier_vocabulaires import ALIAS, DERIVES, feuilles_memo

TICKERS = ["NVDA", "MSFT", "RVMD"]

# Les 4 étapes du processus canonique que §0.3 déclare produites sans preuve indexable.
ETAPES_VISEES = ("4", "5", "6", "8")

# Le benchmark est monté en lecture seule par le lanceur. On le PARSE au lieu de recopier sa
# matrice : recopiée, elle divergerait au premier amendement du benchmark, en silence.
BENCHMARK = pathlib.Path("/roadmap/benchmark-methodologies-decision-investissement.md")

ok = fail = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


def _titre(n: int, t: str) -> None:
    print(f"\n{'─'*72}\nMESURE {n} — {t}\n{'─'*72}")


# ══════════════════════════════════════════════════════════════════════════════
# Matrice de traçabilité du benchmark (Partie E) — étape canonique → champs du mémo
# ══════════════════════════════════════════════════════════════════════════════
def matrice_tracabilite() -> tuple[dict[str, set[str]], list[str]]:
    """`{étape: {feuilles de mémo}}` et la liste des noms cités que le mémo ne porte pas.

    Deux règles de résolution, toutes deux nommées parce qu'elles décident du chiffre :
      · un nom POINTÉ (`moat.type`) est pris tel quel s'il est une feuille du mémo ;
      · un nom NU (`base_rate_anchor`) est qualifié si exactement UN bloc du mémo porte ce champ.
        L'écarter au motif qu'il n'est pas pointé serait un choix de mesure caché dans une règle de
        parsing — et c'est précisément celui qui sépare le compte strict du compte permissif.
    Tout le reste (`base_rate` sur les arguments, `hypotheses[].seuil_invalidation`, un nom de BLOC
    entier comme `moat`) est rendu dans la seconde liste, donc visible, jamais absorbé en silence.
    """
    memo = feuilles_memo()
    par_nom_nu: dict[str, list[str]] = {}
    for f in memo:
        par_nom_nu.setdefault(f.split(".", 1)[1], []).append(f)

    texte = BENCHMARK.read_text(encoding="utf-8")
    partie_e = texte[texte.index("## Partie E"):]
    partie_e = partie_e.split("\n## ")[0]

    etapes: dict[str, set[str]] = {e: set() for e in ETAPES_VISEES}
    hors_memo: list[str] = []
    for ligne in partie_e.splitlines():
        cols = [c.strip() for c in ligne.strip().strip("|").split("|")]
        if len(cols) != 3 or cols[0].startswith("---") or cols[0] == "Méthodologie":
            continue
        # « 3-5, 8 » → {3,4,5,8} : un intervalle est une appartenance, pas deux bornes.
        concernees: set[str] = set()
        for morceau in cols[1].split(","):
            morceau = morceau.strip()
            if "-" in morceau:
                a, b = morceau.split("-", 1)
                if a.strip().isdigit() and b.strip().isdigit():
                    concernees |= {str(i) for i in range(int(a), int(b) + 1)}
            elif morceau.isdigit():
                concernees.add(morceau)
        if not concernees & set(ETAPES_VISEES):
            continue
        for nom in re.findall(r"`([\w.\[\]]+)`", cols[2]):
            if nom in memo:
                cible = nom
            elif len(par_nom_nu.get(nom, [])) == 1:
                cible = par_nom_nu[nom][0]
            else:
                hors_memo.append(f"étape {'/'.join(sorted(concernees & set(ETAPES_VISEES)))} : {nom}")
                continue
            for e in concernees & set(ETAPES_VISEES):
                etapes[e].add(cible)
    return etapes, sorted(set(hors_memo))


# ══════════════════════════════════════════════════════════════════════════════
async def main() -> int:
    url = os.environ.get("DATABASE_URL") or ""
    if not url:
        # Un pré-requis manquant sort en ERREUR, jamais en saut de section : une mesure incomplète
        # qui sortirait à 0 écraserait de la vérité (`feedback_check_degrade_en_sortant_a_zero`).
        print("DATABASE_URL manquant — la ligne de base se REQUÊTE sur le corpus réel.",
              file=sys.stderr)
        return 2
    if not BENCHMARK.exists():
        print(f"{BENCHMARK} introuvable — monter `../roadmap` en /roadmap (cf. le lanceur).",
              file=sys.stderr)
        return 2

    await init_pool(url)
    try:
        async with get_db_session() as conn:
            entries = await conn.fetch("""
                SELECT id, ticker_id, entry_type, source_type, reliability_tier, covers, title
                  FROM knowledge_entries
                 WHERE superseded_by IS NULL AND is_deleted = false AND ticker_id = ANY($1::text[])
                 ORDER BY ticker_id, id
            """, TICKERS)
            total_base = await conn.fetchval("""
                SELECT count(*) FROM knowledge_entries
                 WHERE superseded_by IS NULL AND is_deleted = false
            """)
    finally:
        await close_pool()

    par_ticker: dict[str, list[Any]] = {t: [] for t in TICKERS}
    for e in entries:
        par_ticker[e["ticker_id"]].append(e)

    print(f"Corpus courant : {len(entries)} entries sur {TICKERS}, {total_base} dans toute la base.")
    check("[A] le corpus courant est non vide",
          all(par_ticker[t] for t in TICKERS),
          f"→ {[t for t in TICKERS if not par_ticker[t]]} sans entry : toutes les mesures "
          f"ci-dessous seraient vraies sur zéro ligne")

    # ── MESURE 1 — orphelines par ticker ────────────────────────────────────────
    _titre(1, "entries ORPHELINES (covers vide → elles ne fondent rien)")
    print("  Un `covers` hors des 19 chemins est rendu `None` par `worker._resolve_covers` :")
    print("  l'entry est stockée et n'est indexée nulle part. Elle existe et ne sert à rien.\n")
    orphelines: dict[str, list[Any]] = {}
    for t in TICKERS:
        lignes = par_ticker[t]
        orph = [e for e in lignes if not e["covers"]]
        orphelines[t] = orph
        tierA = [e for e in orph if e["reliability_tier"] == "A"]
        pct = round(100 * len(orph) / len(lignes)) if lignes else 0
        print(f"  {t:5} {len(orph):3} / {len(lignes):3} courantes = {pct:3} %   "
              f"dont tier A : {len(tierA)}")

    print("\n  Les 16 faits tier A orphelins de NVDA — la matière du pilote « qualité financière » :")
    for e in orphelines["NVDA"]:
        if e["reliability_tier"] == "A":
            print(f"      #{e['id']:<4} {(e['title'] or '')[:66]}")

    # ── MESURES 2 et 3 — les deux vocabulaires ──────────────────────────────────
    _titre(2, "feuilles du research_memo SANS chemin d'indexation  /  chemins jamais consommés")
    memo = feuilles_memo()
    index = set(MVDD_FIELD_PATHS)
    sans_index = sorted(f for f in memo - DERIVES if ALIAS.get(f) not in index)
    jamais_consommes = sorted(index - {ALIAS[k] for k in ALIAS if k in memo})
    print(f"  feuilles du mémo (hors refs, hors dérivés) : {len(memo - DERIVES)}")
    print(f"  chemins indexables                         : {len(index)}")
    print(f"  → feuilles SANS chemin d'indexation        : {len(sans_index)}")
    print(f"  → chemins JAMAIS consommés par le mémo     : {len(jamais_consommes)}")
    print("  (détail nominatif : `bash tools/reconcilier_vocabulaires.sh`)")

    # ── MESURE 4 — étapes 4/5/6/8 avec preuve indexable ─────────────────────────
    _titre(4, "étapes 4/5/6/8 du benchmark avec preuve INDEXABLE")
    etapes, hors_memo = matrice_tracabilite()
    check("[A] la matrice de traçabilité a bien été lue",
          all(etapes[e] for e in ETAPES_VISEES),
          f"→ étapes sans aucun champ résolu : {[e for e in ETAPES_VISEES if not etapes[e]]} — "
          f"le parsing de la Partie E a cessé de mordre, '0 preuve' serait vrai sur zéro champ")
    strict = permissif = 0
    for e in ETAPES_VISEES:
        champs = sorted(etapes[e])
        indexes = [c for c in champs if ALIAS.get(c) in index]
        orphs = [c for c in champs if c not in indexes]
        strict += 1 if champs and not orphs else 0
        permissif += 1 if indexes else 0
        print(f"\n  Étape {e} — {len(indexes)}/{len(champs)} champ(s) indexable(s)")
        for c in indexes:
            print(f"      indexable  {c}  →  {ALIAS[c]}")
        for c in orphs:
            print(f"      ORPHELIN   {c}")
    if hors_memo:
        print("\n  Cités par la matrice mais hors des feuilles du mémo (donc non comptés) :")
        for h in hors_memo:
            print(f"      · {h}")
    print(f"\n  → étapes dont TOUS les champs sont indexables (strict) : {strict} / 4")
    print(f"  → étapes dont AU MOINS UN champ est indexable          : {permissif} / 4")
    print("  ⚠️ La spec §9.1 annonce 0 : c'est le compte STRICT. Le mermaid de §0.3 omet\n"
          "     `valuation.base_rate_anchor` (étape 8), seul champ qui sépare les deux comptes.")

    # ── MESURE 5 — synthèses grounded ───────────────────────────────────────────
    _titre(5, "synthèses GROUNDED produites, et matière indexée disponible par cible")
    print("  Une synthèse grounded = entry `analysis` / `agent_synthesis` couvrant une cible.")
    print("  « Matière INDEXÉE » = entries primaires dont `covers` porte la cible, au tier citable.")
    print("  Le feed réel, lui, sélectionne ses candidats par recherche VECTORIELLE sur tout le")
    print("  corpus : les deux comptes peuvent donc diverger, et leur divergence est le sujet.\n")
    for t in TICKERS:
        lignes = par_ticker[t]
        produites = [e for e in lignes
                     if e["entry_type"] == "analysis" and e["source_type"] == "agent_synthesis"]
        couvertes = {c for e in produites for c in (e["covers"] or [])}
        vides = []
        print(f"  {t} — {len(produites)} synthèse(s) grounded")
        for chemin, cible in SYNTHESIS_TARGETS.items():
            citables = [e for e in lignes
                        if chemin in (e["covers"] or [])
                        and e["reliability_tier"] in cible.citable_tiers
                        and not (e["entry_type"] == "analysis"
                                 and e["source_type"] == "agent_synthesis")]
            assez = len(citables) >= cible.min_citations
            if not assez:
                vides.append(chemin)
            # « synthèse SANS matière indexée » : le cas qui compte. La synthèse existe, donc elle
            # a été fondée — mais sur des entries que l'index n'attache PAS à ce champ.
            ecart = "  ⚠ synthétisée SANS matière indexée" if (chemin in couvertes and not assez) \
                else ("  → matière indexée insuffisante" if not assez else "")
            print(f"      {'✓' if chemin in couvertes else '·'} {chemin:34} "
                  f"matière indexée {len(citables)}/{cible.min_citations}{ecart}")
        aveugles = sorted(couvertes & set(vides))
        print(f"      cibles sans matière indexée suffisante : {len(vides)} / "
              f"{len(SYNTHESIS_TARGETS)}"
              + (f"   · dont {len(aveugles)} pourtant SYNTHÉTISÉE(S)" if aveugles else ""))

    print("\n  ⚠️ CE QUE LA SPEC §0.2 NE DIT PAS, et qui sort de cette mesure : NVDA a produit 4\n"
          "     synthèses sur 4 cibles dont la matière INDEXÉE est insuffisante. Elles ne sont pas\n"
          "     inventées — elles sont fondées sur des entries que l'index n'attache pas au champ\n"
          "     synthétisé. C'est le mécanisme de §0.4 (l'entry orpheline #33, citée dans la prose\n"
          "     d'une synthèse) généralisé aux quatre cibles : la recherche vectorielle rattrape\n"
          "     par chance sémantique ce que le rangement a laissé tomber. Ce que le lot 3 doit\n"
          "     rendre reproductible, il le fait aujourd'hui par accident.")

    # ── MESURE 6 — produits.unit_economics ──────────────────────────────────────
    _titre(6, "entries sur `produits.unit_economics`, toute la base confondue")
    ue = [e for t in TICKERS for e in par_ticker[t] if "produits.unit_economics" in (e["covers"] or [])]
    primaires = [e for e in ue if not (e["entry_type"] == "analysis"
                                       and e["source_type"] == "agent_synthesis")]
    print(f"  {len(ue)} entries au total, dont {len(primaires)} PRIMAIRES "
          f"(non issues d'une synthèse) :\n")
    for e in ue:
        marque = "synthèse" if e not in primaires else "PRIMAIRE"
        print(f"      #{e['id']:<4} [{marque}] {e['ticker_id']:5} {(e['title'] or '')[:52]}")
    print("\n  ⚠️ Le champ n'est alimenté QUE par des synthèses de lui-même : aucun fait primaire\n"
          "     ne le fonde nulle part. La spec §0.2 dit « 2 entries » ; la mesure dit en plus\n"
          "     que ces 2 entries sont des dérivées, ce qui est strictement pire.")

    # ── Récapitulatif — la table de §9.1, telle que mesurée ─────────────────────
    print(f"\n{'═'*72}\nLIGNE DE BASE AU {os.environ.get('BASELINE_DATE', '2026-09-09')} "
          f"— table §9.1 mesurée\n{'═'*72}")
    lignes_recap = [
        ("Orphelines par ticker", " · ".join(
            f"{t} {round(100*len(orphelines[t])/len(par_ticker[t]))} %" for t in TICKERS)),
        ("Feuilles de mémo sans chemin d'indexation", str(len(sans_index))),
        ("Chemins jamais consommés", str(len(jamais_consommes))),
        ("Synthèses grounded sur RVMD", str(len([
            e for e in par_ticker["RVMD"]
            if e["entry_type"] == "analysis" and e["source_type"] == "agent_synthesis"]))),
        ("Entries sur produits.unit_economics", f"{len(ue)} (dont {len(primaires)} primaires)"),
        ("Étapes 4/5/6/8 avec preuve indexable", f"{strict} (strict) · {permissif} (permissif)"),
    ]
    for k, v in lignes_recap:
        print(f"  {k:44} {v}")

    print(f"\n{ok} vérifications OK, {fail} échec(s)")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
