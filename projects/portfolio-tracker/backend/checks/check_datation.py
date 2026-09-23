"""Vérification de la DATATION d'une pièce — deux dates nommées, `source_date` dérivée (#79).

Sans réseau ni modèle, sauf §7 qui a besoin de la base (montage explicite) — les six premières
sections gardent la RÈGLE, la septième vérifie l'ÉTAT persisté, qui est l'autre moitié du travail
(#43 : un correctif d'écriture ne se juge pas sur son diff mais sur le comptage par clef).

  • §1  VOCABULAIRE FERMÉ — `constatee` / `prospective` / `indatable`, chaque valeur ATTEIGNABLE
        (#32), aucun état par défaut, et le parcours est GÉNÉRÉ depuis `PORTEES` : retirer un jeton
        retire son propre assert serait le 4ᵉ faux-vert, donc la cardinalité est exigée d'abord.
  • §2  LA DÉRIVATION — `constatee` → date du FAIT ; `prospective` → date du DOCUMENT (l'annonce) ;
        `indatable` → NULL. C'est la règle métier que le fonds a arbitrée le 2026-09-23 : « la
        mesure retenue est celle du dernier FAIT, pas du dernier papier reçu ».
  • §3  LES GARDES SONT DÉCIDABLES — chacune éprouvée SEULE, et sur son propre message. Une garde
        qui échoue sans dire laquelle laisse une mutation rougir pour la mauvaise raison
        (`feedback_test_negatif_trois_faux_verts`).
  • §4  LA FORME, PAS LA SÉVÉRITÉ (#68) — l'assert central du lot. Il ne vérifie pas qu'on DÉTECTE
        une mauvaise datation : il vérifie qu'on ne peut plus l'ÉCRIRE. Une garde vérifie la
        structure, jamais le sens, et deux dates sont structurellement indiscernables.
  • §5  DÉTENTEUR UNIQUE (#46) — `store_knowledge` n'accepte PLUS `source_date=` (signature
        inspectée, pas grepée), et aucun producteur ne la pose. La règle a un seul domicile.
  • §6  LES CAS RÉELS QUI ONT MOTIVÉ LE LOT — #307, #309 et #296 rejoués sur leurs valeurs MESURÉES
        en base le 2026-09-23. C'est l'ancre NON CIRCULAIRE : ces nombres ne sortent pas du code
        testé, ils sortent du corpus, et c'est ce qui empêche le check de se contenter lui-même
        (`feedback_fixture_copiee_du_reel`).
  • §7  ÉTAT PERSISTÉ (optionnel, `CHECK_DB_URL`) — les contraintes SQL existent, aucune ligne ne
        les viole, et toute ligne écrite APRÈS la 045 porte sa portée. Les lignes antérieures sont
        `portee_temporelle IS NULL` : un constat d'héritage à re-collecter, dénombré et NOMMÉ, pas
        toléré en silence.

Hors ligne :
    docker run --rm --network none -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app \
      --env-file checks/env.checks $IMG python checks/check_datation.py
Avec l'état persisté (§7) :
    docker run --rm --network coolify -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app \
      --env-file checks/env.checks --env-file .env $IMG python checks/check_datation.py
"""
import ast
import asyncio
import inspect
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _harness import Bilan, imports_symbol  # noqa: E402

from app.contracts.worker_delegation_schema import ProducedEntry  # noqa: E402
from app.knowledge.datation import (  # noqa: E402
    PORTEES,
    Datation,
    DatationInvalide,
    constatee,
    indatable,
    prospective,
)
from app.knowledge.service import store_knowledge  # noqa: E402

b = Bilan()

# Les dates de référence sont celles du 10-Q de RVMD réellement déposé — pas des dates rondes
# inventées. Une fixture plus commode que la prod est un check aveugle au vert.
FAIT = date(2026, 6, 30)      # le bilan que la pièce décrit
DEPOT = date(2026, 8, 5)      # le 10-Q qui le rapporte, accession 0001193125-26-335104
CLASSEMENT = date(2026, 9, 1)  # la date que #296 portait, et qui n'est NI l'un NI l'autre


def refus(**kw) -> str:
    """Rend le message du refus, ou '' si la construction a été ACCEPTÉE. Rendre le message et non
    un booléen permet d'asserter QUELLE garde a mordu — un booléen laisserait une mutation rougir
    sur la mauvaise règle (6ᵉ faux-vert)."""
    try:
        Datation(**kw)
    except DatationInvalide as e:
        return str(e)
    return ""


