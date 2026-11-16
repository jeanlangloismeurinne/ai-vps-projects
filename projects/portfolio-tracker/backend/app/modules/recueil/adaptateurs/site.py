"""Adaptateur « site de l'émetteur » : les pages que la société publie elle-même, aux lieux que sa
fiche déclare (M1). Aucun lieu n'est deviné : sans lieu à la fiche, l'adaptateur ne s'applique pas.

Repris de l'ancien code (`websearch.fetch_url`) : la lecture directe d'une adresse ; un PDF n'est pas
lu et devient une raison nommée, jamais un silence. Les mots qui mènent d'une page à un genre de
document sont dans `site.json`. Une page ne dit pas toujours sa date : elle reste vide, jamais devinée.
"""
from __future__ import annotations

from typing import Any, Mapping

from ..contrat import Provenance
from . import SITE, Appel, Trouvaille, Trouve, liens, lire_avec_reprise, lisible, referentiel_de

PARTIE = "page"


def _ref() -> Mapping[str, Any]:
    return referentiel_de("site.json")


def _url(adresse: str) -> str:
    return adresse if "//" in adresse else "https://" + adresse


class SiteEmetteur:
    nom = "site_emetteur"
    famille = SITE

    def sait(self, genre: str) -> bool:
        return genre in _ref()["genres"]

    async def _page(self, appel: Appel, url: str, t: Trouvaille, notes: list[str]) -> bytes | None:
        """Lit une page et la range dans `t` si elle est lisible ; sinon note pourquoi."""
        deja = (await appel.deja(url)).get(PARTIE)
        if deja:
            t.trouves.append(Trouve(Provenance(adaptateur=self.nom, adresse=url, identifiant=url, partie=PARTIE),
                                    None, "", deja))
            return None
        lu = await lire_avec_reprise(appel.transport, url)
        if lu.statut != 200:
            notes.append(f"injoignable {url} ({lu.statut})")
            return None
        pourquoi = lisible(lu, _ref()["formats_lus"])
        if pourquoi:
            notes.append(f"illisible {url} ({pourquoi})")
            return None
        t.trouves.append(Trouve(Provenance(adaptateur=self.nom, adresse=url, identifiant=url, partie=PARTIE),
                                lu.contenu, lu.type_media or "text/html"))
        return lu.contenu

    async def chercher(self, appel: Appel) -> Trouvaille:
        regle = _ref()["genres"][appel.demande.genre]
        t, notes = Trouvaille(), []
        if regle.get("adresse_de_la_demande"):
            if not appel.demande.adresse.strip():
                return Trouvaille(raison="non_applicable", detail="la demande ne donne pas d'adresse")
            await self._page(appel, _url(appel.demande.adresse.strip()), t, notes)
            return t if t.trouves else self._raison(notes)

        lieux = [l for g in _ref()["lieux_parcourus"] for l in appel.fiche.lieux if l.genre == g]
        if not lieux:
            return Trouvaille(raison="non_applicable", detail="aucun lieu de publication sur la fiche")
        mots = [m.casefold() for m in regle["mots"]]
        for lieu in lieux:
            url = _url(lieu.adresse)
            lu = await lire_avec_reprise(appel.transport, url)
            if lu.statut != 200:
                notes.append(f"injoignable {url} ({lu.statut})")
                continue
            vus = liens(lu.contenu, url)
            t.rencontrees.extend(a for a, _ in vus)
            retenus = [a for a, texte in vus if any(m in (texte + " " + a).casefold() for m in mots)]
            for a in retenus:
                if sum(1 for x in t.trouves) >= regle["nombre"]:
                    break
                await self._page(appel, a, t, notes)
            if t.trouves:
                break
        if t.trouves:
            return t
        if not notes:
            notes.append(f"aucun lien vers ce genre de document sur {', '.join(l.adresse for l in lieux)}")
        r = self._raison(notes)
        r.rencontrees = t.rencontrees
        return r

    @staticmethod
    def _raison(notes: list[str]) -> Trouvaille:
        if any(n.startswith("illisible") for n in notes):
            raison = "illisible"
        elif any(n.startswith("injoignable") for n in notes):
            raison = "injoignable"
        else:
            raison = "rien_publie"
        return Trouvaille(raison=raison, detail=" ; ".join(notes))
