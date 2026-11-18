"""L'évaluateur réel des sources inconnues (#145, M1 A17) : un rôle distinct de celui qui collecte.

Il reçoit une source (un domaine) et les adresses où la collecte l'a rencontrée ; il lit au moins
autant de publications de CETTE source que la grille de M1 en exige — celles rencontrées d'abord,
complétées par une recherche limitée au domaine ; chaque page lue en direct, à défaut par le texte
que le moteur en a lu depuis chez lui — puis demande au modèle de répondre à la grille.

Ce que le modèle décide : une réponse motivée par question et par publication, et le critère écrit
qui décrit la source (ou aucun). Ce qu'il ne décide pas : la note et l'issue (calculées par M1) ; le
niveau et les natures quand un critère est choisi (ceux que le critère écrit accorde). Une réponse
hors de la forme demandée, ou qui porte sur une page qu'on ne lui a pas donnée, n'est jamais
« complétée » : c'est un échec nommé, avec ce qui a été dépensé, et la source reste à évaluer.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from app.modules.chef_de_dossier.contrat import Depense
from app.modules.emetteurs import contrat as E

from .adaptateurs import Texte, lire_avec_reprise, lisible, texte_de

FORMATS_LUS = ("text/", "application/xhtml", "application/xml")


@lru_cache(maxsize=None)
def referentiel() -> Mapping[str, Any]:
    return json.loads(Path(__file__).with_name("evaluateur.json").read_text(encoding="utf-8"))


class EvaluationImpossible(RuntimeError):
    """La source n'a pas pu être jugée cette fois. Porte ce qui a été dépensé pour essayer."""

    def __init__(self, motif: str, depense: Depense) -> None:
        super().__init__(motif)
        self.depense = depense


def _de_la_source(source: str, adresse: str) -> bool:
    hote = E.domaine(adresse)
    chemin = urlsplit(adresse if "//" in adresse else "https://" + adresse).path
    return bool(hote) and (hote == source or hote.endswith("." + source)) and chemin not in ("", "/")


def message(source: str, grille: Mapping[str, Any], publications: Sequence[Texte]) -> str:
    """Ce que le modèle reçoit : la grille et les critères tels que M1 les écrit, les publications."""
    lignes = [f"Source à juger : {source}", "",
              "Critères écrits (donnez la clé de celui qui décrit cette source, ou \"\" si aucun ne convient) :"]
    for cle, c in grille["criteres"].items():
        lignes.append(f"- {cle} : {c['texte']} (niveau maximal {c['niveau_max']} ; vaut pour : {', '.join(c['natures'])})")
    lignes += ["", f"Échelle des niveaux, du plus sûr au moins sûr : {', '.join(grille['niveaux'])}",
               f"Natures d'information : {', '.join(grille['natures'])}", "",
               "Questions (pour chaque publication : oui ou non, et ce que vous avez constaté) :"]
    lignes += [f"- {cle} : {texte}" for cle, texte in grille["questions"].items()]
    for i, p in enumerate(publications, 1):
        lignes += ["", f"### Publication {i}", f"Adresse : {p.adresse}", f"Titre : {p.titre or '(non donné)'}",
                   f"Date annoncée : {p.publie_le or '(non donnée)'}", "Texte :", p.texte]
    forme = {"critere": "<clé ou chaîne vide>", "natures": ["<nature>"], "niveau": "<niveau>",
             "publications": [{"adresse": "<adresse exacte de la publication>",
                               "reponses": {q: {"oui": True, "constat": "<ce que vous avez constaté>"}
                                            for q in grille["questions"]}}]}
    lignes += ["", "Format de réponse (un objet JSON, une entrée par publication) :",
               json.dumps(forme, ensure_ascii=False, indent=1)]
    return "\n".join(lignes)


def lire_reponse(source: str, grille: Mapping[str, Any], publications: Sequence[Texte],
                 objet: Mapping[str, Any]) -> E.Evaluation:
    """Traduit la réponse du modèle en `Evaluation` de M1, ou refuse (ValueError) : chaque publication
    donnée, et elle seule, reçoit une réponse à chaque question, motivée."""
    questions = list(grille["questions"])
    donnees = [p.adresse for p in publications]
    pubs = objet.get("publications")
    if not isinstance(pubs, list):
        raise ValueError("pas de liste « publications »")
    vues: dict[str, E.ExempleEvalue] = {}
    for p in pubs:
        adresse = p.get("adresse") if isinstance(p, dict) else None
        if adresse not in donnees:
            raise ValueError(f"réponse sur une page qu'on ne lui a pas donnée : {adresse!r}")
        if adresse in vues:
            raise ValueError(f"deux réponses pour la même publication : {adresse}")
        reponses = p.get("reponses")
        if not isinstance(reponses, dict) or sorted(reponses) != sorted(questions):
            raise ValueError(f"{adresse} : il faut une réponse à chaque question de la grille, et à elles seules")
        rs = []
        for q in questions:
            r = reponses[q]
            if not isinstance(r, dict) or not isinstance(r.get("oui"), bool):
                raise ValueError(f"{adresse} — {q} : « oui » doit valoir vrai ou faux")
            constat = r.get("constat")
            if not isinstance(constat, str) or not constat.strip():
                raise ValueError(f"{adresse} — {q} : réponse sans constat")
            rs.append(E.Reponse(q, r["oui"], constat.strip()))
        vues[adresse] = E.ExempleEvalue(adresse, tuple(rs))
    manquent = [a for a in donnees if a not in vues]
    if manquent:
        raise ValueError(f"publications sans réponse : {', '.join(manquent)}")

    critere = objet.get("critere")
    critere = critere.strip() if isinstance(critere, str) else None
    if critere is None or (critere and critere not in grille["criteres"]):
        raise ValueError(f"critère hors de la liste écrite : {objet.get('critere')!r}")
    if critere:
        # Le niveau et les natures sont ceux que le critère écrit accorde : le modèle n'a pas de levier dessus.
        natures, niveau = tuple(grille["criteres"][critere]["natures"]), grille["criteres"][critere]["niveau_max"]
    else:
        natures = objet.get("natures")
        niveau = objet.get("niveau")
        if (not isinstance(natures, list) or not natures or any(n not in grille["natures"] for n in natures)
                or niveau not in grille["niveaux"]):
            raise ValueError(f"sans critère, natures et niveau proposés hors de l'échelle : {natures!r}, {niveau!r}")
        natures = tuple(dict.fromkeys(natures))
    return E.Evaluation(source=source, portee=E.PORTEE_GENERALE, natures=natures, niveau=niveau, critere=critere,
                        exemples=tuple(vues[a] for a in donnees))


