"""Check — l'EXPLORATEUR DU DOSSIER (lot B4f, roadmap V3 `16-lot-B4f-explorateur.md`), §6 « Gardes ».

Cas FICTIFS (aucun nom réel, deux tickers inventés) : un dossier à trois étages (notes → pièces →
documents d'origine, conceptuellement — deux étages ADRESSABLES en pratique : notes et pièces) avec
une note périmée, une pièce remplacée, une pièce longue. Sans réseau, sans modèle, sans base
(`charger_dossier_explorable`, la moitié IO, n'est PAS exercée ici — même frontière que
`check_architecte.py` pour `charger_matiere`).

  • §1 LES FIXTURES — deux dossiers fictifs (`FICTIF-A`, `FICTIF-B`), jamais un nom réel.
  • §2 `etat_piece` — en vigueur / remplacée (avec date) / numéro inconnu.
  • §3 `rendre_table_des_matieres` — étage notes/pieces/toutes, filtre sujet, PAGINATION (> 200
       pièces), étage inconnu refusé nommé, une pièce REMPLACÉE n'apparaît jamais à la table.
  • §4 `rendre_note` — question inconnue, note en vigueur avec ses pièces et leur état.
  • §5 `ouvrir_piece` (asyncio) — pièce courte (mode `whole`), pièce longue sans/avec `chercher`
       (repli lexical, sans réseau — pas de clé d'embeddings dans `env.checks`), pièce REMPLACÉE
       ouvrable et marquée `historique`, numéro inconnu.
  • §6 `rendre_resultats_recherche` — mapping titre/extrait/état, `limite` bornée, jamais reclassé
       (ORDRE d'entrée préservé — « mode tracé », aucune fusion de signaux, #22).
  • §7 `pieces_citables_effectif` — union matière ∪ pièces ouvertes (§3 de la spec).
  • §8 LES EXÉCUTEURS (`make_explorateur_tool_executors`, `make_rechercher_executor`) — le journal
       compte les appels et les pièces ouvertes ; PORTÉE (§6) : un exécuteur fermé sur le dossier A
       ne rend JAMAIS une pièce du dossier B (numéro inconnu) ; `rechercher` transmet le `ticker_id`
       FERMÉ, jamais un argument du modèle.

Cible : pydantic v2 (container). Tester en container, **pas** le python hôte.
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Bilan  # noqa: E402

from app.knowledge.explorateur import (  # noqa: E402
    DossierExplorable, JournalExploration, NoteDossier, PieceDossier,
    etat_piece, make_explorateur_tool_executors, make_rechercher_executor, ouvrir_piece,
    pieces_citables_effectif, rendre_note, rendre_resultats_recherche, rendre_table_des_matieres,
)

b = Bilan()

# ═══════════════════════════════════════════════════════════════════════════════════════════════
# §1 LES FIXTURES — deux dossiers FICTIFS, aucun nom réel
# ═══════════════════════════════════════════════════════════════════════════════════════════════
print("§1 les fixtures")

PIECE_LONGUE = (
    "Section Alpha. " + ("Du texte de remplissage sans intérêt. " * 150) +
    "Le programme Gamma-Zêta est en développement, phase deux, jalon suivant attendu en 2027. " +
    ("Encore du texte de remplissage sans intérêt. " * 150)
)
assert len(PIECE_LONGUE) > 6000, "la pièce longue doit dépasser le seuil de 6000 caractères"

PIECES_A = {
    1: PieceDossier(numero=1, titre="Rapport annuel fictif", contenu="Contenu court en vigueur.",
                     type_source="synthese", date_du_fait=date(2026, 1, 15)),
    2: PieceDossier(numero=2, titre="Ancienne note sectorielle", contenu="Contenu remplacé.",
                     type_source="synthese", date_du_fait=date(2025, 6, 1), superseded_by=3),
    3: PieceDossier(numero=3, titre="Note sectorielle à jour", contenu="Contenu courant.",
                     type_source="synthese", date_du_fait=date(2026, 9, 1)),
    4: PieceDossier(numero=4, titre="Dossier des programmes", contenu=PIECE_LONGUE,
                     type_source="synthese", date_du_fait=date(2026, 8, 1)),
}
NOTES_A = (
    NoteDossier(question_id="me_7", framework_id="modele_economique", statut="repondu",
                verdict="tient", actualite="courante", motif_actualite="à jour au 2026-09-01",
                verbatim="L'entreprise prépare le programme Gamma-Zêta.", pieces=frozenset({1, 3})),
    NoteDossier(question_id="qf_1", framework_id="qualite_financiere", statut="repondu",
                verdict="tient", actualite="perimee", motif_actualite="fait daté du 2025-06-01, "
                "antérieur à l'événement du 2026-02-10", verbatim="Verdict désormais périmé.",
                pieces=frozenset({2})),
)
DOSSIER_A = DossierExplorable(ticker_id="FICTIF-A", notes=NOTES_A, pieces=PIECES_A)

PIECES_B = {1: PieceDossier(numero=1, titre="Pièce du dossier B", contenu="Contenu B, pas A.")}
DOSSIER_B = DossierExplorable(ticker_id="FICTIF-B", notes=(), pieces=PIECES_B)

b.check(DOSSIER_A.ticker_id == "FICTIF-A" and DOSSIER_B.ticker_id == "FICTIF-B",
        "deux dossiers fictifs distincts construits")

# ═══════════════════════════════════════════════════════════════════════════════════════════════
# §2 `etat_piece`
# ═══════════════════════════════════════════════════════════════════════════════════════════════
print("§2 etat_piece")

b.check(etat_piece(1, DOSSIER_A) == "en vigueur", "pièce #1 — en vigueur")
e2 = etat_piece(2, DOSSIER_A)
b.check(e2 == "remplacé par #3 (2026-09-01)",
        f"pièce #2 — remplacée par #3, datée de sa remplaçante : {e2!r}")
b.check(etat_piece(999, DOSSIER_A) == "numéro inconnu", "numéro inconnu")

# ═══════════════════════════════════════════════════════════════════════════════════════════════
# §3 `rendre_table_des_matieres`
# ═══════════════════════════════════════════════════════════════════════════════════════════════
print("§3 table des matières")

tdm_toutes = rendre_table_des_matieres(DOSSIER_A)
types_rendus = {l["type"] for l in tdm_toutes["lignes"]}
b.check(types_rendus == {"note", "piece"}, f"étage par défaut = notes + pièces : {types_rendus}")
numeros_rendus = {l["numero"] for l in tdm_toutes["lignes"] if l["type"] == "piece"}
b.check(2 not in numeros_rendus,
        f"une pièce REMPLACÉE (#2) n'apparaît jamais à la table des matières : {numeros_rendus}")
b.check({1, 3, 4} <= numeros_rendus, f"les pièces en vigueur y figurent : {numeros_rendus}")

tdm_notes = rendre_table_des_matieres(DOSSIER_A, etage="notes")
b.check(all(l["type"] == "note" for l in tdm_notes["lignes"]) and len(tdm_notes["lignes"]) == 2,
        f"étage=notes — seules les notes, 2 attendues : {tdm_notes['lignes']}")

tdm_sujet = rendre_table_des_matieres(DOSSIER_A, etage="pieces", sujet="sectorielle")
b.check([l["numero"] for l in tdm_sujet["lignes"]] == [3],
        f"filtre sujet — seule la pièce #3 porte « sectorielle » EN VIGUEUR : {tdm_sujet['lignes']}")

tdm_ko = rendre_table_des_matieres(DOSSIER_A, etage="inconnu")
b.check("erreur" in tdm_ko, f"étage inconnu refusé nommé : {tdm_ko}")

# Pagination (> 200 pièces, spec §2 : 200 lignes par appel).
pieces_250 = {i: PieceDossier(numero=i, titre=f"Pièce fictive {i}", contenu="x") for i in range(1, 251)}
dossier_250 = DossierExplorable(ticker_id="FICTIF-PAGINATION", notes=(), pieces=pieces_250)
page1 = rendre_table_des_matieres(dossier_250, etage="pieces", page=1)
b.check(len(page1["lignes"]) == 200, f"page 1 — au plus 200 lignes : {len(page1['lignes'])}")
b.check(page1["total"] == 250 and page1["pages_totales"] == 2,
        f"total=250, 2 pages attendues : {page1['total']}/{page1['pages_totales']}")
page2 = rendre_table_des_matieres(dossier_250, etage="pieces", page=2)
b.check(len(page2["lignes"]) == 50, f"page 2 — le reste (50) : {len(page2['lignes'])}")

# ═══════════════════════════════════════════════════════════════════════════════════════════════
# §4 `rendre_note`
# ═══════════════════════════════════════════════════════════════════════════════════════════════
print("§4 ouvrir une note")

note_ko = rendre_note(DOSSIER_A, "question_inexistante")
b.check("erreur" in note_ko, f"question inconnue refusée nommée : {note_ko}")

note_me7 = rendre_note(DOSSIER_A, "me_7")
b.check(note_me7.get("actualite") == "courante", f"me_7 — actualité : {note_me7}")
b.check({p["numero"] for p in note_me7["pieces"]} == {1, 3},
        f"me_7 — ses pièces (#1, #3) : {note_me7['pieces']}")
b.check(all(p["etat"] == "en vigueur" for p in note_me7["pieces"]),
        f"les deux pièces de me_7 sont en vigueur : {note_me7['pieces']}")

note_qf1 = rendre_note(DOSSIER_A, "qf_1")
b.check(note_qf1.get("actualite") == "perimee" and "antérieur" in (note_qf1.get("motif_actualite") or ""),
        f"qf_1 — périmée, motif daté : {note_qf1.get('motif_actualite')}")
etat_piece_2_dans_note = next(p["etat"] for p in note_qf1["pieces"] if p["numero"] == 2)
b.check(etat_piece_2_dans_note.startswith("remplacé par #3"),
        f"la pièce #2 citée par qf_1 est montrée REMPLACÉE : {etat_piece_2_dans_note}")

# ═══════════════════════════════════════════════════════════════════════════════════════════════
# §5 `ouvrir_piece`
# ═══════════════════════════════════════════════════════════════════════════════════════════════
print("§5 ouvrir une pièce")


async def _ouvrir(dossier, numero, chercher=None):
    return await ouvrir_piece(dossier, numero, chercher=chercher)


out_courte, texte_courte = asyncio.run(_ouvrir(DOSSIER_A, 1))
b.check(out_courte["mode"] == "whole" and out_courte["etat"] == "en vigueur" and not out_courte["historique"],
        f"pièce courte — mode `whole`, en vigueur, pas historique : {out_courte}")
b.check(texte_courte == "Contenu court en vigueur.", "le texte rendu est bien le contenu complet")

out_longue, texte_longue = asyncio.run(_ouvrir(DOSSIER_A, 4))
b.check(out_longue["mode"] in ("lexical", "head"),
        f"pièce longue SANS `chercher`, sans clé d'embeddings — repli déclaré : {out_longue['mode']}")
b.check(len(out_longue["texte"]) <= 6000 + 200,
        f"pièce longue — rendu borné (marqueurs de coupure compris) : {len(out_longue['texte'])}")

out_focus, texte_focus = asyncio.run(_ouvrir(DOSSIER_A, 4, chercher="programme Gamma-Zêta"))
b.check("Gamma-Zêta" in out_focus["texte"],
        f"pièce longue AVEC `chercher` — le passage demandé est bien rendu : "
        f"{'Gamma-Zêta' in out_focus['texte']}")

out_histo, texte_histo = asyncio.run(_ouvrir(DOSSIER_A, 2))
b.check(out_histo["historique"] is True and out_histo.get("remplacee_par") == 3,
        f"pièce REMPLACÉE — ouvrable, marquée historique, remplaçante nommée : {out_histo}")
b.check(out_histo["etat"].startswith("remplacé par #3"), f"état cohérent : {out_histo['etat']}")

out_ko, texte_ko = asyncio.run(_ouvrir(DOSSIER_A, 999))
b.check("erreur" in out_ko and texte_ko is None, f"numéro inconnu refusé nommé : {out_ko}")

# ═══════════════════════════════════════════════════════════════════════════════════════════════
# §6 `rendre_resultats_recherche` — jamais de fusion/reclassement (#22)
# ═══════════════════════════════════════════════════════════════════════════════════════════════
print("§6 rendre_resultats_recherche")

ROWS_FICTIFS = [
    {"id": 30, "title": "Zêta — troisième résultat (titre)", "content": "x" * 400},
    {"id": 10, "title": "Alpha — premier résultat (titre)", "content": "y" * 10},
    {"id": 20, "title": "Mu — deuxième résultat (titre)", "content": "z" * 50},
]
res = rendre_resultats_recherche(ROWS_FICTIFS, limite=10)
b.check([r["numero"] for r in res["resultats"]] == [30, 10, 20],
        f"ORDRE d'entrée préservé — aucune fusion/reclassement par ce module (#22) : "
        f"{[r['numero'] for r in res['resultats']]}")
b.check(all(r["etat"] == "en vigueur" for r in res["resultats"]),
        "query_knowledge ne rend que des entrées courantes : état toujours « en vigueur »")
b.check(len(res["resultats"][0]["extrait"]) == 300, "extrait borné à 300 caractères")

res_bornee = rendre_resultats_recherche(ROWS_FICTIFS, limite=999)
b.check(len(res_bornee["resultats"]) <= 10, f"`limite` plafonnée à 10 même si demandé plus haut")

# ═══════════════════════════════════════════════════════════════════════════════════════════════
# §7 `pieces_citables_effectif` — matière ∪ pièces ouvertes (spec §3)
# ═══════════════════════════════════════════════════════════════════════════════════════════════
print("§7 pieces_citables_effectif")

journal_test = JournalExploration()
journal_test.record_piece(4, "texte de la pièce 4")
journal_test.record_piece(7, "texte d'une pièce rendue par `rechercher`, jamais citée par la matière")
union = pieces_citables_effectif(frozenset({1, 3}), journal_test)
b.check(union == frozenset({1, 3, 4, 7}),
        f"union matière ∪ pièces ouvertes, jamais un remplacement : {sorted(union)}")

# ═══════════════════════════════════════════════════════════════════════════════════════════════
# §8 LES EXÉCUTEURS — journal, et PORTÉE (§6 : un exécuteur ne rend jamais une pièce d'un autre titre)
# ═══════════════════════════════════════════════════════════════════════════════════════════════
print("§8 les exécuteurs — journal et portée")


class _FauxConn:
    async def __aenter__(self):
        return None

    async def __aexit__(self, *exc):
        return False


def _faux_conn_factory():
    return _FauxConn()


_APPELS_QUERY_KNOWLEDGE: list[dict] = []


async def _faux_query_knowledge(conn, *, ticker_id, query, limit):
    _APPELS_QUERY_KNOWLEDGE.append({"ticker_id": ticker_id, "query": query, "limit": limit})
    return [{"id": 50, "title": "Résultat fictif de `rechercher`", "content": "contenu trouvé " * 50}]


async def _exercer_executeurs():
    journal = JournalExploration()
    executeurs = make_explorateur_tool_executors(
        DOSSIER_A, journal, conn_factory=_faux_conn_factory, ticker_id="FICTIF-A")

    r_table = await executeurs["table_des_matieres"]({})
    r_note = await executeurs["ouvrir_note"]({"question_id": "me_7"})
    r_piece = await executeurs["ouvrir_piece"]({"numero": 1})
    r_piece_scope = await executeurs["ouvrir_piece"]({"numero": 1})  # FICTIF-B porte aussi un #1
    return journal, r_table, r_note, r_piece, r_piece_scope


import app.knowledge.service as _service_mod  # noqa: E402

_original_query_knowledge = _service_mod.query_knowledge
_service_mod.query_knowledge = _faux_query_knowledge
try:
    journal_exec, r_table, r_note, r_piece, r_piece_scope = asyncio.run(_exercer_executeurs())

    b.check(journal_exec.appels.get("table_des_matieres") == 1, "le journal compte l'appel à `table_des_matieres`")
    b.check(journal_exec.appels.get("ouvrir_note") == 1, "le journal compte l'appel à `ouvrir_note`")
    b.check("erreur" not in r_table and "erreur" not in r_note, "table/note : pas d'erreur")
    b.check(r_piece["etat"] == "en vigueur", "ouvrir_piece — pièce #1 du dossier A, en vigueur")
    b.check(1 in journal_exec.pieces_ouvertes, "le journal garde le texte de la pièce ouverte")

    # PORTÉE : l'exécuteur de A ne peut PAS rendre la pièce #1 du dossier B — son contenu diffère.
    b.check(r_piece_scope["texte"] == "Contenu court en vigueur.",
            f"portée — l'exécuteur fermé sur A rend le CONTENU de A, jamais celui de B : "
            f"{r_piece_scope['texte']!r}")
    b.check(r_piece_scope["texte"] != "Contenu B, pas A.",
            "portée — confirmé négativement : le contenu de B n'apparaît jamais via l'exécuteur de A")

    # `rechercher` — via l'exécuteur ET via `make_rechercher_executor` directement (deux_temps) :
    # le `ticker_id` transmis à `query_knowledge` est FERMÉ, jamais un argument du modèle.
    _APPELS_QUERY_KNOWLEDGE.clear()
    journal_rech = JournalExploration()
    executeur_rechercher = make_rechercher_executor(
        journal_rech, conn_factory=_faux_conn_factory, ticker_id="FICTIF-A")
    resultat_rech = asyncio.run(executeur_rechercher({"sujet": "concurrence du marché visé"}))
    b.check(len(_APPELS_QUERY_KNOWLEDGE) == 1 and _APPELS_QUERY_KNOWLEDGE[0]["ticker_id"] == "FICTIF-A",
            f"rechercher — `ticker_id` FERMÉ transmis à `query_knowledge`, jamais un argument du "
            f"modèle (portée élargie si FAUX) : {_APPELS_QUERY_KNOWLEDGE}")
    b.check(50 in journal_rech.pieces_ouvertes,
            f"rechercher — le journal garde le texte COMPLET de la ligne (pas l'extrait tronqué) : "
            f"{journal_rech.pieces_ouvertes.get(50, '')[:30]!r}")
    b.check("resultats" in resultat_rech and resultat_rech["resultats"][0]["numero"] == 50,
            f"rechercher — résultat mappé : {resultat_rech}")
finally:
    _service_mod.query_knowledge = _original_query_knowledge

sys.exit(b.summary())
