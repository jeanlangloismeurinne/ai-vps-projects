"""Module M3 « Base de connaissance » sur une société FICTIVE — aucune base, aucun réseau, aucun modèle,
aucune dépense. C'est la part « société fictive » de l'acceptation écrite avant la construction
(`roadmap/V3/M3-base-connaissance.md` §3) ; chaque section porte le numéro de la ligne qu'elle prouve,
et `negatif_connaissance.sh` prouve que chacune vire au rouge.

  [K0] le module n'importe ni réseau, ni base, ni modèle : bibliothèque standard et contrats
  [K1] rien n'entre sans origine : document inconnu ou pas encore lu → refusé, motif nommé ; une pièce
       nomme son document et ses lignes, et ses lignes contiennent son extrait
  [K2] lecture reproductible : relire ne relit pas, la même lecture deux fois est identique ; un
       lecteur amélioré ajoute une lecture à côté, les pièces gardent la leur
  [K3] les formes réelles se lisent : communiqué réel (lignes de tableau citables, cellules recollées
       comme imprimées), masqué/script/en-tête de données structurées non lus, bloc dans une cellule,
       texte brut ; données structurées « sans objet » ; vide → impossible nommé ;
       un caractère nul se lit « \ufffd » (sinon la base refuserait la lecture)
  [K4] une pièce ne dit que ce que son document écrit : mot pour mot, texte du DOCUMENT ; court et
       unique → sa ligne ; ambigu ou introuvable → refusé ; une ligne répétée nomme ses autres lignes
  [K5] la même pièce citée deux fois n'est rangée qu'une fois
  [K6] dates du document, période du fait quand l'auteur la dit, rien de deviné
  [K7] ce que vaut la source se lit au jour de la lecture : révoquée après la citation, la pièce est
       signalée ; non admise = marquée ; la pièce elle-même ne change pas
  [K8] recherche par les mots : tous les mots, classement stable, reproductible, sans dépense
  [K9] le pas de lecture : en cours tant qu'un document attend, fait ensuite, indisponible sans
       document ; 0 $ ; ce qui n'en dépend pas avance

Le communiqué est le EX-99.1 réel du 8-K NVIDIA 0001045810-26-000019 (copié tel quel :
`fixtures/connaissance/communique_ex991.htm`) ; la société, ses domaines et les autres documents sont
fictifs (`.example` est réservé), à la forme des documents réels (en-tête de données structurées
masqué, cellules d'espacement masquées, symbole monétaire dans sa propre cellule).
"""
from __future__ import annotations

import ast
import asyncio
import os
import re
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Bilan  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.modules.chef_de_dossier import automate as AU  # noqa: E402
from app.modules.chef_de_dossier import contrat as CD  # noqa: E402
from app.modules.connaissance import coeur as KC  # noqa: E402
from app.modules.connaissance import contrat as K  # noqa: E402
from app.modules.emetteurs import contrat as E  # noqa: E402
from app.modules.recueil import adaptateurs as AD  # noqa: E402
from app.modules.recueil import contrat as R  # noqa: E402

MODULE = BACKEND / "app" / "modules" / "connaissance"
JOUR = "2026-11-21"
LENDEMAIN = "2026-11-22"
EMETTEUR = "FICTIVE-LECTURE"
SITE = "fictive-lecture.example"
PRESSE = "presse-fictive.example"
INCONNUE = "blog-inconnu.example"
SANS_LECTURE = {"emetteurs": False, "recueil": False, "connaissance": False, "test": False}
COMMUNIQUE = (BACKEND / "checks" / "fixtures" / "connaissance" / "communique_ex991.htm").read_bytes()

