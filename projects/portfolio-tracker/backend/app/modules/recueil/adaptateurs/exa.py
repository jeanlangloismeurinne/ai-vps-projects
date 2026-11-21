"""Le moteur de recherche réel : Exa. Repris de l'ancien code (`websearch.ExaBackend`) derrière
l'interface `Moteur`, sans bibliothèque réseau : il passe par le transport, seul à toucher le réseau.

Deux gestes : chercher (des adresses, leur titre, leur date si Exa la connaît) et rendre le texte de
pages qu'Exa a lues depuis chez lui (`contenus`) — le second chemin quand une page refuse la lecture
directe (mesuré le 2026-11-18 : Reuters répond 401 au VPS, Exa en rend le texte). Chaque demande
déclare ce qu'elle a coûté, tel qu'Exa le dit ; sans ce chiffre, un coût de repli prudent. Un refus
ou un silence d'Exa est une `MoteurInjoignable` nommée, jamais une liste vide.
"""
from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from app.modules.chef_de_dossier.contrat import Depense

from . import Lu, MoteurInjoignable, Poste, Resultat, Texte, referentiel_de


def _ref() -> Mapping[str, Any]:
    return referentiel_de("exa.json")


def _jour(valeur: Any) -> str:
    v = str(valeur or "")
    return v[:10] if len(v) >= 10 and v[4] == "-" and v[7] == "-" else ""


class MoteurExa:
    nom = "exa"

    def __init__(self, transport: Poste, clef: str) -> None:
        self._transport, self._clef = transport, clef

    @property
    def caracteres_par_page(self) -> int:
        """Ce que l'équipe demande au plus par page : un texte de cette longueur a été coupé par nous."""
        return int(_ref()["caracteres_par_page"])

    async def _demander(self, quoi: str, corps: Mapping[str, Any]) -> Mapping[str, Any]:
        if not self._clef:
            raise MoteurInjoignable("Exa : aucune clef")
        lu: Lu = await self._transport.envoyer(_ref()["adresses"][quoi], corps, en_tetes={"x-api-key": self._clef},
                                               delai_s=float(_ref()["delai_s"]))
        if lu.statut != 200:
            raise MoteurInjoignable(f"Exa {quoi} : statut {lu.statut} {lu.contenu[:200].decode('utf-8', 'replace')}".strip())
        try:
            rep = json.loads(lu.contenu)
        except ValueError as exc:
            raise MoteurInjoignable(f"Exa {quoi} : réponse illisible ({exc})") from exc
        if not isinstance(rep, dict):
            raise MoteurInjoignable(f"Exa {quoi} : réponse illisible")
        return rep

    @staticmethod
    def _cout(rep: Mapping[str, Any], repli: float) -> Depense:
        total = (rep.get("costDollars") or {}).get("total") if isinstance(rep.get("costDollars"), dict) else None
        ok = isinstance(total, (int, float)) and not isinstance(total, bool) and total >= 0
        return Depense(web_usd=float(total) if ok else repli)

    async def rechercher(self, requete: str, *, domaines: Sequence[str] = (), depuis: str = "",
                         nombre: int = 5, categorie: str = "", exclus: Sequence[str] = (),
                         avec_texte: bool = False) -> tuple[list[Resultat], Depense]:
        # `depuis` n'est pas transmis : Exa écarterait les pages qu'il ne sait pas dater ; l'adaptateur
        # filtre lui-même ce qui est daté.
        corps: dict[str, Any] = {"query": requete, "numResults": int(nombre), "type": _ref()["type_de_recherche"]}
        if domaines:
            corps["includeDomains"] = list(domaines)
        if exclus:
            corps["excludeDomains"] = list(exclus)
        if avec_texte:
            corps["contents"] = {"text": {"maxCharacters": int(_ref()["caracteres_par_page"])}}
        if categorie:
            if categorie not in _ref()["categories"]:
                raise MoteurInjoignable(f"Exa : catégorie inconnue au référentiel : {categorie!r}")
            corps["category"] = _ref()["categories"][categorie]
        rep = await self._demander("recherche", corps)
        resultats = [Resultat(adresse=x["url"], titre=str(x.get("title") or "").strip(), publie_le=_jour(x.get("publishedDate")),
                              texte=str(x.get("text") or "").strip() if avec_texte else "")
                     for x in rep.get("results") or [] if isinstance(x, dict) and x.get("url")]
        return resultats, self._cout(rep, float(_ref()["cout_de_repli_usd"]["recherche"]))

    async def contenus(self, adresses: Sequence[str]) -> tuple[list[Texte], Depense]:
        adresses = [a for a in dict.fromkeys(adresses) if a]
        if not adresses:
            return [], Depense()
        rep = await self._demander("contenus", {"urls": adresses,
                                                "text": {"maxCharacters": int(_ref()["caracteres_par_page"])}})
        textes = []
        for x in rep.get("results") or []:
            if not isinstance(x, dict):
                continue
            # Exa rend l'adresse demandée dans `id` (l'`url` peut être normalisée) : on répond par
            # l'adresse demandée, sinon l'appelant ne retrouverait pas sa page.
            adresse = x.get("id") if x.get("id") in adresses else x.get("url")
            texte = str(x.get("text") or "").strip()
            if adresse in adresses and texte:
                textes.append(Texte(adresse=adresse, texte=texte, titre=str(x.get("title") or "").strip(),
                                    publie_le=_jour(x.get("publishedDate"))))
        repli = float(_ref()["cout_de_repli_usd"]["page"]) * len(adresses)
        return textes, self._cout(rep, repli)