def date_de(**kw):
    """La `source_date` DÉRIVÉE, ou la chaîne `REFUSÉ : …` si la construction est refusée.

    §2 juge une dérivation, pas une validité — mais si une garde devenait trop sévère, construire
    l'objet lèverait, et le script mourrait AVANT son bilan : un échec qui ne se compte pas
    (`feedback_bilan_par_sa_forme`). Un refus inattendu doit apparaître comme un FAIL NOMMÉ, au
    même titre qu'une date fausse. Mesuré : `negatif_datation.sh` mutation 15 tuait le script ici.
    """
    try:
        return Datation(**kw).source_date()
    except DatationInvalide as e:
        return f"REFUSÉ : {e}"


# ─────────────────────────────────────────────────────────────────────────────
print("\n1. LE VOCABULAIRE EST FERMÉ, ET CHAQUE VALEUR EST ATTEIGNABLE")

b.require(PORTEES, 3, "le vocabulaire des portées")
b.check(PORTEES == {"constatee", "prospective", "indatable"},
        f"les trois jetons attendus — obtenu {sorted(PORTEES)}")

# Le parcours est généré depuis le vocabulaire : un jeton ajouté sans constructeur rougit ici.
_CONSTRUCTIBLE = {
    "constatee": lambda: constatee(date_du_fait=FAIT, date_du_document=DEPOT),
    "prospective": lambda: prospective(date_du_document=DEPOT, periode_visee=date(2026, 12, 31)),
    "indatable": lambda: indatable(motif="description du modèle d'affaires, sans date"),
}
b.require(set(_CONSTRUCTIBLE), 3, "chaque portée a un cas constructible")
b.check(set(_CONSTRUCTIBLE) == PORTEES,
        "aucune portée du vocabulaire n'est un mot mort (#32)")
for _p, _mk in _CONSTRUCTIBLE.items():
    b.check(_mk().portee == _p, f"`{_p}` est réellement atteignable")

b.check(refus(portee="probablement_constatee", date_du_fait=FAIT, date_du_document=DEPOT) != "",
        "un quatrième état n'existe pas")
b.check(refus(portee="", date_du_fait=FAIT, date_du_document=DEPOT) != "",
        "une portée vide n'est pas un défaut silencieux")
b.check("hors vocabulaire fermé" in refus(portee="inconnue", date_du_document=DEPOT),
        "le refus NOMME que le jeton est hors vocabulaire")

# ─────────────────────────────────────────────────────────────────────────────
print("\n2. LA DÉRIVATION — la mesure retenue est celle du dernier FAIT, pas du dernier papier")

b.check(constatee(date_du_fait=FAIT, date_du_document=DEPOT).source_date() == FAIT,
        "un constat fait foi à la date du FAIT (2026-06-30), pas du dépôt (2026-08-05)")
b.check(prospective(date_du_document=DEPOT, periode_visee=date(2026, 12, 31)).source_date() == DEPOT,
        "une prévision fait foi à la date de son ANNONCE")
b.check(indatable(motif="cadre réglementaire stable").source_date() is None,
        "une pièce indatable n'a PAS de date de tri")
# ⚠️ LE CAS QUI COMPTE, et qui manquait : une indatable qui NOMME son document. Le nommer est
# légitime (§3 l'asserte : c'est la traçabilité) — en DÉRIVER une date ne l'est pas. Sans cet
# assert, `source_date()` pouvait rendre `date_du_document` pour une indatable sans que rien ne
# rougisse : la page « gouvernance » re-servie chaque trimestre aurait gagné l'élection de
# fraîcheur contre un fait mesuré. Trou trouvé PAR `negatif_datation.sh` (mutation 5), qui est
# resté VERT jusqu'à cette ligne — un assert écrit sur le cas commode est aveugle au cas réel.
b.check(date_de(portee="indatable", motif="page gouvernance, aucune date de fait affirmée",
                date_du_document=DEPOT) is None,
        "…même quand elle NOMME le document d'où elle vient, son tri reste NULL")

# L'arbitrage du fonds, rejoué : deux pièces qui décrivent le MÊME instant s'égalisent, et c'est
# le départage aval (`dossier._rang`) qui tranche — pas une date de page.
_narratif = constatee(date_du_fait=FAIT, date_du_document=DEPOT)
_xbrl = constatee(date_du_fait=FAIT, date_du_document=DEPOT)
b.check(_narratif.source_date() == _xbrl.source_date(),
        "deux lectures du même bilan cessent de s'ordonner par le canal qui les a apportées")

