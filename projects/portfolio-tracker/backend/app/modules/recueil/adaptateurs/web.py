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

from ..contrat import Provenance
from . import WEB, Appel, MoteurInjoignable, Resultat, Trouvaille, Trouve, lire_avec_reprise, lisible, referentiel_de

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
            t.raison = "illisible" if any(n.startswith("illisible") for n in notes) else (
                "injoignable" if notes else "rien_publie")
            t.detail = " ; ".join(notes) or "aucun résultat dans la période demandée"
        return t
