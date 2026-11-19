"""Adaptateur « web » : un moteur de recherche, les domaines de la fiche d'abord, le web ouvert
ensuite (#133 : la source d'origine d'abord, à défaut ailleurs).

Repris de l'ancien code (`websearch.web_search`, `fetch_url`) derrière l'interface : le moteur est
INJECTÉ (simulé sur une société fictive, sans dépense). Chaque recherche déclare ce qu'elle coûte.
Un document d'une source inconnue est gardé, marqué non admis par le cœur, et sa source part à
l'évaluateur ; l'adaptateur ne juge rien.
"""
from __future__ import annotations

from typing import Any, Mapping

from app.modules.chef_de_dossier.contrat import Depense
from app.modules.emetteurs import contrat as E

from ..contrat import Provenance
from . import WEB, Appel, MoteurInjoignable, Resultat, Texte, Trouvaille, Trouve, lire_avec_reprise, lisible, referentiel_de
from . import apercus

PARTIE = "page"


def _ref() -> Mapping[str, Any]:
    return referentiel_de("web.json")


class Web:
    nom = "web"
    famille = WEB

    def sait(self, genre: str) -> bool:
        return genre in _ref()["genres"]

    async def chercher(self, appel: Appel) -> Trouvaille:
        if appel.moteur is None:
            return Trouvaille(raison="non_applicable", detail="aucun moteur de recherche n'est branché")
        regle = _ref()["genres"][appel.demande.genre]
        requete = regle["requete"].format(raison_sociale=appel.fiche.raison_sociale)
        domaines = sorted({l.adresse.split("/", 1)[0] for l in appel.fiche.lieux})
        depense = Depense()
        resultats: list[Resultat] = []
        for restreint in ([domaines] if domaines else []) + [[]]:
            try:
                r, d = await appel.moteur.rechercher(requete, domaines=restreint, depuis=appel.demande.depuis,
                                                     nombre=regle["nombre"])
            except MoteurInjoignable as exc:
                if resultats:
                    break   # le web ouvert ne répond pas : on garde ce que les domaines de la fiche ont rendu
                return Trouvaille(raison="injoignable", detail=f"moteur de recherche : {exc}", depense=depense)
            depense = depense.plus(d)
            resultats.extend(x for x in r if x.adresse not in {y.adresse for y in resultats})
        t = Trouvaille(depense=depense, rencontrees=[r.adresse for r in resultats])
        notes: list[str] = []
        suivis = 0
        for r in resultats:
            if len(t.trouves) >= regle["nombre"]:
                break
            if appel.demande.depuis and r.publie_le and r.publie_le < appel.demande.depuis:
                continue
            prov = Provenance(adaptateur=self.nom, adresse=r.adresse, identifiant=r.adresse, partie=PARTIE,
                              publie_le=r.publie_le)
            deja = (await appel.deja(r.adresse)).get(PARTIE)
            if deja:
                t.trouves.append(Trouve(prov, None, "", deja))
                continue
            lu = await lire_avec_reprise(appel.transport, r.adresse)
            if lu.statut in apercus.ref()["acces_refuses"] and hasattr(appel.moteur, "contenus"):
                # Accès refusé : au mieux un aperçu, qui n'est jamais rangé (P1) ; il sert de signal (P2, P3).
                if suivis >= int(apercus.ref()["suivis_max_par_demande"]):
                    notes.append(f"apercu {r.adresse} ({lu.statut}) : non suivi, {suivis} suivis déjà faits")
                    continue
                suivis += 1
                trouve, note, d = await self._suivre(appel, r, domaines)
                t.depense = t.depense.plus(d)
                if trouve is None:
                    notes.append(note)
                elif trouve.provenance.identifiant not in {x.provenance.identifiant for x in t.trouves}:
                    t.trouves.append(trouve)
                continue
            if lu.statut != 200:
                notes.append(f"injoignable {r.adresse} ({lu.statut})")
                continue
            pourquoi = lisible(lu, _ref()["formats_lus"])
            if pourquoi:
                notes.append(f"illisible {r.adresse} ({pourquoi})")
                continue
            t.trouves.append(Trouve(prov, lu.contenu, lu.type_media or "text/html"))
        if t.trouves:
            return t
        if not resultats:
            t.raison, t.detail = "rien_publie", f"aucun résultat pour « {requete} »"
        else:
            t.raison = next((r for r in ("illisible", "apercu", "injoignable") if any(n.startswith(r) for n in notes)),
                            "rien_publie")
            t.detail = " ; ".join(notes) or "aucun résultat dans la période demandée"
        return t

    async def _suivre(self, appel: Appel, r: Resultat, domaines: list[str]) -> tuple[Trouve | None, str, Depense]:
        """Un aperçu (page à l'accès refusé) : son texte par le moteur, puis UNE recherche par son titre
        (`apercus.suivre`). La pièce d'origine, sur un lieu de la fiche et lisible, passe devant la reprise."""
        source = E.domaine(r.adresse) or ""
        try:
            textes, depense = await appel.moteur.contenus([r.adresse])
        except MoteurInjoignable as exc:
            return None, f"apercu {r.adresse} : moteur de recherche : {exc}", Depense()
        texte = next((x for x in textes if x.adresse == r.adresse), None)
        apercu = Texte(r.adresse, texte.texte if texte else "", r.titre or (texte.titre if texte else ""),
                       r.publie_le or (texte.publie_le if texte else ""))
        suite = await apercus.suivre(appel.moteur, apercu, source=source, lieux=domaines)
        depense = depense.plus(suite.depense)
        for o in suite.origine:
            # Mesuré le 2026-11-19 : le site IR de Broadridge refuse la lecture directe (403) ; le moteur,
            # lui, a rendu son texte avec la recherche (déjà payé) : il est rangé, dit en texte brut.
            lu = await lire_avec_reprise(appel.transport, o.adresse)
            prov = Provenance(adaptateur=self.nom, adresse=o.adresse, identifiant=o.adresse, partie=PARTIE,
                              publie_le=o.publie_le,
                              mention=f"pièce d'origine, signalée par l'aperçu {r.adresse} (« {apercu.titre} »)")
            if lu.statut == 200 and not lisible(lu, _ref()["formats_lus"]):
                return Trouve(prov, lu.contenu, lu.type_media or "text/html"), "", depense
            if o.texte:
                return Trouve(prov, o.texte.encode("utf-8"), "text/plain; charset=utf-8"), "", depense
        if suite.reprise is not None:
            lieu = suite.reprise.lu_chez
            prov = Provenance(adaptateur=self.nom, adresse=r.adresse, identifiant=lieu, partie=PARTIE,
                              publie_le=apercu.publie_le, mention=f"reprise sous licence : {suite.detail}")
            lu = await lire_avec_reprise(appel.transport, lieu)
            if lu.statut == 200 and not lisible(lu, _ref()["formats_lus"]):
                return Trouve(prov, lu.contenu, lu.type_media or "text/html"), "", depense
            return Trouve(prov, suite.reprise.texte.encode("utf-8"), "text/plain; charset=utf-8"), "", depense
        return None, f"apercu {r.adresse} : {suite.detail}", depense