RAPPORT = """<html><head><title>Rapport annuel fictif</title><style>p{color:red}</style>
<script>var cache = "SCRIPT-NON-LU";</script></head><body>
<div style="display:none"><ix:header><ix:hidden>FAIT-MASQUE-NON-LU</ix:hidden></ix:header></div>
<p>Fictive Lecture Corp is a fictional company used to test the reading of annual reports.</p>
<script>var corps = "SCRIPT-DU-CORPS-NON-LU";</script>
<p>Our principal customers are "distributors" located in three regions.</p>
<table>
<tr><td>Product sales</td><td>$</td><td>1,234</td><td style="display:none">ESPACEMENT</td><td>(</td><td>12</td><td>)%</td></tr>
<tr><td>Total revenue</td><td>$</td><td>2,468</td><td><p>see note 3</p></td></tr>
</table>
<p>Total revenue grew because distributors increased orders.</p>
<p>Total revenue grew because distributors increased orders.</p>
</body></html>""".encode("utf-8")
VIDE = b"<html><head><script>rien()</script></head><body><div style='display: none'>cache</div></body></html>"
TEXTE_PRESSE = ("Fictive Lecture Corp announced a new distribution agreement.\n\n"
                "The agreement covers three regions and starts in January 2027.\n").encode("utf-8")
TEXTE_BLOG = b"Rumours say Fictive Lecture Corp will double its prices next year.\n"
DONNEES = b'{"facts": {"Revenue": [{"val": 2468}]}}'


def a(chemin: str) -> str:
    return "https://" + chemin


class Simule:
    """Un adaptateur de la famille « site » qui rend des documents fixés par genre (ni réseau ni
    dépense) : la collecte de M2 tourne pour de vrai, seule la source est simulée."""
    nom = "site_simule"
    famille = AD.SITE

    def __init__(self, par_genre: dict[str, list[AD.Trouve]]) -> None:
        self.par_genre = par_genre

    def sait(self, genre: str) -> bool:
        return genre in self.par_genre

    async def chercher(self, appel: AD.Appel) -> AD.Trouvaille:
        return AD.Trouvaille(trouves=list(self.par_genre[appel.demande.genre]))


class Outils:
    def __init__(self, adaptateurs):
        self.transport, self.moteur, self.adaptateurs = None, None, adaptateurs


def trouve(adresse, contenu, type_media, publie_le="", faits_au=""):
    return AD.Trouve(R.Provenance(adaptateur="site_simule", adresse=adresse, publie_le=publie_le,
                                  faits_au=faits_au), contenu, type_media)


MONDE = {
    "derniers_comptes_annuels": [trouve(a(SITE + "/rapport-2025.htm"), RAPPORT, "text/html",
                                        "2026-02-26", "2025-12-31")],
    "annonces_importantes": [
        trouve(a(SITE + "/communique-t4.htm"), COMMUNIQUE, "text/html", "2026-02-25", "2026-01-25"),
        trouve(a(PRESSE + "/accord"), TEXTE_PRESSE, "text/plain", "2026-03-02"),
        trouve(a(INCONNUE + "/rumeur"), TEXTE_BLOG, "text/plain"),
    ],
    "donnees_comptables_structurees": [trouve(a(SITE + "/donnees.json"), DONNEES, "application/json")],
    "document_de_convocation": [trouve(a(SITE + "/convocation.htm"), VIDE, "text/html", "2026-04-01")],
}
DEMANDES = [R.Demande("derniers_comptes_annuels", EMETTEUR),
            R.Demande("annonces_importantes", EMETTEUR, depuis="2026-01-01"),
            R.Demande("donnees_comptables_structurees", EMETTEUR),
            R.Demande("document_de_convocation", EMETTEUR)]


async def monde():
    ed, rd, kd = E.DepotMemoire(), R.DepotMemoire(), K.DepotMemoire()
    await E.etablir_fiche(ed, EMETTEUR, raison_sociale="Fictive Lecture Corp", auteur=E.UTILISATEUR,
                          motif="ouverture", le=JOUR, lieux=[("site", SITE)])
    await E.admettre_source(ed, source=PRESSE, portee=E.PORTEE_GENERALE, natures=["evenement"], niveau="B",
                            auteur=E.UTILISATEUR, motif="presse fictive", le=JOUR)
    out = Outils([Simule(MONDE)])
    for d in DEMANDES:
        await R.collecter(d, depot=rd, emetteurs_depot=ed, outils=out, le=JOUR)
    return ed, rd, kd


class Bilan2(Bilan):
    def check(self, condition: bool, label: str, detail: str = "") -> bool:
        return super().check(bool(condition), label + (f" — {detail}" if detail and not condition else ""))


