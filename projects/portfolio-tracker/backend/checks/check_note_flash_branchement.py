"""Le BRANCHEMENT de la note flash au flux (lot 7, arbitrage 2026-09-26, option c) — hors ligne.

La note flash n'avait qu'un appelant : l'outil manuel. Un 8.01 publié demain restait « à qualifier »
(donc rouvrait tout) jusqu'à ce que quelqu'un lance l'outil. Arbitrage : l'analyste lit (a) CHAQUE MATIN
pour tout titre suivi, sous le réglage de dépense automatique, et (b) à CHAQUE PASSAGE DE LA CHAÎNE.

  • §1 RECENSER NE COÛTE RIEN : `ecrire=False` sans aperçu — ni téléchargement, ni modèle, ni écriture ;
       la limite du passage s'applique et l'arriéré au-delà est compté (reporté, pas oublié).
  • §2 UN DÉPÔT NE TAIT PAS LES SUIVANTS : refus du pont, panne inattendue, lecture qui ne rend pas la
       main, doublon concurrent — chacun est un refus NOMMÉ, et le dépôt suivant est lu.
  • §3 HORS FLUX : un titre sans flux EDGAR (Paris, non coté) est dit, rien n'est appelé.
  • §4 LE MATIN, RÉGLAGE COUPÉ : aucun appel modèle ; seuls les dépôts publiés depuis la veille sont
       signalés — l'arriéré connu ne se re-signale pas ; un titre en panne n'arrête pas les suivants.
  • §5 LE MATIN, RÉGLAGE OUVERT : les notes sont écrites et le gérant reçoit types + passage + refus.
  • §6 LES APPELANTS : la chaîne et le bouclage lisent AVANT de charger le dossier ; le job du matin est
       enregistré ; l'outil passe par le même détenteur (#46).

Lancer : `bash checks/run_all.sh` (hors ligne, réseau `none`).
"""
import ast
import asyncio
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Bilan, strip_code  # noqa: E402

import asyncpg  # noqa: E402

import app.agents.v2.note_flash as nf  # noqa: E402
from app.agents.v2.frameworks import load_frameworks  # noqa: E402
from app.knowledge.material_events import MaterialEvent, MaterialEventLookup  # noqa: E402

b = Bilan()
fichier = load_frameworks()
AUJ = date(2026, 9, 26)

# Formes copiées du flux RVMD réel (8.01 FDA du 26/08, 8.01 d'avril, 7.01 seul) ; numéros FICTIFS.
def ev(jour: date, items: tuple[str, ...], n: int) -> MaterialEvent:
    return MaterialEvent(form="8-K", event_date=jour, filing_date=jour, items=items,
                         accession=f"0000000000-26-{n:06d}")

HIER = ev(date(2026, 9, 25), ("8.01",), 925)
FDA = ev(date(2026, 8, 26), ("8.01",), 826)
SEPT = ev(date(2026, 9, 2), ("7.01",), 902)
AVRIL = ev(date(2026, 4, 13), ("8.01",), 413)
RES = ev(date(2026, 8, 5), ("2.02", "9.01"), 805)      # la forme décide : jamais lu
TOUS = (HIER, SEPT, FDA, RES, AVRIL)


class Journal:
    def __init__(self):
        self.telecharges, self.rediges, self.persistes, self.notifs = [], [], [], []


class _Tx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class FauxConn:
    def __init__(self, auto=False, titres=("RVMD",)):
        self.auto, self.titres, self.sql = auto, titres, ""

    def transaction(self):
        return _Tx()

    async def fetchval(self, sql, *a):
        assert "v2_auto_enabled" in sql
        return self.auto

    async def fetch(self, sql, *a):
        assert "FROM tickers" in sql
        self.sql = sql
        return [{"id": t} for t in self.titres]


