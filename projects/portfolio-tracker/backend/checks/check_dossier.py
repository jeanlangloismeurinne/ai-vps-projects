"""Vérifie l'ASSEMBLAGE du dossier remis à l'analyste (`app/agents/v2/dossier.py`).

Hors-ligne : aucune base, aucun réseau, aucun modèle. La fixture est COPIÉE du corpus RVMD réel
mesuré le 2026-09-22 (ids, dates de source et dates de collecte authentiques) — une fixture plus
favorable que la prod est un check aveugle au vert, et elle neutralise aussi le test négatif
(`feedback_fixture_copiee_du_reel`). On y garde donc les trois travers réels : trois versions du
même point, une pièce partagée par deux points, et une datation hétérogène.

CE QUI SE JOUE ICI, ET QU'AUCUN AUTRE CHECK NE VOIT
----------------------------------------------------
§3 garde l'invariant d'ORDRE. Il n'est pas décoratif : à la première écriture, `_rang` triait en
ordre croissant et élisait donc la pièce la plus ANCIENNE « en vigueur ». Le dossier sortait bien
formé, de la bonne taille, une pièce par point — aucun décompte ne pouvait le voir, et l'outil de
lecture imprimait « 3 vérifications OK, 0 échec ». Le défaut n'a été trouvé qu'en LISANT le dossier
en texte (`feedback_rendu_est_un_producteur`). §3 le fige : une inversion de signe dans `_rang`
doit virer au rouge.
"""
from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness import Bilan  # noqa: E402

from app.agents.v2.dossier import assembler_dossier  # noqa: E402

B = Bilan()


def _e(i: int, sd, collecte: str, tier: str = "A") -> dict:
    return {
        "id": i,
        "source_date": sd,
        "created_at": datetime.fromisoformat(collecte),
        "reliability_tier": tier,
        "nature": "mesure",
        "content": f"pièce #{i}",
    }


# ── fixture, copiée du corpus RVMD réel (2026-09-22) ─────────────────────────
ENTRIES = {
    # qf_4.endettement_brut_et_net — TROIS versions, et la datation y est hétérogène : la pièce
    # dont la `source_date` est la plus récente (#296) a été collectée la PREMIÈRE.
    296: _e(296, date(2026, 9, 1), "2026-09-12T10:00:00"),
    340: _e(340, date(2026, 6, 30), "2026-09-19T10:00:00"),
    443: _e(443, date(2026, 6, 30), "2026-09-21T10:00:00"),
    # lignes_de_credit_non_tirees — réclamé par qf_4 ET qf_7, une seule pièce les couvre.
    300: _e(300, date(2026, 8, 5), "2026-09-12T10:00:00"),
    445: _e(445, date(2025, 6, 30), "2026-09-21T10:00:00"),
    # un point à version unique
    301: _e(301, date(2026, 8, 5), "2026-09-12T10:00:00"),
    # une pièce NON DATÉE rattachée à un point daté. Sa date de COLLECTE est antérieure à celle de
    # #301 : cette chemise est donc le TÉMOIN non suspect de §8 — sans lui, les quatre chemises
    # seraient suspectes et l'assert serait satisfait par un détecteur qui lève toujours la main.
    999: _e(999, None, "2026-09-11T10:00:00"),
    # hors index — les faits déterministes du flux EDGAR
    282: _e(282, date(2026, 6, 30), "2026-09-11T10:00:00"),
    283: _e(283, date(2025, 12, 31), "2026-09-11T10:00:00"),
    284: _e(284, date(2025, 12, 31), "2026-09-11T10:00:00"),
}
LIENS = [
    ("qf_4", "endettement_brut_et_net", 296),
    ("qf_4", "endettement_brut_et_net", 340),
    ("qf_4", "endettement_brut_et_net", 443),
    ("qf_4", "lignes_de_credit_non_tirees", 300),
    ("qf_4", "lignes_de_credit_non_tirees", 445),
    ("qf_7", "lignes_de_credit_non_tirees", 300),
    ("qf_7", "lignes_de_credit_non_tirees", 445),
    ("qf_6", "provisions_et_depreciations", 301),
    ("qf_6", "provisions_et_depreciations", 999),
    ("qf_4", "echeancier_de_la_dette", 77777),  # lien mort : entry absente du corpus
]

