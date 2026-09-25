"""Vérification de `qualite_info` — la MESURE de qualité d'information (lot 6, `app/agents/v2/qualite_info.py`).

Sans réseau, sans modèle, sans base : la dérivation est une fonction PURE sur des réponses DÉJÀ
SERVIES (actualité recalculée en amont). Toute sa décision se joue hors ligne — la frontière gratuite
(`feedback_frontiere_gratuite_avant_depense_modele`). Le SERVICE (réponse → réponse servie) et la
lecture de base sont éprouvés ailleurs (`check_datation`, `montrer_qualite_info` sur base réelle).

  • §1 LES QUATRE ARBITRAGES DU FONDS, CHACUN ATTEIGNABLE ET DISCRIMINANT (#63, 5ᵉ faux vert). Aucun
       n'est vrai « par construction » : chacun se prouve par un couple où changer le seul facteur
       visé change la mesure.
       ① `sans_objet` HORS base — il compte dans `n_sans_objet`, jamais dans `base`.
       ② `repondu` et `approxime` valent le MÊME crédit de statut — à actualité égale, un dossier
          d'approximations vaut autant qu'un dossier de réponses pleines.
       ③ `perimee` (et `indeterminable`) → crédit 0, `courante` → plein. La seule bascule de
          l'actualité fait tomber le score.
       ④ `non_fondable` → crédit 0 mais DANS la base (un trou, pas une exclusion — il tire le score
          vers le bas là où un `sans_objet` ne le touche pas).
  • §2 LE TROISIÈME ÉTAT (#44) : toutes les questions hors objet ⟹ `aucune_question_applicable`,
       `score=None`. Jamais un 0 qui se lirait « dossier de mauvaise qualité » là où la vérité est
       « ce cadre ne s'applique pas ici ».
  • §3 LE RANG EST PUBLIÉ, JAMAIS FONDU DANS LE SCORE (#50, arbitrage 3). Une réponse périmée
       contribue 0 au score ET compte quand même dans `rang_moyen` : la solidité de la source est un
       axe distinct de sa fraîcheur. C'est l'assert qui aurait vu une fusion des deux axes.
  • §4 UNE MESURE PAR (framework, version) — deux versions ne se mêlent jamais (écart V9).
  • §5 DÉTENTEURS UNIQUES, JAMAIS RECOPIÉS (#46). Le crédit d'actualité est `FACTEUR_ACTUALITE` du
       contrat ; l'ordre des tiers est le `Tier` Literal lu par `get_args`, pas une 2ᵉ liste ; aucune
       table tier → nombre n'est écrite dans le module (elle divergerait de `RELIABILITY_TABLE`).
  • §6 EXACTITUDE ARITHMÉTIQUE du score sur un dossier mixte, au chiffre près.

Cible : pydantic v2 (container backend). Tester en container, **pas** le python hôte (v1).
"""
import sys
from pathlib import Path

from app.agents.v2.qualite_info import derive_qualite_info, rang_moyen_de, TIERS_ORDONNES
from app.contracts.framework_answer_schema import (
    Approximation, FondationServie, FrameworkAnswerServie, Reponse)
from app.contracts.qualite_info_schema import FACTEUR_ACTUALITE, QualiteInfo
from app.contracts.readiness_report_schema import GapItem

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Bilan, imports_symbol, strip_code  # noqa: E402

b = Bilan()
MOD = "app/agents/v2/qualite_info.py"
CODE = strip_code(Path(MOD).read_text(encoding="utf-8"))


# ── fabriques de réponses SERVIES (actualité déjà posée) ────────────────────────────────────────
def _repondu(qid, *, act="courante", rang="A", fw="qualite_financiere", ver="v3.0.0", analyste="a"):
    return FrameworkAnswerServie(
        framework_id=fw, framework_version=ver, question_id=qid, ticker_id="RVMD",
        analyste=analyste, statut="repondu",
        reponse=Reponse(verbatim="x", valeur=1.0, unite="%"),
        fondation=FondationServie(cited_entry_ids=[10], rang_derive=rang, nature_effective="mesure",
                                  actualite=act, motif_actualite="m"))


def _approxime(qid, *, act="courante", rang="A-", fw="qualite_financiere", ver="v3.0.0"):
    return FrameworkAnswerServie(
        framework_id=fw, framework_version=ver, question_id=qid, ticker_id="RVMD",
        analyste="a", statut="approxime",
        reponse=Reponse(verbatim="x", valeur=1.0, unite="%"),
        fondation=FondationServie(cited_entry_ids=[10, 11], rang_derive=rang,
                                  nature_effective="interpretation", actualite=act,
                                  motif_actualite="m"),
        approximation=Approximation(methode="m", ingredients_entry_ids=[10, 11],
                                    hypotheses_explicites=["h"], sensibilite="s"))


