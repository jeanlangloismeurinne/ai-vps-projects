"""Module M2 « Collecte de sources » sur des sociétés FICTIVES — aucune base, aucun réseau, aucun
modèle, aucune dépense. C'est la part « société fictive » de l'acceptation écrite avant la
construction (`roadmap/V3/M2-collecte-sources.md` §2) ; chaque section porte le numéro de la ligne
qu'elle prouve, et `negatif_recueil.sh` prouve que chacune vire au rouge.

  [B0]  le cœur n'importe ni réseau ni modèle : seul `adaptateurs/transport.py` touche le réseau
  [B1]  le cœur ne nomme aucun formulaire (ceux des référentiels des adaptateurs, lus ici) ; un
        registre de plus = un adaptateur de plus, le cœur ne change pas
  [B2]  sans numéro au registre, non cotée, ou sans fiche : jamais une exception, toujours un
        document ou une indisponibilité nommée ; sans fiche, le chef de dossier attend l'acte
  [B3]  récemment introduite : le prospectus tient lieu de comptes annuels, et l'origine le dit ;
        jamais un trimestre ; dès qu'un rapport annuel existe, c'est lui
  [B4]  gardé brut, rangé une fois (empreinte) ; un amendement cite le document qu'il amende
  [B5]  chaque document dit d'où il vient et ce que M1 en dit ; non admis = marqué non admis
  [B6]  une source inconnue part à l'évaluateur ; la collecte ne l'attend pas ; au seuil admise,
        dessous en suspens ; un évaluateur qui plante la laisse à évaluer
  [B7]  une page de relations investisseurs d'une AUTRE société, rencontrée, est admise
  [B8]  la collecte est un travail suivi : en cours, le dossier avance à côté ; reprise sans
        recollecter ; un échec est relancé une fois, puis arrête le dossier
  [B9]  la dépense est déclarée au chef de dossier : web et évaluateur ; registre et site à 0
  [B10] la fiche se complète depuis le registre ; votre correction tient ; les lieux ne sont
        jamais touchés ; un homonyme n'est jamais tranché (acte attendu)
  [B11] dans le doute, indisponible : PDF, page vide, registre en erreur deux fois

Les sociétés, numéros et domaines sont inventés (`.example` est réservé) ; les réponses simulées du
registre copient la FORME des réponses réelles (champs relevés sur le registre le 2026-11-16 :
`isForeignLocation` nul pour une société domestique, soumission découpée en <DOCUMENT>).
"""
from __future__ import annotations

import ast
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Bilan, strip_code  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.modules.chef_de_dossier import automate as AU  # noqa: E402
from app.modules.chef_de_dossier import contrat as CD  # noqa: E402
from app.modules.emetteurs import contrat as E  # noqa: E402
from app.modules.recueil import adaptateurs as AD  # noqa: E402
from app.modules.recueil import contrat as R  # noqa: E402

MODULE = BACKEND / "app" / "modules" / "recueil"
JOUR = "2026-11-16"
# La lecture humaine de chaque sortie (D6) est levée pour ces modules : on éprouve la collecte, pas
# l'arrêt de lecture, que le contrôle du chef de dossier garde déjà.
SANS_LECTURE = {"emetteurs": False, "recueil": False, "test": False}
SEC = json.loads((MODULE / "adaptateurs" / "registre_sec.json").read_text(encoding="utf-8"))
URL = SEC["adresses"]


# ── Le monde simulé ─────────────────────────────────────────────────────────────────────────

class Transport:
    """Adresse → réponses successives (la dernière se répète). Compte les lectures par adresse."""

    def __init__(self, pages: dict[str, list[AD.Lu] | AD.Lu]) -> None:
        self.pages = {k: (v if isinstance(v, list) else [v]) for k, v in pages.items()}
        self.lectures: dict[str, int] = {}
        self.plante_sur: set[str] = set()

    async def lire(self, adresse: str) -> AD.Lu:
        if adresse in self.plante_sur:
            raise RuntimeError(f"coupure simulée sur {adresse}")
        n = self.lectures.get(adresse, 0)
        self.lectures[adresse] = n + 1
        rep = self.pages.get(adresse)
        if rep is None:
            return AD.Lu(404)
        return rep[min(n, len(rep) - 1)]


class Moteur:
    COUT = 0.004

    def __init__(self, resultats: dict[tuple[str, bool], list[AD.Resultat]]) -> None:
        self.resultats = resultats
        self.appels: list[tuple[str, tuple[str, ...]]] = []

    async def rechercher(self, requete, *, domaines=(), depuis="", nombre=5):
        self.appels.append((requete, tuple(domaines)))
        return list(self.resultats.get((requete, bool(domaines)), [])), CD.Depense(web_usd=self.COUT)


class Outils:
    def __init__(self, transport, moteur=None, adaptateurs=None):
        self.transport, self.moteur = transport, moteur
        if adaptateurs is not None:
            self.adaptateurs = adaptateurs


def html(texte: str) -> AD.Lu:
    return AD.Lu(200, f"<html><body>{texte}</body></html>".encode(), "text/html; charset=utf-8")


def js(obj) -> AD.Lu:
    return AD.Lu(200, json.dumps(obj).encode(), "application/json")


def depots(numero: int, nom: str, symbole: str, lignes: list[tuple[str, str, str, str, str]],
           etat: str = "TX", place: str = "Nasdaq") -> AD.Lu:
    """La liste des dépôts, sous la forme réelle du registre. lignes = (formulaire, date de dépôt,
    date des faits, numéro de dépôt, document principal)."""
    cles = ("form", "filingDate", "reportDate", "accessionNumber", "primaryDocument")
    recent = {k: [l[i] for l in lignes] for i, k in enumerate(cles)}
    recent.update({"acceptanceDateTime": ["" for _ in lignes], "size": [1000 for _ in lignes]})
    return js({"cik": f"{numero:010d}", "name": nom, "tickers": [symbole] if symbole else [],
               "exchanges": [place] if symbole else [],
               "addresses": {"business": {"stateOrCountry": etat, "isForeignLocation": None, "country": None}},
               "filings": {"recent": recent, "files": []}})


def u_depots(n):
    return URL["depots"].format(numero10=f"{n:010d}")


def u_doc(n, acc, doc):
    return URL["document"].format(numero=n, dossier=acc.replace("-", ""), document=doc)


def u_soum(n, acc):
    return URL["soumission"].format(numero=n, dossier=acc.replace("-", ""), accession=acc)


