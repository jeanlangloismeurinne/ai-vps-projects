"""Adaptateur « registre de la SEC » : les dépôts officiels d'une société enregistrée aux États-Unis.

Repris de l'ancien code (tri de `roadmap/V3/M2-collecte-sources.md` §1), réécrit en bibliothèque
standard derrière l'interface : le registre des symboles (`edgar_feed.resolve_cik`), la liste des
dépôts (`material_events._submissions`), le téléchargement d'une soumission et son découpage en
documents (`note_flash.telecharger_soumission`, `extraire_documents`) — le texte est gardé BRUT,
sans conversion. Les noms de formulaires sont dans `registre_sec.json`, nulle part ailleurs.
"""
from __future__ import annotations

import json
import re
from typing import Any, Mapping

from ..contrat import Provenance
from . import (
    REGISTRE,
    Appel,
    Identification,
    Lu,
    Transport,
    Trouvaille,
    Trouve,
    lire_avec_reprise,
    lisible,
    referentiel_de,
)

_BLOC = re.compile(rb"<DOCUMENT>(.*?)</DOCUMENT>", re.S)
_CHAMP = re.compile(rb"<(TYPE|FILENAME)>([^\r\n<]*)")
_TEXTE = re.compile(rb"<TEXT>\r?\n?(.*?)</TEXT>", re.S)


def _ref() -> Mapping[str, Any]:
    return referentiel_de("registre_sec.json")


def _norme(texte: str) -> str:
    """Un nom comparé sans casse, ponctuation ni espaces multiples."""
    return " ".join(re.sub(r"[^\w]+", " ", (texte or "").casefold()).split())


def _type_media(nom_fichier: str) -> str:
    n = nom_fichier.lower()
    if n.endswith((".htm", ".html")):
        return "text/html"
    if n.endswith(".xml"):
        return "application/xml"
    if n.endswith(".txt"):
        return "text/plain"
    if n.endswith(".pdf"):
        return "application/pdf"
    return ""


