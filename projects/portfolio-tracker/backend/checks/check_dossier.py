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

sys.exit(B.summary())