def soumission(*blocs: tuple[str, str, bytes]) -> AD.Lu:
    corps = b"<SEC-DOCUMENT>x.txt\n<SEC-HEADER>en-tete</SEC-HEADER>\n"
    for typ, fichier, contenu in blocs:
        corps += (b"<DOCUMENT>\n<TYPE>" + typ.encode() + b"\n<SEQUENCE>1\n<FILENAME>" + fichier.encode()
                  + b"\n<DESCRIPTION>x\n<TEXT>\n" + contenu + b"\n</TEXT>\n</DOCUMENT>\n")
    return AD.Lu(200, corps, "text/plain")


INTRO, ANCIENNE, HOMO_1, HOMO_2 = 9000001, 9000002, 9000003, 9000004
SYMBOLES = js({"fields": ["cik", "name", "ticker", "exchange"], "data": [
    [INTRO, "FICTIVE INTRODUITE CORP", "FINT", "Nasdaq"],
    [ANCIENNE, "FICTIVE ANCIENNE INC", "FANC", "NYSE"],
    [HOMO_1, "HOMONYME HOLDINGS", "HOM1", "Nasdaq"],
    [HOMO_2, "Homonyme Holdings", "HOM2", "OTC"],
]})

DEPOTS_INTRO = [
    ("8-K", "2026-10-20", "2026-10-20", "0009000001-26-000009", "fint-8k.htm"),
    ("10-Q", "2026-10-22", "2026-09-30", "0009000001-26-000008", "fint-q3.htm"),
    ("424B4", "2026-06-12", "", "0009000001-26-000002", "fint-prospectus.htm"),
    ("S-1", "2026-05-20", "", "0009000001-26-000001", "fint-s1.htm"),
]
DEPOTS_ANCIENNE = [
    ("10-K/A", "2026-04-10", "2025-12-31", "0009000002-26-000005", "fanc-10ka.htm"),
    ("10-K", "2026-02-25", "2025-12-31", "0009000002-26-000004", "fanc-10k.htm"),
    ("10-K", "2025-02-26", "2024-12-31", "0009000002-25-000001", "fanc-10k-2024.htm"),
    ("10-Q", "2025-11-05", "2025-09-30", "0009000002-25-000009", "fanc-q3.htm"),
]


def monde() -> dict[str, list[AD.Lu] | AD.Lu]:
    p: dict[str, list[AD.Lu] | AD.Lu] = {URL["symboles"]: SYMBOLES}
    p[u_depots(INTRO)] = depots(INTRO, "FICTIVE INTRODUITE CORP", "FINT", DEPOTS_INTRO)
    p[u_depots(ANCIENNE)] = depots(ANCIENNE, "FICTIVE ANCIENNE INC", "FANC", DEPOTS_ANCIENNE, place="NYSE")
    for forme, _, _, acc, doc in DEPOTS_INTRO:
        p[u_doc(INTRO, acc, doc)] = html(f"{forme} de la société introduite")
    for forme, _, _, acc, doc in DEPOTS_ANCIENNE:
        p[u_doc(ANCIENNE, acc, doc)] = html(f"{forme} {acc} de la société ancienne")
    p[u_soum(INTRO, "0009000001-26-000009")] = soumission(
        ("8-K", "fint-8k.htm", b"<html>formulaire 8-K</html>"),
        ("EX-99.1", "fint-ex991.htm", b"<html>communique de resultats</html>"),
        ("GRAPHIC", "logo.jpg", b"begin 644 logo.jpg"))
    # La société sans registre : son site et le web.
    p["https://ir.fictive-privee.example"] = html(
        '<a href="/ar2025.pdf">Annual Report 2025</a>'
        '<a href="/news/q3.html">Press release: third quarter</a>'
        '<a href="https://ir.partenaire-cote.example/">Our partner</a>'
        '<a href="/pres.html">Investor presentation</a>')
    p["https://ir.fictive-privee.example/ar2025.pdf"] = AD.Lu(200, b"%PDF-1.7 ...", "application/pdf")
    p["https://ir.fictive-privee.example/news/q3.html"] = html("communiqué du troisième trimestre")
    p["https://ir.fictive-privee.example/pres.html"] = html("")
    p["https://fictive-privee.example"] = html("accueil")
    for i in (1, 2, 3):
        p[f"https://blog.inconnu.example/a{i}"] = html(f"article {i} sur la société privée")
    p["https://www.fictive-privee.example/rapport.html"] = html("rapport annuel publié sur le site")
    return p


REQ_ANNUEL = "Société Fictive Privée annual report audited financial statements"
REQ_ANNONCES = "Société Fictive Privée press release announces"
RESULTATS = {
    (REQ_ANNUEL, True): [AD.Resultat("https://www.fictive-privee.example/rapport.html", "rapport", "2026-03-01")],
    (REQ_ANNUEL, False): [AD.Resultat(f"https://blog.inconnu.example/a{i}", "a", "2026-03-0" + str(i)) for i in (1, 2, 3)],
    (REQ_ANNONCES, False): [AD.Resultat("https://blog.inconnu.example/a1", "a", "2026-03-01"),
                            AD.Resultat("https://ir.autre-emetteur.example/news", "concurrent", "2026-03-02")],
}


async def fiches(ed):
    await E.etablir_fiche(ed, "FICTIVE-INTRO", raison_sociale="FINT", auteur=E.UTILISATEUR,
                          motif="ajout à l'écran", le=JOUR)                        # le symbole pour nom
    await E.etablir_fiche(ed, "FICTIVE-ANCIENNE", raison_sociale="Fictive Ancienne Inc", auteur=E.UTILISATEUR,
                          motif="ouverture", le=JOUR, cotations=[("NYSE-FICTIVE", "FANC")],
                          references=[(SEC["reference"], str(ANCIENNE))],
                          lieux=[("site", "fictive-ancienne.example")])
    await E.etablir_fiche(ed, "FICTIVE-PRIVEE", raison_sociale="Société Fictive Privée", auteur=E.UTILISATEUR,
                          motif="non cotée", le=JOUR,
                          lieux=[("relations_investisseurs", "ir.fictive-privee.example"),
                                 ("site", "fictive-privee.example")])
    await E.etablir_fiche(ed, "FICTIVE-HOMO", raison_sociale="Homonyme Holdings", auteur=E.UTILISATEUR,
                          motif="ouverture", le=JOUR)


class Bilan2(Bilan):
    """Le bilan du harnais, avec le détail de l'écart imprimé à côté de l'assert qui rougit."""

    def check(self, condition: bool, label: str, detail: str = "") -> bool:
        return super().check(bool(condition), label + (f" — {detail}" if detail and not condition else ""))


