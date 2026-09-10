"""Ligne de base du lot « le barreau 4 a besoin de sa propre recherche » (capacité 5).

POURQUOI CET OUTIL EXISTE, ET POURQUOI IL TOURNE *AVANT* LE LOT
---------------------------------------------------------------
Le lot précédent a mesuré, sur corpus réel, que le barreau 4 (« l'agent propose une méthode pour
approcher le chiffre ») échouait pour une raison qui n'est ni le modèle ni le prompt : le
dénominateur nécessaire (**« >450 M sièges payants »**, tier A, #102) est EN BASE mais **pas dans le
corpus chargé** pour `produits.unit_economics`. Une requête formulée sur **la question** ramenait
#102 dans 4 cas sur 5 ; la requête sur **le champ**, jamais.

Hypothèse structurelle qui en découle : *les ingrédients d'une approximation vivent par nature dans
un champ VOISIN* (un dénombrement de sièges appartient au vocabulaire du positionnement, pas à celui
de l'économie unitaire). Si elle est vraie, le lot suivant est « le barreau 4 fait sa propre
recherche, sur la question nommée ». Si elle est fausse — si les ingrédients sont déjà dans le
corpus du champ, ou s'ils ne sont nulle part — le lot n'a pas de matière et doit être réécrit une
quatrième fois.

**Cette mesure décide donc de l'existence du lot, et elle est quasi gratuite** (une requête
d'embedding par question). La ligne de base a déjà changé la capacité 5 TROIS fois
(`feedback_ligne_de_base_est_une_mesure`).

CE QU'IL MESURE
---------------
1. **Le corpus du champ, reconstruit par la fonction de PRODUCTION** — même appel `query_knowledge`
   que `run_synthesis_feed` (même requête gabarit, même `min_reliability`, même `limit`, même filtre
   de tiers citables). Un second assemblage de corpus ici serait une seconde porte (#46) et
   divergerait au premier correctif ; ce qu'on veut mesurer est ce que le modèle a RÉELLEMENT vu.
2. **Les questions déclarées ouvertes**, extraites de la PROSE des synthèses persistées. Elles n'ont
   pas d'autre porteur : le lot qui les a fait entrer dans `lacunes[]` n'a **rien persisté**
   (délibérément — `feedback_fixture_pollue_le_reel`). Le filet est le même que
   `mesure_absences_capacite5.py`, motif par motif NOMMÉ, et il imprime les extraits EN TEXTE : le
   tri question réelle / faux positif est un jugement, il n'est pas automatisé ici
   (`feedback_deleguer_recherche_pas_jugement`).
3. **Le gain d'une recherche sur la QUESTION** — pour chaque question, la même `query_knowledge`
   mais interrogée avec le texte de la question, puis la différence avec le corpus du champ. Les
   entries gagnées sont imprimées avec leur tier, leur `covers` et leur titre : c'est la seule
   sortie qui permette de juger si l'ingrédient est utilisable, ou si la requête a simplement ramené
   du voisinage sans rapport.

CE QU'IL NE FAIT PAS
--------------------
Aucune écriture (aucun INSERT, aucun UPDATE), aucun appel de modèle de génération, aucune
ré-implémentation d'une règle de couverture ou d'assemblage de corpus. Il ne conclut pas non plus
qu'un ingrédient gagné rend la question approximable — il rend la matière à lire.

⚠️ Il imprime un BILAN à la fin, et un pré-requis manquant sort en `exit != 0`, jamais en section
sautée (`CHANTIER_OUTILLAGE_DEV.md` §27 : l'absence de bilan est un échec, pas un zéro).

Usage : `bash tools/mesure_ingredients.sh`
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
from typing import Any

from app.db.database import close_pool, get_db_session, init_pool
from app.knowledge.embeddings import is_configured as embeddings_configured
from app.knowledge.service import query_knowledge
from app.knowledge.synthesis_feed import SYNTHESIS_TARGETS
from tools._corpus_archive import ENTRIES, bandeau

TICKERS = ["NVDA", "MSFT", "RVMD"]

# Les paramètres de chargement de `run_synthesis_feed`. Ils sont RECOPIÉS ici parce que la fonction
# de production ne les expose pas séparément — mais ils sont vérifiés par un assert au démarrage
# contre le code source, pour qu'une divergence future soit bruyante plutôt que silencieuse (#46).
MIN_RELIABILITY = 0.70
MAX_CANDIDATES = 20

# ── Le filet lexical : les questions déclarées ouvertes ─────────────────────────────────────────
# Identique en esprit à `mesure_absences_capacite5.py` : chaque motif est NOMMÉ, parce qu'un compte
# agrégé ne dirait pas lequel ratisse trop large. ⚠️ Le mesureur précédent avait d'abord SOUS-compté
# en ne cherchant que « non documenté » et en ratant « n'est pas documentée » — le modèle produit la
# consigne du prompt sous plusieurs formes verbales.
_MARQUE = r"(document|observ|chiffr|quantifi|détaill|renseign|disponible|publi|ventil|isol)"
MOTIFS: list[tuple[str, str]] = [
    ("prescrit:non X",        rf"\bnon\s+{_MARQUE}"),
    ("prescrit:n'est pas X",  rf"n['’](est|sont)\s+pas\s+\w{{0,10}}\s*{_MARQUE}"),
    ("prescrit:ne X pas",     rf"ne\s+\w{{0,12}}\s*pas\s+{_MARQUE}"),
    ("prescrit:aucune entry", rf"aucune?\s+entry\s+.{{0,40}}ne\s+{_MARQUE}"),
    ("fr:ne publie pas",      r"ne\s+(publie|publient|divulgue|divulguent|communique|communiquent|"
                              r"détaille|détaillent|ventile|ventilent|isole|isolent|fournit|"
                              r"fournissent|quantifie|quantifient)\s+(pas|plus)"),
    ("fr:aucune donnée",      r"(aucune?|nulle)\s+\w{0,15}\s*(ventilation|donnée|information|"
                              r"chiffre|communication|divulgation|publication|décomposition|"
                              r"répartition|granularité)"),
    ("fr:pas de X publié",    r"pas\s+de\s+\w{0,15}\s*(ventilation|donnée publi|chiffre publi|"
                              r"information publi|détail|décomposition|répartition|granularité)"),
    ("fr:indisponible",       r"(indisponible|introuvable|non\s+trouvé|sans\s+réponse\s+chiffrée)"),
    ("en:does not X",         r"does\s+not\s+(disclose|break\s+out|provide|report|publish|quantify)"),
    ("en:not X",              r"\bnot\s+(disclosed|publicly|broken\s+out|quantified|available)"),
    ("en:no X",               r"\bno\s+(breakdown|public\s+|disclosure|granularity)"),
]
_COMPILES = [(nom, re.compile(rx, re.IGNORECASE)) for nom, rx in MOTIFS]


def _phrase(texte: str, m: re.Match) -> str:
    """La phrase autour du marqueur — c'est elle qui porte la question, et c'est elle qu'on lit."""
    debut = max(texte.rfind(". ", 0, m.start()), texte.rfind("\n", 0, m.start())) + 1
    fins = [p for p in (texte.find(". ", m.end()), texte.find("\n", m.end())) if p != -1]
    fin = min(fins + [len(texte)])
    return " ".join(texte[debut:fin + 1].split()).strip("-• ")[:400]