def _json(lu: Lu) -> Any:
    try:
        return json.loads(lu.contenu.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None


class RegistreSec:
    nom = "registre_sec"
    famille = REGISTRE

    def __init__(self) -> None:
        # La liste des dépôts lue pour l'identité sert à la recherche qui suit, une fois : une
        # collecte ne lit le registre qu'une fois par société (cadence bornée par le registre).
        self._lue: dict[str, Mapping[str, Any]] = {}

    def sait(self, genre: str) -> bool:
        return genre in _ref()["genres"]

    # ── L'identité (#147) ─────────────────────────────────────────────────────────────────

    def _numero(self, fiche: Any) -> str | None:
        return fiche.reference(_ref()["reference"])

    async def _depots(self, transport: Transport, numero: str) -> tuple[Mapping[str, Any] | None, str]:
        url = _ref()["adresses"]["depots"].format(numero10=f"{int(numero):010d}")
        lu = await lire_avec_reprise(transport, url)
        if lu.statut != 200:
            return None, f"liste des dépôts : réponse {lu.statut} ({url})"
        donnees = _json(lu)
        if not isinstance(donnees, dict):
            return None, f"liste des dépôts illisible ({url})"
        return donnees, url

    def _identite(self, depots: Mapping[str, Any], numero: str) -> Identification:
        ref = _ref()
        cotations = []
        for symbole, place in zip(depots.get("tickers") or [], depots.get("exchanges") or []):
            if symbole and place:
                cotations.append((ref["places"].get(place, place), symbole))
        adresse = ((depots.get("addresses") or {}).get("business") or {})
        etranger = adresse.get("isForeignLocation")
        domestique = etranger in (0, False) or (
            etranger is None and adresse.get("stateOrCountry") in ref["etats_domestiques"])
        pays = ref["pays_domestique"] if domestique else ""
        return Identification(
            issue="trouvee", registre=ref["libelle"], raison_sociale=str(depots.get("name") or "").strip(),
            pays=pays, cotations=tuple(cotations), references=((ref["reference"], str(int(numero))),))

    async def identifier(self, fiche: Any, transport: Transport) -> Identification:
        """Ce que le registre dit de l'émetteur. Avec un numéro à la fiche : on le lit. Sans : on
        cherche chaque nom que la fiche porte (identifiant maison, raison sociale, symboles) parmi les
        symboles et les raisons sociales du registre ; une seule société → trouvée ; plusieurs →
        homonyme, que le système ne tranche jamais."""
        ref = _ref()
        numero = self._numero(fiche)
        if numero is None:
            lu = await lire_avec_reprise(transport, ref["adresses"]["symboles"])
            table = _json(lu) if lu.statut == 200 else None
            if not isinstance(table, dict) or "data" not in table:
                return Identification("injoignable", ref["libelle"],
                                      detail=f"registre des symboles : réponse {lu.statut}")
            champs = table.get("fields") or ["cik", "name", "ticker", "exchange"]
            i_num, i_nom, i_sym = champs.index("cik"), champs.index("name"), champs.index("ticker")
            cherches = {fiche.emetteur, fiche.raison_sociale} | {c.symbole for c in fiche.cotations}
            par_symbole = {s.upper() for s in cherches if s}
            par_nom = {_norme(s) for s in cherches if s}
            trouves: dict[str, str] = {}
            for ligne in table["data"]:
                if str(ligne[i_sym] or "").upper() in par_symbole or _norme(str(ligne[i_nom])) in par_nom:
                    trouves[str(int(ligne[i_num]))] = str(ligne[i_nom])
            if not trouves:
                return Identification("inconnue", ref["libelle"],
                                      detail=f"aucune société du registre ne porte : {', '.join(sorted(cherches))}")
            if len(trouves) > 1:
                return Identification("homonyme", ref["libelle"], candidats=tuple(
                    f"{nom} ({num})" for num, nom in sorted(trouves.items())),
                    detail=f"{len(trouves)} sociétés du registre répondent à {', '.join(sorted(cherches))}")
            numero = next(iter(trouves))
        depots, ou = await self._depots(transport, numero)
        if depots is None:
            return Identification("injoignable", ref["libelle"], detail=ou)
        self._lue[str(int(numero))] = depots
        return self._identite(depots, numero)

    # ── Les documents ─────────────────────────────────────────────────────────────────────

    async def chercher(self, appel: Appel) -> Trouvaille:
        ref = _ref()
        numero = self._numero(appel.fiche)
        if numero is None:
            return Trouvaille(raison="non_applicable", detail="aucun numéro à ce registre sur la fiche")
        regle = ref["genres"][appel.demande.genre]
        if regle["lecture"] == "donnees":
            return await self._donnees(appel, numero)
        depots = self._lue.pop(str(int(numero)), None)
        if depots is None:
            depots, ou = await self._depots(appel.transport, numero)
            if depots is None:
                return Trouvaille(raison="injoignable", detail=ou)
        lignes = self._lignes(depots)
        choisis, mention = self._choisir(lignes, regle, appel)
        if not choisis:
            quand = f" depuis le {appel.demande.depuis}" if appel.demande.depuis else ""
            return Trouvaille(raison="rien_publie",
                              detail=f"aucun dépôt de ce genre{quand} parmi {len(lignes)} dépôts récents")
        t = Trouvaille()
        for ligne in choisis:
            m = mention if ligne["form"].split(ref["suffixe_amendement"])[0] in (
                regle.get("a_defaut") or {}).get("formulaires", ()) else ""
            sous = await self._lire_depot(appel, numero, ligne, regle, lignes, m)
            if sous.raison:
                return sous          # un dépôt choisi illisible : la demande le dit, rien de partiel
            t.trouves.extend(sous.trouves)
        return t

    def _lignes(self, depots: Mapping[str, Any]) -> list[dict[str, str]]:
        r = (depots.get("filings") or {}).get("recent") or {}
        n = len(r.get("accessionNumber") or [])
        cles = ("accessionNumber", "filingDate", "reportDate", "form", "primaryDocument")
        return [{k: str((r.get(k) or [""] * n)[i] or "") for k in cles} for i in range(n)]

    def _choisir(self, lignes: list[dict[str, str]], regle: Mapping[str, Any],
                 appel: Appel) -> tuple[list[dict[str, str]], str]:
        suffixe = _ref()["suffixe_amendement"]

        def de_base(forme: str) -> str:
            return forme[:-len(suffixe)] if forme.endswith(suffixe) else forme

        if appel.genre["etendue"] == "depuis":
            formes = set(regle["formulaires"])
            return sorted((l for l in lignes if de_base(l["form"]) in formes
                           and l["filingDate"] >= (appel.demande.depuis or "")),
                          key=lambda l: (l["filingDate"], l["accessionNumber"]), reverse=True), ""
        # « le dernier » : le plus récent des formulaires attendus ; à défaut, l'ordre du référentiel.
        for formes, mention in ((regle["formulaires"], ""),
                                *(((regle["a_defaut"]["formulaires"], regle["a_defaut"]["mention"]),)
                                  if regle.get("a_defaut") else ())):
            for forme in formes:
                originaux = [l for l in lignes if l["form"] == forme]
                if not originaux:
                    continue
                dernier = max(originaux, key=lambda l: (l["filingDate"], l["accessionNumber"]))
                amendements = [l for l in lignes if l["form"] == forme + suffixe
                               and l["reportDate"] == dernier["reportDate"]
                               and l["filingDate"] >= dernier["filingDate"]]
                return [dernier] + sorted(amendements, key=lambda l: l["filingDate"]), mention
            if not regle.get("a_defaut"):
                break
        return [], ""

    def _remplace(self, ligne: dict[str, str], lignes: list[dict[str, str]]) -> str:
        suffixe = _ref()["suffixe_amendement"]
        if not ligne["form"].endswith(suffixe):
            return ""
        base = ligne["form"][:-len(suffixe)]
        avant = [l for l in lignes if l["form"] == base and l["reportDate"] == ligne["reportDate"]
                 and l["filingDate"] <= ligne["filingDate"]]
        return max(avant, key=lambda l: l["filingDate"])["accessionNumber"] if avant else ""

    async def _lire_depot(self, appel: Appel, numero: str, ligne: dict[str, str], regle: Mapping[str, Any],
                          lignes: list[dict[str, str]], mention: str) -> Trouvaille:
        ref = _ref()
        acc = ligne["accessionNumber"]
        dossier = acc.replace("-", "")
        base = dict(adaptateur=self.nom, registre=ref["libelle"], identifiant=acc,
                    publie_le=ligne["filingDate"], faits_au=ligne["reportDate"],
                    remplace=self._remplace(ligne, lignes), mention=mention)
        if regle["lecture"] == "document_principal":
            url = ref["adresses"]["document"].format(numero=int(numero), dossier=dossier,
                                                      document=ligne["primaryDocument"])
            partie = ligne["form"]
            deja = (await appel.deja(acc)).get(partie)
            if deja:
                return Trouvaille(trouves=[Trouve(Provenance(adresse=url, partie=partie, **base), None, "", deja)])
            lu = await lire_avec_reprise(appel.transport, url)
            if lu.statut != 200:
                return Trouvaille(raison="injoignable", detail=f"{ligne['form']} {acc} : réponse {lu.statut}")
            tm = lu.type_media or _type_media(ligne["primaryDocument"])
            pourquoi = lisible(Lu(200, lu.contenu, tm), ref["formats_lus"])
            if pourquoi:
                return Trouvaille(raison="illisible", detail=f"{ligne['form']} {acc} : {pourquoi}")
            return Trouvaille(trouves=[Trouve(Provenance(adresse=url, partie=partie, **base), lu.contenu, tm)])

        # « soumission » : le dépôt complet, découpé en documents ; on garde le formulaire et les
        # pièces jointes que le référentiel nomme, chacun tel quel.
        url = ref["adresses"]["soumission"].format(numero=int(numero), dossier=dossier, accession=acc)
        rangees = await appel.deja(acc)
        if ligne["form"].upper() in rangees:
            # Déjà rangé (collecte interrompue, ou demandée deux fois) : on ne relit pas la soumission.
            return Trouvaille(trouves=[Trouve(Provenance(adresse=url, partie=p, **base), None, "", e)
                                       for p, e in sorted(rangees.items())])
        lu = await lire_avec_reprise(appel.transport, url)
        if lu.statut != 200:
            return Trouvaille(raison="injoignable", detail=f"{ligne['form']} {acc} : réponse {lu.statut}")
        t = Trouvaille()
        jointes = tuple(regle.get("parties_jointes") or ())
        for bloc in _BLOC.findall(lu.contenu):
            champs = {k.decode().upper(): v.decode("utf-8", "replace").strip() for k, v in _CHAMP.findall(bloc)}
            typ = champs.get("TYPE", "").upper()
            if typ != ligne["form"].upper() and not typ.startswith(jointes):
                continue
            texte = _TEXTE.search(bloc)
            contenu = texte.group(1) if texte else b""
            tm = _type_media(champs.get("FILENAME", "")) or "text/plain"
            pourquoi = lisible(Lu(200, contenu, tm), ref["formats_lus"])
            if pourquoi:
                if typ == ligne["form"].upper():
                    return Trouvaille(raison="illisible", detail=f"{ligne['form']} {acc} : {pourquoi}")
                continue         # une pièce jointe illisible (image, PDF) n'emporte pas le dépôt
            partie = typ if typ == ligne["form"].upper() else f"{typ} {champs.get('FILENAME', '')}".strip()
            t.trouves.append(Trouve(Provenance(adresse=url, partie=partie, **base), contenu, tm))
        if not any(x.provenance.partie == ligne["form"].upper() for x in t.trouves):
            return Trouvaille(raison="illisible", detail=f"{ligne['form']} {acc} : formulaire absent de la soumission")
        return t

    async def _donnees(self, appel: Appel, numero: str) -> Trouvaille:
        ref = _ref()
        url = ref["adresses"]["donnees"].format(numero10=f"{int(numero):010d}")
        lu = await lire_avec_reprise(appel.transport, url)
        if lu.statut == 404:
            return Trouvaille(raison="rien_publie", detail="le registre ne publie aucune donnée structurée pour ce numéro")
        if lu.statut != 200:
            return Trouvaille(raison="injoignable", detail=f"données structurées : réponse {lu.statut}")
        pourquoi = lisible(Lu(200, lu.contenu, lu.type_media or "application/json"), ref["formats_lus"])
        if pourquoi or not isinstance(_json(lu), dict):
            return Trouvaille(raison="illisible", detail=f"données structurées : {pourquoi or 'JSON illisible'}")
        return Trouvaille(trouves=[Trouve(Provenance(adaptateur=self.nom, adresse=url, registre=ref["libelle"],
                                                     identifiant=url, partie="donnees"),
                                          lu.contenu, "application/json")])
