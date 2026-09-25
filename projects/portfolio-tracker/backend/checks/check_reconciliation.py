"""Vérification de la RÈGLE de réconciliation des vocabulaires (`tools/reconcilier_vocabulaires`).

Ce check ne mesure PAS l'écart courant — `tools/reconcilier_vocabulaires.sh` le fait, et il est
ROUGE par construction (30 feuilles de mémo sans question, 13 questions jamais consommées, spec §6).
Ici on éprouve l'INSTRUMENT, hors ligne, et il est vert aujourd'hui.

POURQUOI IL EXISTE
------------------
Le 2026-09-21, deux copies de la même règle ont été trouvées en divergence : `reconcilier_
vocabulaires` jugeait contre `FIELD_PROFILES` (la grille MVDD à qui le lot 3 a retiré son autorité)
et rendait `14 / 3`, pendant que `tools/acceptation_frameworks` jugeait contre les frameworks et
rendait `30 / 13`. C'est le `14 / 3` du mesureur périmé qui avait été recopié dans le 00-REPRISE,
dans la spec §0.3 et dans trois notes de lot. La règle vit désormais une seule fois, dans
`ecart()` ; ce fichier garde le fait qu'elle est éprouvable, pas le chiffre qu'elle rend.

CE QU'IL NE FAIT PAS : asserter `30` et `13`. Un décompte de corpus gelé dans un assert est une
cible interdite (§0.6) — il rougirait à la première question ajoutée, pour la meilleure des
raisons. Les asserts ci-dessous portent sur la FORME de la règle, jamais sur sa valeur du jour.

  • §1 l'instrument lit quelque chose — les deux vocabulaires sont non vides et viennent de leurs
       détenteurs uniques (`load_frameworks()`, les `model_fields` Pydantic) ;
  • §2 SATISFIABILITÉ — la règle PEUT virer au vert. Un critère écrit avant sa capacité et qu'aucune
       entrée ne peut satisfaire n'est pas une exigence, c'est un décor
       (`feedback_acceptation_rouge_bidirectionnelle`) ;
  • §3 DISCRIMINATION — une mutation par clause, et c'est la clause VISÉE qui bouge ;
  • §4 le faux vert du vocabulaire vide, nommé et gardé : sur zéro question, T7 rend zéro et a l'air
       tenu (`all()` sur liste vide). C'est §A qui l'arrête, pas §B.
"""
import sys

from app.contracts.memo_blocs import BLOCS_MEMO, feuilles_memo
from tools.reconcilier_vocabulaires import DERIVES, ecart, vocabulaire_questions

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


memo = feuilles_memo()
questions = vocabulaire_questions()          # LÈVE si le référentiel est illisible — voulu
a_fonder = memo - DERIVES

print("\n1. l'instrument lit ses deux vocabulaires chez leurs détenteurs uniques (#46)")
check("le vocabulaire des QUESTIONS est non vide", bool(questions),
      "→ sur zéro question, tout champ du mémo paraîtrait orphelin")
check("le vocabulaire de SORTIE est non vide", bool(memo),
      "→ sur zéro feuille, « zéro orpheline » serait vrai sur zéro ligne")
check("les DÉRIVÉS sont un sous-ensemble strict des feuilles du mémo",
      DERIVES < memo,
      f"→ {sorted(DERIVES - memo)} : une dispense qui ne dispense plus rien")
check("chaque bloc déclaré est une classe du contrat `ResearchMemo`",
      all(hasattr(c, "model_fields") for c in BLOCS_MEMO.values()),
      "→ un bloc qui n'est plus un modèle Pydantic rendrait zéro feuille sans se plaindre")

print("\n2. SATISFIABILITÉ — la règle peut virer au vert")
# L'état terminal de la roadmap : un framework par bloc de mémo, une question par feuille à fonder.
sans, jamais = ecart(memo, set(a_fonder))
check("un vocabulaire qui couvre EXACTEMENT les feuilles à fonder rend 0 / 0",
      (sans, jamais) == ([], []),
      f"→ {len(sans)} orphelines / {len(jamais)} inutilisées : la règle est inatteignable, "
      f"donc ce n'est pas une exigence mais un décor")
check("les champs DÉRIVÉS ne comptent pas comme orphelins",
      ecart(memo, set())[0] == sorted(a_fonder),
      "→ un dérivé compté orphelin gonflerait T6 d'un défaut qui n'en est pas un")

print("\n3. DISCRIMINATION — une mutation par clause")
temoin_t6 = sorted(a_fonder)[0]
sans, jamais = ecart(memo, set(a_fonder) - {temoin_t6})
check(f"retirer `{temoin_t6}` du vocabulaire rend CE champ orphelin, et lui seul",
      (sans, jamais) == ([temoin_t6], []),
      f"→ {sans} / {jamais} : la clause T6 ne désigne pas le champ qu'on a retiré")
TEMOIN_T7 = "cadre_absent.question_que_le_memo_n_a_pas"
sans, jamais = ecart(memo, set(a_fonder) | {TEMOIN_T7})
check(f"ajouter `{TEMOIN_T7}` le rend inutilisé, sans toucher T6",
      (sans, jamais) == ([], [TEMOIN_T7]),
      f"→ {sans} / {jamais} : la clause T7 déborde sur T6, un rouge ne dirait plus laquelle")

print("\n4. le faux vert du vocabulaire vide, nommé")
# Sur zéro question, T7 = `set() - memo` = vide : la clause est VRAIE, et elle ne prouve rien.
# C'est le 4ᵉ faux vert (`all()` sur liste vide). Rien en §B ne peut l'attraper — seule la garde
# de non-vacuité de §A l'arrête, et c'est pour ça qu'elle existe.
check("sur un vocabulaire VIDE, la clause T7 est vraie — donc §B seul ne suffit pas",
      ecart(memo, set())[1] == [],
      "→ si ce n'est plus vrai, le raisonnement de §A a changé et son commentaire ment")
check("la garde de non-vacuité est ce qui rattrape ce cas", bool(questions),
      "→ garde absente : un référentiel vide passerait T7 en silence")

print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
