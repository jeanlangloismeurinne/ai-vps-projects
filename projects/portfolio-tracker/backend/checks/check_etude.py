"""Contrôle du module « Étude » (le déclencheur du chef de dossier) — société fictive, sans base,
sans réseau, sans dépense. Acceptation : `roadmap/V3/M3-base-connaissance.md` §3, lignes K10 et K11
(société fictive), et l'arbitrage du 2026-11-21 sur la relecture humaine. Rougi par
`negatif_etude.sh`.

  [T0]  ni réseau, ni base, ni modèle dans le module
  [K10] mettre à l'étude : refusé sans fiche (motif), une seule étude par société ; un dossier non mis
        à l'étude n'avance jamais ; la tâche de fond relève, lit et fait avancer sans geste ; l'état
        du dossier et ce qu'il a lancé sont rangés ensemble ou pas du tout ; deux passages
        simultanés : le second ne fait rien ; rien de payant sur un dossier en pause ; un passage qui
        dépasse sa durée est arrêté, noté, et ne retient pas les autres dossiers
  [K11] les besoins : deux modules qui se recoupent → chaque genre une fois ; un troisième ne change
        aucun code ; un besoin mal formé ou d'un genre inconnu est refusé avec son module ; le besoin
        réel des comptes est celui de l'arbitrage (dernier annuel + données structurées)
  [L1]  un seul arrêt pour vous : après la collecte (fiche, évaluation des sources, mise en lecture ne
        s'arrêtent pas) ; rétablir une relecture = basculer une valeur
  [T1]  les gestes : acte non attendu, pause non posée, dossier non étudié → refus nommés
  [T2]  le journal des passages : seul un passage qui a fait quelque chose est noté ; une panne en
        route se dit dans le passage et n'empêche pas d'avancer

La société, ses domaines et ses documents sont fictifs (`.example` est réservé).
"""
from __future__ import annotations

import ast
import asyncio
import contextlib
import copy
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Bilan  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.modules.chef_de_dossier import contrat as CD  # noqa: E402
from app.modules.comptes import contrat as COMPTES  # noqa: E402
from app.modules.connaissance import contrat as K  # noqa: E402
from app.modules.emetteurs import contrat as E  # noqa: E402
from app.modules.etude import coeur as TC  # noqa: E402
from app.modules.etude import contrat as T  # noqa: E402
from app.modules.recueil import adaptateurs as AD  # noqa: E402
from app.modules.recueil import coeur as RC  # noqa: E402
from app.modules.recueil import contrat as R  # noqa: E402

MODULE = BACKEND / "app" / "modules" / "etude"
JOUR = "2026-11-21"
EMETTEUR = "FICTIVE-ETUDE"
AUTRE = "FICTIVE-ETUDE-BIS"
SITE = "fictive-etude.example"
SITE_BIS = "fictive-etude-bis.example"
INCONNUE = "miroir-inconnu.example"

RAPPORT = (b"<html><body><p>Fictive Etude Corp annual report.</p>"
           b"<table><tr><td>Total revenue</td><td>$</td><td>2,468</td></tr></table></body></html>")
DONNEES = b'{"facts": {"Revenue": [{"val": 2468}]}}'


class Bilan2(Bilan):
    def check(self, condition: bool, label: str, detail: str = "") -> bool:
        return super().check(bool(condition), label + (f" — {detail}" if detail and not condition else ""))


def run(coro):
    try:
        return asyncio.run(coro)
    except Exception as exc:  # noqa: BLE001 — l'assert attendu rougit, le contrôle atteint son bilan
        print(f"  (scénario planté : {type(exc).__name__}: {exc})")
        return None


def trouve(adresse, contenu, type_media):
    return AD.Trouve(R.Provenance(adaptateur="site_simule", adresse=adresse, publie_le="2026-02-26",
                                  faits_au="2025-12-31"), contenu, type_media)