class EvaluateurDeSources:
    """L'`Evaluateur` du contrat : `await evaluateur(source, adresses)` → (`Evaluation`, dépense)."""

    def __init__(self, *, transport: Any, moteur: Any, modele: Any) -> None:
        self._transport, self._moteur, self._modele = transport, moteur, modele

    async def _publications(self, source: str, adresses: Sequence[str], n: int) -> tuple[list[Texte], Depense, list[str]]:
        """Au moins `n` publications lisibles de la source : celles rencontrées d'abord ; une recherche
        limitée au domaine seulement s'il en manque ; chaque page lue en direct, à défaut par le texte
        du moteur. Rien hors du domaine de la source."""
        ref = referentiel()
        depense, notes = Depense(), []
        lues: list[Texte] = []
        vues: set[str] = set()
        candidats = [a for a in dict.fromkeys(adresses) if _de_la_source(source, a)][: ref["candidats_max"]]
        titres: dict[str, Any] = {}
        recherches = list(ref["recherches"]) if self._moteur is not None else []
        while True:
            a_relire: list[str] = []
            for a in candidats:
                if len(lues) >= n:
                    break
                vues.add(a)
                lu = await lire_avec_reprise(self._transport, a if "//" in a else "https://" + a)
                pourquoi = f"statut {lu.statut}" if lu.statut != 200 else lisible(lu, FORMATS_LUS)
                texte = "" if pourquoi else texte_de(lu.contenu)
                if not pourquoi and len(texte) < ref["caracteres_min"]:
                    pourquoi = f"texte trop court ({len(texte)} caractères)"
                if pourquoi:
                    notes.append(f"{a} : {pourquoi}")
                    a_relire.append(a)
                    continue
                r = titres.get(a)
                lues.append(Texte(a, texte, r.titre if r else "", r.publie_le if r else ""))
            if len(lues) < n and a_relire and hasattr(self._moteur, "contenus"):
                # Seulement ce qui manque, plus une page de marge : chaque page lue par le moteur se paie.
                textes, d = await self._moteur.contenus(a_relire[: n - len(lues) + 1])
                depense = depense.plus(d)
                for t in textes:
                    if len(lues) < n and len(t.texte) >= ref["caracteres_min"]:
                        lues.append(t)
            if len(lues) >= n or not recherches:
                break
            r = recherches.pop(0)
            trouves, d = await self._moteur.rechercher(r["requete"].format(source=source), domaines=[source],
                                                       nombre=ref["candidats_max"], categorie=r["categorie"])
            depense = depense.plus(d)
            titres.update({x.adresse: x for x in trouves})
            # Une recherche limitée à un site rend aussi ses pages de rubrique (des listes d'articles, pas
            # des publications) ; le moteur ne date que les publications : les pages datées d'abord.
            candidats = [x.adresse for x in sorted(trouves, key=lambda x: not x.publie_le)
                         if _de_la_source(source, x.adresse) and x.adresse not in vues]
        coupe = ref["caracteres_par_publication"]
        return [Texte(t.adresse, t.texte[:coupe], t.titre, t.publie_le) for t in lues[:n]], depense, notes

    async def __call__(self, source: str, adresses: Sequence[str]) -> tuple[E.Evaluation, Depense]:
        ref = referentiel()
        grille = E.grille_d_evaluation()
        n = grille["exemples_min"]
        try:
            publications, depense, notes = await self._publications(source, adresses, n)
        except Exception as exc:  # noqa: BLE001 — le moteur en panne : nommé, la source reste à évaluer
            raise EvaluationImpossible(f"lecture des publications : {type(exc).__name__}: {exc}", Depense()) from exc
        if len(publications) < n:
            raise EvaluationImpossible(
                f"{len(publications)} publication(s) lisible(s) de {source} sur {n} exigées"
                + (f" ({' ; '.join(notes[:4])})" if notes else ""), depense)
        try:
            objet, d = await self._modele.completer(modele=ref["modele"], consigne=ref["consigne"],
                                                    message=message(source, grille, publications),
                                                    temperature=float(ref["temperature"]),
                                                    max_jetons=int(ref["max_jetons"]))
        except Exception as exc:  # noqa: BLE001
            raise EvaluationImpossible(f"modèle : {exc}", depense.plus(getattr(exc, "depense", None) or Depense())) from exc
        depense = depense.plus(d)
        try:
            return lire_reponse(source, grille, publications, objet), depense
        except ValueError as exc:
            raise EvaluationImpossible(f"réponse du modèle hors de la forme demandée : {exc}", depense) from exc