D = assembler_dossier(entries=ENTRIES, liens=LIENS, plafond=40)
PAR_POINT = {(c.question_id, c.ingredient_id): c for c in D.chemises}

print("§1 regroupement — un point de la liste du comité par chemise")
B.require(D.chemises, 4, "une chemise par point réellement couvert")
B.check(
    ("qf_4", "echeancier_de_la_dette") not in PAR_POINT,
    "un lien vers une entry absente n'ouvre PAS de chemise vide — une chemise vide se lirait "
    "« point instruit » alors que rien ne le fonde",
)
B.check(
    PAR_POINT[("qf_4", "lignes_de_credit_non_tirees")].en_vigueur
    == PAR_POINT[("qf_7", "lignes_de_credit_non_tirees")].en_vigueur == 300,
    "une pièce partagée par deux points est en vigueur sur les DEUX",
)
B.check(
    sum(1 for i in D.entries if i == 300) == 1,
    "…et ne compte qu'UNE fois dans le dossier remis",
)

print("\n§2 la pièce en vigueur est la plus récente de sa chemise")
B.check(
    PAR_POINT[("qf_4", "endettement_brut_et_net")].en_vigueur == 296,
    "#296 (source_date 2026-09-01) est en vigueur devant #340 et #443 (2026-06-30)",
)
B.check(
    PAR_POINT[("qf_4", "lignes_de_credit_non_tirees")].en_vigueur == 300,
    "#300 (2026-08-05) est en vigueur devant #445 (2025-06-30)",
)
B.check(
    PAR_POINT[("qf_4", "endettement_brut_et_net")].anterieures == (443, 340),
    "les antérieures restent ordonnées de la plus récente à la plus ancienne "
    "(#443 et #340 à égalité de date, l'id le plus haut d'abord)",
)

print("\n§2bis une pièce d'HÉRITAGE cède devant une pièce DATÉE sous la 045 (#104, application de #79)")
# Le cas RÉEL du 2026-09-30 : #296 (héritage, `source_date` 2026-09-01 = la date d'un 8-K cité dans sa
# prose) pour des chiffres AU 2026-06-30. Une re-collecte datée au 2026-06-30 (#443 ici, qualifiée
# `constatee`) doit passer devant — sinon re-collecter ne change jamais la pièce lue par l'analyste.
QUALIFIEE = {**ENTRIES, 443: dict(ENTRIES[443], portee_temporelle="constatee")}
DQ = assembler_dossier(entries=QUALIFIEE, liens=LIENS, plafond=40)
PQ = {(c.question_id, c.ingredient_id): c for c in DQ.chemises}
B.check(
    PQ[("qf_4", "endettement_brut_et_net")].en_vigueur == 443,
    "#443 (datée 2026-06-30 sous la 045) est en vigueur devant #296 (héritage « 2026-09-01 »)",
)
B.check(
    PQ[("qf_4", "endettement_brut_et_net")].anterieures == (296, 340),
    "…et l'héritage reste rangé par sa date parmi les antérieures, jamais perdu (#25)",
)
B.check(
    PQ[("qf_6", "provisions_et_depreciations")].en_vigueur == 301,
    "une pièce SANS AUCUNE date reste dernière même face à l'héritage (#999 derrière #301)",
)
B.check(
    PAR_POINT[("qf_4", "endettement_brut_et_net")].en_vigueur == 296,
    "sans pièce qualifiée, l'ordre d'avant est inchangé (tout le corpus RVMD qf_* est héritage)",
)


