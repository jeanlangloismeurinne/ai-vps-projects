"""Vérification du COLLECTEUR / AIGUILLEUR (chantier v3, lot 2c — `app/agents/v2/collecteur.py`).

Sans réseau ni modèle ni base. L'exécution réelle d'une ligne est injectée (`collecter`) ; on éprouve
ici la LOGIQUE d'aiguillage, qui est déterministe et porte les garanties structurantes de §3.6.

  • §1 LE COLLECTEUR EST AVEUGLE À LA QUESTION — `LigneAveugle` n'a NI `question_id`, NI
       `ingredient_id`, NI framework. L'exécuteur ne peut donc pas savoir à quelle question il répond,
       donc l'entry qu'il écrit ne peut pas porter de vocabulaire de framework (principe 2, structurel).
  • §2 UN RÉSULTAT DE COLLECTE EST UN XOR — une entry OU un échec motivé, jamais les deux ni aucun
       (#25 : un échec n'est pas un vide).
  • §3 LA COUVERTURE EST UN SOUS-PRODUIT DÉTERMINISTE DU DISPATCH — l'aiguilleur, qui tient le plan,
       rattache l'entry à SA (question, ingrédient) ; le collecteur ne l'a jamais su (#57). Les clefs
       viennent du PLAN, pas d'une déclaration de modèle.
  • §4 TROIS ÉTATS, AUCUNE LIGNE NE S'ÉVAPORE — chaque ligne produit EXACTEMENT un lien OU un mandat.
       `inobtenable` → mandat (origine `inobtenable`, jamais exécuté) ; collecte échouée → mandat
       (origine `echec_collecte`) ; jamais un silence.
  • §5 LES COLONNES DU LIEN SONT CELLES DE `question_coverage` — la persistance mappe 1:1 (§6,
       migration 036), pas une nomenclature devinée qui lirait `None` pour toujours.

Cible : pydantic v2 (container backend). Tester en container, **pas** le python hôte (v1).
"""
import sys

from pydantic import ValidationError

from app.agents.v2.collecteur import (
    LienCouverture,
    LigneAveugle,
    MandatCollecte,
    ResultatCollecte,
    aiguiller_plan,
    ligne_aveugle,
)
from app.contracts.collection_plan_schema import CollectionPlan, CollectionPlanItem

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


def rejete(label, fn, motif):
    global ok, fail
    try:
        fn()
        fail += 1
        print(f"  FAIL {label} → ACCEPTÉ alors qu'il devait être refusé")
    except (ValidationError, ValueError) as e:
        if motif in str(e):
            ok += 1
            print(f"  ok   {label}")
        else:
            fail += 1
            print(f"  FAIL {label} → refusé, mais PAS par la règle visée (attendu « {motif} »)")
    except Exception as e:  # noqa: BLE001
        fail += 1
        print(f"  FAIL {label} → mauvaise exception {type(e).__name__}")


# ── fixtures : un plan minimal, 3 lignes couvrant les trois états ────────────────────────────────
TRAD_OK = CollectionPlanItem(question_id="qf_1", ingredient_id="resultat_operationnel_apres_impot",
                             statut="traduit", metrique="résultat d'exploitation après impôt",
                             source_pressentie="10-K", ancre="clôture de l'exercice")
TRAD_KO = CollectionPlanItem(question_id="qf_1", ingredient_id="capital_employe",
                             statut="traduit", metrique="ECHEC capital employé net",
                             source_pressentie="10-K", ancre="clôture de l'exercice")
INOB = CollectionPlanItem(question_id="qf_1", ingredient_id="cout_du_capital", statut="inobtenable",
                          motif="aucun poste EDGAR ne produit le coût du capital directement")
PLAN = CollectionPlan(ticker_id="NVDA", framework_id="qualite_financiere",
                      framework_version="v3.0.0", archetype="rentable",
                      items=[TRAD_OK, TRAD_KO, INOB])


class Espion:
    """Exécuteur factice : réussit sauf si la métrique commence par ECHEC. Enregistre ce qu'il a VU."""
    def __init__(self):
        self.vues: list[LigneAveugle] = []
        self._n = 100

    def __call__(self, ligne: LigneAveugle) -> ResultatCollecte:
        self.vues.append(ligne)
        if ligne.metrique.startswith("ECHEC"):
            return ResultatCollecte(echec="la source pressentie n'a rien rendu")
        self._n += 1
        return ResultatCollecte(entry_id=self._n)


