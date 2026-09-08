"""Ligne de base de la capacité 5 — combien de pièces documentent une ABSENCE, et que fondent-elles ?

POURQUOI CET OUTIL EXISTE, ET POURQUOI IL TOURNE *AVANT* LE LOT
---------------------------------------------------------------
La capacité 5 a été réfutée deux fois par sa propre mesure (file d'arbitrage humain : 0 conflit ;
arbitrage de textes : 0 divergence réelle sur 29 couples, et un jugement instable d'un passage à
l'autre à température 0). Le défaut que ces deux mesures ont trouvé au passage est le vrai sujet du
lot : **une pièce qui documente une absence est comptée comme une fondation** — MSFT #97
(`edgar_official`, A) dit « Microsoft ne publie PAS de ventilation quantitative » et rend pourtant
`business_model.recurrence_pct` `couvert`.

#97 est le cas CONNU. Ce script répond à la seule question qui décide de l'ampleur du lot, et elle
est gratuite : **combien y en a-t-il d'autres, et sur combien de champs comptent-ils aujourd'hui ?**
(`feedback_ligne_de_base_est_une_mesure` — la ligne de base a changé le lot trois fois de suite.)

CE QU'IL MESURE
---------------
1. **Le filet lexical** — les entries courantes dont le texte porte un marqueur d'absence, avec
   l'extrait imprimé EN TEXTE. Le filet ratisse large à dessein : il ne conclut rien, il donne à
   LIRE. Le tri candidat/faux positif est un jugement, il n'est pas automatisé ici
   (`feedback_deleguer_recherche_pas_jugement`).
2. **Ce que chaque candidat FONDE réellement aujourd'hui** — non pas ce que son `covers` annonce,
   mais ce que la porte de production lui accorde : on rejoue `_apply_deterministic_overrides`
   (#54) sur le `report_json` PERSISTÉ et on lit les `fondations`. Une entry sous plancher ou périmée
   n'est comptée nulle part : elle ne fonde rien, elle n'est donc pas le sujet du lot.
3. **L'ampleur du correctif** — pour chaque champ fondé par un candidat : ce candidat est-il le SEUL
   à le fonder ? Si oui, le champ bascule le jour où « une absence ne fonde plus » ; sinon le champ
   tient tout seul et le correctif est cosmétique sur lui. C'est ce compte, et lui seul, qui dit si
   le lot vaut la chaîne entière ou un garde-fou.
4. **Les trois traitements d'une même réalité** — le verdict rendu sur
   `business_model.recurrence_pct` émetteur par émetteur (NVDA dispensé · MSFT couvert · RVMD non
   couvert), relu en base plutôt que recopié de la spec : c'est la mesure du défaut, et une
   consignation n'est pas une mesure.

CE QU'IL NE FAIT PAS
--------------------
Il n'écrit rien (aucun UPDATE, aucun INSERT), n'appelle aucun modèle, et ne ré-implémente aucune
règle de couverture : il appelle `_apply_deterministic_overrides`, la fonction de production. Un
second calcul de couverture ici serait une seconde porte (#46), et elle divergerait au premier
correctif.

⚠️ RVMD n'a AUCUN rapport `readiness` persisté (mesuré à la capacité 4). Pour lui, la porte ne peut
pas être rejouée : son bloc est calculé depuis l'index `covers` + les planchers, et il est
**étiqueté comme tel** dans la sortie. Confondre les deux ferait lire une absence de rapport comme
un « aucun candidat ne fonde rien » — le zéro le plus rassurant produit par la pire des raisons
(#49).

Usage : `bash tools/mesure_absences.sh`
"""
from __future__ import annotations

import asyncio
import copy
import json
import os
import re
import sys
from typing import Any, Optional

from app.agents.v2.common import FIELD_PROFILES
from app.agents.v2.curator import (
    _apply_deterministic_overrides,
    _plancher_for,
    _tier_ge,
    nonblocking_gaps_for,
)
from app.db.database import close_pool, get_db_session, init_pool
from app.knowledge.material_events import ancre_substantielle, material_anchor_for_ticker
from app.knowledge.service import get_current_entries

TICKERS = ["NVDA", "MSFT", "RVMD"]

# Le champ qui porte le défaut connu — nommé par ce qu'il EST, pas par l'id de l'entry qui l'a
# révélé : un id codé en dur se périme au premier re-seed et la mesure sortirait un zéro muet.
CHAMP_TEMOIN = "business_model.recurrence_pct"