def _sd(i: int):
    """La `source_date` de la pièce #i selon la FIXTURE — `None` si la fixture ne la connaît pas.

    Lecture défensive à dessein : un assemblage fautif peut faire entrer dans une chemise un id
    qu'aucune pièce ne porte (mesuré comme mutation : un lien mort « toléré » par stub). Indexer sec
    ferait mourir le script AVANT ses asserts — tout aussi rouge, mais par un autre canal, et §1
    perdrait la possibilité de NOMMER le défaut (2ᵉ faux vert, `feedback_test_negatif_trois_faux_verts`).
    Un id inconnu n'a pas de date : il est simplement hors du périmètre de l'invariant d'ordre.
    """
    return ENTRIES.get(i, {}).get("source_date")


print("\n§3 INVARIANT D'ORDRE — une inversion de signe dans `_rang` doit mordre ici")
datees = [
    c for c in D.chemises
    if _sd(c.en_vigueur) is not None
    and any(_sd(a) is not None for a in c.anterieures)
]
B.require(datees, 3, "chemises entièrement datées à éprouver")
B.check(
    all(
        _sd(c.en_vigueur) >= _sd(a)
        for c in datees for a in c.anterieures
        if _sd(a) is not None
    ),
    "AUCUNE antérieure n'est plus récente que la pièce en vigueur de sa chemise — "
    "c'est exactement ce qui était faux à la première écriture, et qu'aucun décompte ne voyait",
)

print("\n§4 une pièce NON DATÉE ne prétend jamais être la plus récente")
B.check(
    PAR_POINT[("qf_6", "provisions_et_depreciations")].en_vigueur == 301,
    "#301 (datée) passe devant #999 (non datée) — indéterminable n'est pas frais",
)
B.check(
    999 in PAR_POINT[("qf_6", "provisions_et_depreciations")].anterieures,
    "…et #999 est rangée en antérieure, pas silencieusement perdue (#25)",
)

print("\n§5 le plafond ne coupe jamais une pièce en vigueur")
SERRE = assembler_dossier(entries=ENTRIES, liens=LIENS, plafond=5)
B.check(
    {c.en_vigueur for c in SERRE.chemises} <= set(SERRE.entries),
    "à plafond serré, toutes les pièces en vigueur sont encore dans le dossier remis",
)
B.check(
    not SERRE.plafond_insuffisant,
    "3 pièces en vigueur distinctes pour un plafond de 5 : le plafond suffit",
)
B.check(
    len(SERRE.entries) == 5 and len(SERRE.hors_index_retenues) == 2,
    "une pièce en vigueur sur DEUX points ne consomme qu'une place du plafond — la compter deux "
    "fois rognerait le dossier d'une pièce qu'on avait le budget de joindre",
)
ETRIQUE = assembler_dossier(entries=ENTRIES, liens=LIENS, plafond=2)
B.check(
    ETRIQUE.plafond_insuffisant and {c.en_vigueur for c in ETRIQUE.chemises} <= set(ETRIQUE.entries),
    "plafond sous le nombre de pièces en vigueur : c'est DIT, et on ne coupe toujours pas — "
    "couper ferait lire « le corpus ne fonde pas » là où c'est le budget qui a tranché",
)

print("\n§6 les pièces hors index sont JOINTES, jamais écartées")
B.check(
    {282, 283, 284} <= set(D.entries),
    "les faits déterministes hors index sont dans le dossier — les écarter ferait lire "
    "« indisponible » là où il y a de la donnée",
)
B.check(
    D.hors_index_retenues[0] == 282,
    "…et ils sont joints du plus récent au plus ancien (#282 du 2026-06-30 en tête)",
)
B.check(
    set(SERRE.laissees_dehors) and set(SERRE.laissees_dehors) <= set(ENTRIES),
    "ce que le plafond laisse dehors est NOMMÉ, jamais tu",
)

print("\n§7 les versions antérieures sont dédoublonnées au rendu")
B.check(
    D.anterieures_ecartees == (340, 443, 445, 999),
    "#445 est antérieure sous qf_4 ET qf_7 : elle ne compte qu'une fois — un décompte de rendu "
    "se lit comme une propriété du corpus",
)