class Plante:
    """Le résultat d'un scénario qui a levé : FAUX partout où on l'interroge, pour que l'assert
    attendu rougisse au lieu que le contrôle meure avant son bilan (2ᵉ faux vert)."""

    def __init__(self, exc: BaseException) -> None:
        object.__setattr__(self, "exc", exc)

    def __getattr__(self, _):
        return self

    def __call__(self, *a, **k):
        return self

    def __bool__(self):
        return False

    def __len__(self):
        return 0

    def __iter__(self):
        return iter(())

    def __getitem__(self, _):
        return self

    def __contains__(self, _):
        return False

    def __eq__(self, _):
        return False

    def __ne__(self, _):
        return True

    __lt__ = __le__ = __gt__ = __ge__ = __eq__
    __hash__ = object.__hash__

    def __repr__(self):
        return f"<scénario planté : {type(self.exc).__name__}: {self.exc}>"


def premier(seq):
    """Le premier élément, ou un résultat FAUX (jamais une IndexError qui tuerait le contrôle)."""
    return seq[0] if seq else Plante(IndexError("aucun élément"))


def run(coro, n: int = 1):
    try:
        return asyncio.run(coro)
    except Exception as exc:  # noqa: BLE001
        print(f"  (scénario planté : {type(exc).__name__}: {exc})")
        p = Plante(exc)
        return p if n == 1 else (p,) * n


