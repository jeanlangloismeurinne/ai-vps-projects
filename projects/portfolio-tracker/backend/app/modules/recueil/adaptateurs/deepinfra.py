"""Le modèle réel : un appel au fournisseur DeepInfra, qui rend un objet JSON. Sans bibliothèque
réseau ni SDK : il passe par le transport, seul à toucher le réseau.

Un appel rend l'objet ET ce qu'il a coûté (`usage.estimated_cost` déclaré par DeepInfra ; à défaut,
les jetons au prix du référentiel). Ce qui n'est pas un objet JSON complet — refus, réponse coupée
par la limite de longueur, texte libre — est une `ModeleEnEchec` nommée, avec la dépense déjà
engagée : on ne rend jamais une réponse partielle comme bonne, et ce qui a été payé reste compté.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Mapping

from app.modules.chef_de_dossier.contrat import Depense

from . import PASSAGERES, Lu, Poste, referentiel_de


def _ref() -> Mapping[str, Any]:
    return referentiel_de("deepinfra.json")


class ModeleEnEchec(RuntimeError):
    def __init__(self, motif: str, depense: Depense | None = None) -> None:
        super().__init__(motif)
        self.depense = depense or Depense()


def _cout(modele: str, usage: Mapping[str, Any]) -> Depense:
    declare = usage.get("estimated_cost")
    if isinstance(declare, (int, float)) and not isinstance(declare, bool) and declare >= 0:
        return Depense(modeles_usd=float(declare))
    prix = _ref()["prix_usd_par_million_de_jetons"].get(modele) or _ref()["prix_de_repli"]
    entree, sortie = int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0)
    return Depense(modeles_usd=(entree * prix["entree"] + sortie * prix["sortie"]) / 1_000_000)


class ModeleDeepInfra:
    nom = "deepinfra"

    def __init__(self, transport: Poste, clef: str) -> None:
        self._transport, self._clef = transport, clef

    async def _envoyer(self, corps: Mapping[str, Any]) -> Lu:
        return await self._transport.envoyer(_ref()["adresse"], corps, en_tetes={"Authorization": f"Bearer {self._clef}"},
                                             delai_s=float(_ref()["delai_s"]))

    async def completer(self, *, modele: str, consigne: str, message: str, temperature: float,
                        max_jetons: int) -> tuple[dict[str, Any], Depense]:
        if not self._clef:
            raise ModeleEnEchec("DeepInfra : aucune clef")
        corps = {"model": modele, "temperature": temperature, "max_tokens": int(max_jetons),
                 "response_format": {"type": "json_object"},
                 "messages": [{"role": "system", "content": consigne}, {"role": "user", "content": message}]}
        lu: Lu = await self._envoyer(corps)
        # Une erreur passagère (mesuré le 2026-11-18 : 429 « modèle occupé », fréquent sur les longues
        # demandes) se reprend après chaque pause du référentiel, puis l'échec est nommé : jamais une boucle.
        for pause in _ref()["pauses_avant_reprise_s"]:
            if lu.statut not in PASSAGERES:
                break
            await asyncio.sleep(float(pause))
            lu = await self._envoyer(corps)
        if lu.statut != 200:
            raise ModeleEnEchec(f"DeepInfra : statut {lu.statut} {lu.contenu[:200].decode('utf-8', 'replace')}".strip())
        try:
            rep = json.loads(lu.contenu)
            choix = rep["choices"][0]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ModeleEnEchec(f"DeepInfra : réponse illisible ({type(exc).__name__})") from exc
        depense = _cout(modele, rep.get("usage") or {})
        if choix.get("finish_reason") == "length":
            raise ModeleEnEchec(f"réponse coupée à {max_jetons} jetons", depense)
        try:
            objet = json.loads(choix["message"]["content"] or "")
        except (ValueError, KeyError, TypeError) as exc:
            raise ModeleEnEchec(f"la réponse n'est pas un objet JSON ({type(exc).__name__})", depense) from exc
        if not isinstance(objet, dict):
            raise ModeleEnEchec("la réponse n'est pas un objet JSON", depense)
        return objet, depense