print("\n§8 la datation hétérogène est NOMMÉE, et son absence de mesure aussi")
B.check(
    D.datation_mesurable
    and {(c.question_id, c.ingredient_id) for c in D.datation_suspecte}
    == {("qf_4", "endettement_brut_et_net"),
        ("qf_4", "lignes_de_credit_non_tirees"),
        ("qf_7", "lignes_de_credit_non_tirees")},
    "les chemises dont la pièce en vigueur a été collectée avant une antérieure sont signalées",
)
B.check(
    ("qf_6", "provisions_et_depreciations")
    not in {(c.question_id, c.ingredient_id) for c in D.datation_suspecte},
    "…et le TÉMOIN ne l'est pas : un détecteur qui lève toujours la main ne détecte rien",
)
SANS_DATES = {i: {k: v for k, v in e.items() if k != "created_at"} for i, e in ENTRIES.items()}
MUET = assembler_dossier(entries=SANS_DATES, liens=LIENS, plafond=40)
B.check(
    not MUET.datation_mesurable and MUET.datation_suspecte == (),
    "sans `created_at`, la datation est INDÉTERMINABLE — un tuple vide ne doit pas se lire "
    "« rien à signaler » (#25/#44), d'où le drapeau distinct",
)
B.check(
    "INDÉTERMINABLE" in MUET.bilan(),
    "…et le bilan le DIT au lieu d'omettre la ligne",
)

print("\n§9 un dossier vide n'est pas un résultat")
try:
    assembler_dossier(entries=ENTRIES, liens=LIENS, plafond=0)
    B.check(False, "plafond=0 doit LEVER, jamais rendre un dossier vide (#25)")
except ValueError:
    B.check(True, "plafond=0 lève — une erreur n'est jamais un résultat vide (#25)")

print("\n§10 (#106) une lecture de dépôt à lire est JOINTE d'office au dossier")
# #296 est ANTÉRIEURE dans sa chemise dès qu'une pièce qualifiée passe devant (§2bis) : jointe d'office,
# elle reste au dossier — c'est ce qui a manqué à la réponse #976, née périmée faute de voir le 8-K.
DJ = assembler_dossier(entries=QUALIFIEE, liens=LIENS, plafond=40, joindre=[296, 77777])
B.check(296 in DJ.entries and 296 in DJ.jointes,
        "une pièce jointe d'office est remise même si elle est antérieure dans sa chemise")
B.check(296 not in DJ.anterieures_ecartees,
        "…et elle n'est plus annoncée « non remise » (le bilan ne ment pas sur ce qui part)")
B.check(77777 not in DJ.jointes, "un id absent du corpus n'est pas joint (lien mort toléré, pas fabriqué)")
DJ_SERRE = assembler_dossier(entries=QUALIFIEE, liens=LIENS, plafond=4, joindre=[296])
B.check(296 in DJ_SERRE.entries and all(c.en_vigueur in DJ_SERRE.entries for c in DJ_SERRE.chemises),
        "à plafond serré, la jointe et les pièces en vigueur passent AVANT le hors index")
B.check(len(DJ_SERRE.hors_index_retenues) == 0,
        "…et la place qu'elle prend est retirée au hors index (4 en vigueur + 1 jointe > plafond 4)")

print("\n§11 (#106) la LECTURE d'un dépôt : le texte déposé, daté par le dépôt, adressé dans son dossier")
import asyncio  # noqa: E402
from datetime import date as _d  # noqa: E402

import app.knowledge.lecture_depot as ld  # noqa: E402
from app.agents.v2.frameworks import provient_du_depot  # noqa: E402
from app.agents.v2.note_flash import DocumentDepot, NoteFlashImpossible  # noqa: E402
from app.knowledge.material_events import MaterialEvent  # noqa: E402

# Le 8-K RÉEL des baux de RVMD (flux EDGAR du 2026-09-30).
BAUX = MaterialEvent(form="8-K", event_date=_d(2026, 8, 27), filing_date=_d(2026, 9, 1),
                     items=("1.01", "2.03"), accession="0001193125-26-377362",
                     url="https://www.sec.gov/Archives/edgar/data/1628171/000119312526377362/rvmd-20260827.htm")
