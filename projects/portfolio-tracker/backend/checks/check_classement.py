"""Vérification du CLASSEMENT PAR LE COMITÉ et de la recommandation de « changement de stade » (#139).

Sans réseau, sans modèle, sans base. La table est éprouvée contre une copie du réel par
`negatif_059.sh` ; la jonction de la pièce à tous les chapitres par `check_dossier` §14.

CE QUE FERAIT UN VRAI FONDS. Le stade de la société est écrit en tête de chaque dossier. Quand une biotech
obtient l'autorisation de vendre son premier produit, l'analyste propose de la reclasser « commerciale » ;
le directeur de la recherche décide, date, signe et cite l'événement — jamais le système seul.

  • §1 LE CATALOGUE (1.7.0) : `changement_de_stade`, d'origine émetteur, recommande pre_revenus → rentable ;
       il rouvre EXACTEMENT la table validée par l'utilisateur le 2026-10-18 (les questions rouvertes par
       l'approbation, plus qf_6, qf_7, me_2/3/4/6, se_2/3, ma_1, va_1/4/5) ; la consigne des pairs (se_3)
       dit qu'un changement de stade POSE la question des pairs sans la trancher.
  • §2 LE CONTRAT ET LE PONT : `reclasse` refusé sur un type extérieur ; [W] refuse un archétype inconnu
       et une recommandation de ne rien changer.
  • §3 LA RECOMMANDATION (pure, recalculée à la lecture) : RVMD classée d'origine APRÈS l'approbation
       reçoit quand même la recommandation (un classement d'origine ne tranche rien) ; « réglementaire
       favorable » seul ne recommande rien ; une décision du comité ferme les faits jusqu'à sa date, un
       fait ultérieur rouvre ; le premier fait non tranché est retenu ; non classé ou déjà rentable : rien.
  • §4 LE GESTE (`decider_classement`) : archétype déclaré, dépôt du fil de l'émetteur, décision
       postérieure au classement en vigueur, lecture obtenue — sinon refus nommé ; la ligne porte la
       pièce, l'auteur et le dépôt, et prend effet le jour du geste.
  • §5 LE NIVEAU 1 : la recommandation en suspens empêche « dossier complet » ; le classement et la
       recommandation sont servis ; l'écran les rend et propose reclasser / maintenir.

Cible : pydantic v2 (container backend). Tester en container, **pas** le python hôte.
"""
import asyncio
import copy
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from app.agents.v2 import classement as CL
from app.agents.v2.classement import ClassementRefuse, recommandation_de_classement
from app.agents.v2.framework_persist import Classement
from app.agents.v2.frameworks import FrameworkDefinitionRefused, load_frameworks
from app.agents.v2.frameworks import _valider_pont_definitions as valider_pont_frameworks
from app.agents.v2.parcours import EtatDossier, dresser_niveau1
from app.agents.v2.projection_memo import memo_de_l_etat
from app.contracts.framework_definition_schema import FrameworksFile, TypeEvenement
from app.knowledge.evenements import QualificationLue
from app.knowledge.lecture_depot import Lecture
from app.knowledge.material_events import MaterialEvent, MaterialEventLookup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Bilan  # noqa: E402

b = Bilan()
FICHIER = load_frameworks()
T0 = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)
ACC_FDA = "0001193125-26-366931"       # 8-K du 26/08 : approbation de RASONQUE
ACC_ESSAI = "0001193125-26-152039"     # 8-K du 13/04 : essai qui atteint son objectif


def refuse(fn, motif: str, label: str) -> None:
    """Un refus prononcé par une AUTRE règle est un FAIL (4ᵉ faux vert)."""
    try:
        fn()
    except Exception as e:  # noqa: BLE001
        b.check(motif in str(e), f"{label} — refusé, mais pas pour la bonne raison : {e}")
        return
    b.check(False, f"{label} — ACCEPTÉ")


# ══ §1 LE CATALOGUE ════════════════════════════════════════════════════════════════════════════
print("[1] le catalogue 1.7.0")
TYPES = {t.id: t for t in FICHIER.types_evenement}
st = TYPES.get("changement_de_stade")
b.check(FICHIER.types_evenement_version == "1.7.0",
        f"§1 le catalogue est monté en 1.7.0 (→ {FICHIER.types_evenement_version}) : le lecteur relit les dépôts")