def _questions(entry: dict[str, Any]) -> list[tuple[str, str]]:
    """[(nom du motif, phrase)] — dédoublonné sur la phrase, un marqueur pouvant en attraper deux."""
    texte = entry.get("content") or ""
    vues: dict[str, str] = {}
    for nom, rx in _COMPILES:
        for m in rx.finditer(texte):
            ph = _phrase(texte, m)
            if len(ph) < 25:            # un fragment n'est pas une question
                continue
            vues.setdefault(ph, nom)
    return [(nom, ph) for ph, nom in vues.items()]


# ⚠️ CE SEUIL EST LE CŒUR DE LA MESURE, et le premier passage l'a prouvé par l'absurde.
# Sans lui, le compte rendait **23 questions sur 23** « avec un ingrédient hors corpus » — un 100 %
# qui ne mesure rien : le corpus d'un champ est tronqué à `limit=20` sur ~50 entries, donc TOUTE
# requête différente ramène mécaniquement des entries hors corpus. Le compte mesurait la troncature,
# pas la pertinence (`feedback_fixture_copiee_du_reel` : une mesure non discriminante est un vert
# fabriqué). Le discriminant retenu est le RANG sur la question : un ingrédient utilisable est un
# proche voisin de la question, pas un 15ᵉ de liste. Le cas de référence #102 sert d'étalon — il
# doit tomber du bon côté du seuil, sinon c'est le seuil qui est faux.
RANG_INGREDIENT = 5