class Simule:
    """Un adaptateur de la famille « site » : documents fixés par genre, une copie sur un domaine
    inconnu (source rencontrée), et un coût de recherche déclaré. Compte ses appels."""
    nom = "site_simule"
    famille = AD.SITE

    def __init__(self, cout_web: float = 0.0) -> None:
        self.cout_web = cout_web
        self.appels: list[str] = []

    def sait(self, genre: str) -> bool:
        return genre in ("derniers_comptes_annuels", "donnees_comptables_structurees")

    async def chercher(self, appel: AD.Appel) -> AD.Trouvaille:
        d = appel.demande
        self.appels.append(f"{d.emetteur}|{d.genre}")
        site = SITE if d.emetteur == EMETTEUR else SITE_BIS
        if d.genre == "derniers_comptes_annuels":
            trouves = [trouve(f"https://{site}/rapport.htm", RAPPORT + d.emetteur.encode(), "text/html"),
                       trouve(f"https://{INCONNUE}/{d.emetteur}/rapport.htm",
                              RAPPORT + b"copie" + d.emetteur.encode(), "text/html")]
        else:
            trouves = [trouve(f"https://{site}/donnees.json", DONNEES + d.emetteur.encode(), "application/json")]
        return AD.Trouvaille(trouves=trouves, depense=CD.Depense(web_usd=self.cout_web))


class Outils:
    def __init__(self, adaptateurs):
        self.transport, self.moteur, self.adaptateurs = None, None, adaptateurs


class Evaluateur:
    """L'évaluateur simulé : admet la source, compte ses appels par source."""

    def __init__(self, cout: float = 0.01) -> None:
        self.cout = cout
        self.appels: list[str] = []

    async def __call__(self, source, adresses):
        self.appels.append(source)
        questions = [q for q in E_QUESTIONS]
        pubs = tuple(E.ExempleEvalue(f"https://{source}/p{i}", tuple(E.Reponse(q, True, "constaté")
                                                                     for q in questions)) for i in range(3))
        return (E.Evaluation(source=source, portee=E.PORTEE_GENERALE, natures=("mesure",), niveau="B",
                             critere="presse_financiere", exemples=pubs), CD.Depense(modeles_usd=self.cout))


import json  # noqa: E402

E_QUESTIONS = list(json.loads((BACKEND / "app/modules/emetteurs/referentiel.json").read_text())
                   ["evaluation_des_sources"]["questions"])


@contextlib.contextmanager
def relecture(**interrupteurs):
    """Le temps d'un scénario, des interrupteurs de relecture autres que ceux en vigueur : le mécanisme
    d'arrêt reste prouvé quelle que soit la valeur choisie en production."""
    ref = copy.deepcopy(dict(TC.referentiel()))
    ref["lecture_humaine"] = {**ref["lecture_humaine"], **interrupteurs}
    anc = TC.referentiel
    TC.referentiel = lambda: ref
    try:
        yield
    finally:
        TC.referentiel = anc


def transaction_memoire(*depots):
    """Une transaction en mémoire : instantané des dépôts, restauré si le bloc lève (ce que la base
    fait par ROLLBACK). Sans elle, l'atomicité ne se prouverait pas sur la société fictive."""
    @contextlib.asynccontextmanager
    async def tx():
        avant = [copy.deepcopy(d.__dict__) for d in depots]
        try:
            yield
        except BaseException:
            for d, etat in zip(depots, avant):
                d.__dict__.clear()
                d.__dict__.update(etat)
            raise
    return tx


async def nouveau_monde(cout_web=0.0, evaluateur=None, avec_fiche=True, chef=None):
    ed, rd, kd, td = E.DepotMemoire(), R.DepotMemoire(), K.DepotMemoire(), T.DepotMemoire()
    chef = chef or CD.RangementMemoire()
    if avec_fiche:
        for dossier, site in ((EMETTEUR, SITE), (AUTRE, SITE_BIS)):
            await E.etablir_fiche(ed, dossier, raison_sociale=f"{dossier} Corp", auteur=E.UTILISATEUR,
                                  motif="ouverture", le=JOUR, lieux=[("site", site)])
    simule = Simule(cout_web)
    monde = T.Monde(etude=td, chef=chef, emetteurs=ed, recueil=rd, connaissance=kd,
                    outils=Outils([simule]), evaluateur=evaluateur or Evaluateur(),
                    transaction=transaction_memoire(chef, ed, rd, kd))
    return monde, simule