B.check(provient_du_depot({"source_url": ld.adresse_du_depot(BAUX, 1628171)}, BAUX.accession),
        "l'adresse de la lecture est DANS le dossier EDGAR du dépôt (c'est ce qui la dit « tirée du dépôt »)")
SANS_URL = MaterialEvent(form="8-K", event_date=BAUX.event_date, filing_date=BAUX.filing_date,
                         items=BAUX.items, accession=BAUX.accession, url=None)
B.check(provient_du_depot({"source_url": ld.adresse_du_depot(SANS_URL, 1628171)}, BAUX.accession),
        "…même quand le flux ne donne pas le document principal (index du dépôt)")
B.check(ld.type_de_piece(BAUX) == "fact_financial",
        "un 8-K portant un item de la section 2 (obligation financière) est une pièce financière")
B.check(ld.type_de_piece(MaterialEvent(form="8-K", event_date=BAUX.event_date, filing_date=BAUX.filing_date,
                                       items=("5.02",), accession="x")) == "fact_qualitative",
        "…un changement de dirigeants (5.02) une pièce qualitative — la nomenclature de la SEC, pas un jugement")
_DOC = DocumentDepot(type="8-K", nom="rvmd-20260827.htm",
                     texte="Item 1.01 Entry into a Material Definitive Agreement. On August 27, 2026 …",
                     taille=5000, tronque=True)
_txt = ld.construire_contenu(BAUX, [_DOC])
B.check("Item 1.01 Entry into a Material Definitive Agreement" in _txt and "TRONQUÉ" in _txt
        and "0001193125-26-377362" in _txt,
        "le contenu est le texte DÉPOSÉ, tel quel, avec l'accession et la troncature dite")


class _ConnLecture:
    def __init__(self, deja=None):
        self.deja = deja

    async def fetchval(self, *a):
        return self.deja


_ecrits: list[dict] = []


async def _store(conn, **kw):
    _ecrits.append(kw)
    return {"id": 9001}


async def _soumission(cik, acc):
    return "soumission"


_orig_ld = (ld.store_knowledge, ld.telecharger_soumission, ld.extraire_documents)
ld.store_knowledge, ld.telecharger_soumission, ld.extraire_documents = _store, _soumission, lambda s: [_DOC]
try:
    L1 = asyncio.run(ld.assurer_lectures(_ConnLecture(), "RVMD", 1628171, [BAUX, BAUX]))
    B.check([x.entry_id for x in L1] == [9001] and L1[0].ecrite and len(_ecrits) == 1,
            "un dépôt se lit UNE fois, même cité par deux questions")
    kw = _ecrits[0] if _ecrits else {}
    B.check(kw.get("source_type") == "edgar_official" and ld.ETIQUETTE in (kw.get("tags") or [])
            and BAUX.accession in (kw.get("tags") or []),
            "la pièce est un dépôt officiel, étiquetée « lecture du dépôt » + accession")
    B.check(kw.get("datation") is not None and kw["datation"].date_du_fait == _d(2026, 8, 27)
            and kw["datation"].date_du_document == _d(2026, 9, 1),
            "datée par le dépôt : le fait au 27/08 (reportDate), le document au 01/09 (filingDate) — #79")
    L2 = asyncio.run(ld.assurer_lectures(_ConnLecture(deja=555), "RVMD", 1628171, [BAUX]))
    B.check([x.entry_id for x in L2] == [555] and not L2[0].ecrite and len(_ecrits) == 1,
            "un dépôt DÉJÀ lu n'est ni retéléchargé ni réécrit")

    async def _panne(cik, acc):
        raise NoteFlashImpossible("EDGAR 503 sur la soumission")
    ld.telecharger_soumission = _panne
    L3 = asyncio.run(ld.assurer_lectures(_ConnLecture(), "RVMD", 1628171, [BAUX]))
    B.check(L3[0].entry_id is None and "503" in (L3[0].motif or "") and len(_ecrits) == 1,
            "une panne n'écrit rien et est RENDUE nommée — jamais une pièce vide (#25)")
    L4 = asyncio.run(ld.assurer_lectures(_ConnLecture(), "RVMD", None, [BAUX]))
    B.check(L4[0].entry_id is None and "CIK" in (L4[0].motif or ""), "un titre hors EDGAR est dit, pas lu")