def _sans_objet(qid, *, fw="qualite_financiere", ver="v3.0.0"):
    from app.contracts.framework_answer_schema import SansObjet
    return FrameworkAnswerServie(
        framework_id=fw, framework_version=ver, question_id=qid, ticker_id="RVMD",
        analyste="a", statut="sans_objet",
        sans_objet=SansObjet(motif="sans revenus", aucun_substitut=True))


def _non_fondable(qid, *, fw="qualite_financiere", ver="v3.0.0"):
    return FrameworkAnswerServie(
        framework_id=fw, framework_version=ver, question_id=qid, ticker_id="RVMD",
        analyste="a", statut="non_fondable",
        gap=GapItem(dimension="d", champs_cibles=[qid], manque="m", priorite="haute",
                    coverage_actuelle="0/1"))


def _un(mesures):
    assert len(mesures) == 1, f"attendu une seule mesure, {len(mesures)}"
    return mesures[0]


# ══ §1 ① — sans_objet HORS base ════════════════════════════════════════════════════════════════
m = _un(derive_qualite_info([_repondu("qf_4"), _sans_objet("qf_1"), _sans_objet("qf_2")]))
b.check(m.n_sans_objet == 2, "§1① les `sans_objet` sont comptés (n_sans_objet)")
b.check(m.base == 1, "§1① mais HORS base — seule la question applicable y entre")
b.check(m.score == 1.0, "§1① le score ne se dilue pas des `sans_objet` (1 repondu courant = 1.0)")

# ② repondu et approxime : MÊME crédit de statut (à actualité égale) ─────────────────────────────
m_rep = _un(derive_qualite_info([_repondu("qf_4"), _repondu("qf_5")]))
m_app = _un(derive_qualite_info([_approxime("qf_4"), _approxime("qf_5")]))
b.check(m_rep.score == m_app.score == 1.0,
        "§1② un dossier d'approximations courantes vaut autant qu'un dossier de réponses pleines")

# ③ actualité : perimee/indeterminable → 0, courante → plein (seul facteur qui bascule) ──────────
m_c = _un(derive_qualite_info([_repondu("qf_4", act="courante")]))
m_p = _un(derive_qualite_info([_repondu("qf_4", act="perimee")]))
m_i = _un(derive_qualite_info([_repondu("qf_4", act="indeterminable")]))
b.check(m_c.score == 1.0 and m_p.score == 0.0 and m_i.score == 0.0,
        "§1③ la seule bascule d'actualité fait tomber le score (1.0 → 0.0)")
b.check(m_p.n_perimee == 1 and m_i.n_indeterminable == 1 and m_p.n_indeterminable == 0,
        "§1③ perimee et indeterminable restent comptées SÉPARÉMENT (remèdes distincts, #53)")

# ④ non_fondable : crédit 0 mais DANS la base (tire le score, là où sans_objet ne le touche pas) ─
m_nf = _un(derive_qualite_info([_repondu("qf_4"), _non_fondable("qf_5")]))
m_so = _un(derive_qualite_info([_repondu("qf_4"), _sans_objet("qf_5")]))
b.check(m_nf.base == 2 and m_nf.score == 0.5, "§1④ non_fondable entre dans la base à crédit nul")
b.check(m_so.base == 1 and m_so.score == 1.0, "§1④ sans_objet, lui, sort de la base")
b.check(m_nf.score < m_so.score,
        "§1④ discriminant : un trou (non_fondable) pénalise, une exclusion (sans_objet) non")

# ══ §2 — le troisième état : aucune question applicable ═════════════════════════════════════════
m0 = _un(derive_qualite_info([_sans_objet("qf_1"), _sans_objet("qf_2")]))
b.check(m0.etat == "aucune_question_applicable" and m0.score is None,
        "§2 tout hors objet ⟹ état nommé, score=None (jamais 0 — #44)")
b.check(m0.base == 0 and m0.n_sans_objet == 2, "§2 la base est vide, les hors-objet sont comptés")