# Le cas #309 : la colonne comparative. Le fait est d'il y a un an, le papier est d'hier.
_comparatif = constatee(date_du_fait=date(2025, 6, 30), date_du_document=DEPOT)
b.check(_comparatif.source_date() == date(2025, 6, 30),
        "un comparatif cesse de porter le tampon le plus frais du dossier")
b.check(_comparatif.source_date() < _narratif.source_date(),
        "et il passe DERRIÈRE le fait de l'exercice courant")

# ─────────────────────────────────────────────────────────────────────────────
print("\n3. LES GARDES SONT DÉCIDABLES, ET CHACUNE DIT LAQUELLE A MORDU")

_CAS_REFUSES = [
    ("constatee sans date du fait",
     dict(portee="constatee", date_du_document=DEPOT), "exige `date_du_fait`"),
    ("constatee sans date du document",
     dict(portee="constatee", date_du_fait=FAIT), "exige `date_du_document`"),
    ("constatee dont le fait est POSTÉRIEUR au document",
     dict(portee="constatee", date_du_fait=DEPOT, date_du_document=FAIT), "POSTÉRIEURE"),
    ("constatee qui porte une période visée",
     dict(portee="constatee", date_du_fait=FAIT, date_du_document=DEPOT,
          periode_visee=date(2027, 12, 31)), "ne porte pas `periode_visee`"),
    ("prospective sans période visée",
     dict(portee="prospective", date_du_document=DEPOT), "exige `periode_visee`"),
    ("prospective sans date d'annonce",
     dict(portee="prospective", periode_visee=date(2027, 12, 31)), "exige `date_du_document`"),
    ("prospective dont la période est DÉJÀ CLOSE à l'annonce",
     dict(portee="prospective", date_du_document=DEPOT, periode_visee=FAIT),
     "n'est pas postérieure"),
    ("prospective qui porte déjà un fait",
     dict(portee="prospective", date_du_document=DEPOT, periode_visee=date(2027, 12, 31),
          date_du_fait=FAIT), "ne porte pas `date_du_fait`"),
    ("indatable qui porte quand même un fait",
     dict(portee="indatable", date_du_fait=FAIT, motif="x"), "ne porte ni"),
    ("indatable sans motif",
     dict(portee="indatable"), "exige un `motif`"),
    ("indatable au motif vide",
     dict(portee="indatable", motif="   "), "exige un `motif`"),
]
b.require(_CAS_REFUSES, 11, "les refus décidables énumérés")
for _label, _kw, _attendu in _CAS_REFUSES:
    _msg = refus(**_kw)
    b.check(_msg != "", f"REFUSÉ : {_label}")
    b.check(_attendu in _msg, f"…et le refus nomme sa règle ({_attendu!r}) — obtenu {_msg[:70]!r}")

# Le miroir : les cas LÉGITIMES passent. Sans lui, une garde qui refuserait TOUT serait verte.
b.check(refus(portee="constatee", date_du_fait=DEPOT, date_du_document=DEPOT) == "",
        "un 8-K déposé le jour de l'événement est ACCEPTÉ (fait = document)")
b.check(refus(portee="indatable", motif="modèle d'affaires", date_du_document=DEPOT) == "",
        "une pièce indatable PEUT nommer son document")

# ─────────────────────────────────────────────────────────────────────────────
print("\n4. LA CONFUSION EST INEXPRIMABLE — c'est la FORME qui a changé, pas la sévérité (#68)")

# #307 tel qu'il est en base : « Au 2026-06-30 », trié au 2026-08-05. Sous le nouveau contrat il
# n'existe AUCUNE combinaison qui produise ce résultat en déclarant le fait au 2026-06-30.
b.check(constatee(date_du_fait=FAIT, date_du_document=DEPOT).source_date() != DEPOT,
        "on ne peut plus déclarer un fait au 2026-06-30 et le faire trier au 2026-08-05")
# Le seul moyen de faire trier au 2026-08-05 est de DÉCLARER que le fait est du 2026-08-05 —
# c'est-à-dire d'écrire un mensonge explicite, contredit par la prose de la pièce, au lieu d'un
# tampon tacite que rien ne contredisait.
b.check(constatee(date_du_fait=DEPOT, date_du_document=DEPOT).source_date() == DEPOT,
        "…il faudrait AFFIRMER que le fait date du dépôt, ce qui est une assertion contestable")