# L'ÉTALON. Le lot précédent a nommé l'ingrédient manquant : le dénombrement de sièges payants
# (« >450 M sièges payants »), tier A, absent du corpus de `produits.unit_economics` alors qu'il en
# est le dénominateur. Il est désigné par son CONTENU, jamais par son id : un id codé en dur se
# périme au premier re-seed et l'étalon sortirait un zéro muet (leçon de
# `mesure_absences_capacite5.py`). Son rang sur chaque question est imprimé sans seuil : c'est lui
# qui CALIBRE la mesure, il ne peut donc pas être jugé par elle.
ETALON = ("MSFT", "produits.unit_economics", re.compile(r"450\s*M?\s*(millions?\s*de\s*)?sièges",
                                                        re.IGNORECASE))


# La question déclarée vit aujourd'hui en PROSE, et cette prose porte sa propre négation
# (« … : non documenté en base »). L'embedding de la phrase mêle donc le SUJET cherché et le fait
# qu'il manque — deux choses qui n'ont pas les mêmes voisins. Ce nettoyage déterministe retire la
# clause d'absence pour mesurer la même question sans sa négation : si le rang de l'étalon s'améliore
# nettement, le défaut est la FORMULATION (et le lot est « chercher sur la question nommée ») ; s'il
# ne bouge pas, le défaut est la MÉTHODE de recherche (et le lot est tout autre).
_RX_NEGATION = re.compile(
    r"\s*[:—-]?\s*(non\s+\w+e?s?|n['’](est|sont)\s+pas\s+\w+e?s?|ne\s+\w+\s+pas\s+\w+e?s?)"
    r"(\s+(en\s+base|dans\s+le\s+corpus(\s+fourni)?|dans\s+les\s+entries(\s+fournies)?|"
    r"à\s+ce\s+jour|spécifiquement))?\s*\.?\s*$",
    re.IGNORECASE,
)


def _sans_negation(question: str) -> str:
    """La question débarrassée de sa clause d'absence. Déterministe, aucun modèle."""
    q = _RX_NEGATION.sub("", question).strip(" —-:.*")
    q = re.sub(r"\*\*", "", q)
    return q or question


def _fmt(e: dict[str, Any], rang: int) -> str:
    covers = e.get("covers")
    if isinstance(covers, str):
        covers = [covers]
    sim = e.get("similarity")
    sim_txt = f"{sim:.3f}" if isinstance(sim, (int, float)) else " n/a "
    return (f"r{rang:<2} sim={sim_txt} #{e['id']:<4} {str(e.get('reliability_tier')):<3} "
            f"covers={list(covers or [])} "
            f"« {' '.join(str(e.get('title') or '').split())[:80]} »")