finally:
    ld.store_knowledge, ld.telecharger_soumission, ld.extraire_documents = _orig_ld

print("\n§12 (#107) les SŒURS de la pièce élue partent avec elle ; seules les collectes précédentes sont antérieures")
# Fixture RECOPIÉE de la base (2026-10-03). MSFT qf_1 : une réponse du chercheur a écrit #355, #356
# et #357 dans la même transaction (même `created_at`), toutes au 2026-06-30, toutes d'héritage.
# RVMD qf_6 : #716 (10-K, clos 2025-12-31) et #717 (10-Q, clos 2026-06-30) de la même réponse, et
# #345 d'une collecte PRÉCÉDENTE (19/09) — le témoin qui doit rester antérieure.
def _h(i, sd, collecte, heritage):
    e = _e(i, sd, collecte)
    e["portee_temporelle"] = None if heritage else "ponctuelle"
    return e


_ts_msft = "2026-09-19T13:02:08.673186"
_ts_rvmd = "2026-09-30T08:21:35.604314"
E12 = {
    355: _h(355, date(2026, 6, 30), _ts_msft, True),
    356: _h(356, date(2026, 6, 30), _ts_msft, True),
    357: _h(357, date(2026, 6, 30), _ts_msft, True),
    716: _h(716, date(2025, 12, 31), _ts_rvmd, False),
    717: _h(717, date(2026, 6, 30), _ts_rvmd, False),
    345: _h(345, date(2025, 12, 31), "2026-09-19T10:00:00", True),
}
L12 = [("qf_1", "resultat_operationnel_apres_impot", i) for i in (355, 356, 357)] + [
    ("qf_6", "politique_de_capitalisation", i) for i in (716, 717, 345)]
D12 = assembler_dossier(entries=E12, liens=L12, plafond=40)
C12 = {c.question_id: c for c in D12.chemises}
B.check(set(C12["qf_1"].remises) == {355, 356, 357} and C12["qf_1"].anterieures == (),
        "MSFT qf_1 : les trois pièces d'une même réponse sont REMISES ensemble — aucune n'est "
        f"rangée en version antérieure (→ remises={C12['qf_1'].remises}, "
        f"antérieures={C12['qf_1'].anterieures})")
B.check(C12["qf_6"].en_vigueur == 717 and C12["qf_6"].soeurs == (716,),
        "RVMD qf_6 : le 10-Q #717 est élu, le 10-K #716 de la même réponse part avec lui "
        f"(→ élue #{C12['qf_6'].en_vigueur}, sœurs {C12['qf_6'].soeurs})")
B.check(C12["qf_6"].anterieures == (345,) and 345 not in D12.entries,
        "…et #345, d'une collecte PRÉCÉDENTE, reste antérieure, non remise — la règle ne fait "
        "pas tout partir")
B.check({355, 356, 357, 716, 717} <= set(D12.entries),
        "les sœurs sont dans le dossier remis (le point de lecture, pas seulement la chemise)")
_sans_ts = {i: {**e, "created_at": None} for i, e in E12.items()}
D12b = assembler_dossier(entries=_sans_ts, liens=L12, plafond=40)
B.check(all(c.soeurs == () for c in D12b.chemises),
        "sans horodatage chargé, AUCUNE sœur — `None == None` ne fabrique pas une réponse commune")
D12c = assembler_dossier(entries=E12, liens=L12, plafond=1)
B.check({355, 356, 357, 716, 717} <= set(D12c.entries) and D12c.plafond_insuffisant,
        "le plafond ne coupe pas une sœur : elle est porteuse comme la pièce élue (et le plafond "
        "insuffisant est DIT)")

sys.exit(B.summary())