# ══ §3 — le rang est PUBLIÉ, jamais fondu dans le score (#50) ═══════════════════════════════════
# Une réponse PÉRIMÉE contribue 0 au score ET compte dans rang_moyen : deux axes distincts.
m_per_A = _un(derive_qualite_info([_repondu("qf_4", act="perimee", rang="A")]))
b.check(m_per_A.score == 0.0, "§3 une réponse périmée ne fonde pas la décision du jour (score 0)")
b.check(m_per_A.rang_moyen == "A",
        "§3 …mais sa source reste solide : rang_moyen='A' même si elle est périmée (axes séparés)")
# rang_moyen sur un mélange A / A- : moyenne de position, jamais un nombre [0,1].
m_mix = _un(derive_qualite_info([_repondu("qf_4", rang="A"), _approxime("qf_6", rang="A-")]))
b.check(m_mix.rang_moyen == "A-", "§3 rang_moyen(A, A-) = A- (moyenne de position dans le tier)")
# aucune réponse fondée ⟹ rang_moyen absent (jamais un rang sur zéro ligne).
m_nf_only = _un(derive_qualite_info([_non_fondable("qf_4"), _non_fondable("qf_5")]))
b.check(m_nf_only.rang_moyen is None and m_nf_only.score == 0.0,
        "§3 aucune réponse fondée ⟹ rang_moyen=None (pas un rang inventé sur zéro ligne)")

# ══ §4 — une mesure par (framework, version) ═══════════════════════════════════════════════════
mm = derive_qualite_info([
    _repondu("qf_4", fw="qualite_financiere"),
    _repondu("mo_1", fw="defendabilite"),
    _repondu("qf_4", fw="qualite_financiere", ver="v3.1.0")])
b.check(len(mm) == 3, "§4 trois (framework, version) distincts ⟹ trois mesures")
b.check({(x.framework_id, x.framework_version) for x in mm} ==
        {("qualite_financiere", "v3.0.0"), ("defendabilite", "v3.0.0"),
         ("qualite_financiere", "v3.1.0")},
        "§4 chaque mesure porte SON couple (framework, version) — jamais mêlées (écart V9)")

# ══ §5 — détenteurs uniques, jamais recopiés (#46) ═════════════════════════════════════════════
b.check(imports_symbol(MOD, "FACTEUR_ACTUALITE", from_module="app.contracts.qualite_info_schema"),
        "§5 le crédit d'actualité est LU dans le contrat, pas redéfini")
b.check(imports_symbol(MOD, "Tier", from_module="app.contracts.analysis_v2_schemas"),
        "§5 l'ordre des tiers vient du `Tier` Literal, détenteur unique du vocabulaire")
b.check("get_args" in CODE and "TIERS_ORDONNES" in CODE,
        "§5 l'ordre est dérivé par get_args(Tier), pas recopié en dur")
# Aucune table tier → nombre écrite dans le module : chercher un littéral de tier associé à un float.
b.check(not any(f'"{t}"' in CODE and f'"{t}":' in CODE for t in ("A", "A-", "B+", "B")),
        "§5 aucune table tier → nombre dans le module (elle divergerait de RELIABILITY_TABLE)")
# Le crédit du contrat est bien celui-ci, et les trois états y figurent.
b.check(FACTEUR_ACTUALITE == {"courante": 1.0, "perimee": 0.0, "indeterminable": 0.0},
        "§5 FACTEUR_ACTUALITE : courante plein, perimee/indeterminable nuls")
# rang_moyen_de est fondé sur l'ordre réel du Literal.
b.check(TIERS_ORDONNES[0] == "A" and TIERS_ORDONNES[-1] == "C",
        "§5 TIERS_ORDONNES va du meilleur (A) au plus faible (C)")
b.check(rang_moyen_de([]) is None, "§5 rang_moyen_de([]) = None (jamais un rang sur zéro ligne)")

# ══ §6 — exactitude arithmétique sur un dossier mixte ══════════════════════════════════════════
# 1 repondu courante (1.0) + 1 approxime périmée (0.0) + 1 non_fondable (0.0) sur base 3 = 0.3333.
m6 = _un(derive_qualite_info([
    _repondu("qf_4", act="courante"), _approxime("qf_6", act="perimee"), _non_fondable("qf_7")]))
b.check(m6.base == 3 and m6.score == round(1.0 / 3, 4),
        "§6 score = crédit_total / base, au chiffre près (1/3 = 0.3333)")
b.check(m6.n_courante == 1 and m6.n_perimee == 1 and m6.n_indeterminable == 0,
        "§6 la ventilation d'actualité couvre EXACTEMENT les réponses fondées (2), pas le non_fondable")

sys.exit(b.summary())