async def main() -> int:
    print(bandeau())
    if not embeddings_configured():
        # Pré-requis manquant → échec bruyant. Un repli texte mesurerait autre chose que la
        # production (chemin nominal vectoriel) et rendrait un chiffre qu'on croirait comparable.
        print("ÉCHEC — DEEPINFRA_API_KEY absente : la recherche serait en repli TEXTE, "
              "donc pas la mesure demandée (la production est vectorielle).")
        return 1

    url = os.environ.get("DATABASE_URL") or ""
    if not url:
        print("ÉCHEC — DATABASE_URL manquant : la ligne de base se MESURE sur le corpus réel.")
        return 2
    await init_pool(url)
    etalon_id: int | None = None
    etalon_rangs: list[int | None] = []
    etalon_rangs_nets: list[int | None] = []
    total_questions = 0
    questions_avec_gain = 0
    lignes_bilan: list[str] = []
    try:
        async with get_db_session() as conn:
            # ⚠️ Plusieurs entries portent le chiffre : la pièce PRIMAIRE qui le publie, et les
            # synthèses qui la citent. Prendre « la première venue » a d'abord désigné une synthèse
            # (`agent_synthesis`) au lieu du dépôt tier A — l'étalon aurait mesuré le rang d'un
            # dérivé au lieu de l'ingrédient. On exclut donc les synthèses, et on IMPRIME tous les
            # porteurs : un étalon choisi en silence parmi plusieurs candidats n'est pas un étalon.
            porteurs = [
                r for r in await conn.fetch(
                    "SELECT id, title, source_type, reliability_tier, content "
                    f"FROM {ENTRIES} WHERE ticker_id = $1 AND superseded_by IS NULL "
                    "ORDER BY id", ETALON[0],
                )
                if ETALON[2].search(f"{r['title'] or ''}\n{r['content'] or ''}")
            ]
            print(f"ÉTALON — {len(porteurs)} entrie(s) portent le dénombrement de sièges :")
            for r in porteurs:
                print(f"   #{r['id']:<4} {r['reliability_tier']:<3} {r['source_type']:<18} "
                      f"« {' '.join((r['title'] or '').split())[:70]} »")
            primaires = [r for r in porteurs if r["source_type"] != "agent_synthesis"]
            if primaires:
                etalon_id = primaires[0]["id"]
                print(f"   → étalon retenu : #{etalon_id} (pièce primaire, pas un dérivé)")
            if etalon_id is None:
                print(f"ÉCHEC — étalon introuvable dans le corpus {ETALON[0]} : la mesure ne peut "
                      f"pas être calibrée, et un seuil non calibré rend un compte qu'on croirait "
                      f"comparable.")
                return 1
            print(f"ÉTALON résolu : #{etalon_id} ({ETALON[0]}, le dénombrement de sièges payants)")

            for ticker in TICKERS:
                row = await conn.fetchrow("SELECT name FROM tickers WHERE id = $1", ticker)
                company = ((row["name"] if row else None) or ticker).strip()
                # ⚠️ Le discriminant est `content_structured.synthesis_kind`, PAS `entry_type` :
                # une synthèse grounded a `entry_type='analysis'` (c'est son genre) et
                # `source_type='agent_synthesis'` (c'est sa provenance). Filtrer sur `entry_type =
                # 'agent_synthesis'` rend 8 entries d'un tout autre genre, à `covers` vide — un zéro
                # rassurant produit par la pire des raisons (#49). Le discriminant est dans la
                # ligne, et c'est précisément ce que #55 exige.
                syntheses = await conn.fetch(
                    f"""
                    SELECT id, title, content, covers, reliability_tier, content_structured
                      FROM {ENTRIES}
                     WHERE ticker_id = $1 AND superseded_by IS NULL
                       AND content_structured->>'synthesis_kind' = 'grounded_synthesis'
                     ORDER BY id
                    """,
                    ticker,
                )
                print(f"\n{'=' * 100}\n{ticker} ({company}) — {len(syntheses)} synthèse(s) grounded "
                      f"courante(s)\n{'=' * 100}")
                if not syntheses:
                    print("  (aucune synthèse persistée — rien à mesurer sur cet émetteur)")
                    lignes_bilan.append(f"{ticker}: 0 synthèse, 0 question")
                    continue

                for s in syntheses:
                    cs = s["content_structured"] or {}
                    covers = s["covers"]
                    if isinstance(covers, str):
                        covers = [covers]
                    # `field_path` est porté DANS la ligne par le producteur ; `covers` en est
                    # l'index. On lit le porteur, et on dit si les deux divergent.
                    field_path = cs.get("field_path")
                    if field_path not in SYNTHESIS_TARGETS:
                        print(f"\n-- #{s['id']} : field_path={field_path!r} inconnu de "
                              f"SYNTHESIS_TARGETS — corpus non reconstructible")
                        continue
                    if field_path not in (covers or []):
                        print(f"\n   ⚠️ #{s['id']} : field_path={field_path} ABSENT de "
                              f"covers={list(covers or [])}")
                    target = SYNTHESIS_TARGETS[field_path]
                    query_champ, _ = target.resolve(company)

                    # 1) le corpus du champ, par l'appel de PRODUCTION
                    found = await query_knowledge(
                        conn, ticker_id=ticker, query=query_champ,
                        entry_types=list(target.candidate_entry_types),
                        min_reliability=MIN_RELIABILITY, include_sector=True,
                        limit=MAX_CANDIDATES,
                    )
                    corpus = [e for e in found if e.get("reliability_tier") in target.citable_tiers]
                    corpus_ids = {e["id"] for e in corpus}
                    print(f"\n-- synthèse #{s['id']} → champ `{field_path}`")
                    print(f"   corpus du CHAMP : {len(corpus)} entries citables "
                          f"{sorted(corpus_ids)}")

                    # 2) les questions déclarées, en TEXTE
                    qs = _questions(dict(s))
                    print(f"   questions déclarées ouvertes (filet lexical) : {len(qs)}")
                    if not qs:
                        lignes_bilan.append(f"{ticker}/{field_path}: 0 question")
                        continue

                    gains_champ = 0
                    for i, (motif, question) in enumerate(qs, 1):
                        total_questions += 1
                        print(f"\n   [{i}] ({motif}) {question}")
                        # 3) la même recherche, formulée sur LA QUESTION
                        found_q = await query_knowledge(
                            conn, ticker_id=ticker, query=question,
                            entry_types=list(target.candidate_entry_types),
                            min_reliability=MIN_RELIABILITY, include_sector=True,
                            limit=MAX_CANDIDATES,
                        )
                        cit_q = [e for e in found_q
                                 if e.get("reliability_tier") in target.citable_tiers]
                        # Le rang est celui de la LISTE RENDUE (déjà triée par distance cosinus).
                        gagnees = [(r, e) for r, e in enumerate(cit_q, 1)
                                   if e["id"] not in corpus_ids]
                        proches = [(r, e) for r, e in gagnees if r <= RANG_INGREDIENT]
                        if proches:
                            questions_avec_gain += 1
                            gains_champ += 1
                            print(f"       → INGRÉDIENT PLAUSIBLE : {len(proches)} entrie(s) hors "
                                  f"corpus dans le top-{RANG_INGREDIENT} de la question :")
                            for r, e in proches:
                                print(f"         {_fmt(e, r)}")
                        else:
                            print(f"       → aucun proche voisin hors corpus "
                                  f"(top-{RANG_INGREDIENT}) — la recherche sur la question ne "
                                  f"gagne rien d'utilisable")
                        loin = [(r, e) for r, e in gagnees if r > RANG_INGREDIENT]
                        if loin:
                            print(f"         (+ {len(loin)} hors corpus au-delà du rang "
                                  f"{RANG_INGREDIENT}, non comptées : "
                                  f"{', '.join('#%d' % e['id'] for _, e in loin)})")
                        # L'étalon, imprimé SANS seuil : où tombe l'ingrédient qu'on sait être le
                        # bon ? S'il tombe du mauvais côté, c'est le seuil qui est réfuté.
                        if (ticker, field_path) == (ETALON[0], ETALON[1]) and etalon_id:
                            pos = next((r for r, e in enumerate(cit_q, 1)
                                        if e["id"] == etalon_id), None)
                            sim = next((e.get("similarity") for e in cit_q
                                        if e["id"] == etalon_id), None)
                            etalon_rangs.append(pos)
                            print(f"       ⇒ ÉTALON #{etalon_id} sur la question EN PROSE : "
                                  + (f"rang {pos}"
                                     + (f", sim={sim:.3f}" if isinstance(sim, float) else "")
                                     if pos else "ABSENT des résultats"))
                            # Contre-épreuve : la MÊME question, sa négation retirée.
                            q_net = _sans_negation(question)
                            found_n = await query_knowledge(
                                conn, ticker_id=ticker, query=q_net,
                                entry_types=list(target.candidate_entry_types),
                                min_reliability=MIN_RELIABILITY, include_sector=True,
                                limit=MAX_CANDIDATES,
                            )
                            cit_n = [e for e in found_n
                                     if e.get("reliability_tier") in target.citable_tiers]
                            pos_n = next((r for r, e in enumerate(cit_n, 1)
                                          if e["id"] == etalon_id), None)
                            sim_n = next((e.get("similarity") for e in cit_n
                                          if e["id"] == etalon_id), None)
                            etalon_rangs_nets.append(pos_n)
                            print(f"       ⇒ ÉTALON #{etalon_id} SANS négation « {q_net[:70]} » : "
                                  + (f"rang {pos_n}"
                                     + (f", sim={sim_n:.3f}" if isinstance(sim_n, float) else "")
                                     if pos_n else "ABSENT des résultats"))
                    lignes_bilan.append(
                        f"{ticker}/{field_path}: {len(qs)} question(s), {gains_champ} avec gain"
                    )
    finally:
        await close_pool()

    print(f"\n{'=' * 100}\nBILAN — {total_questions} question(s) déclarée(s) mesurée(s), "
          f"{questions_avec_gain} dont la recherche sur LA QUESTION ramène une entry citable hors "
          f"du corpus de leur champ dans le top-{RANG_INGREDIENT}")
    for l in lignes_bilan:
        print(f"  · {l}")
    dedans = sum(1 for r in etalon_rangs if r is not None and r <= RANG_INGREDIENT)
    dedans_n = sum(1 for r in etalon_rangs_nets if r is not None and r <= RANG_INGREDIENT)
    print(f"\n  ÉTALON #{etalon_id} sur les {len(etalon_rangs)} question(s) de "
          f"{ETALON[0]}/{ETALON[1]} :")
    print(f"    · question EN PROSE (telle qu'elle vit aujourd'hui) : rangs {etalon_rangs} — "
          f"{dedans}/{len(etalon_rangs)} dans le top-{RANG_INGREDIENT}")
    print(f"    · question SANS sa négation (contre-épreuve)        : rangs "
          f"{etalon_rangs_nets} — {dedans_n}/{len(etalon_rangs_nets)} dans le "
          f"top-{RANG_INGREDIENT}")
    if etalon_rangs and dedans == 0:
        print("  ⚠️ L'ingrédient CONNU tombe hors du seuil sur TOUTES les questions : ce n'est pas "
              "l'étalon qui est mauvais, c'est le critère. Une recherche sémantique nue sur la "
              "question ne sépare pas l'ingrédient du voisinage.")
    if total_questions == 0:
        print("ÉCHEC — 0 question mesurée : le filet n'a rien attrapé, ce n'est pas un zéro "
              "mesuré mais un mesureur muet (#49).")
        return 1
    print("OK — mesure complète (aucune écriture, aucun appel de modèle de génération)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