# ── Le filet lexical ────────────────────────────────────────────────────────────────────────────
# Chaque motif est NOMMÉ : un compte agrégé ne dirait pas lequel ratisse trop large, et c'est
# précisément ce qu'il faut pouvoir lire pour calibrer le lot. Le corpus est en français (#027)
# mais cite des dépôts anglophones : les deux langues sont couvertes.
MOTIFS: list[tuple[str, str]] = [
    ("fr:ne publie pas",   r"ne\s+(publie|publient|divulgue|divulguent|communique|communiquent|"
                           r"détaille|détaillent|ventile|ventilent|isole|isolent|fournit|fournissent|"
                           r"chiffre|chiffrent|quantifie|quantifient)\s+(pas|plus)"),
    ("fr:n'est pas publié", r"n['’](est|sont)\s+(pas|ni)\s+\w{0,12}\s*(publi|divulgu|communiqu|"
                            r"détaill|ventil|isol|renseign|quantifi|chiffré|disponible|accessible)"),
    ("fr:aucune donnée",   r"(aucune?|nulle)\s+\w{0,15}\s*(ventilation|donnée|information|chiffre|"
                           r"communication|divulgation|publication|décomposition|répartition)"),
    ("fr:pas de X publié", r"pas\s+de\s+\w{0,15}\s*(ventilation|donnée publi|chiffre publi|"
                           r"information publi|détail|décomposition|répartition|granularité)"),
    ("fr:non publié",      r"\bnon\s+(publi|divulgu|communiqu|renseign|quantifi|chiffré|détaill|"
                           r"ventil|disponible|accessible|documenté)"),
    ("fr:indisponible",    r"(indisponible|introuvable|non\s+trouvé|sans\s+réponse\s+chiffrée)"),
    ("en:does not X",      r"does\s+not\s+(disclose|break\s+out|provide|report|publish|quantify|"
                           r"separately)"),
    ("en:not X",           r"\bnot\s+(disclosed|publicly|broken\s+out|quantified|available|"
                           r"reported\s+separately|provided)"),
    ("en:no X",            r"\bno\s+(breakdown|public\s+|disclosure|granularity)"),
    ("en:undisclosed",     r"undisclosed"),
    ("clef:not_available", r"(not_available|not_disclosed|non_publie|non_disponible|"
                           r"donnee_absente)"),
]
_COMPILES = [(nom, re.compile(rx, re.IGNORECASE)) for nom, rx in MOTIFS]

# Le marqueur PRESCRIT par le prompt de synthèse (`synthesis_feed`, trois formulations), plus les
# variantes que le modèle produit réellement. On cherche la formule imposée, pas une absence en
# général : c'est ce qui rend ce compte reproductible d'un passage à l'autre.
#
# ⚠️ Le premier jet ne cherchait que la forme « non documenté ». Il ratait les trois trous de #55,
# écrits « n'est pas documentée » / « ne sont pas documentées » — le modèle produit la consigne du
# prompt sous deux formes verbales, et n'en attraper qu'une SOUS-compte en silence. Un mesureur qui
# rate ce qu'il cherche rend un zéro rassurant produit par la pire des raisons (#49).
_MARQUE = r"(document|observ|chiffr|quantifi|détaill|renseign|disponible|publi)"
_RX_TROU = re.compile(
    rf"(non\s+{_MARQUE}"                          # « non documenté en base »
    rf"|n['’](est|sont)\s+pas\s+\w{{0,10}}\s*{_MARQUE}"   # « n'est pas documentée »
    rf"|ne\s+\w{{0,12}}\s*pas\s+{_MARQUE}"        # « ne sont pas documentés »
    rf"|aucune?\s+entry\s+.{{0,40}}ne\s+{_MARQUE})",
    re.IGNORECASE,
)


def _extrait(texte: str, m: re.Match) -> str:
    """La phrase autour du marqueur — c'est ce qui se LIT, le compte ne se juge pas tout seul."""
    debut = max(texte.rfind(".", 0, m.start()), texte.rfind("\n", 0, m.start())) + 1
    fin = min([p for p in (texte.find(". ", m.end()), texte.find("\n", m.end())) if p != -1]
              + [len(texte)])
    return " ".join(texte[debut:fin + 1].split())[:400]