def main() -> int:
    b = Bilan2()

    # ── [B0] ni réseau ni modèle hors du transport ──────────────────────────────────────────
    interdits = {"urllib.request", "urllib.error", "http", "socket", "httpx", "requests", "aiohttp", "openai",
                 "anthropic", "asyncpg"}
    fichiers = sorted(p for p in MODULE.rglob("*.py") if "__pycache__" not in p.parts)
    b.check(len(fichiers) >= 6, "[B0] le module a été lu (au moins 6 fichiers Python)")
    fautifs = []
    for f in fichiers:
        for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            mods = [a.name for a in n.names] if isinstance(n, ast.Import) else (
                [n.module or ""] if isinstance(n, ast.ImportFrom) and n.level == 0 else [])
            for m in mods:
                if any(m == i or m.startswith(i + ".") for i in interdits) and f.name != "transport.py":
                    fautifs.append(f"{f.relative_to(BACKEND)} importe {m}")
    b.check(not fautifs, "[B0] seul adaptateurs/transport.py touche le réseau ; aucun modèle importé", "; ".join(fautifs))

    # ── [B1] le cœur ne nomme aucun formulaire ─────────────────────────────────────────────
    formulaires: set[str] = set()
    for j in (MODULE / "adaptateurs").glob("*.json"):
        def rec(x):
            if isinstance(x, dict):
                for k, v in x.items():
                    if k == "formulaires":
                        formulaires.update(v)
                    else:
                        rec(v)
        rec(json.loads(j.read_text(encoding="utf-8")))
    b.check(len(formulaires) >= 8, "[B1] les formulaires des référentiels des adaptateurs ont été lus")
    coeur = strip_code((MODULE / "coeur.py").read_text(encoding="utf-8")) + strip_code(
        (MODULE / "contrat.py").read_text(encoding="utf-8")) + (MODULE / "referentiel.json").read_text(encoding="utf-8")
    nommes = sorted(f for f in formulaires if f in coeur)
    b.check(not nommes, "[B1] le cœur (code et référentiel) ne nomme aucun formulaire", ", ".join(nommes))
    b.check("registre_sec" not in coeur, "[B1] le cœur ne nomme aucun adaptateur particulier")

    class AutreRegistre:
        """Un registre d'un autre pays, ajouté sans toucher au cœur."""
        nom, famille = "autre_registre", AD.REGISTRE

        def sait(self, genre):
            return genre == "derniers_comptes_annuels"

        async def identifier(self, fiche, transport):
            return AD.Identification("inconnue", "registre fictif", detail="société absente")

        async def chercher(self, appel):
            if appel.fiche.emetteur != "FICTIVE-PRIVEE":
                return AD.Trouvaille(raison="non_applicable", detail="hors de ce registre")
            return AD.Trouvaille(trouves=[AD.Trouve(R.Provenance(adaptateur=self.nom, adresse="registre.example/d/1",
                                                                 registre="registre fictif", identifiant="d-1",
                                                                 partie="rapport", publie_le="2026-04-30"),
                                                    b"rapport annuel au registre fictif", "text/plain")])

    async def s_b1():
        ed, rd = E.DepotMemoire(), R.DepotMemoire()
        await fiches(ed)
        t = Transport(monde())
        out = Outils(t, Moteur(RESULTATS), adaptateurs=[*AD.tous(), AutreRegistre()])
        return await R.collecter(R.Demande("derniers_comptes_annuels", "FICTIVE-PRIVEE"), depot=rd,
                                 emetteurs_depot=ed, outils=out, le=JOUR)
    rep = run(s_b1())
    b.check(len(rep.documents) == 1 and rep.documents[0].provenance.adaptateur == "autre_registre",
            "[B1] un registre de plus, injecté, répond avant le site et le web (ordre d'autorité)",
            f"{[d.provenance.adaptateur for d in rep.documents]}")

    # ── [B2] jamais une exception pour une société ────────────────────────────────────────
    async def s_b2():
        ed, rd = E.DepotMemoire(), R.DepotMemoire()
        await fiches(ed)
        out = Outils(Transport(monde()), Moteur(RESULTATS))
        rendus = {}
        for g in json.loads((MODULE / "referentiel.json").read_text(encoding="utf-8"))["genres"]:
            d = R.Demande(g, "FICTIVE-PRIVEE", depuis="2026-01-01" if g != "page_web" else "",
                          adresse="https://ir.fictive-privee.example/news/q3.html" if g == "page_web" else "")
            rendus[g] = await R.collecter(d, depot=rd, emetteurs_depot=ed, outils=out, le=JOUR)
        sans = await R.collecter(R.Demande("derniers_comptes_annuels", "INCONNUE"), depot=rd,
                                 emetteurs_depot=ed, outils=out, le=JOUR)
        return rendus, sans
    rendus, sans = run(s_b2(), n=2)
    b.check(len(rendus) == 7, "[B2] tous les genres du référentiel ont été demandés")
    b.check(all(r.documents or (r.indisponibilite and r.indisponibilite.raison and r.indisponibilite.essais)
                for r in rendus.values()),
            "[B2] sans numéro au registre ni cotation : chaque genre rend des documents ou une indisponibilité nommée")
    b.check(rendus["annonces_importantes"].documents
            and rendus["annonces_importantes"].documents[0].provenance.adaptateur == "site_emetteur",
            "[B2] sans registre, les annonces viennent du site de l'émetteur")
    reg = [e for e in (rendus["comptes_intermediaires"].indisponibilite.essais
                       if rendus["comptes_intermediaires"].indisponibilite else ()) if e[0] == "registre_sec"]
    b.check(bool(reg) and "non_applicable" in reg[0][1],
            "[B2] le registre essayé dit pourquoi il ne s'applique pas", f"{reg}")
    b.check(sans.indisponibilite is not None and sans.indisponibilite.raison == "fiche_absente",
            "[B2] sans fiche : indisponibilité « fiche absente »")

    async def s_b2_chef():
        ed, rd = E.DepotMemoire(), R.DepotMemoire()
        envoi = R.Envoi()
        pas = [E.pas_fiche(None), R.pas_collecte("collecte", [R.Demande("derniers_comptes_annuels", "INCONNUE")],
                                                 await R.vue_travaux(rd, "INCONNUE"), envoi)]   # sans `apres`
        etat = AU.avancer(CD.EtatDossier(dossier="INCONNUE"), pas)
        return etat, envoi
    etat, envoi = run(s_b2_chef(), n=2)
    b.check(etat.arret.motif == CD.ARRET_ACTE_HUMAIN and etat.arret.acte == E.ACTE_ETABLIR_LA_FICHE
            and not envoi.a_lancer,
            "[B2] sans fiche, le chef de dossier attend l'acte et ne lance aucune collecte")

    # ── [B3] le prospectus tient lieu de comptes annuels ─────────────────────────────────
    async def s_b3(avec_rapport: bool):
        ed, rd = E.DepotMemoire(), R.DepotMemoire()
        await fiches(ed)
        p = monde()
        if avec_rapport:
            lignes = [("10-K", "2027-02-20", "2026-12-31", "0009000001-27-000001", "fint-10k.htm")] + DEPOTS_INTRO
            p[u_depots(INTRO)] = depots(INTRO, "FICTIVE INTRODUITE CORP", "FINT", lignes)
            p[u_doc(INTRO, "0009000001-27-000001", "fint-10k.htm")] = html("premier rapport annuel")
        return await R.collecter(R.Demande("derniers_comptes_annuels", "FICTIVE-INTRO"), depot=rd,
                                 emetteurs_depot=ed, outils=Outils(Transport(p)), le=JOUR)
    rep = run(s_b3(False))
    docs = rep.documents
    b.check(len(docs) == 1 and docs[0].provenance.partie == "424B4",
            "[B3] aucun rapport annuel : le prospectus d'introduction est rendu", f"{[d.provenance.partie for d in docs]}")
    b.check(bool(docs) and "prospectus" in docs[0].provenance.mention.lower()
            and "tient lieu" in docs[0].provenance.mention,
            "[B3] l'origine dit que le prospectus tient lieu de comptes annuels")
    b.check(not any(d.provenance.partie == "10-Q" for d in docs), "[B3] jamais un trimestre pour une année")
    rep = run(s_b3(True))
    b.check([d.provenance.partie for d in rep.documents] == ["10-K"] and not rep.documents[0].provenance.mention,
            "[B3] dès qu'un rapport annuel existe, c'est lui, sans mention", f"{[d.provenance.partie for d in rep.documents]}")

    # ── [B4] brut, une fois, amendement cité ─────────────────────────────────────────────
    async def s_b4():
        ed, rd = E.DepotMemoire(), R.DepotMemoire()
        await fiches(ed)
        t = Transport(monde())
        out = Outils(t)
        a = await R.collecter(R.Demande("derniers_comptes_annuels", "FICTIVE-ANCIENNE"), depot=rd,
                              emetteurs_depot=ed, outils=out, le=JOUR)
        b2 = await R.collecter(R.Demande("derniers_comptes_annuels", "FICTIVE-ANCIENNE"), depot=rd,
                               emetteurs_depot=ed, outils=out, le="2026-11-17")
        brut = await R.lire_contenu(rd, a.documents[0].empreinte)
        refus = await rd.ranger_document({"empreinte": a.documents[0].empreinte, "emetteur": "x"}, b"autre")
        return a, b2, brut, refus, rd, t
    a, b2, brut, refus, rd, t = run(s_b4(), n=6)
    parties = [(d.provenance.partie, d.provenance.identifiant, d.provenance.remplace) for d in a.documents]
    b.check(parties == [("10-K", "0009000002-26-000004", ""), ("10-K/A", "0009000002-26-000005", "0009000002-26-000004")],
            "[B4] le dernier rapport annuel, puis son amendement qui cite le document qu'il amende", f"{parties}")
    b.check(brut == html("10-K 0009000002-26-000004 de la société ancienne").contenu,
            "[B4] le contenu rangé est le contenu reçu, octet pour octet")
    b.check([d.empreinte for d in b2.documents] == [d.empreinte for d in a.documents]
            and len(rd._documents) == 2 and refus is False,
            "[B4] collecté deux fois, rangé une fois ; un document rangé ne se réécrit pas")
    b.check(t.lectures.get(u_doc(ANCIENNE, "0009000002-26-000004", "fanc-10k.htm")) == 1,
            "[B4] la seconde collecte ne retélécharge pas ce qui est rangé")

    # ── [B5] origine et qualification ───────────────────────────────────────────────────
    async def s_b5():
        ed, rd = E.DepotMemoire(), R.DepotMemoire()
        await fiches(ed)
        out = Outils(Transport(monde()), Moteur(RESULTATS))
        sans = await R.collecter(R.Demande("comptes_intermediaires", "FICTIVE-ANCIENNE", depuis="2025-01-01"),
                                 depot=rd, emetteurs_depot=ed, outils=out, le=JOUR)
        await E.admettre_source(ed, source="sec.gov", portee=E.PORTEE_GENERALE, natures=["mesure", "evenement"],
                                niveau="A", auteur=E.UTILISATEUR, motif="registre officiel", le=JOUR)
        avec = await R.collecter(R.Demande("annonces_importantes", "FICTIVE-INTRO", depuis="2026-01-01"),
                                 depot=rd, emetteurs_depot=ed, outils=out, le=JOUR)
        web = await R.collecter(R.Demande("derniers_comptes_annuels", "FICTIVE-PRIVEE"), depot=rd,
                                emetteurs_depot=ed, outils=out, le=JOUR)
        return sans, avec, web
    sans, avec, web = run(s_b5(), n=3)
    d0 = premier(sans.documents)
    b.check(d0.provenance.adresse.startswith("https://") and d0.provenance.publie_le == "2025-11-05"
            and d0.provenance.faits_au == "2025-09-30" and d0.provenance.registre and len(d0.empreinte) == 64,
            "[B5] un document dit son adresse, son registre, ses deux dates, son empreinte")
    b.check(not d0.qualification.admise and "aucune admission" in d0.qualification.motif,
            "[B5] une source non admise est gardée et marquée non admise, avec le motif de M1")
    b.check(all(d.qualification.admise and d.qualification.niveau == "A" for d in avec.documents)
            and {d.provenance.partie.split()[0] for d in avec.documents} == {"8-K", "EX-99.1"},
            "[B5] admise : la qualification de M1 au jour de la collecte ; le communiqué joint est rangé",
            f"{[(d.provenance.partie, d.qualification.admise) for d in avec.documents]}")
    b.check(not any("GRAPHIC" in d.provenance.partie for d in avec.documents),
            "[B5] seules les pièces que le référentiel nomme sont rangées")
    b.check(web.documents and web.documents[0].provenance.adaptateur == "web"
            and web.documents[0].qualification.admise,
            "[B5] le site de l'émetteur trouvé par le web est qualifié comme sa publication (domaines de la fiche d'abord)")

    # ── [B6] l'évaluateur ────────────────────────────────────────────────────────────────
    questions = list(json.loads((BACKEND / "app/modules/emetteurs/referentiel.json").read_text())
                     ["evaluation_des_sources"]["questions"])

    def evaluateur(oui: bool, plante: bool = False, cout: float = 0.02):
        async def ev(source, adresses):
            if plante:
                raise RuntimeError("modèle indisponible")
            pubs = tuple(E.ExempleEvalue(f"https://{source}/p{i}", tuple(
                E.Reponse(q, oui or i > 0, "constaté") for q in questions)) for i in range(3))
            return (E.Evaluation(source=source, portee=E.PORTEE_GENERALE, natures=("interpretation",),
                                 niveau="B", critere="presse_financiere", exemples=pubs), CD.Depense(modeles_usd=cout))
        return ev

    async def s_b6(oui, plante=False):
        ed, rd = E.DepotMemoire(), R.DepotMemoire()
        await fiches(ed)
        out = Outils(Transport(monde()), Moteur({(REQ_ANNUEL, False): RESULTATS[(REQ_ANNUEL, False)]}))
        rep = await R.collecter(R.Demande("derniers_comptes_annuels", "FICTIVE-PRIVEE"), depot=rd,
                                emetteurs_depot=ed, outils=out, le=JOUR)
        avant = [dict(s) for s in await rd.sources_rencontrees()]
        lignes = await R.evaluer_les_sources_rencontrees(depot=rd, emetteurs_depot=ed,
                                                         evaluateur=evaluateur(oui, plante), le=JOUR)
        fiche = await E.lire_fiche(ed, "FICTIVE-PRIVEE")
        if not plante:
            lignes.append({"second_passage": await R.evaluer_les_sources_rencontrees(
                depot=rd, emetteurs_depot=ed, evaluateur=evaluateur(oui), le=JOUR)})
        return rep, avant, lignes, fiche, [dict(s) for s in await rd.sources_rencontrees()]
    rep, avant, lignes, fiche, apres = run(s_b6(True), n=5)
    b.check(len(rep.documents) == 3 and all(not d.qualification.admise for d in rep.documents),
            "[B6] la collecte rend les documents de la source inconnue sans attendre son évaluation")
    b.check([(s["source"], s["statut"], len(s["adresses"])) for s in avant] == [("blog.inconnu.example", "a_evaluer", 3)],
            "[B6] la source inconnue est notée à évaluer, avec les publications rencontrées", f"{avant}")
    b.check(premier(lignes).get("issue") == "admise" and any(s.source == "blog.inconnu.example" for s in fiche.sources),
            "[B6] note au seuil : le système l'admet", f"{lignes}")
    b.check(bool(lignes) and lignes[-1] == {"second_passage": []},
            "[B6] une source jugée n'est pas représentée à l'évaluateur", f"{lignes[-1:] if lignes else lignes}")
    _, _, lignes, fiche, _ = run(s_b6(False), n=5)
    b.check(premier(lignes).get("issue") == "en_suspens" and any(x.source == "blog.inconnu.example" for x in fiche.en_suspens),
            "[B6] note sous le seuil : en suspens, pour votre arbitrage", f"{lignes}")
    _, _, lignes, _, apres = run(s_b6(True, plante=True), n=5)
    b.check(premier(apres).get("statut") == "a_evaluer" and premier(apres).get("essais") == 1,
            "[B6] un évaluateur qui plante laisse la source à évaluer, et le compte")

    async def s_b6_deux_fois():
        ed, rd = E.DepotMemoire(), R.DepotMemoire()
        await fiches(ed)
        out = Outils(Transport(monde()), Moteur({(REQ_ANNUEL, False): RESULTATS[(REQ_ANNUEL, False)]}))
        await R.collecter(R.Demande("derniers_comptes_annuels", "FICTIVE-PRIVEE"), depot=rd, emetteurs_depot=ed,
                          outils=out, le=JOUR)
        async def passage(etat):
            envoi = R.Envoi()
            pas = R.pas_evaluation("evaluation", "FICTIVE-PRIVEE", await R.vue_travaux(rd, "FICTIVE-PRIVEE"), envoi)
            etat = AU.avancer(etat, [pas], lecture_humaine=SANS_LECTURE)
            await R.ranger_envoi(rd, envoi)
            return etat
        etat = await passage(CD.EtatDossier(dossier="FICTIVE-PRIVEE"))   # le pas attend le jugement
        for _ in range(2):
            await R.evaluer_les_sources_rencontrees(depot=rd, emetteurs_depot=ed, evaluateur=evaluateur(True, True),
                                                    le=JOUR)
        statut = (await rd.sources_rencontrees())[0]["statut"]
        etat = await passage(etat)
        return statut, etat, (await rd.sources_rencontrees())[0]
    statut, etat, source = run(s_b6_deux_fois(), n=3)
    b.check(statut == "en_echec" and dict(etat.echecs).get("evaluation") == 1 and source["statut"] == "a_evaluer"
            and source["essais"] == 0,
            "[B6] l'évaluateur qui plante deux fois : échec nommé au dossier, relancé une fois",
            f"{statut} {etat.echecs} {source}")

    # ── [B7] pages de relations investisseurs d'une autre société ────────────────────────
    async def s_b7():
        ed, rd = E.DepotMemoire(), R.DepotMemoire()
        await fiches(ed)
        out = Outils(Transport(monde()), Moteur(RESULTATS))
        await R.collecter(R.Demande("annonces_importantes", "FICTIVE-PRIVEE", depuis="2026-01-01"), depot=rd,
                          emetteurs_depot=ed, outils=out, le=JOUR)
        return {(s.source, s.auteur) for s in (await E.lire_fiche(ed, "FICTIVE-PRIVEE")).sources}
    admises = run(s_b7())
    b.check(("partenaire-cote.example".join(["ir.", ""]), E.AUTEUR_PAGES_INVESTISSEURS) in admises,
            "[B7] la page de relations investisseurs d'une autre société, vue sur le site, est admise", f"{admises}")
    b.check(not any(s == "ir.fictive-privee.example" for s, _ in admises),
            "[B7] les pages de la société elle-même ne sont pas admises comme celles d'une autre")

    # ── [B8] un travail suivi ────────────────────────────────────────────────────────────
    demandes = [R.Demande("derniers_comptes_annuels", "FICTIVE-INTRO"),
                R.Demande("annonces_importantes", "FICTIVE-INTRO", depuis="2026-01-01")]

    def parcours(vue, envoi, fiche, journal):
        def independant(ctx):
            journal.append("indépendant")
            return CD.Resultat(issue=CD.FAIT)

        def dependant(ctx):
            journal.append("dépendant")
            return CD.Resultat(issue=CD.FAIT)
        return [E.pas_fiche(fiche),
                R.pas_collecte("collecte", demandes, vue, envoi, apres=(E.NOM_DU_PAS,)),
                CD.Pas(nom="independant", module="test", apres=(E.NOM_DU_PAS,), executer=independant),
                CD.Pas(nom="dependant", module="test", apres=("collecte",), executer=dependant)]

    async def passage(etat, rd, ed, journal):
        envoi = R.Envoi()
        fiche = await E.lire_fiche(ed, "FICTIVE-INTRO")
        etat = AU.avancer(etat, lecture_humaine=SANS_LECTURE, parcours=parcours(await R.vue_travaux(rd, "FICTIVE-INTRO"), envoi, fiche, journal))
        await R.ranger_envoi(rd, envoi)
        return etat

    async def s_b8():
        ed, rd = E.DepotMemoire(), R.DepotMemoire()
        await fiches(ed)
        t = Transport(monde())
        out = Outils(t)
        journal: list[str] = []
        etat = await passage(CD.EtatDossier(dossier="FICTIVE-INTRO"), rd, ed, journal)
        etat = await passage(etat, rd, ed, journal)          # rien n'a encore répondu
        lance = (etat, list(journal), [x["statut"] for x in await rd.travaux()])
        # Interruption : la collecte tombe au milieu (le communiqué joint ne se lit pas).
        t.plante_sur.add(u_soum(INTRO, "0009000001-26-000009"))
        await R.traiter_les_travaux(depot=rd, emetteurs_depot=ed, outils=out, le=JOUR)
        etat = await passage(etat, rd, ed, journal)          # échec vu, relancé une fois
        relance = (etat, sorted(x["statut"] for x in await rd.travaux()))
        t.plante_sur.clear()
        await R.traiter_les_travaux(depot=rd, emetteurs_depot=ed, outils=out, le=JOUR)
        etat = await passage(etat, rd, ed, journal)
        nb = {}
        for r in await rd.reponses("FICTIVE-INTRO"):
            nb[r["demande"]["genre"]] = nb.get(r["demande"]["genre"], 0) + 1
        return lance, relance, etat, journal, (t, nb)
    (e1, j1, s1), (e2, s2), e3, journal, (t, nb) = run(s_b8(), n=5)
    b.check(dict(e1.en_cours).get("collecte", "").startswith("collecte lancée") and s1 == ["lancee", "lancee"],
            "[B8] le pas lance la collecte et rend « en cours »", f"{e1.en_cours} {s1}")
    b.check(j1.count("indépendant") == 1 and "dépendant" not in j1 and e1.arret.motif == CD.ARRET_ATTENTE
            and "collecte" in dict(e1.en_cours),
            "[B8] pendant la collecte, ce qui n'en dépend pas avance ; ce qui en dépend attend")
    b.check("collecte" in dict(e2.echecs) and s2 == ["lancee", "repondue"],
            "[B8] une collecte en échec est relancée une fois (seule la demande échouée)", f"{e2.echecs} {s2}")
    b.check("collecte" in e3.faits and "dependant" in e3.faits and e3.arret.motif == CD.ARRET_PARCOURS_TERMINE,
            "[B8] toutes les demandes répondues : le pas est fait, ce qui en dépend avance",
            f"{e3.faits} {e3.arret.motif if e3.arret else None}")
    b.check(t.lectures.get(u_doc(INTRO, "0009000001-26-000002", "fint-prospectus.htm")) == 1
            and nb == {"derniers_comptes_annuels": 1, "annonces_importantes": 1},
            "[B8] la reprise ne recollecte pas ce qui est déjà rangé (une réponse par demande)", f"{nb}")

    async def s_b8_deux_echecs():
        ed, rd = E.DepotMemoire(), R.DepotMemoire()
        await fiches(ed)
        t = Transport(monde())
        t.plante_sur.add(u_soum(INTRO, "0009000001-26-000009"))
        etat = CD.EtatDossier(dossier="FICTIVE-INTRO")
        for _ in range(3):
            etat = await passage(etat, rd, ed, [])
            await R.traiter_les_travaux(depot=rd, emetteurs_depot=ed, outils=Outils(t), le=JOUR)
        return await passage(etat, rd, ed, [])
    e4 = run(s_b8_deux_echecs())
    b.check(e4.arret is not None and any(a.motif == CD.ARRET_ECHEC_REPETE and a.pas == "collecte"
                                         for a in e4.arret.attentes),
            "[B8] deux échecs de suite arrêtent le dossier, motif nommé",
            f"{e4.arret.motif if e4.arret else None} {[a.motif for a in e4.arret.attentes] if e4.arret else None}")

    # ── [B9] la dépense ──────────────────────────────────────────────────────────────────
    class Partiel:
        """Le dépôt vu par une tâche de fond qui n'a encore traité qu'une partie des demandes."""

        def __init__(self, depot, genres):
            self._d, self._g = depot, genres

        def __getattr__(self, nom):
            return getattr(self._d, nom)

        async def travaux(self, emetteur=None):
            return [t for t in await self._d.travaux(emetteur) if t["demande"]["genre"] in self._g]

    async def s_b9():
        ed, rd = E.DepotMemoire(), R.DepotMemoire()
        await fiches(ed)
        out = Outils(Transport(monde()), Moteur(RESULTATS))
        dem = [R.Demande("derniers_comptes_annuels", "FICTIVE-PRIVEE"),
               R.Demande("annonces_importantes", "FICTIVE-PRIVEE", depuis="2026-01-01")]
        fiche = await E.lire_fiche(ed, "FICTIVE-PRIVEE")

        async def p(etat):
            envoi = R.Envoi()
            vue = await R.vue_travaux(rd, "FICTIVE-PRIVEE")
            etat = AU.avancer(etat, [E.pas_fiche(fiche),
                                     R.pas_collecte("collecte", dem, vue, envoi, apres=(E.NOM_DU_PAS,)),
                                     R.pas_evaluation("evaluation", "FICTIVE-PRIVEE", vue, envoi, apres=("collecte",))],
                              lecture_humaine=SANS_LECTURE)
            await R.ranger_envoi(rd, envoi)
            return etat
        etat = await p(CD.EtatDossier(dossier="FICTIVE-PRIVEE"))
        await R.traiter_les_travaux(depot=Partiel(rd, {"derniers_comptes_annuels"}), emetteurs_depot=ed,
                                    outils=out, le=JOUR)
        e1 = await p(etat)                      # une demande répondue, l'autre en cours
        e2 = await p(e1)                        # rien de neuf : rien de plus à déclarer
        await R.traiter_les_travaux(depot=rd, emetteurs_depot=ed, outils=out, le=JOUR)
        e3 = await p(e2)                        # collecte faite ; l'évaluation attend son jugement
        await R.evaluer_les_sources_rencontrees(depot=rd, emetteurs_depot=ed, evaluateur=evaluateur(True), le=JOUR)
        e4 = await p(e3)                        # jugement rendu : sa dépense est déclarée
        notee = [(x.get("declare"), x.get("depense")) for x in await rd.sources_rencontrees()]
        sec = await R.collecter(R.Demande("derniers_comptes_annuels", "FICTIVE-INTRO"), depot=rd,
                                emetteurs_depot=ed, outils=out, le=JOUR)
        return e1, e2, e3, (e4, notee), sec, out.moteur, await R.lire_recueil(rd, "FICTIVE-PRIVEE")
    e1, e2, e3, (e4, notee), sec, moteur, recueil = run(s_b9(), n=7)
    web_attendu = round(len([a for a in moteur.appels if "Privée" in a[0]]) * Moteur.COUT, 6)
    b.check(e1.depense.web_usd == web_attendu and web_attendu > 0 and "collecte" in dict(e1.en_cours),
            "[B9] chaque recherche web est déclarée au chef de dossier, dès la réponse", f"{e1.depense} attendu {web_attendu}")
    b.check(e2.depense == e1.depense and e3.depense == e1.depense,
            "[B9] une dépense déclarée ne l'est qu'une fois", f"{e1.depense} {e2.depense} {e3.depense}")
    b.check("collecte" in e3.faits and "evaluation" in dict(e3.en_cours) and e3.arret.motif == CD.ARRET_ATTENTE,
            "[B9] la collecte faite, l'évaluation des sources reste en cours sans retenir le dossier",
            f"{e3.faits} {e3.en_cours}")
    b.check(e4.depense.modeles_usd == 0.02 and e4.depense.web_usd == web_attendu and "evaluation" in e4.faits,
            "[B9] l'appel de l'évaluateur est déclaré au chef de dossier", f"{e4.depense}")
    b.check(notee == [({"modeles_usd": 0.02, "web_usd": 0.0}, {"modeles_usd": 0.02, "web_usd": 0.0})],
            "[B9] la dépense de l'évaluateur, une fois déclarée, est notée comme telle", f"{notee}")
    b.check(sec.depense.total_usd == 0 and sec.documents, "[B9] registre et site : 0")
    b.check(recueil.depense.total_usd == round(web_attendu + 0.02, 6),
            "[B9] le recueil dit ce que la collecte a dépensé", f"{recueil.depense}")

    # ── [B10] l'identité depuis le registre ──────────────────────────────────────────────
    async def s_b10():
        ed, rd = E.DepotMemoire(), R.DepotMemoire()
        await fiches(ed)
        await E.etablir_fiche(ed, "FICTIVE-INTRO", raison_sociale="FINT", auteur=E.UTILISATEUR, motif="ses pages",
                              le=JOUR, lieux=[("relations_investisseurs", "ir.fint.example")])
        out = Outils(Transport(monde()))
        r1 = await R.collecter(R.Demande("comptes_intermediaires", "FICTIVE-INTRO", depuis="2026-01-01"),
                               depot=rd, emetteurs_depot=ed, outils=out, le=JOUR)
        f1 = await E.lire_fiche(ed, "FICTIVE-INTRO")
        f = f1
        await E.etablir_fiche(ed, "FICTIVE-INTRO", raison_sociale="Fictive Introduite (nom d'usage)", auteur=E.UTILISATEUR,
                              motif="je corrige", le=JOUR, pays=f.pays, cotations=[(c.place, c.symbole) for c in f.cotations],
                              references=[(x.registre, x.valeur) for x in f.references],
                              lieux=[(l.genre, l.adresse) for l in f.lieux])
        r2 = await R.collecter(R.Demande("comptes_intermediaires", "FICTIVE-INTRO", depuis="2026-01-01"),
                               depot=rd, emetteurs_depot=ed, outils=out, le="2026-11-17")
        f2 = await E.lire_fiche(ed, "FICTIVE-INTRO")
        homo = await R.collecter(R.Demande("derniers_comptes_annuels", "FICTIVE-HOMO"), depot=rd,
                                 emetteurs_depot=ed, outils=out, le=JOUR)
        fh = await E.lire_fiche(ed, "FICTIVE-HOMO")
        ancienne = await E.lire_fiche(ed, "FICTIVE-ANCIENNE")
        await R.collecter(R.Demande("comptes_intermediaires", "FICTIVE-ANCIENNE", depuis="2025-01-01"),
                          depot=rd, emetteurs_depot=ed, outils=out, le=JOUR)
        ancienne2 = await E.lire_fiche(ed, "FICTIVE-ANCIENNE")
        refus = None
        try:
            await E.completer_identite(ed, "FICTIVE-INTRO", raison_sociale="X", pays="", cotations=[], references=[],
                                       auteur=E.UTILISATEUR, motif="m", le=JOUR)
        except E.ActeRefuse as exc:
            refus = str(exc)
        return r1, f1, r2, f2, homo, fh, ancienne, ancienne2, refus
    r1, f1, r2, f2, homo, fh, anc, anc2, refus = run(s_b10(), n=9)
    b.check(f1.raison_sociale == "FICTIVE INTRODUITE CORP" and f1.reference(SEC["reference"]) == str(INTRO)
            and f1.pays == "US" and [(c.place, c.symbole) for c in f1.cotations] == [("NASDAQ", "FINT")],
            "[B10] la fiche se complète depuis le registre (raison sociale, numéro, place, symbole, pays)",
            f"{f1.raison_sociale} {f1.references} {f1.pays} {f1.cotations}")
    b.check(f1.auteur.startswith(E.PREFIXE_SYSTEME) and "registre" in f1.motif and JOUR in f1.motif,
            "[B10] la révision est signée du système, registre et date cités", f"{f1.auteur} {f1.motif}")
    b.check(f1.lieux == (E.Lieu("relations_investisseurs", "ir.fint.example"),),
            "[B10] les lieux de publication ne sont jamais touchés")
    b.check(r1.documents and r1.identite.get("issue") == "completee",
            "[B10] la collecte se poursuit avec la fiche complétée")
    b.check(f2.raison_sociale == "Fictive Introduite (nom d'usage)" and f2.auteur == E.UTILISATEUR
            and r2.identite.get("tenus") == ["raison_sociale"],
            "[B10] votre correction tient, et l'écart avec le registre est montré",
            f"{f2.raison_sociale} {r2.identite}")
    b.check(homo.indisponibilite is not None and homo.indisponibilite.raison == "homonyme"
            and "HOM1" not in fh.raison_sociale and not fh.references and homo.acte_attendu
            and "9000003" in homo.acte_attendu and "9000004" in homo.acte_attendu,
            "[B10] un homonyme n'est jamais tranché : indisponibilité nommée, acte attendu, fiche intacte",
            f"{homo.indisponibilite} {homo.acte_attendu}")
    b.check(anc2.revision == anc.revision + 1 and anc2.raison_sociale == "FICTIVE ANCIENNE INC"
            and [(c.place, c.symbole) for c in anc2.cotations] == [("NYSE", "FANC")],
            "[B10] la saisie d'ouverture (avant tout passage du système) est complétée par le registre",
            f"{anc2.raison_sociale} {anc2.cotations}")
    b.check(refus is not None and "système" in refus, "[B10] compléter depuis un registre est un acte du système")

    async def s_b10_chef():
        ed, rd = E.DepotMemoire(), R.DepotMemoire()
        await fiches(ed)
        out = Outils(Transport(monde()))
        dem = [R.Demande("derniers_comptes_annuels", "FICTIVE-HOMO")]

        async def p(etat):
            envoi = R.Envoi()
            fiche = await E.lire_fiche(ed, "FICTIVE-HOMO")
            etat = AU.avancer(etat, [E.pas_fiche(fiche), R.pas_collecte(
                "collecte", dem, await R.vue_travaux(rd, "FICTIVE-HOMO"), envoi, apres=(E.NOM_DU_PAS,))],
                lecture_humaine=SANS_LECTURE)
            await R.ranger_envoi(rd, envoi)
            return etat
        etat = await p(CD.EtatDossier(dossier="FICTIVE-HOMO"))
        await R.traiter_les_travaux(depot=rd, emetteurs_depot=ed, outils=out, le=JOUR)
        etat = await p(etat)
        arret = etat.arret
        await E.etablir_fiche(ed, "FICTIVE-HOMO", raison_sociale="Homonyme Holdings", auteur=E.UTILISATEUR,
                              motif="c'est celle-ci", le=JOUR, references=[(SEC["reference"], str(HOMO_1))])
        etat = AU.enregistrer_acte(etat, arret.cle)
        etat = await p(etat)
        relancee = [t["statut"] for t in await rd.travaux()]
        return arret, relancee
    arret, relancee = run(s_b10_chef(), n=2)
    b.check(arret.motif == CD.ARRET_ACTE_HUMAIN and "plusieurs" in arret.acte,
            "[B10] le chef de dossier s'arrête sur l'acte d'identité", f"{arret}")
    b.check(relancee == ["lancee"], "[B10] votre acte enregistré, la collecte repart avec la fiche corrigée",
            f"{relancee}")

    # ── [B11] dans le doute, indisponible ────────────────────────────────────────────────
    async def s_b11(pages_modif):
        ed, rd = E.DepotMemoire(), R.DepotMemoire()
        await fiches(ed)
        p = monde()
        p.update(pages_modif)
        t = Transport(p)
        out = Outils(t)
        rep = await R.collecter(R.Demande("derniers_comptes_annuels", "FICTIVE-ANCIENNE"), depot=rd,
                                emetteurs_depot=ed, outils=out, le=JOUR)
        return rep, t, rd
    rep, t, rd = run(s_b11({u_depots(ANCIENNE): [AD.Lu(503), AD.Lu(503)]}), n=3)
    b.check(rep.indisponibilite is not None and rep.indisponibilite.raison == "injoignable"
            and t.lectures[u_depots(ANCIENNE)] == 2,
            "[B11] registre en erreur deux fois : indisponible (injoignable), une seule seconde tentative",
            f"{rep.indisponibilite} {t.lectures.get(u_depots(ANCIENNE))}")
    ok = depots(ANCIENNE, "FICTIVE ANCIENNE INC", "FANC", DEPOTS_ANCIENNE, place="NYSE")
    rep, t, _ = run(s_b11({u_depots(ANCIENNE): [AD.Lu(503), ok]}), n=3)
    b.check(rep.documents and rep.indisponibilite is None, "[B11] une erreur passagère, puis la réponse : collecté")
    rep, _, rd = run(s_b11({u_doc(ANCIENNE, "0009000002-26-000004", "fanc-10k.htm"): AD.Lu(200, b"   ", "text/html")}), n=3)
    b.check(rep.indisponibilite is not None and rep.indisponibilite.raison == "illisible" and not rd._documents,
            "[B11] un document vide n'est jamais rangé comme bon", f"{rep.indisponibilite}")
    class Negligent:
        nom, famille = "negligent", AD.SITE

        def sait(self, genre):
            return True

        async def chercher(self, appel):
            return AD.Trouvaille(trouves=[AD.Trouve(R.Provenance(adaptateur=self.nom, adresse="vide.example/x",
                                                                 identifiant="x", partie="page"), b" \n ", "text/html")])

    async def s_b11_coeur():
        ed, rd = E.DepotMemoire(), R.DepotMemoire()
        await fiches(ed)
        rep = await R.collecter(R.Demande("presentation_aux_investisseurs", "FICTIVE-PRIVEE", depuis="2026-01-01"),
                                depot=rd, emetteurs_depot=ed, outils=Outils(Transport({}), adaptateurs=[Negligent()]),
                                le=JOUR)
        return rep, rd
    rep, rd = run(s_b11_coeur(), n=2)
    b.check(rep.indisponibilite is not None and rep.indisponibilite.raison == "illisible" and not rd._documents,
            "[B11] le cœur refuse lui-même un document vide qu'un adaptateur lui rend", f"{rep}")
    pdf_rep = rendus["derniers_comptes_annuels"]
    essais_site = [m for a, m in pdf_rep.essais if a == "site_emetteur"]
    b.check(pdf_rep.documents and pdf_rep.documents[0].provenance.adaptateur == "web"
            and any(m.startswith("illisible") and "PDF" in m for m in essais_site),
            "[B11] un PDF n'est pas lu : la raison est nommée et gardée, la collecte passe au web",
            f"{pdf_rep.essais}")
    b.check(not any(d.type_media == "application/pdf" for r in rendus.values() for d in r.documents),
            "[B11] aucun PDF rangé")

    return b.summary()


if __name__ == "__main__":
    sys.exit(main())