def monter(j: Journal, *, flux=None, comportement=None, conn=None):
    """Remplace les dépendances RÉSEAU/BASE du module — jamais la règle testée."""
    comportement = comportement or {}

    async def anchor(conn, ticker_id):
        if ticker_id == "PANNE":
            raise RuntimeError("EDGAR a répondu n'importe quoi")
        if flux is not None and ticker_id in flux:
            return flux[ticker_id]
        return MaterialEventLookup(status="found", cik=1_000_001, event=TOUS[0], recents=TOUS)

    async def quals(conn, cik, fichier):
        return {}

    async def identite(conn, ticker_id):
        return SimpleNamespace(raison_sociale=f"Émetteur {ticker_id}", symbole=ticker_id, cik=1_000_001)

    async def telecharger(cik, accession):
        j.telecharges.append(accession)
        return f"<DOCUMENT><TYPE>8-K<FILENAME>x.htm<TEXT>Item 8.01 Other Events. texte {accession}</TEXT></DOCUMENT>"

    async def rediger(event, **kw):
        j.rediges.append(event.accession)
        c = comportement.get(event.accession)
        if c == "refus":
            raise nf.NoteFlashRefusee("passage introuvable dans le texte")
        if c == "panne":
            raise RuntimeError("le fournisseur a coupé")
        if c == "lent":
            await asyncio.sleep(5)
        note = nf.NoteValidee(lisible=True, types=("reglementaire_favorable",), motif=None,
                              elements=[{"type": "reglementaire_favorable",
                                         "passage": f"approved RASONQUE {event.accession}"}])
        return nf.NoteRedigee(ticker_id="RVMD", cik=1_000_001, event=event,
                              catalogue_version=fichier.types_evenement_version, note=note,
                              documents=[], modele="check",
                              runs=[SimpleNamespace(cost_usd=0.0003)])

    async def persister(conn, red):
        if comportement.get(red.event.accession) == "doublon":
            raise asyncpg.UniqueViolationError("notes_flash_une_lecture")
        j.persistes.append(red.event.accession)
        return 500 + len(j.persistes)

    async def agent():
        return SimpleNamespace(model="check")

    class _Session:
        async def __aenter__(self):
            return conn or FauxConn()

        async def __aexit__(self, *a):
            return False

    nf.material_anchor_for_ticker = anchor
    nf.qualifications_de_l_emetteur = quals
    nf.identite_de_l_emetteur = identite
    nf.telecharger_soumission = telecharger
    nf.rediger_note_flash = rediger
    nf.persister_note = persister
    nf._resoudre_agent = agent
    nf._PAUSE_EDGAR_S = 0
    nf.get_db_session = lambda: _Session()


def _vide(ticker="RVMD"):
    return nf.LectureDesDepots(ticker_id=ticker, ecrire=False, depuis=AUJ,
                               catalogue_version=fichier.types_evenement_version)


async def lire(j, **kw):
    """Une exception qui s'échappe du passage est un FAIL NOMMÉ, jamais la mort du script avant son
    bilan : c'est précisément ce que le passage promet de ne jamais faire."""
    try:
        return await nf.lire_les_depots_en_attente(FauxConn(), "RVMD", fichier=fichier,
                                                   depuis=date(2025, 8, 22), **kw)
    except Exception as ex:  # noqa: BLE001
        b.check(False, f"le passage a laissé s'échapper {type(ex).__name__} : {ex}")
        return _vide()


async def matin(today, notifier):
    try:
        return await nf.lecture_du_matin(today, notifier=notifier)
    except Exception as ex:  # noqa: BLE001
        b.check(False, f"le passage du matin a laissé s'échapper {type(ex).__name__} : {ex}")
        return []