# ── §1 le collecteur est aveugle à la question ────────────────────────────────────────────────────
print("[1] le collecteur ne voit NI la question NI l'ingrédient (principe 2, structurel)")
check("`LigneAveugle` ne déclare aucun champ de question/ingrédient/framework",
      not ({"question_id", "ingredient_id", "framework_id", "framework_version"}
           & set(LigneAveugle.model_fields)), f"→ {set(LigneAveugle.model_fields)}")
_la = ligne_aveugle(TRAD_OK, "NVDA")
check("`ligne_aveugle` produit bien un objet aveugle (métrique/source/ancre/ticker seulement)",
      set(_la.model_dump()) == {"ticker_id", "metrique", "source_pressentie", "ancre"})
rejete("`ligne_aveugle` refuse une ligne `inobtenable` (rien à collecter)",
       lambda: ligne_aveugle(INOB, "NVDA"), "seule une ligne traduite")

# ── §2 un résultat de collecte est un XOR ─────────────────────────────────────────────────────────
print("\n[2] une collecte a réussi (une entry) OU échoué (un motif), jamais un entre-deux (#25)")
check("entry seule est valide", ResultatCollecte(entry_id=1).entry_id == 1)
check("échec seul est valide", ResultatCollecte(echec="rien trouvé").echec == "rien trouvé")
rejete("les deux à la fois → refusé", lambda: ResultatCollecte(entry_id=1, echec="rien"),
       "SOIT `entry_id` SOIT `echec`")
rejete("aucun des deux → refusé", lambda: ResultatCollecte(), "SOIT `entry_id` SOIT `echec`")

# ── §3 + §4 aiguillage : couverture déterministe, trois états, rien ne s'évapore ─────────────────
print("\n[3+4] aiguillage : couverture = sous-produit du dispatch · trois états · aucune évaporation")
espion = Espion()
R = aiguiller_plan(PLAN, collecter=espion)

check("le collecteur n'a été appelé QUE sur les lignes traduites (inobtenable jamais exécuté)",
      len(espion.vues) == 2 and all(isinstance(v, LigneAveugle) for v in espion.vues),
      f"→ {len(espion.vues)} appels")
check("une collecte réussie produit UN lien de couverture", len(R.liens) == 1)
_lien = R.liens[0]
check("… clefé par la (question, ingrédient) du PLAN, pas par le collecteur (#57)",
      (_lien.framework_id, _lien.framework_version, _lien.question_id, _lien.ingredient_id,
       _lien.entry_id) == ("qualite_financiere", "v3.0.0", "qf_1",
                           "resultat_operationnel_apres_impot", 101),
      f"→ {_lien.model_dump()}")
check("l'inobtenable devient un mandat d'origine `inobtenable` (jamais exécuté)",
      any(m.origine == "inobtenable" and m.ingredient_id == "cout_du_capital" for m in R.mandats))
check("la collecte échouée devient un mandat d'origine `echec_collecte` (jamais un silence, #25)",
      any(m.origine == "echec_collecte" and m.ingredient_id == "capital_employe" for m in R.mandats))
check("AUCUNE ligne ne s'évapore : liens + mandats == lignes vues",
      len(R.liens) + len(R.mandats) == R.lignes_vues == len(PLAN.items),
      f"→ {len(R.liens)} + {len(R.mandats)} vs {R.lignes_vues}")
rejete("un mandat d'origine inconnue est refusé (pas de 3ᵉ cause muette)",
       lambda: MandatCollecte(framework_id="f", framework_version="v", question_id="qf_1",
                              ingredient_id="x", motif="peu importe", origine="autre"),
       "origine `autre` inconnue")

# ── §5 les colonnes du lien sont celles de question_coverage ──────────────────────────────────────
print("\n[5] le lien mappe 1:1 sur `question_coverage` (persistance sans nomenclature devinée)")
check("`LienCouverture` porte EXACTEMENT les colonnes métier de `question_coverage`",
      set(LienCouverture.model_fields) ==
      {"framework_id", "framework_version", "question_id", "ingredient_id", "entry_id"},
      f"→ {set(LienCouverture.model_fields)}")


print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