b.check(st is not None and st.origine == "emetteur" and st.portee == "questions_declarees",
        "§1 `changement_de_stade` existe, lu dans les dépôts de l'émetteur, rouvre les questions qui le déclarent")
b.check(st is not None and st.reclasse == {"pre_revenus": "rentable"},
        f"§1 il recommande « sans revenus » → « commerciale » (→ {st.reclasse if st else None})")
b.check(st is not None and "PREMIER" in st.libelle and "ANNONCÉ PAR CE DÉPÔT" in st.libelle
        and "produit supplémentaire" in st.libelle,
        "§1 son libellé dit « premier produit », « annoncé par ce dépôt », et ce qui n'en est pas un")
EN_PLUS = {"qf_6", "qf_7", "me_2", "me_3", "me_4", "me_6", "se_2", "se_3", "ma_1", "va_1", "va_4", "va_5"}
toutes = [q for f in FICHIER.frameworks for q in f.questions]
par_approbation = {q.id for q in toutes if "reglementaire_favorable" in q.rouverte_par}
rouvertes = {q.id for q in toutes if "changement_de_stade" in q.rouverte_par}
b.check(rouvertes == par_approbation | EN_PLUS,
        f"§1 il rouvre EXACTEMENT la table validée (→ en trop {sorted(rouvertes - par_approbation - EN_PLUS)}, "
        f"manquantes {sorted((par_approbation | EN_PLUS) - rouvertes)})")
b.check(not rouvertes & {"qf_4", "qf_8", "se_4", "se_6", "ma_2", "ma_3", "ma_4", "ma_5", "ma_6", "ma_7"},
        "§1 … et pas ce que la table écarte (dette, engagements, cycle, concurrents, gouvernance)")
pairs = next(i for q in toutes if q.id == "se_3" for i in q.ingredients_requis if i.id == "pairs_directs")
b.check("changement de stade" in pairs.libelle and "juste derrière en calendrier" in pairs.libelle
        and "marché analogue" in pairs.libelle,
        "§1 la consigne des pairs : même marché ou analogue, un changement de stade pose la question sans la trancher")

# ══ §2 LE CONTRAT ET LE PONT ═══════════════════════════════════════════════════════════════════
print("[2] le contrat et le pont [W]")
refuse(lambda: TypeEvenement(id="concurrent_x", libelle="Chez un concurrent — un événement quelconque",
                             portee="questions_declarees", origine="exterieur",
                             reclasse={"pre_revenus": "rentable"}),
       "ne change pas le stade", "§2 un type EXTÉRIEUR qui recommanderait un reclassement est refusé")


def _avec_reclasse(reclasse):
    brut = FICHIER.model_dump()
    for t in brut["types_evenement"]:
        if t["id"] == "changement_de_stade":
            t["reclasse"] = reclasse
    return FrameworksFile.model_validate(brut)


refuse(lambda: valider_pont_frameworks(_avec_reclasse({"pre_revenus": "licorne"})),
       "[W]", "§2 [W] une cible hors des archétypes déclarés est refusée")
refuse(lambda: valider_pont_frameworks(_avec_reclasse({"rentable": "rentable"})),
       "ne rien changer", "§2 [W] une recommandation de ne rien changer est refusée")
try:
    valider_pont_frameworks(copy.deepcopy(FICHIER))
    b.check(True, "")
except FrameworkDefinitionRefused as e:
    b.check(False, f"§2 le référentiel réel passe le pont (témoin) — refusé : {e}")

# ══ §3 LA RECOMMANDATION ═══════════════════════════════════════════════════════════════════════
print("[3] la recommandation, recalculée à la lecture")
ORIGINE = Classement(archetype="pre_revenus", motif="classement d'origine", effective_from=date(2026, 9, 24))


def note(types, le):
    return QualificationLue(types=frozenset(types), resume=f"note flash du {le}", date_evenement=le)


NOTES = {ACC_ESSAI: note({"reglementaire_favorable"}, date(2026, 4, 13)),
         ACC_FDA: note({"reglementaire_favorable", "changement_de_stade"}, date(2026, 8, 26))}
r = recommandation_de_classement(ORIGINE, NOTES, FICHIER)
b.check(r is not None and r.vers == "rentable" and r.de == "pre_revenus" and r.accession == ACC_FDA
        and r.fait_du == date(2026, 8, 26) and r.type_id == "changement_de_stade",
        f"§3 RVMD classée d'origine le 24/09 APRÈS l'approbation du 26/08 reçoit la recommandation (→ {r})")
