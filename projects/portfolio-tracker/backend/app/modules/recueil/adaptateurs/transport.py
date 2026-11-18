"""Le transport réel : lire une adresse sur le réseau, ou lui ENVOYER une demande en JSON (moteur de
recherche, modèle), en bibliothèque standard. Seul fichier du module qui touche le réseau ; les
contrôles le remplacent par un transport simulé.

Un seul détenteur pour la politesse envers chaque hôte : l'en-tête d'identification et la cadence
maximale que l'hôte impose (règle publique du registre : 10 demandes par seconde), lues dans le
référentiel de l'adaptateur qui en a besoin. Aucune reprise ici : la seconde tentative est
`lire_avec_reprise`, partagée par tous les adaptateurs.
"""
from __future__ import annotations

import asyncio
import json
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from typing import Any, Mapping

from . import Lu, referentiel_de

TAILLE_MAX = 80_000_000
DELAI_S = 60


class TransportReel:
    def __init__(self) -> None:
        sec = referentiel_de("registre_sec.json")
        hotes = {urlsplit(u).hostname for u in sec["adresses"].values()}
        self._politesse = {h: (sec["en_tete_identification"], 1.0 / sec["demandes_par_seconde"]) for h in hotes}
        self._dernier: dict[str, float] = {}
        self._verrou = asyncio.Lock()

    async def lire(self, adresse: str) -> Lu:
        hote = urlsplit(adresse).hostname or ""
        agent, ecart = self._politesse.get(hote, ("Mozilla/5.0 (compatible; portfolio-tracker/2.0)", 0.0))
        async with self._verrou:
            attente = self._dernier.get(hote, 0.0) + ecart - time.monotonic()
            if attente > 0:
                await asyncio.sleep(attente)
            self._dernier[hote] = time.monotonic()
        return await asyncio.to_thread(self._lire, adresse, agent)

    @staticmethod
    def _lire(adresse: str, agent: str) -> Lu:
        req = urllib.request.Request(adresse, headers={"User-Agent": agent, "Accept": "*/*"})
        try:
            with urllib.request.urlopen(req, timeout=DELAI_S) as r:
                contenu = r.read(TAILLE_MAX + 1)
                return Lu(r.status, contenu, r.headers.get("Content-Type", ""))
        except urllib.error.HTTPError as e:
            return Lu(e.code, b"", "")
        except (urllib.error.URLError, TimeoutError, OSError):
            return Lu(0, b"", "")

    async def envoyer(self, adresse: str, corps: Mapping[str, Any], *, en_tetes: Mapping[str, str],
                      delai_s: float = DELAI_S) -> Lu:
        """Une demande POST en JSON. Rend le statut et le corps tels quels : c'est l'appelant qui sait
        lire la réponse de SON service, et qui nomme l'échec."""
        return await asyncio.to_thread(self._envoyer, adresse, json.dumps(corps).encode("utf-8"),
                                       dict(en_tetes), delai_s)

    @staticmethod
    def _envoyer(adresse: str, corps: bytes, en_tetes: dict[str, str], delai_s: float) -> Lu:
        req = urllib.request.Request(adresse, data=corps, method="POST",
                                     headers={"Content-Type": "application/json", "Accept": "application/json",
                                              **en_tetes})
        try:
            with urllib.request.urlopen(req, timeout=delai_s) as r:
                return Lu(r.status, r.read(TAILLE_MAX + 1), r.headers.get("Content-Type", ""))
        except urllib.error.HTTPError as e:
            return Lu(e.code, e.read(4000), "")
        except (urllib.error.URLError, TimeoutError, OSError):
            return Lu(0, b"", "")