def _candidats(entries: list[dict[str, Any]]) -> dict[int, list[tuple[str, str]]]:
    """id → [(nom du motif, extrait)]. Titre ET contenu : un titre porte souvent l'assertion."""
    out: dict[int, list[tuple[str, str]]] = {}
    for e in entries:
        texte = f"{e.get('title') or ''}\n{e.get('content') or ''}"
        # `content_structured` est scanné en JSON brut : une clef `not_available` y vit sans phrase.
        cs = e.get("content_structured")
        if cs:
            texte += "\n" + (cs if isinstance(cs, str) else json.dumps(cs, ensure_ascii=False))
        hits = []
        for nom, rx in _COMPILES:
            m = rx.search(texte)
            if m:
                hits.append((nom, _extrait(texte, m)))
        if hits:
            out[e["id"]] = hits
    return out


# ── Ce que la porte accorde réellement ──────────────────────────────────────────────────────────
_SQL_DERNIER = """
    SELECT id, verdict, report_json
      FROM knowledge_curator_reports
     WHERE ticker_id = $1 AND report_type = 'readiness'
     ORDER BY created_at DESC, id DESC
     LIMIT 1
"""


def _fondations(coverage: dict[str, Any]) -> dict[str, list[int]]:
    """`dimension.champ` → entry_ids que la PORTE compte comme fondations (pas le `covers` annoncé)."""
    out: dict[str, list[int]] = {}
    for bloc in ("structuree", "qualitative_marche"):
        for d in (coverage.get(bloc) or {}).get("dimensions") or []:
            if not isinstance(d, dict):
                continue
            for f in d.get("fondations") or []:
                out[f"{d.get('dimension')}.{f.get('champ')}"] = list(f.get("entry_ids") or [])
    return out


def _statut_champ(coverage: dict[str, Any], path: str) -> str:
    """Le verdict rendu sur UN champ : couvert / couvert_perime / non_couvert (#54)."""
    dim, _, champ = path.partition(".")
    for bloc in ("structuree", "qualitative_marche"):
        for d in (coverage.get(bloc) or {}).get("dimensions") or []:
            if not isinstance(d, dict) or d.get("dimension") != dim:
                continue
            if champ not in (d.get("champs_requis") or []):
                continue
            if champ in (d.get("champs_perimes") or []):
                return "couvert_perime"
            if champ in (d.get("champs_non_fondables") or []):
                return "non_couvert"
            return "couvert"
    return "hors_requis"


def _index_covers(entries: list[dict[str, Any]]) -> dict[str, list[tuple[int, str]]]:
    """Repli SANS rapport persisté : l'index brut + le plancher, sans l'axe d'actualité.

    ⚠️ Ce n'est PAS la porte, et la sortie le dit. Sans rapport, `champs_requis` n'existe pas :
    on lit `FIELD_PROFILES`, la table de doctrine, qui dit quel plancher chaque champ exige.
    """
    idx: dict[str, list[tuple[int, str]]] = {}
    for e in entries:
        covers = e.get("covers")
        if isinstance(covers, str):
            covers = [covers]
        for path in covers or []:
            idx.setdefault(path, []).append((e["id"], e.get("reliability_tier")))
    return idx


async def mesurer(conn, ticker_id: str) -> dict[str, Any]:
    entries = await get_current_entries(conn, ticker_id, min_reliability=0.0, limit=500)
    ancre = ancre_substantielle(await material_anchor_for_ticker(conn, ticker_id))
    cands = _candidats(entries)

    ligne = await conn.fetchrow(_SQL_DERNIER, ticker_id)
    res: dict[str, Any] = {
        "entries": {e["id"]: e for e in entries},
        "candidats": cands,
        "ancre": ancre,
        "source": None,
        "fondations": {},
        "coverage": None,
        "report_id": None,
    }
    if ligne is not None:
        stocke = ligne["report_json"]
        if isinstance(stocke, str):
            stocke = json.loads(stocke)
        apres = _apply_deterministic_overrides(copy.deepcopy(stocke), entries,
                                               ancre=ancre, ticker_id=ticker_id)
        res["source"] = "porte rejouée sur le rapport persisté"
        res["report_id"] = ligne["id"]
        res["coverage"] = apres.get("coverage") or {}
        res["fondations"] = _fondations(res["coverage"])
    else:
        # Repli déclaré — pas de rapport, donc pas de porte. On dit ce qu'on fait.
        res["source"] = "index `covers` + planchers (AUCUN rapport persisté — ce n'est pas la porte)"
        idx = _index_covers(entries)
        dispenses = nonblocking_gaps_for(ticker_id)
        fond: dict[str, list[int]] = {}
        for path, membres in idx.items():
            if path in dispenses:
                continue
            dim, _, champ = path.partition(".")
            plancher = _plancher_for(dim, champ, "B")
            retenues = [i for i, t in membres if _tier_ge(t, plancher)]
            if retenues:
                fond[path] = retenues
        res["fondations"] = fond
    return res