b.check(recommandation_de_classement(ORIGINE, {ACC_ESSAI: NOTES[ACC_ESSAI]}, FICHIER) is None,
        "§3 « réglementaire favorable » seul (un essai réussi) ne recommande rien")
MAINTENU = Classement(archetype="pre_revenus", motif="maintenu", effective_from=date(2026, 10, 18),
                      piece_id=944, auteur="gérant", declencheur_accession=ACC_FDA)
b.check(recommandation_de_classement(MAINTENU, NOTES, FICHIER) is None,
        "§3 une DÉCISION du comité (maintenir) ferme les faits survenus jusqu'à sa date")
ULTERIEUR = {**NOTES, "0000000000-26-999999": note({"changement_de_stade"}, date(2026, 11, 5))}
r2 = recommandation_de_classement(MAINTENU, ULTERIEUR, FICHIER)
b.check(r2 is not None and r2.accession == "0000000000-26-999999",
        "§3 … un fait ULTÉRIEUR du même ordre rouvre la recommandation")
r3 = recommandation_de_classement(ORIGINE, ULTERIEUR, FICHIER)
b.check(r3 is not None and r3.accession == ACC_FDA,
        f"§3 plusieurs faits non tranchés : le PREMIER est retenu (→ {r3.accession if r3 else None})")
RECLASSE = Classement(archetype="rentable", motif="reclassée", effective_from=date(2026, 10, 18),
                      piece_id=944, auteur="gérant", declencheur_accession=ACC_FDA)
b.check(recommandation_de_classement(RECLASSE, ULTERIEUR, FICHIER) is None,
        "§3 un émetteur déjà « commercial » ne reçoit aucune recommandation")
b.check(recommandation_de_classement(None, NOTES, FICHIER) is None,
        "§3 un émetteur NON classé ne reçoit pas de recommandation (son manque est d'être classé)")
b.check(recommandation_de_classement(ORIGINE, {ACC_FDA: QualificationLue(
            types=frozenset({"changement_de_stade"}), resume="x", date_evenement=None)}, FICHIER) is None,
        "§3 une note sans date d'événement ne recommande rien (aucun fait datable)")

# ══ §4 LE GESTE ════════════════════════════════════════════════════════════════════════════════
print("[4] le geste du comité")
FDA = MaterialEvent(form="8-K", event_date=date(2026, 8, 26), filing_date=date(2026, 8, 26),
                    items=("8.01",), accession=ACC_FDA)
ANCRE = MaterialEventLookup(status="found", event=FDA, cik=1858848, recents=(FDA,))
ecrit: list = []
_vrais = (CL.read_classement, CL.persist_archetype)


def geste(*, courant=ORIGINE, lecture=Lecture(accession=ACC_FDA, entry_id=944), archetype="rentable",
          accession=ACC_FDA, ancre=ANCRE, jour=date(2026, 10, 18)):
    import app.knowledge.lecture_depot as LD

    async def _lire(conn, *, ticker_id, a_la_date=None):
        return courant

    async def _ecrire(conn, **kw):
        ecrit.append(kw)
        return 7

    async def _lectures(conn, ticker_id, cik, events):
        return [lecture]

    vrai_ld = LD.assurer_lectures
    CL.read_classement, CL.persist_archetype, LD.assurer_lectures = _lire, _ecrire, _lectures
    try:
        return asyncio.run(CL.decider_classement(
            None, ticker_id="RVMD", archetype=archetype, accession=accession, motif=" premier produit ",
            auteur=" gérant ", fichier=FICHIER, ancre=ancre, aujourd_hui=jour))
    finally:
        CL.read_classement, CL.persist_archetype = _vrais
        LD.assurer_lectures = vrai_ld


b.check(geste() == 7 and ecrit and ecrit[-1]["piece_id"] == 944 and ecrit[-1]["auteur"] == "gérant"
        and ecrit[-1]["declencheur_accession"] == ACC_FDA and ecrit[-1]["archetype"] == "rentable"
        and ecrit[-1]["effective_from"] == date(2026, 10, 18) and ecrit[-1]["motif"] == "premier produit",
        f"§4 reclasser écrit la pièce, l'auteur, le dépôt, et prend effet le jour du geste (→ {ecrit[-1] if ecrit else None})")