async def etat(monde, dossier=EMETTEUR) -> CD.EtatDossier:
    return CD.lire_etat(await monde.chef.ouvrir(dossier), dossier)


def main() -> int:
    b = Bilan2()

    # ── [T0] ni réseau, ni base, ni modèle ──────────────────────────────────────────────────
    interdits = {"urllib", "http", "socket", "httpx", "requests", "aiohttp", "asyncpg", "openai", "anthropic"}
    sources = sorted(p for p in MODULE.glob("*.py") if p.name != "depot_base.py")
    b.check(len(sources) >= 3, "[T0] le module est lu (contrat, cœur)", f"{[p.name for p in sources]}")
    fautifs = []
    for src in sources:
        for n in ast.walk(ast.parse(src.read_text(encoding="utf-8"))):
            noms = [a.name for a in n.names] if isinstance(n, ast.Import) else \
                [n.module or ""] if isinstance(n, ast.ImportFrom) else []
            fautifs += [f"{src.name}:{x}" for x in noms if x.split(".")[0] in interdits]
    b.check(not fautifs, "[T0] ni réseau, ni base, ni modèle dans le module", f"{fautifs}")

    # ── [K11] les besoins ───────────────────────────────────────────────────────────────────
    b.check(COMPTES.besoins_initiaux() == [{"genre": "derniers_comptes_annuels"},
                                          {"genre": "donnees_comptables_structurees"}],
            "[K11] le besoin réel des comptes : le dernier annuel et ses données structurées",
            f"{COMPTES.besoins_initiaux()}")
    b.check(TC.besoins_des_consommateurs() == {"comptes": COMPTES.besoins_initiaux()},
            "[K11] le passage rassemble les besoins déclarés par les modules consommateurs")
    deux = {"modele_a": [{"genre": "derniers_comptes_annuels"}, {"genre": "comptes_intermediaires", "depuis": "2026-01-01"}],
            "modele_b": [{"genre": "comptes_intermediaires", "depuis": "2026-01-01"}, {"genre": "derniers_comptes_annuels"},
                         {"genre": "annonces_importantes", "depuis": "2026-06-01"}]}
    dem = TC.rassembler(deux, EMETTEUR)
    b.check([(d.genre, d.depuis) for d in dem] == [("derniers_comptes_annuels", ""),
                                                   ("comptes_intermediaires", "2026-01-01"),
                                                   ("annonces_importantes", "2026-06-01")],
            "[K11] deux modules qui se recoupent : chaque genre demandé une fois", f"{dem}")
    trois = dict(deux, modele_c=[{"genre": "document_de_convocation"}, {"genre": "derniers_comptes_annuels"}])
    dem3 = TC.rassembler(trois, EMETTEUR)
    b.check(len(dem3) == 4 and dem3[:3] == dem and dem3[3].genre == "document_de_convocation",
            "[K11] un troisième module : sa demande s'ajoute, rien d'autre ne change", f"{dem3}")
    for besoins, quoi in (({"modele_x": [{"genre": "genre_qui_n_existe_pas"}]}, "genre inconnu"),
                          ({"modele_x": [{"genre": "derniers_comptes_annuels", "formulaire": "10-K"}]}, "champ inconnu"),
                          ({"modele_x": [{"genre": "comptes_intermediaires"}]}, "genre « depuis » sans date")):
        try:
            TC.rassembler(besoins, EMETTEUR)
            motif = None
        except R.DemandeRefusee as exc:
            motif = str(exc)
        except Exception as exc:  # noqa: BLE001 — un plantage n'est pas un refus nommé
            motif = f"(plantage {type(exc).__name__}: {exc})"
        b.check(motif is not None and "modele_x" in motif and "plantage" not in motif,
                f"[K11] un besoin mal formé est refusé avec le module qui l'a déclaré ({quoi})", f"{motif}")

    # ── [K10] mettre à l'étude ──────────────────────────────────────────────────────────────
    async def s_mise():
        monde, _ = await nouveau_monde()
        refus = None
        try:
            await T.mettre_a_l_etude(monde, "SANS-FICHE", par="gerant", motif="essai", le=JOUR)
        except T.GesteRefuse as exc:
            refus = str(exc)
        e1 = await T.mettre_a_l_etude(monde, EMETTEUR, par="gerant", motif="initiation", le=JOUR)
        e2 = await T.mettre_a_l_etude(monde, EMETTEUR, par="autre", motif="encore", le="2026-11-22")
        return refus, e1, e2, await monde.etude.etudes()
    r = run(s_mise())
    refus, e1, e2, etudes = r if r else (None, None, None, [])
    b.check(refus is not None and "fiche" in refus and "SANS-FICHE" in refus,
            "[K10] une société sans fiche ne se met pas à l'étude (motif nommé)", f"{refus}")
    b.check(e1 and e2 == e1 and len(etudes) == 1 and e1.par == "gerant",
            "[K10] une seule étude par société : la mettre deux fois rend l'étude d'origine", f"{e1} {e2} {etudes}")

    # ── [K10] un dossier non mis à l'étude n'avance jamais ──────────────────────────────────
    async def s_non_etudie():
        monde, simule = await nouveau_monde()
        p = await T.passer(monde, EMETTEUR, le=JOUR)
        await T.traiter_les_dossiers(monde, le=JOUR)
        return p, simule.appels, await monde.recueil.travaux(), await monde.chef.ouvrir(EMETTEUR)
    r = run(s_non_etudie())
    p, appels, travaux, d = r if r else (None, ["?"], ["?"], None)
    b.check(p and p.issue == T.NON_ETUDIE and not appels and not travaux and d and d.charger(EMETTEUR) is None,
            "[K10] un dossier non mis à l'étude n'avance jamais : ni état, ni collecte", f"{p} {appels} {travaux}")

    # ── [K10] [L1] bout en bout : la tâche de fond fait avancer, un seul arrêt ──────────────
    async def s_parcours():
        ev = Evaluateur()
        monde, simule = await nouveau_monde(evaluateur=ev)
        await T.mettre_a_l_etude(monde, EMETTEUR, par="gerant", motif="initiation", le=JOUR)
        etats, passages, actes = [], [], []
        for i in range(8):
            ps = await T.traiter_les_dossiers(monde, le=JOUR)
            passages += ps
            e = await etat(monde)
            etats.append(e)
            if e.arret and e.arret.motif == CD.ARRET_ACTE_HUMAIN:
                actes.append(e.arret.cle)
                await T.enregistrer_acte(monde, EMETTEUR, e.arret.cle, le=JOUR)
            if e.arret and e.arret.motif == CD.ARRET_PARCOURS_TERMINE:
                break
        return monde, simule, ev, etats, passages, actes
    r = run(s_parcours())
    monde, simule, ev, etats, passages, actes = r if r else (None, None, None, [], [], [])
    premier = etats[0] if etats else None
    b.check(premier and dict(premier.en_cours).get("collecte", "").startswith("collecte lancée")
            and "fiche_emetteur" in premier.faits,
            "[K10] premier passage : la fiche est faite, la collecte des besoins est lancée",
            f"{premier and (premier.faits, premier.en_cours)}")
    b.check(sorted(simule.appels if simule else []) == sorted([f"{EMETTEUR}|derniers_comptes_annuels",
                                                               f"{EMETTEUR}|donnees_comptables_structurees"]),
            "[K10] la tâche de fond relève les collectes lancées, chaque besoin une fois",
            f"{simule and simule.appels}")
    b.check(actes == [],
            "[L1] aucun arrêt pour vous : le dossier va au bout seul (collecte non relue depuis le 2026-11-22)",
            f"{actes}")
    fin = etats[-1] if etats else None
    b.check(fin and fin.arret and fin.arret.motif == CD.ARRET_PARCOURS_TERMINE
            and {"fiche_emetteur", "collecte", "evaluation_des_sources", "lecture"} <= set(fin.faits),
            "[K10] sans autre geste, le dossier va au bout (collecte, évaluation des sources, lecture)",
            f"{fin and (fin.faits, fin.arret)}")
    b.check(ev and ev.appels == [INCONNUE],
            "[K10] la source inconnue rencontrée est jugée une fois", f"{ev and ev.appels}")
    lus = [l for p in passages for l in p.lectures]
    b.check(len(lus) == 3 and any(l["statut"] != "lue" for l in lus),
            "[K10] les documents arrivés sont mis en lecture (données structurées comprises, sans objet)",
            f"{lus}")
    b.check(fin and fin.depense.modeles_usd == 0.01,
            "[K10] la dépense de l'évaluateur est déclarée au dossier", f"{fin and fin.depense}")

    # ── [L1] rétablir une relecture = basculer une valeur ───────────────────────────────────
    table = T.lecture_humaine()
    b.check(table.get("recueil") is False and table.get("recueil:evaluation_des_sources") is False
            and table.get("emetteurs") is False and table.get("connaissance") is False,
            "[L1] les interrupteurs en vigueur : rien n'est relu", f"{table}")

    async def s_relecture_retablie():
        with relecture(recueil=True):
            monde, _ = await nouveau_monde()
            await T.mettre_a_l_etude(monde, EMETTEUR, par="gerant", motif="initiation", le=JOUR)
            actes = []
            for i in range(8):
                await T.traiter_les_dossiers(monde, le=JOUR)
                e = await etat(monde)
                if e.arret and e.arret.motif == CD.ARRET_ACTE_HUMAIN:
                    actes.append(e.arret.cle)
                    await T.enregistrer_acte(monde, EMETTEUR, e.arret.cle, le=JOUR)
                if e.arret and e.arret.motif == CD.ARRET_PARCOURS_TERMINE:
                    break
            return actes
    actes2 = run(s_relecture_retablie())
    b.check(actes2 == ["lecture:collecte"],
            "[L1] rétablir la relecture de la collecte : une valeur, un arrêt", f"{actes2}")

    # ── [K10] ensemble ou pas du tout ───────────────────────────────────────────────────────
    class ChefQuiRefuse(CD.RangementMemoire):
        async def refermer(self, dossier, depot):
            raise CD.EcritureConcurrente("un autre passage a rangé (simulé)")

    async def s_atomique():
        chef = ChefQuiRefuse()
        monde, simule = await nouveau_monde(chef=chef)
        await T.mettre_a_l_etude(monde, EMETTEUR, par="gerant", motif="initiation", le=JOUR)
        p = await T.passer(monde, EMETTEUR, le=JOUR)
        return p, await monde.recueil.travaux(), chef.charger_brut() if hasattr(chef, "charger_brut") else \
            (await chef.ouvrir(EMETTEUR)).charger(EMETTEUR)
    r = run(s_atomique())
    p, travaux, brut = r if r else (None, ["?"], "?")
    b.check(p and not travaux and brut is None,
            "[K10] l'état refusé : aucune demande de collecte n'est lancée (rangés ensemble ou pas du tout)",
            f"{travaux} {brut}")
    b.check(p and "avancement du dossier" in p.detail and "EcritureConcurrente" in p.detail,
            "[K10] le refus se dit dans le passage", f"{p and p.detail}")

    # ── [K10] deux passages simultanés : le second ne fait rien ─────────────────────────────
    async def s_simultanes():
        monde, simule = await nouveau_monde()
        await T.mettre_a_l_etude(monde, EMETTEUR, par="gerant", motif="initiation", le=JOUR)
        await T.passer(monde, EMETTEUR, le=JOUR)          # la collecte est lancée
        assert await monde.etude.prendre(EMETTEUR)        # un premier passage tient le dossier
        p2 = await T.passer(monde, EMETTEUR, le=JOUR)
        apres_second = (list(simule.appels), await etat(monde))
        await monde.etude.rendre(EMETTEUR)
        p3 = await T.passer(monde, EMETTEUR, le=JOUR)
        return p2, apres_second, p3, simule.appels
    r = run(s_simultanes())
    p2, (appels2, e2), p3, appels3 = r if r else (None, ([], None), None, [])
    b.check(p2 and p2.issue == T.DEJA_EN_COURS and not appels2,
            "[K10] deux passages simultanés : le second ne relève rien", f"{p2} {appels2}")
    b.check(p3 and p3.issue == T.AVANCE and len(appels3) == 2,
            "[K10] le dossier rendu, le passage suivant reprend", f"{p3} {appels3}")

    # ── [K10] rien de payant sur un dossier en pause ────────────────────────────────────────
    async def s_pause():
        with relecture(recueil=True):  # l'autre dossier attend sa relecture : il reste ouvert au payant
            ev = Evaluateur()
            monde, simule = await nouveau_monde(cout_web=0.6, evaluateur=ev)   # 2 × 0,60 $ : le palier
            for dossier in (EMETTEUR, AUTRE):
                await T.mettre_a_l_etude(monde, dossier, par="gerant", motif="initiation", le=JOUR)
            en_pause = None
            for i in range(8):
                await T.traiter_les_dossiers(monde, le=JOUR)
                e = await etat(monde)
                if e.arret and e.arret.motif == CD.ARRET_PAUSE_DEPENSE:
                    en_pause = e
                    break
                if e.arret and e.arret.motif == CD.ARRET_ACTE_HUMAIN:
                    await T.enregistrer_acte(monde, EMETTEUR, e.arret.cle, le=JOUR)
            # Du travail payant attend sur les deux dossiers : une demande relancée, une source inconnue.
            for dossier in (EMETTEUR, AUTRE):
                d = R.Demande("derniers_comptes_annuels", dossier)
                t = next(t for t in await monde.recueil.travaux(dossier) if t["cle"] == d.cle)
                await monde.recueil.ecrire_travail({**t, "statut": R.LANCEE})
                await monde.recueil.noter_source_rencontree({
                    "source": f"autre-inconnue-{dossier.lower()}.example", "emetteur": dossier, "nature": "mesure",
                    "adresses": [f"https://autre-inconnue-{dossier.lower()}.example/x"], "vue_le": JOUR,
                    "statut": RC.A_EVALUER, "travail": d.cle, "essais": 0, "motif": ""})
            avant_appels, avant_ev = len(simule.appels), len(ev.appels)
            p_pause = await T.passer(monde, EMETTEUR, le=JOUR)
            payes_en_pause = (simule.appels[avant_appels:], ev.appels[avant_ev:])
            p_autre = await T.passer(monde, AUTRE, le=JOUR)
            payes_autre = (simule.appels[avant_appels:], ev.appels[avant_ev:])
            en_pause_intacts = (
                next(t for t in await monde.recueil.travaux(EMETTEUR)
                     if t["cle"] == R.Demande("derniers_comptes_annuels", EMETTEUR).cle)["statut"],
                next(s["statut"] for s in await monde.recueil.sources_rencontrees()
                     if s["source"] == "autre-inconnue-fictive-etude.example"))
            await T.lever_pause(monde, EMETTEUR, le=JOUR)
            p_leve = await T.passer(monde, EMETTEUR, le=JOUR)
            return en_pause, p_pause, payes_en_pause, payes_autre, en_pause_intacts, p_leve, simule.appels, ev.appels
    r = run(s_pause())
    en_pause, p_pause, payes_en_pause, payes_autre, intacts, p_leve, appels, ev_appels = \
        r if r else (None,) * 6 + ([], [])
    b.check(en_pause is not None, "[K10] le dossier atteint la pause de dépense (scénario)",
            f"{en_pause and en_pause.arret}")
    b.check(p_pause and p_pause.payant_suspendu and payes_en_pause == ([], []),
            "[K10] rien de payant sur un dossier en pause : ni collecte, ni évaluation de source",
            f"{p_pause} {payes_en_pause}")
    b.check(payes_autre and payes_autre[0] == [f"{AUTRE}|derniers_comptes_annuels"]
            and payes_autre[1] == ["autre-inconnue-fictive-etude-bis.example"],
            "[K10] un autre dossier, lui, avance (la pause est par dossier)", f"{payes_autre}")
    b.check(intacts == (R.LANCEE, RC.A_EVALUER),
            "[K10] le passage d'un autre dossier ne paie rien pour un dossier en pause", f"{intacts}")
    b.check(p_leve and not p_leve.payant_suspendu and f"{EMETTEUR}|derniers_comptes_annuels" in appels[-2:]
            and "autre-inconnue-fictive-etude.example" in ev_appels,
            "[K10] la pause levée, le travail payant reprend", f"{p_leve} {appels[-2:]} {ev_appels}")

    # ── [K10] un passage qui bloque est arrêté, noté, et ne retient pas les autres dossiers ──
    async def s_bloque():
        monde, simule = await nouveau_monde()
        for dossier in (EMETTEUR, AUTRE):
            await T.mettre_a_l_etude(monde, dossier, par="gerant", motif="initiation", le=JOUR)
        await T.traiter_les_dossiers(monde, le=JOUR)          # les collectes sont lancées
        anc = simule.chercher

        async def chercher_bloque(appel):
            if appel.demande.emetteur == EMETTEUR:
                await asyncio.sleep(3600)                    # le réseau ne répond plus (simulé)
            return await anc(appel)
        simule.chercher = chercher_bloque
        rendus = await T.traiter_les_dossiers(monde, le=JOUR, delai_par_dossier_s=0.2)
        reprise = await monde.etude.prendre(EMETTEUR)
        await monde.etude.rendre(EMETTEUR)
        return rendus, reprise, await monde.etude.passages(EMETTEUR), \
            [t["statut"] for t in await monde.recueil.travaux(EMETTEUR)]
    r = run(s_bloque())
    rendus, reprise, journal, statuts = r if r else ([], False, [], [])
    issues = {p.dossier: p.issue for p in rendus}
    b.check(issues.get(EMETTEUR) == T.INTERROMPU and "reprendra" in rendus[0].detail,
            "[K10] un passage qui dépasse sa durée est arrêté, motif nommé", f"{rendus[:1]}")
    b.check(issues.get(AUTRE) == T.AVANCE,
            "[K10] un dossier bloqué ne retient pas les autres dossiers", f"{issues}")
    b.check(reprise and journal and journal[-1]["issue"] == T.INTERROMPU and R.LANCEE in statuts,
            "[K10] arrêté : le verrou est rendu, l'arrêt noté au journal, la collecte reste à relever",
            f"{reprise} {journal[-1:]} {statuts}")
    b.check(TC.referentiel()["passage"]["delai_par_dossier_s"] > 0,
            "[K10] la durée d'un passage est une donnée du référentiel")

    # ── [T1] les gestes ─────────────────────────────────────────────────────────────────────
    async def s_gestes():
        with relecture(recueil=True):               # les gestes se jouent sur un arrêt : la collecte relue
            monde, _ = await nouveau_monde()
            refus = {}
            for nom, coro in (("non étudié", lambda: T.lever_pause(monde, EMETTEUR, le=JOUR)),):
                try:
                    await coro()
                except T.GesteRefuse as exc:
                    refus[nom] = str(exc)
            await T.mettre_a_l_etude(monde, EMETTEUR, par="gerant", motif="initiation", le=JOUR)
            await T.passer(monde, EMETTEUR, le=JOUR)
            await T.passer(monde, EMETTEUR, le=JOUR)       # la collecte a répondu : la relecture est attendue
            for nom, coro in (("acte non attendu", lambda: T.enregistrer_acte(monde, EMETTEUR, "lecture:lecture", le=JOUR)),
                              ("pause non posée", lambda: T.lever_pause(monde, EMETTEUR, le=JOUR)),
                              ("rien à relancer", lambda: T.relancer(monde, EMETTEUR, le=JOUR))):
                try:
                    await coro()
                except T.GesteRefuse as exc:
                    refus[nom] = str(exc)
            clair = await T.enregistrer_acte(monde, EMETTEUR, "lecture:collecte", le=JOUR)
            return refus, clair, await etat(monde)
    r = run(s_gestes())
    refus, clair, e = r if r else ({}, "", None)
    b.check("pas à l'étude" in refus.get("non étudié", ""), "[T1] un geste sur une société non étudiée est refusé",
            f"{refus}")
    b.check("lecture:collecte" in refus.get("acte non attendu", ""),
            "[T1] un acte non attendu est refusé, l'acte attendu est nommé", f"{refus}")
    b.check("pause" in refus.get("pause non posée", "") and "échec" in refus.get("rien à relancer", ""),
            "[T1] lever une pause non posée, relancer sans échec : refusés", f"{refus}")
    b.check(e and "lecture:collecte" in e.actes_accomplis and "Dossier" in clair,
            "[T1] l'acte attendu est enregistré et le dossier se rend en clair", f"{e and e.actes_accomplis}")

    # ── [T2] le journal des passages ; une panne en route ───────────────────────────────────
    async def s_journal():
        monde, _ = await nouveau_monde()
        await T.mettre_a_l_etude(monde, EMETTEUR, par="gerant", motif="initiation", le=JOUR)
        await T.passer(monde, EMETTEUR, le=JOUR)                    # la collecte est lancée

        async def ecriture_cassee(*a, **k):
            raise RuntimeError("disque plein (simulé)")
        anc = monde.connaissance.ranger_lecture
        monde.connaissance.ranger_lecture = ecriture_cassee
        casse = await T.passer(monde, EMETTEUR, le=JOUR)            # documents arrivés, lecture en panne
        monde.connaissance.ranger_lecture = anc
        relu = await T.passer(monde, EMETTEUR, le=JOUR)             # la lecture reprend
        n = len(await monde.etude.passages(EMETTEUR))
        vide = await T.passer(monde, EMETTEUR, le=JOUR)             # attend votre relecture : rien de neuf
        n_apres = len(await monde.etude.passages(EMETTEUR))
        lues = await T.lire_etudes(monde)
        return n, vide, n_apres, casse, relu, lues
    r = run(s_journal())
    n, vide, n_apres, casse, relu, lues = r if r else (0, None, -1, None, None, [])
    b.check(n == 3 and vide and vide.issue == T.RIEN_DE_NEUF and n_apres == n,
            "[T2] seul un passage qui a fait quelque chose est noté", f"{n} {vide} {n_apres}")
    b.check(casse and "mise en lecture" in casse.detail and "disque plein" in casse.detail,
            "[T2] une panne en route se dit dans le passage", f"{casse and casse.detail}")
    b.check(casse and any(ev.startswith("collecte : indisponible") or ev.startswith("collecte : fait")
                          for ev in casse.evenements),
            "[T2] la panne n'empêche pas le dossier d'avancer", f"{casse and casse.evenements}")
    b.check(relu and len(relu.lectures) == 3 and not relu.detail,
            "[T2] la panne passée, le passage suivant met en lecture", f"{relu}")
    b.check(len(lues) == 1 and lues[0].dernier_passage == relu
            and lues[0].dossier_en_clair.startswith(f"Dossier {EMETTEUR}"),
            "[T2] la lecture du module : l'étude, son dernier passage, le dossier en clair",
            f"{lues}")

    return b.summary()


if __name__ == "__main__":
    sys.exit(main())