# #296 : une date qui n'est NI le fait NI le document n'a plus de case où se loger.
b.check(all(d.source_date() != CLASSEMENT for d in (
            constatee(date_du_fait=FAIT, date_du_document=DEPOT),
            prospective(date_du_document=DEPOT, periode_visee=date(2027, 12, 31)),
            indatable(motif="x"))),
        "une date de CLASSEMENT (2026-09-01) ne peut plus sortir d'aucune portée")

# Et le modèle ne peut pas contourner par le contrat : `source_date` n'est plus une clef admise.
b.check("source_date" not in ProducedEntry.model_fields,
        "le contrat d'entry produite n'a PLUS de champ `source_date`")
for _c in ("portee_temporelle", "date_du_fait", "date_du_document", "periode_visee"):
    b.check(_c in ProducedEntry.model_fields, f"…et il porte `{_c}`")
b.check(ProducedEntry.model_config.get("extra") == "forbid",
        "le contrat REJETTE une clef inconnue (un `source_date` résiduel ne serait pas ignoré, #54)")
b.check(ProducedEntry.model_fields["portee_temporelle"].is_required(),
        "la portée est OBLIGATOIRE : pas d'entry sans datation déclarée")

# ─────────────────────────────────────────────────────────────────────────────
print("\n5. DÉTENTEUR UNIQUE — la règle n'a qu'un domicile (#46)")

_sig = inspect.signature(store_knowledge).parameters
b.check("source_date" not in _sig,
        "`store_knowledge` n'accepte PLUS `source_date=` (signature, pas grep)")
b.check("datation" in _sig, "…il exige `datation`")
b.check(_sig["datation"].default is inspect.Parameter.empty,
        "…sans valeur par défaut : une entry non datée ne peut pas entrer par omission")

# ⚠️ Un grep `"source_date=" not in src` serait un FAUX ROUGE : `compute_reliability(...,
# source_date=...)` est un appel LÉGITIME, et la datation n'y change rien. L'interdit ne porte pas
# sur le jeton mais sur la RELATION « cet argument va à ce destinataire » — donc il se lit dans
# l'AST, pas dans le texte (`feedback_faux_rouge_se_creuse` : chercher pourquoi ça rougit avant de
# corriger l'outil).
def _kwargs_de(src: str, fonction: str) -> set[str]:
    """Les noms d'arguments nommés passés à `fonction` n'importe où dans le module."""
    noms: set[str] = set()
    for node in ast.walk(ast.parse(src)):
        if not isinstance(node, ast.Call):
            continue
        cible = node.func
        nom = cible.attr if isinstance(cible, ast.Attribute) else getattr(cible, "id", None)
        if nom == fonction:
            noms |= {k.arg for k in node.keywords if k.arg}
    return noms


_RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ⚠️ LA LISTE DES PRODUCTEURS SE DÉCOUVRE, ELLE NE SE RETAPE PAS. La première version énumérait
# SIX fichiers à la main — il y en avait NEUF. `curator.py`, `base_rate_corpus.py` et
# `synthesis_feed.py` appelaient `store_knowledge` sans `datation=`, donc plantaient au premier
# appel réel, et le check était VERT : il ne les regardait pas. Un recensement par nom qui ne
# couvre qu'une partie du corpus refait le bug en `verdict=ok`
# (`feedback_adressage_par_nom_exige_lecture`). Les appelants sont donc LUS dans l'arbre des
# sources, et la liste attendue ci-dessous n'est qu'un ACCUSÉ DE RÉCEPTION : tout écart — un
# producteur neuf comme un producteur disparu — rougit et exige une décision explicite sur sa
# datation, au lieu de passer inaperçu.
_DEFINIT = "app/knowledge/service.py"   # le guichet lui-même : il DÉFINIT `store_knowledge`


def _appelants_de_store_knowledge() -> set[str]:
    trouves: set[str] = set()
    for base, _, fichiers in os.walk(os.path.join(_RACINE, "app")):
        for nom in fichiers:
            if not nom.endswith(".py"):
                continue
            chemin = os.path.join(base, nom)
            rel = os.path.relpath(chemin, _RACINE)
            if rel == _DEFINIT:
                continue
            if _kwargs_de(open(chemin, encoding="utf-8").read(), "store_knowledge"):
                trouves.add(rel)
    return trouves