b.check(geste(archetype="pre_revenus") == 7 and ecrit[-1]["archetype"] == "pre_revenus"
        and ecrit[-1]["piece_id"] == 944,
        "§4 maintenir est le même geste, avec le même archétype — signé et adossé au dépôt")
n_avant = len(ecrit)
refuse(lambda: geste(archetype="licorne"), "n'est pas un classement déclaré",
       "§4 un archétype inconnu est refusé")
refuse(lambda: geste(accession="0000000000-00-000000"), "n'est pas dans le fil EDGAR",
       "§4 un dépôt absent du fil de l'émetteur est refusé")
refuse(lambda: geste(courant=MAINTENU), "même jour",
       "§4 une seconde décision le même jour est refusée (elle réécrirait la première)")
refuse(lambda: geste(lecture=Lecture(accession=ACC_FDA, motif="EDGAR injoignable")),
       "n'a pas pu être versée", "§4 sans lecture du dépôt, pas de décision (aucune pièce à joindre)")
refuse(lambda: geste(jour=date(2026, 8, 1)), "dans le futur",
       "§4 un dépôt postérieur au jour du geste est refusé")
b.check(len(ecrit) == n_avant, "§4 un refus n'écrit RIEN")

# ══ §5 LE NIVEAU 1 ═════════════════════════════════════════════════════════════════════════════
print("[5] le niveau 1")


def etat(*, classement=ORIGINE, recommandation=None):
    vide = {f.id: frozenset() for f in FICHIER.frameworks}
    return EtatDossier(ticker_id="RVMD", fichier=FICHIER, archetype=classement.archetype, reponses=[],
                       pieces={}, applicables=dict(vide), dispenses=dict(vide), mandats_ouverts={},
                       collecte={}, genere_le=T0, classement=classement, recommandation=recommandation)


e_ok = etat()
n_ok = dresser_niveau1(e_ok, memo_de_l_etat(e_ok, genere_le=T0))
b.check(n_ok.peut_on_decider.etat == "dossier_complet",
        f"§5 témoin : sans recommandation, rien d'applicable en souffrance → complet ({n_ok.peut_on_decider.etat})")
e_r = etat(recommandation=r)
n_r = dresser_niveau1(e_r, memo_de_l_etat(e_r, genere_le=T0))
b.check(n_r.peut_on_decider.etat == "non_revalidable" and "26/08/2026" in n_r.peut_on_decider.motif
        and "reclasser ou maintenir" in n_r.peut_on_decider.motif,
        f"§5 une recommandation en suspens empêche « dossier complet » (→ {n_r.peut_on_decider.etat})")
b.check(n_r.reclassement_recommande is not None and n_r.reclassement_recommande.accession == ACC_FDA
        and n_r.reclassement_recommande.vers == "rentable"
        and n_r.classement is not None and n_r.classement.depuis == date(2026, 9, 24),
        "§5 le classement et la recommandation sont SERVIS au niveau 1")
e_d = etat(classement=RECLASSE)
n_d = dresser_niveau1(e_d, memo_de_l_etat(e_d, genere_le=T0))
b.check(n_d.classement.piece_id == 944 and n_d.classement.auteur == "gérant"
        and n_d.classement.declencheur_accession == ACC_FDA and n_d.reclassement_recommande is None,
        "§5 une décision du comité est servie avec sa pièce, son auteur et son dépôt")

ECRAN = Path("/frontend/components/v2/ClassementEmetteur.js")
N1 = Path("/frontend/components/v2/DossierComite.js")
if not ECRAN.exists() or not N1.exists():
    b.check(False, f"§5 écrans absents ({ECRAN}) — section non mesurée (montage /frontend manquant ?)")
else:
    src = ECRAN.read_text(encoding="utf-8")
    b.check("<ClassementEmetteur d={d} onRecalcule={setD} />" in N1.read_text(encoding="utf-8"),
            "§5 le niveau 1 monte le bloc du classement")
    for champ in ("c.archetype", "c.depuis", "c.motif", "c.auteur", "c.declencheur_accession", "c.piece_id",
                  "r.vers", "r.de", "r.fait_du", "r.accession", "r.type_id", "r.resume"):
        b.check(champ in src, f"§5 l'écran rend `{champ}` (chaque champ servi a son pixel)")
    b.check("/classement`" in src and "geste === 'reclasser' ? r.vers : r.de" in src,
            "§5 l'écran envoie reclasser (vers) ou maintenir (de) au geste du comité")

sys.exit(b.summary())