async def main():
    # ── §1 recenser ne coûte rien ────────────────────────────────────────────────────────────────
    j = Journal(); monter(j)
    l = await lire(j, ecrire=False, limite=3)
    b.check(l.en_attente == 4, f"§1 4 dépôts à qualifier dans la fenêtre (2.02 exclu) — {l.en_attente}")
    b.require(l.depots, 3, "§1 la limite du passage s'applique")
    b.check([d.event.accession for d in l.depots] == [HIER.accession, SEPT.accession, FDA.accession],
            "§1 du plus récent au plus ancien")
    b.check(l.reportes == 1, f"§1 l'arriéré au-delà de la limite est COMPTÉ reporté — {l.reportes}")
    b.check(not j.telecharges and not j.rediges and not j.persistes,
            f"§1 recensement : 0 téléchargement, 0 modèle, 0 écriture — {j.telecharges} {j.rediges}")
    j = Journal(); monter(j)
    l = await lire(j, ecrire=False, apercu=True, limite=2)
    b.check(len(j.telecharges) == 2 and not j.rediges and not j.persistes,
            "§1 aperçu : télécharge, n'appelle pas le modèle, n'écrit pas")
    b.check(all(d.apercu for d in l.depots), "§1 aperçu : le début du texte est montré")

    # ── §2 un dépôt ne tait pas les suivants ─────────────────────────────────────────────────────
    j = Journal()
    monter(j, comportement={SEPT.accession: "refus", FDA.accession: "panne", AVRIL.accession: "doublon"})
    l = await lire(j, ecrire=True)
    b.check(j.rediges == [HIER.accession, SEPT.accession, FDA.accession, AVRIL.accession],
            f"§2 les 4 dépôts sont lus malgré refus et panne — {j.rediges}")
    b.check([d.event.accession for d in l.ecrits] == [HIER.accession], "§2 seul le dépôt lu proprement est écrit")
    refus = {d.event.accession: d.refus for d in l.refus}
    b.require(refus, 3, "§2 trois refus nommés")
    b.check("NoteFlashRefusee" in (refus.get(SEPT.accession) or ""), "§2 refus du pont nommé")
    b.check("RuntimeError" in (refus.get(FDA.accession) or "") and "lecture par le modèle" in refus[FDA.accession],
            f"§2 panne inattendue nommée avec son étape — {refus.get(FDA.accession)}")
    b.check("concurrent" in (refus.get(AVRIL.accession) or ""), "§2 doublon concurrent : la note existante fait foi")
    b.check(abs(l.cout_usd - 0.0006) < 1e-9, f"§2 le coût des lectures abouties est compté — {l.cout_usd}")
    txt = l.texte()
    b.check("INVENTAIRE — 1 note(s) écrite(s), 3 refus" in txt and "notes_flash #501" in txt,
            "§2 l'inventaire nommé est imprimé")
    j = Journal(); monter(j, comportement={HIER.accession: "lent"})
    ancienne, nf.BORNE_PAR_ETAPE_S = nf.BORNE_PAR_ETAPE_S, 0.05
    try:
        l = await lire(j, ecrire=True, limite=2)
    finally:
        nf.BORNE_PAR_ETAPE_S = ancienne
    b.check(l.refus and "non terminé" in l.refus[0].refus and l.ecrits and l.ecrits[0].event == SEPT,
            "§2 une lecture qui ne rend pas la main est bornée, nommée, et la suivante est lue")

    # ── §3 hors flux ─────────────────────────────────────────────────────────────────────────────
    j = Journal()
    monter(j, flux={"CAP.PA": MaterialEventLookup(status="unavailable", raison="CIK non résolu")})
    l = await nf.lire_les_depots_en_attente(FauxConn(), "CAP.PA", ecrire=True, fichier=fichier)
    b.check(l.hors_flux and "CIK non résolu" in l.hors_flux and not l.depots and not j.rediges,
            "§3 titre hors EDGAR : dit, rien appelé")

    # ── §4 le matin, réglage coupé ───────────────────────────────────────────────────────────────
    j = Journal(); conn = FauxConn(auto=False, titres=("CAP.PA", "PANNE", "RVMD"))
    monter(j, conn=conn, flux={"CAP.PA": MaterialEventLookup(status="unavailable", raison="hors SEC")})

    async def notif(m):
        j.notifs.append(m)
    lectures = await matin(AUJ, notif)
    b.check(not j.rediges and not j.persistes and not j.telecharges,
            "§4 réglage coupé : AUCUN appel modèle, aucun téléchargement, aucune écriture")
    b.require(lectures, 3, "§4 les trois titres suivis sont passés")
    b.check("'portfolio'" in conn.sql and "'watchlist'" in conn.sql,
            "§4 les titres suivis = détenus ET sous surveillance")
    par = {x.ticker_id: x for x in lectures}
    panne = par.get("PANNE", _vide("PANNE"))
    b.check(bool(panne.hors_flux) and "RuntimeError" in panne.hors_flux, "§4 un titre en panne est nommé")
    b.check(par.get("RVMD", _vide()).en_attente == 4, "§4 RVMD, après le titre en panne, est bien recensé")
    b.require(j.notifs, 1, "§4 une notification")
    m = j.notifs[0] if j.notifs else ""
    b.check("2026-09-25" in m and "2026-09-02" not in m,
            "§4 seul le dépôt publié depuis la veille est signalé, pas l'arriéré")
    b.check("rediger_notes_flash.sh RVMD --ecrire" in m and "v2_auto_enabled=FALSE" in m,
            "§4 le signal dit pourquoi il n'est pas lu et comment le lire")
    j = Journal(); monter(j, conn=FauxConn(auto=False))
    await matin(date(2026, 9, 28), notif)
    b.check(not j.notifs, "§4 arriéré seul (rien de neuf depuis la veille) : AUCUNE notification")

    # ── §5 le matin, réglage ouvert ──────────────────────────────────────────────────────────────
    j = Journal(); monter(j, conn=FauxConn(auto=True), comportement={SEPT.accession: "refus"})
    lectures = await matin(AUJ, notif)
    b.check(len(j.persistes) == 3, f"§5 réglage ouvert : les notes sont écrites — {j.persistes}")
    m = j.notifs[0] if j.notifs else ""
    b.check("3 communiqué(s) lu(s), 1 non qualifié(s)" in m and "reglementaire_favorable" in m
            and "rouvre toutes les questions" in m, "§5 le gérant reçoit types, passage et refus")

    # ── §6 les appelants ─────────────────────────────────────────────────────────────────────────
    racine = Path(__file__).resolve().parent.parent
    chaine = strip_code((racine / "tools/executer_chaine.py").read_text())
    b.check("lire_les_depots_en_attente(" in chaine
            and chaine.index("lire_les_depots_en_attente(") < chaine.index("charger_dossier("),
            "§6 la chaîne lit les dépôts AVANT de charger le dossier")
    bouc = strip_code((racine / "app/agents/v2/bouclage.py").read_text())
    b.check("lire_les_depots_en_attente(" in bouc
            and bouc.index("lire_les_depots_en_attente(") < bouc.index("charger_dossier(")
            and bouc.index("if not ouverts") < bouc.index("lire_les_depots_en_attente("),
            "§6 le bouclage lit AVANT le dossier, et seulement s'il y a un renvoi")
    b.check("sur_lecture=" in strip_code((racine / "tools/boucler_renvois.py").read_text()),
            "§6 l'outil de bouclage demande la lecture")
    # Le job se lit sur l'AST : un `add_job` dont le 1er argument EST `_notes_flash_matin`, et une
    # fonction `_notes_flash_matin` qui appelle `lecture_du_matin` — un nom laissé dans une définition
    # jamais planifiée satisferait un grep.
    arbre = ast.parse((racine / "app/main.py").read_text())
    planifies = {c.args[0].id for c in ast.walk(arbre) if isinstance(c, ast.Call)
                 and isinstance(c.func, ast.Attribute) and c.func.attr == "add_job"
                 and c.args and isinstance(c.args[0], ast.Name)}
    job = next((f for f in ast.walk(arbre) if isinstance(f, ast.AsyncFunctionDef)
                and f.name == "_notes_flash_matin"), None)
    appelle = job is not None and any(isinstance(c, ast.Call) and getattr(c.func, "id", None) == "lecture_du_matin"
                                      for c in ast.walk(job))
    b.check("_notes_flash_matin" in planifies and appelle, "§6 le job du matin est planifié et lit")
    outil = strip_code((racine / "tools/rediger_notes_flash.py").read_text())
    b.check("lire_les_depots_en_attente(" in outil and "rediger_note_flash(" not in outil,
            "§6 l'outil passe par le détenteur unique")
    b.check("v2_auto_enabled" in strip_code(Path(nf.__file__).read_text()),
            "§6 la dépense du matin est gardée par le réglage")


asyncio.run(main())
sys.exit(b.summary())