def main_rapport(mesures: dict[str, dict[str, Any]]) -> None:
    total_cand = total_fondants = 0
    champs_touches: list[tuple[str, str, int, bool]] = []   # ticker, champ, entry, seul fondateur

    for ticker in TICKERS:
        m = mesures[ticker]
        a = m["ancre"]
        print(f"\n{'='*78}\n=== {ticker} — {len(m['entries'])} entries courantes ===")
        print(f"  ancre    : {a.status}" + (f" · {a.event.form} du {a.event.event_date}"
                                            if a.event else ""))
        print(f"  couverture lue depuis : {m['source']}"
              + (f" (rapport #{m['report_id']})" if m["report_id"] else ""))

        if not m["candidats"]:
            print("  aucune entry ne porte de marqueur d'absence.")
            continue

        # index inverse : quelle entry fonde quel champ, selon la porte
        fonde_par: dict[int, list[str]] = {}
        for path, ids in m["fondations"].items():
            for i in ids:
                fonde_par.setdefault(i, []).append(path)

        for eid, hits in sorted(m["candidats"].items()):
            e = m["entries"][eid]
            total_cand += 1
            porte = sorted(fonde_par.get(eid, []))
            annonce = sorted(e.get("covers") or [])
            marque = "🔴 FONDE" if porte else "   (ne fonde rien)"
            print(f"\n  {marque}  #{eid}  {e.get('reliability_tier')}/{e.get('source_type')}"
                  f"/{e.get('nature')}  {e.get('source_date')}")
            print(f"      titre   : {(e.get('title') or '')[:110]}")
            print(f"      covers  : {', '.join(annonce) or '—'}")
            if porte:
                total_fondants += 1
                for path in porte:
                    seul = m["fondations"].get(path, []) == [eid]
                    autres = [i for i in m["fondations"].get(path, []) if i != eid]
                    champs_touches.append((ticker, path, eid, seul))
                    print(f"      FONDE   {path}  "
                          + ("← SEULE fondation : le champ bascule" if seul
                             else f"← co-fondé avec {autres}"))
            for nom, extrait in hits:
                print(f"      [{nom}] {extrait}")

    # ── Le champ témoin, relu en base émetteur par émetteur ────────────────────────────────────
    print(f"\n{'='*78}\n=== Le champ témoin `{CHAMP_TEMOIN}`, émetteur par émetteur ===")
    print(f"  profil : plancher={FIELD_PROFILES.get(CHAMP_TEMOIN, {}).get('plancher')} · "
          f"nature={FIELD_PROFILES.get(CHAMP_TEMOIN, {}).get('nature')} · "
          f"actualite_bloquante={FIELD_PROFILES.get(CHAMP_TEMOIN, {}).get('actualite_bloquante')}")
    for ticker in TICKERS:
        m = mesures[ticker]
        if CHAMP_TEMOIN in nonblocking_gaps_for(ticker):
            print(f"  {ticker:5} : DISPENSÉ (lacune déclarée non bloquante, en code)")
            continue
        if m["coverage"] is None:
            ids = m["fondations"].get(CHAMP_TEMOIN, [])
            print(f"  {ticker:5} : {'au plancher' if ids else 'rien au plancher'} — "
                  f"{ids or '—'}  (hors porte, aucun rapport persisté)")
            continue
        statut = _statut_champ(m["coverage"], CHAMP_TEMOIN)
        print(f"  {ticker:5} : {statut}  fondé par {m['fondations'].get(CHAMP_TEMOIN, []) or '—'}")

    # ── Les TROUS DÉCLARÉS, qui sont les appelants réels de la méthode d'approche ──────────────
    # Arbitrage utilisateur du 2026-09-09 : l'unité n'est pas le CRITÈRE, c'est la QUESTION posée.
    # Un trou qui vit à l'intérieur d'un critère fondé est un appelant de l'approximation au même
    # titre qu'un critère entièrement non fondé — et c'est là que la matière se trouvait.
    #
    # Ces trous ne sont pas une trouvaille : le prompt de synthèse les PRESCRIT (« si l'information
    # manque, écris-le explicitement "non documenté en base" plutôt que de l'inventer »). Ils sont
    # donc produits de façon régulière — mais en PROSE, dans le markdown, et pas dans le contrat.
    # C'est #55 : la règle est juste dans le producteur, son porteur est absent de la ligne, donc
    # aucun lecteur en aval (écran, porte, agent suivant) ne peut la voir.
    print(f"\n{'='*78}\n=== Les trous DÉCLARÉS par les pièces, question par question ===")
    total_trous = 0
    for ticker in TICKERS:
        m = mesures[ticker]
        fonde_par: dict[int, list[str]] = {}
        for path, ids in m["fondations"].items():
            for i in ids:
                fonde_par.setdefault(i, []).append(path)
        lignes_t = []
        for eid, e in sorted(m["entries"].items()):
            for ligne in (e.get("content") or "").splitlines():
                if not _RX_TROU.search(ligne):
                    continue
                texte = " ".join(ligne.strip().lstrip("-*# ").split())
                if len(texte) < 12:          # un titre de section n'est pas un trou
                    continue
                lignes_t.append((eid, sorted(fonde_par.get(eid, [])), texte[:190]))
        total_trous += len(lignes_t)
        print(f"\n  {ticker} — {len(lignes_t)} trou(s) déclaré(s) :")
        for eid, porte, texte in lignes_t:
            print(f"      #{eid} [{', '.join(porte) or 'ne fonde rien'}]")
            print(f"           {texte}")

    # ── Les critères CHIFFRÉS et ce qui les fonde ──────────────────────────────────────────────
    # Le filet lexical ne voit que les pièces qui DISENT l'absence. Il est aveugle à la pièce qui
    # répond à côté sans rien déclarer — #98 (prises de commandes, RPO) fonde `recurrence_pct` en
    # étant muette sur la récurrence. Cette section donne à LIRE, critère chiffré par critère
    # chiffré, ce que la porte compte comme fondation : le tri « porte le chiffre / répond à côté »
    # est un jugement, il n'est pas automatisé (on ne sait pas encore le rendre déterministe, et
    # une heuristique inventée ici fabriquerait sa propre ligne de base).
    chiffres = sorted(p for p, prof in FIELD_PROFILES.items() if prof.get("nature") == "mesure")
    print(f"\n{'='*78}\n=== Les {len(chiffres)} critères de nature `mesure`, et ce qui les fonde ===")
    for ticker in TICKERS:
        m = mesures[ticker]
        if m["coverage"] is None:
            print(f"\n  {ticker} — hors porte (aucun rapport persisté), non listé")
            continue
        print(f"\n  {ticker} :")
        for path in chiffres:
            statut = _statut_champ(m["coverage"], path)
            if statut != "couvert":
                continue
            for eid in m["fondations"].get(path, []):
                e = m["entries"].get(eid, {})
                cs = e.get("content_structured") or {}
                clefs = sorted(cs.keys())[:8] if isinstance(cs, dict) else []
                print(f"      {path:42} ← #{eid} {e.get('reliability_tier')} "
                      f"{(e.get('title') or '')[:60]}")
                print(f"      {'':42}   clefs structurées : {', '.join(clefs) or '—'}")

    # ── Le compte qui décide de l'ampleur ──────────────────────────────────────────────────────
    bascules = [c for c in champs_touches if c[3]]
    print(f"\n{'='*78}\n=== LIGNE DE BASE ===")
    print(f"  entries portant un marqueur d'absence      : {total_cand}")
    print(f"  … dont comptées comme FONDATION par la porte: {total_fondants}")
    print(f"  couples (émetteur, champ) fondés par l'une  : {len(champs_touches)}")
    print(f"  … dont l'absence est la SEULE fondation     : {len(bascules)}")
    for t, path, eid, _ in bascules:
        print(f"        {t:5} {path}  (#{eid})")
    print("\n  ⚠️ Ces comptes sont un FILET LEXICAL, pas un verdict : chaque extrait ci-dessus se")
    print("     lit avant d'être compté. Un marqueur mentionné en passant dans une entry qui")
    print("     livre quand même son chiffre est un faux positif, et il se voit à la lecture.")


async def main() -> int:
    url = os.environ.get("DATABASE_URL") or ""
    if not url:
        print("DATABASE_URL manquant — la ligne de base se MESURE sur le corpus réel.",
              file=sys.stderr)
        return 2
    await init_pool(url)
    try:
        async with get_db_session() as conn:
            mesures = {t: await mesurer(conn, t) for t in TICKERS}
    finally:
        await close_pool()
    main_rapport(mesures)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