def refus(coro) -> str | None:
    """Le motif d'un `PieceRefusee`, ou None si la citation a été acceptée."""
    try:
        asyncio.run(coro)
    except K.PieceRefusee as exc:
        return str(exc)
    except Exception as exc:  # noqa: BLE001 — un plantage n'est pas un refus nommé : l'assert rougit
        return f"(plantage {type(exc).__name__}: {exc})"
    return None


def run(coro):
    try:
        return asyncio.run(coro)
    except Exception as exc:  # noqa: BLE001 — l'assert attendu rougit, le contrôle atteint son bilan
        print(f"  (scénario planté : {type(exc).__name__}: {exc})")
        return None


def par_adresse(lectures, fin):
    return next((l for l in lectures if l.adresse.endswith(fin)), None)


def main() -> int:
    b = Bilan2()

    # ── [K0] ni réseau, ni base, ni modèle ──────────────────────────────────────────────────
    interdits = {"urllib", "http", "socket", "httpx", "requests", "aiohttp", "asyncpg", "openai", "anthropic"}
    fautifs = []
    for f in sorted(MODULE.glob("*.py")):
        if f.name == "depot_base.py":
            continue                        # le rangement en base reçoit sa connexion, il n'en ouvre pas
        for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            noms = [x.name for x in n.names] if isinstance(n, ast.Import) else (
                [f"{n.module}.{x.name}" if n.module and n.module.startswith("app.") else (n.module or "")
                 for x in n.names] if isinstance(n, ast.ImportFrom) else [])
            for nom in noms:
                if nom.split(".")[0] in interdits or nom.startswith("app.") and not re.match(
                        r"app\.modules\.\w+\.contrat(\.|$)", nom):
                    fautifs.append(f"{f.name}: {nom}")
    b.check(not fautifs, "[K0] le module n'importe ni réseau, ni base, ni modèle, ni l'ancien code", f"{fautifs}")

    # ── Le monde : M2 collecte pour de vrai, M3 lit ─────────────────────────────────────────
    async def s_lecture():
        ed, rd, kd = await monde()
        avant = await K.lire_connaissance(kd, recueil_depot=rd, emetteurs_depot=ed, emetteur=EMETTEUR)
        premier = await K.lire_documents(kd, recueil_depot=rd, emetteur=EMETTEUR, le=JOUR)
        second = await K.lire_documents(kd, recueil_depot=rd, emetteur=EMETTEUR, le=LENDEMAIN)
        apres = await K.lire_connaissance(kd, recueil_depot=rd, emetteurs_depot=ed, emetteur=EMETTEUR)
        return ed, rd, kd, avant, premier, second, apres
    r = run(s_lecture())
    if r is None:
        b.check(False, "[K2] le monde fictif se lit")
        return b.summary()
    ed, rd, kd, avant, premier, second, apres = r
    lect = {l.adresse.rsplit("/", 1)[-1]: l for l in apres.lectures}

    def lignes(nom):
        l = lect.get(nom)
        return asyncio.run(K.lire_lignes(kd, l.empreinte, l.lecteur)) if l and l.statut == K.LUE else ()

    # ── [K2] reproductible ──────────────────────────────────────────────────────────────────
    b.require(premier, 6, "[K2] chaque document collecté est mis en lecture une fois")
    b.check(len(avant.a_lire) == 6 and not apres.a_lire, "[K2] avant : six à lire ; après : aucun",
            f"{len(avant.a_lire)} / {apres.a_lire}")
    b.check(second == [], "[K2] relire ne relit pas ce qui a déjà sa lecture courante", f"{second}")
    regles = KC.referentiel()["lecteur"]
    b.check(KC.L.lire(RAPPORT, "text/html", regles) == KC.L.lire(RAPPORT, "text/html", regles)
            and tuple(lignes("rapport-2025.htm")) == KC.L.lire(RAPPORT, "text/html", regles).lignes,
            "[K2] la même lecture deux fois est identique, octet pour octet")

    # ── [K3] les formes réelles ─────────────────────────────────────────────────────────────
    com = lignes("communique-t4.htm")
    b.check("Revenue\t$68,127\t$57,006\t$39,331\t20%\t73%" in com,
            "[K3] une ligne de tableau du communiqué réel : cellules sur tabulation, « 20 » et « % » recollés",
            f"{[l for l in com if l.startswith('Revenue')][:2]}")
    b.check(com and com[0] == "NVIDIA Announces Financial Results for Fourth Quarter and Fiscal 2026",
            "[K3] le communiqué réel commence par son titre", f"{com[:1]}")
    rap = lignes("rapport-2025.htm")
    tout = "\n".join(rap)
    b.check("FAIT-MASQUE-NON-LU" not in tout and "ESPACEMENT" not in tout,
            "[K3] ce qui est masqué (en-tête des données structurées, cellule d'espacement) n'est pas lu", tout[:200])
    b.check("SCRIPT-DU-CORPS-NON-LU" not in tout and "SCRIPT-NON-LU" not in tout and "color:red" not in tout and "Rapport annuel fictif" not in tout,
            "[K3] scripts, styles et en-tête de page ne sont pas lus")
    b.check("Product sales\t$1,234\t(12)%" in rap,
            "[K3] symbole monétaire au nombre qui suit, ponctuation à la cellule d'avant", f"{rap}")
    b.check("Total revenue\t$2,468\tsee note 3" in rap, "[K3] un bloc dans une cellule ne coupe pas la ligne", f"{rap}")
    b.check(lignes("accord") == ("Fictive Lecture Corp announced a new distribution agreement.",
                                 "The agreement covers three regions and starts in January 2027."),
            "[K3] un texte brut : ses lignes non vides", f"{lignes('accord')}")
    b.check(lect.get("donnees.json") and lect["donnees.json"].statut == K.SANS_OBJET,
            "[K3] données structurées : « sans objet », pas « impossible »")
    conv = lect.get("convocation.htm")
    b.check(conv and conv.statut == K.IMPOSSIBLE and conv.raison == "vide" and conv.nb_lignes == 0,
            "[K3] une page sans texte visible : lecture impossible, raison nommée", f"{conv}")
    from app.modules.connaissance import lecteur as KL
    nuls = [KL.lire(c, t, KC.referentiel()["lecteur"]).lignes
            for c, t in ((b"<p>Revenue\x00 $12</p>", "text/html"), (b"Revenue\x00 $12", "text/plain"))]
    b.check(nuls == [("Revenue\ufffd $12",)] * 2,
            "[K3] un caractère nul se lit « \ufffd » (comme un navigateur) : la base peut ranger la lecture", f"{nuls}")

    # ── [K1] rien sans origine ──────────────────────────────────────────────────────────────
    async def citer(nom, extrait, **kw):
        l = lect[nom]
        return await K.citer(kd, emetteur=EMETTEUR, empreinte=l.empreinte, extrait=extrait,
                             auteur=kw.pop("auteur", "comptes"), le=kw.pop("le", JOUR), **kw)

    m = refus(K.citer(kd, emetteur=EMETTEUR, empreinte="0" * 64, extrait="Fictive Lecture Corp is a fictional",
                      auteur="comptes", le=JOUR))
    b.check(m and "rien n'entre sans document d'origine" in m, "[K1] un document inconnu ne donne pas de pièce", f"{m}")

    async def s_pas_encore_lu():
        ed2, rd2, kd2 = await monde()
        e = (await K.vue_lecture(kd2, recueil_depot=rd2, emetteur=EMETTEUR)).documents[0]
        return await K.citer(kd2, emetteur=EMETTEUR, empreinte=e, extrait="Fictive Lecture Corp is a fictional",
                             auteur="comptes", le=JOUR)
    m = refus(s_pas_encore_lu())
    b.check(m and "pas encore mis en lecture" in m, "[K1] un document collecté mais pas encore lu ne donne pas de pièce", f"{m}")
    m = refus(citer("convocation.htm", "cache"))
    b.check(m and "impossible" in m, "[K1] une lecture impossible ne donne pas de pièce", f"{m}")
    m = refus(citer("rapport-2025.htm", "Our principal customers are distributors", auteur=" "))
    b.check(m and "nomme celui qui la cite" in m, "[K1] une pièce nomme son auteur", f"{m}")
    p1 = run(citer("rapport-2025.htm", "our PRINCIPAL customers are “distributors” located"))
    b.check(p1 and p1.empreinte == lect["rapport-2025.htm"].empreinte and p1.ligne_debut == p1.ligne_fin == 2,
            "[K1] la pièce nomme son document et ses lignes", f"{p1}")
    b.check(p1 and K.normaliser(p1.extrait) in K.normaliser(" ".join(
        asyncio.run(K.lire_lignes(kd, p1.empreinte, p1.lecteur, p1.ligne_debut, p1.ligne_fin)))),
        "[K1] les lignes de la pièce contiennent son extrait")

    # ── [K4] mot pour mot, texte du document ────────────────────────────────────────────────
    b.check(p1 and p1.extrait == 'Our principal customers are "distributors" located',
            "[K4] la pièce porte le texte du DOCUMENT, pas la casse ni les guillemets de l'auteur", f"{p1 and p1.extrait!r}")
    p_tab = run(citer("communique-t4.htm", "Revenue $68,127 $57,006 $39,331 20% 73%"))
    b.check(p_tab and p_tab.extrait.startswith("Revenue\t$68,127") and p_tab.autres_lignes,
            "[K4] une ligne de tableau se cite telle qu'imprimée ; répétée ailleurs, la pièce nomme ses autres lignes",
            f"{p_tab}")
    p_court = run(citer("rapport-2025.htm", "$2,468"))
    b.check(p_court and p_court.extrait == "Total revenue\t$2,468\tsee note 3",
            "[K4] un extrait court et unique est remplacé par sa ligne", f"{p_court}")
    m = refus(citer("communique-t4.htm", "Revenue"))
    b.check(m and "non discriminant" in m, "[K4] un extrait court ambigu est refusé", f"{m}")
    m = refus(citer("communique-t4.htm", "quarterly revenue reached a record $68.1 billion"))
    b.check(m and "introuvable dans le texte rapporté" in m, "[K4] une paraphrase est refusée par la vérification mot pour mot, motif nommé", f"{m}")
    m = refus(citer("communique-t4.htm", "record quarterly revenue of $68.2 billion"))
    b.check(m and "introuvable dans le texte rapporté" in m, "[K4] un chiffre changé est refusé", f"{m}")
    p_rep = run(citer("rapport-2025.htm", "Total revenue grew because distributors increased orders."))
    b.check(p_rep and p_rep.autres_lignes == (p_rep.ligne_debut + 1,),
            "[K4] une phrase répétée : première occurrence retenue, l'autre ligne nommée", f"{p_rep}")

    # ── [K5] une fois ───────────────────────────────────────────────────────────────────────
    async def s_deux_fois():
        x = await citer("accord", "covers three regions and starts in January 2027", periode="2027", auteur="carte")
        y = await citer("accord", "COVERS three regions and starts in January 2027", periode="2027",
                        auteur="recherche", le=LENDEMAIN)
        z = await citer("accord", "covers three regions and starts in January 2027", periode="", auteur="carte")
        return x, y, z, len(await kd.pieces(EMETTEUR))
    r5 = run(s_deux_fois())
    x, y, z, n_avant = r5 if r5 else (None, None, None, 0)
    b.check(x and y and x == y and y.auteur == "carte" and y.cite_le == JOUR,
            "[K5] la même pièce citée deux fois : la seconde rend la première, inchangée", f"{x} / {y}")
    b.check(z and x and z.identifiant != x.identifiant,
            "[K5] le même extrait pour une autre période est une autre pièce")

    # ── [K6] dates ──────────────────────────────────────────────────────────────────────────
    b.check(p1 and (p1.publie_le, p1.faits_au, p1.periode) == ("2026-02-26", "2025-12-31", ""),
            "[K6] dates du document ; période non dite = vide", f"{p1}")
    b.check(x and x.periode == "2027" and x.publie_le == "2026-03-02" and x.faits_au == "",
            "[K6] la période dite par l'auteur est gardée ; une date absente reste absente", f"{x}")
    p_blog = run(citer("rumeur", "will double its prices next year"))
    b.check(p_blog and p_blog.publie_le == "" and p_blog.faits_au == "",
            "[K6] un document sans date : la pièce n'en invente pas", f"{p_blog}")

    # ── [K7] ce que vaut la source, au jour de la lecture ───────────────────────────────────
    def valeur(piece):
        c = asyncio.run(K.lire_connaissance(kd, recueil_depot=rd, emetteurs_depot=ed, emetteur=EMETTEUR))
        return next((pl for pl in c.pieces if pl.piece.identifiant == piece.identifiant), None)
    v_avant = valeur(x) if x else None
    b.check(v_avant and v_avant.valeur.admise and not v_avant.valeur.revoquee_le,
            "[K7] une pièce de la presse admise : admise", f"{v_avant}")
    v_blog = valeur(p_blog) if p_blog else None
    b.check(v_blog and not v_blog.valeur.admise, "[K7] une pièce d'une source non admise est marquée comme telle",
            f"{v_blog}")
    v_site = valeur(p1) if p1 else None
    b.check(v_site and v_site.valeur.admise, "[K7] une pièce du site de la société : admise", f"{v_site}")
    run(E.revoquer_source(ed, source=PRESSE, portee=E.PORTEE_GENERALE, auteur=E.UTILISATEUR,
                          motif="reprend des rumeurs", le=LENDEMAIN))
    v_apres = valeur(x) if x else None
    b.check(v_apres and not v_apres.valeur.admise and v_apres.valeur.revoquee_le == LENDEMAIN
            and "rumeurs" in v_apres.valeur.motif_revocation,
            "[K7] révoquée après la citation : la pièce est signalée à la lecture suivante", f"{v_apres}")
    b.check(v_apres and v_avant and v_apres.piece == v_avant.piece,
            "[K7] la pièce elle-même ne change pas : seule sa valeur se relit")

    # ── [K8] chercher par les mots ──────────────────────────────────────────────────────────
    r8 = run(K.chercher(kd, emetteur=EMETTEUR, mots="Data Center revenue"))
    r8b = run(K.chercher(kd, emetteur=EMETTEUR, mots="data   CENTER Revenue"))
    b.check(r8 and all(all(m in K.normaliser(p.texte) for m in ("data", "center", "revenue")) for p in r8),
            "[K8] chaque ligne rendue contient tous les mots", f"{r8 and r8[:2]}")
    b.check(r8 and r8 == r8b, "[K8] deux recherches identiques (casse, blancs) : même résultat")
    b.check(r8 and [p.occurrences for p in r8] == sorted((p.occurrences for p in r8), reverse=True),
            "[K8] les lignes les plus riches en occurrences d'abord")
    r8c = run(K.chercher(kd, emetteur=EMETTEUR, mots="revenue", genre="derniers_comptes_annuels"))
    b.check(r8c and {p.genre for p in r8c} == {"derniers_comptes_annuels"} and all(p.ligne >= 1 for p in r8c),
            "[K8] filtré par genre, chaque passage dit sa ligne", f"{r8c}")
    b.check(run(K.chercher(kd, emetteur=EMETTEUR, mots="   ")) == [], "[K8] une recherche vide ne rend rien")

    # ── [K9] le pas de lecture ──────────────────────────────────────────────────────────────
    def parcours(vue_r, envoi, fiche, vue_k, journal):
        def independant(ctx):
            journal.append("indépendant")
            return CD.Resultat(issue=CD.FAIT)
        return [E.pas_fiche(fiche), R.pas_collecte("collecte", DEMANDES, vue_r, envoi),
                K.pas_lecture("lecture", vue_k, apres=("collecte",)),
                CD.Pas(nom="independant", module="test", apres=("collecte",), executer=independant)]

    async def s_pas():
        ed2, rd2, kd2 = E.DepotMemoire(), R.DepotMemoire(), K.DepotMemoire()
        await E.etablir_fiche(ed2, EMETTEUR, raison_sociale="Fictive Lecture Corp", auteur=E.UTILISATEUR,
                              motif="ouverture", le=JOUR, lieux=[("site", SITE)])
        journal: list[str] = []
        etat = CD.EtatDossier(dossier=EMETTEUR)

        async def passage(etat):
            envoi = R.Envoi()
            fiche = await E.lire_fiche(ed2, EMETTEUR)
            etat = AU.avancer(etat, parcours(await R.vue_travaux(rd2, EMETTEUR), envoi, fiche,
                                             await K.vue_lecture(kd2, recueil_depot=rd2, emetteur=EMETTEUR), journal),
                              lecture_humaine=SANS_LECTURE)
            await R.ranger_envoi(rd2, envoi)
            return etat
        etat = await passage(etat)
        await R.traiter_les_travaux(depot=rd2, emetteurs_depot=ed2, outils=Outils([Simule(MONDE)]), le=JOUR)
        etat = await passage(etat)
        en_lecture = etat
        await K.lire_documents(kd2, recueil_depot=rd2, emetteur=EMETTEUR, le=JOUR)
        etat = await passage(etat)
        return en_lecture, etat, journal
    r9 = run(s_pas())
    e1, e2, journal = r9 if r9 else (None, None, [])
    b.check(e1 and dict(e1.en_cours).get("lecture", "").startswith("lecture : 0/6")
            and "independant" in e1.faits and "lecture" not in e1.faits,
            "[K9] collecte faite, documents pas encore lus : la lecture est en cours, ce qui n'en dépend pas avance",
            f"{e1 and (e1.en_cours, e1.faits)}")
    b.check(e2 and "lecture" in e2.faits and e2.arret.motif == CD.ARRET_PARCOURS_TERMINE,
            "[K9] tout lu : le pas est fait, le parcours se termine", f"{e2 and (e2.faits, e2.arret)}")
    b.check(e2 and e2.depense.total_usd == 0.0, "[K9] la lecture ne dépense rien", f"{e2 and e2.depense}")
    vide = K.pas_lecture("lecture", K.VueLecture(), apres=("collecte",)).executer(CD.Contexte(dossier=EMETTEUR))
    b.check(vide.issue == CD.INDISPONIBLE and "aucun document" in vide.motif,
            "[K9] aucun document collecté : indisponible, nommé", f"{vide}")
    lu_impossible = K.VueLecture(documents=("a", "b"), lus=frozenset({"a", "b"}))
    b.check(K.pas_lecture("lecture", lu_impossible, apres=("collecte",)).executer(
        CD.Contexte(dossier=EMETTEUR)).issue == CD.FAIT,
        "[K9] une lecture impossible nommée compte comme lue : le dossier ne l'attend pas")

    # ── [K2] un lecteur amélioré lit à côté ─────────────────────────────────────────────────
    async def s_nouvelle_version():
        ref = dict(KC.referentiel())
        ref["lecteur"] = {**ref["lecteur"], "version": "9.9.9"}
        KC.referentiel.cache_clear()
        original = KC.referentiel
        KC.referentiel = lambda: ref
        try:
            relues = await K.lire_documents(kd, recueil_depot=rd, emetteur=EMETTEUR, le=LENDEMAIN)
            c = await K.lire_connaissance(kd, recueil_depot=rd, emetteurs_depot=ed, emetteur=EMETTEUR)
        finally:
            KC.referentiel = original
        return relues, c
    r2 = run(s_nouvelle_version())
    relues, c2 = r2 if r2 else ([], None)
    b.check(len(relues) == 6 and c2 and {l.lecteur for l in c2.lectures} == {"9.9.9"},
            "[K2] un lecteur amélioré produit une lecture nouvelle de chaque document", f"{len(relues)}")
    b.check(c2 and p1 and any(pl.piece.identifiant == p1.identifiant and pl.piece.lecteur == p1.lecteur
                              for pl in c2.pieces)
            and run(K.lire_lignes(kd, p1.empreinte, p1.lecteur)) is not None,
            "[K2] les pièces déjà citées gardent leur lecture, toujours lisible")

    return b.summary()


if __name__ == "__main__":
    sys.exit(main())