_RECENSES = {
    "app/knowledge/edgar_feed.py",        # socle XBRL — constat, daté du fait
    "app/knowledge/financials_feed.py",   # ratios dérivés du socle
    "app/knowledge/valuation_feed.py",
    "app/knowledge/appariement_feed.py",
    "app/knowledge/base_rate_corpus.py",  # corpus `indatable` + ancre, note du jour
    "app/knowledge/synthesis_feed.py",    # note du jour (arbitrage 2026-09-23)
    "app/agents/v2/worker.py",            # datation DÉCLARÉE par le modèle, validée au contrat
    "app/agents/v2/curator.py",           # context pack — note du jour
    "app/agents/v2/exit.py",
}
_PRODUCTEURS = _appelants_de_store_knowledge()
b.require(_PRODUCTEURS, 9, "les appelants de `store_knowledge` LUS dans les sources")
b.check(_PRODUCTEURS == _RECENSES,
        f"tout appelant du guichet est RECENSÉ — non recensés : {sorted(_PRODUCTEURS - _RECENSES)} "
        f"· recensés mais disparus : {sorted(_RECENSES - _PRODUCTEURS)}")
# Le parcours porte sur les DÉCOUVERTS, jamais sur les recensés : un producteur neuf doit être
# JUGÉ par les asserts suivants, pas seulement signalé par celui du dessus.
for _f in sorted(_PRODUCTEURS):
    _chemin = os.path.join(_RACINE, _f)
    _kw = _kwargs_de(open(_chemin, encoding="utf-8").read(), "store_knowledge")
    # ⚠️ Plus d'assert « {_f} appelle bien `store_knowledge` » ici : depuis que la liste est
    # DÉCOUVERTE, `_kw` est non vide par construction — l'assert serait une tautologie, et une
    # garde qu'aucune mutation ne peut atteindre est le 6ᵉ faux-vert. Ce qu'il protégeait (juger
    # sur un ensemble vide) est tenu en amont par `require(…, 9)` et par le recensement : un
    # producteur qui cesserait d'appeler le guichet sort de la découverte et rougit là-haut.
    b.check("source_date" not in _kw, f"{_f} ne passe plus `source_date=` à `store_knowledge`")
    b.check("datation" in _kw, f"{_f} passe `datation=`")
    # Quel symbole importer dépend du producteur (`constatee`, `indatable`, `Datation`…) : ce qui
    # est exigé est qu'il tienne la règle DU module et n'en recopie pas une variante locale (#46).
    b.check(any(imports_symbol(_chemin, _s, from_module="app.knowledge.datation")
                for _s in ("Datation", "constatee", "prospective", "indatable")),
            f"{_f} importe la règle depuis `app.knowledge.datation` au lieu de la recopier")

# ─────────────────────────────────────────────────────────────────────────────
print("\n6. LES CAS RÉELS DU CORPUS, REJOUÉS (ancre non circulaire)")

# Valeurs RELEVÉES en base le 2026-09-23, avant le lot. Elles ne sortent pas du code testé.
_MESURES = [
    # (id, ce que la prose affirme, ce que la colonne portait, ce que la règle produit)
    (307, FAIT, DEPOT, FAIT),
    (309, date(2025, 6, 30), DEPOT, date(2025, 6, 30)),
    (296, FAIT, CLASSEMENT, FAIT),
    (444, FAIT, FAIT, FAIT),  # le cas DÉJÀ juste : la règle ne doit pas le casser
]
b.require(_MESURES, 4, "les entries mesurées avant le lot")
for _id, _prose, _avant, _attendu in _MESURES:
    _d = constatee(date_du_fait=_prose, date_du_document=max(_prose, DEPOT))
    b.check(_d.source_date() == _attendu,
            f"#{_id} : la règle date au {_attendu} (la colonne portait {_avant})")
_change = [m for m in _MESURES if m[2] != m[3]]
b.check(len(_change) == 3,
        f"la règle CHANGE 3 des 4 cas mesurés — sinon elle ne ferme rien (obtenu {len(_change)})")
b.check(any(m[0] == 444 for m in _MESURES if m[2] == m[3]),
        "…et elle laisse intact le cas qui était déjà juste (#444)")

# ─────────────────────────────────────────────────────────────────────────────
print("\n7. L'ÉTAT PERSISTÉ (base réelle)")

# ⚠️ `CHECK_DB_URL` UNIQUEMENT — jamais `DATABASE_URL`, que `checks/env.checks` renseigne avec une
# URL factice qui RÉSOUT MAL au lieu d'être vide. La lire ferait planter la connexion, et le script
# mourrait AVANT son bilan : un échec qui ne se compte pas (`feedback_bilan_par_sa_forme`).
_DB = os.environ.get("CHECK_DB_URL") or ""
if not _DB:
    # Un pré-requis manquant sort en ÉCHEC, jamais en saut de section : une mesure incomplète
    # écraserait de la vérité (`feedback_check_degrade_en_sortant_a_zero`).
    b.check(False, "CHECK_DB_URL absente — §7 n'a pas mesuré l'état persisté")
else:
    import asyncpg  # noqa: E402

    async def _etat():
        conn = await asyncpg.connect(_DB.replace("postgresql+asyncpg://", "postgresql://"))
        try:
            contraintes = [r["conname"] for r in await conn.fetch(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = 'knowledge_entries'::regclass AND contype = 'c'")]
            cols = [r["column_name"] for r in await conn.fetch(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='knowledge_entries' AND column_name IN "
                "('portee_temporelle','date_du_fait','date_du_document','periode_visee','datation_motif')")]
            incoherentes = await conn.fetchval("""
                SELECT count(*) FROM knowledge_entries WHERE portee_temporelle IS NOT NULL AND NOT (
                    (portee_temporelle='constatee'   AND source_date = date_du_fait)
                 OR (portee_temporelle='prospective' AND source_date = date_du_document)
                 OR (portee_temporelle='indatable'   AND source_date IS NULL))""")
            heritees = await conn.fetchval(
                "SELECT count(*) FROM knowledge_entries "
                "WHERE portee_temporelle IS NULL AND superseded_by IS NULL")
            datees = await conn.fetchval(
                "SELECT count(*) FROM knowledge_entries "
                "WHERE portee_temporelle IS NOT NULL AND superseded_by IS NULL")
            return contraintes, cols, incoherentes, heritees, datees
        finally:
            await conn.close()

    # Une panne de connexion est un ÉCHEC NOMMÉ, pas une exception qui tue le script avant son
    # bilan. C'est #49 en petit : une base injoignable ne doit jamais se lire « rien à signaler ».
    try:
        _cont, _cols, _incoh, _herit, _datees = asyncio.run(_etat())
    except Exception as _e:  # noqa: BLE001
        b.check(False, f"§7 : base injoignable — {type(_e).__name__}: {_e}")
        print(f"\n{'='*60}")
        sys.exit(b.summary())
    b.require(_cols, 5, "les colonnes de la migration 045")
    # Les noms attendus sont LUS DANS LA MIGRATION, jamais recopiés ici (#46) : une contrainte
    # ajoutée au fichier devient exigée sans qu'on touche au check, et une renommée ne peut pas
    # passer inaperçue. ⚠️ La première version filtrait par `LIKE '%datation%'` : elle ne pouvait
    # structurellement pas voir `..._source_date_derivee_check`, dont le nom ne porte aucun de ces
    # motifs — un FAUX ROUGE sur une base parfaitement conforme (`feedback_faux_rouge_se_creuse`).
    _SQL_045 = os.path.join(_RACINE, "app/db/migrations/045_v2_datation_fait_document.sql")
    _attendues = re.findall(r"ADD CONSTRAINT\s+(\w+)", open(_SQL_045, encoding="utf-8").read())
    b.require(_attendues, 3, "les contraintes déclarées par la migration 045")
    for _nom in _attendues:
        b.check(_nom in _cont, f"la contrainte `{_nom}` de la 045 est POSÉE en base")
    b.check(_incoh == 0,
            f"aucune ligne ne contredit sa propre portée — {_incoh} ligne(s) incohérente(s)")
    # L'héritage est DÉNOMBRÉ, pas toléré en silence : c'est la dette que la re-collecte doit
    # résorber, et son chiffre est le seul moyen de savoir si elle avance.
    print(f"  ·    héritage à re-collecter : {_herit} entrée(s) courante(s) sans portée "
          f"· {_datees} déjà datée(s) sous la 045")
    b.check(_herit + _datees > 0, "le corpus courant n'est pas vide (sinon §7 juge sur rien)")

sys.exit(b.summary())
