"""Maillon 1 du découpage — l'INVENTAIRE (plan B4g, 2026-10-24) : la vérification par le CODE des fiches
que le modèle relève (`app/modele_entreprise/inventaire.verifier_inventaire`), le contrat, le prompt.

Hors-ligne, sans base ni modèle. Le texte des pièces est RÉEL : le verbatim de `me_7` NVDA (#2625, rendu du
dossier le 2026-10-24, `fixtures/architecte/2026-10-24/nvda_me7_verbatim.txt`). Mutations gardées par
`checks/negatif_inventaire.sh`.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Bilan  # noqa: E402

from pydantic import ValidationError  # noqa: E402

from app.agents.providers.base import MODEL_COSTS  # noqa: E402
from app.contracts.inventaire_schema import InventaireSortie  # noqa: E402
import app.modele_entreprise.inventaire as inv_mod  # noqa: E402
from app.modele_entreprise.inventaire import (  # noqa: E402
    MODELE_INVENTAIRE, cle_de_fiche, rendre_pieces, verifier_inventaire)

b = Bilan()
ME7 = (Path(__file__).resolve().parent / "fixtures" / "architecte" / "2026-10-24" / "nvda_me7_verbatim.txt"
       ).read_text(encoding="utf-8").strip()
ENTRIES = {
    997: {"title": "NVIDIA CORP — Moteurs de croissance identifiés dans le 10-Q T2 FY2027", "content": ME7,
          "source_date": "2026-07-26"},
    1010: {"title": "NVIDIA CORP — Acquisition Hugging Face (8-K du 2026-09-02)",
           "content": "Accord définitif du 2026-09-02 pour l'acquisition de Hugging Face ; clôture attendue au S1 2027.",
           "date_du_document": "2026-09-02"},
}


def F(**kw) -> dict:
    base = dict(nom="Vera CPU", marche_vise="IA agentique",
                extrait="Vera CPU, premier CPU pour l'IA agentique, ouvre un nouveau TAM de 200 Mds$",
                stade="lancé", origine="interne", pieces=[997])
    base.update(kw)
    return base


def V(*fiches, non_nommes=None):
    """Jamais un plantage du script : sous une mutation, l'assert visé doit rougir, pas le bilan mourir."""
    try:
        return verifier_inventaire(InventaireSortie.model_validate({"fiches": list(fiches), "non_nommes": non_nommes}),
                                   ENTRIES, "NVDA")
    except Exception as e:  # noqa: BLE001
        from types import SimpleNamespace
        return SimpleNamespace(fiches=[], ecartees=[SimpleNamespace(motif=f"PLANTAGE {e!r}")], non_nommes=None)


print("§1 vérification des fiches contre les pièces (réelles)")
r = V(F())
b.check(len(r.fiches) == 1 and not r.ecartees, f"fiche recopiée des pièces : admise ({r.ecartees})")
r = V(F(nom="VERA  cpu", extrait="vera cpu, premier CPU pour l’IA agentique, ouvre un nouveau TAM de 200 Mds$"))
b.check(len(r.fiches) == 1, f"casse, espaces et apostrophe typographique différents : admise ({r.ecartees})")
r = V(F(nom="Vera CPU Max"))
b.check(not r.fiches and "['nom']" in r.ecartees[0].motif, f"nom absent du dossier : écartée, motif dit ({r.ecartees})")
r = V(F(nom="Acquisition Hugging Face"))
b.check(len(r.fiches) == 1 and any("présent ailleurs au dossier" in x for x in r.signaux),
        f"nom absent de la pièce citée mais présent ailleurs au dossier (alias) : admise, SIGNALÉE ({r.signaux})")
r = V(F(marche_vise="processeurs pour serveurs"))
b.check(len(r.fiches) == 1 and r.fiches[0].marche_vise is None and any("non recopié" in x for x in r.signaux),
        f"marché visé reformulé (absent des pièces) : l'élément RESTE, le marché est retiré et dit ({r.signaux})")
r = V(F(extrait="Vera CPU est un processeur central conçu pour l'IA agentique et ses agents."))
b.check(not r.fiches and "extrait" in r.ecartees[0].motif, f"extrait paraphrasé : écartée ({r.ecartees})")
r = V(F(pieces=[4242]))
b.check(not r.fiches and "hors du dossier" in r.ecartees[0].motif, f"pièce hors du dossier : écartée ({r.ecartees})")
r = V(F(pieces=[1010]))
b.check(not r.fiches, "le nom figure dans le dossier, mais pas dans la pièce CITÉE : écartée")
r = V(F(marche_vise=None))
b.check(len(r.fiches) == 1, "aucun marché nommé (`null`) : admise, rien à vérifier")
r = V(F(), F(pieces=[997, 1010], nom="vera cpu"))
b.check(len(r.fiches) == 1 and r.fiches[0].pieces == [997, 1010],
        f"même élément × même marché relevé deux fois : FUSIONNÉ, pièces réunies ({[f.pieces for f in r.fiches]})")
from app.contracts.inventaire_schema import FicheElement  # noqa: E402
b.check(cle_de_fiche(FicheElement.model_validate(F(nom="zoldonrasib (RMC-9805)"))) ==
        cle_de_fiche(FicheElement.model_validate(F(nom="zoldonrasib"))),
        "une précision entre parenthèses ne change pas l'identité d'une fiche")
r = V(F(), F(marche_vise="agentique", extrait="premier CPU pour l'IA agentique, ouvre un nouveau TAM"))
b.check(len(r.fiches) == 2, "même nom, DEUX marchés : deux fiches (l'unité est l'élément × marché)")
b.check(len(r.fiches) == 2 and cle_de_fiche(r.fiches[0]) != cle_de_fiche(r.fiches[1]),
        "l'identité d'une fiche est nom × marché")

ENTRIES[1004] = {"title": "NVIDIA CORP — TAM CPU data center : $200 milliards pour Vera CPU",
                 "content": "le CEO Jensen Huang a annoncé que le processeur **Vera CPU** — premier CPU conçu "
                            "spécifiquement pour l'IA agentique — ouvre un **nouveau TAM de $200 milliards**"}
r = V(F(extrait="le processeur Vera CPU — premier CPU conçu spécifiquement pour l'IA agentique — ouvre un "
                "nouveau TAM de $200 milliards", pieces=[1004], marche_vise="l'IA agentique"))
b.check(len(r.fiches) == 1, f"pièce en gras Markdown (texte RÉEL de #1004) : l'extrait recopié sans le gras est admis ({r.ecartees})")
b.check(cle_de_fiche(V(F(nom="**Vera CPU**")).fiches[0]) == cle_de_fiche(V(F()).fiches[0]),
        "la mise en forme ne change pas l'identité d'une fiche")

print("§2 les non nommés")
NN = {"nombre": 2, "extrait": "Accord définitif du 2026-09-02 pour l'acquisition de Hugging Face", "pieces": [1010]}
b.check(V(non_nommes=NN).non_nommes is not None, "relevé des non nommés recopié : admis")
r = V(non_nommes={**NN, "extrait": "Deux programmes de recherche amont non divulgués à ce jour."})
b.check(r.non_nommes is None and "non nommés" in r.ecartees[0].motif, "relevé des non nommés inventé : écarté")
r = V(non_nommes={**NN, "pieces": [4242]})
b.check(r.non_nommes is None and r.ecartees, "relevé des non nommés sur une pièce hors du dossier : écarté")

print("§3 contrat")
try:
    InventaireSortie.model_validate({"fiches": [], "non_nommes": {**NN, "nombre": 0}})
    b.check(False, "contrat — `nombre` = 0 de non nommés devait être refusé")
except ValidationError:
    b.check(True, "contrat — `nombre` = 0 de non nommés refusé")
for champ, val in (("origine", "inconnue"), ("pieces", []), ("extrait", "trop court")):
    try:
        InventaireSortie.model_validate({"fiches": [F(**{champ: val})]})
        b.check(False, f"contrat — `{champ}` = {val!r} devait être refusé")
    except ValidationError:
        b.check(True, f"contrat — `{champ}` = {val!r} refusé")
try:
    InventaireSortie.model_validate({"fiches": [{**F(), "deja_vendu": True}]})
    b.check(False, "contrat — un champ de CLASSEMENT (`deja_vendu`) devait être refusé (Strict)")
except ValidationError:
    b.check(True, "contrat — l'inventaire ne classe pas : un champ de classement est refusé (Strict)")
b.check(InventaireSortie.model_validate(inv_mod._EXEMPLE).fiches[0].nom == "Produit Z",
        "contrat — l'exemple du prompt est valide")

print("§4 prompt, modèle, rendu")
p = inv_mod._INVENTAIRE_SYSTEM_PROMPT
b.check("une fiche par ÉLÉMENT × MARCHÉ" in p and "ne sont PAS des éléments : un ESSAI CLINIQUE (il sert une molécule" in p,
        "prompt — l'unité est FIXÉE (élément × marché ; un essai n'est pas un élément)")
b.check("sous le MÊME `nom`" in p and "MOT POUR MOT" in p, "prompt — même nom par marché ; recopier mot pour mot")
b.check("NE TRADUIS PAS" in p and "DANS LA LANGUE DE CETTE PIÈCE" in p and "les configurations ou déclinaisons" in p
        and "un PARTENAIRE" in p,
        "prompt — ne pas traduire ; une famille de produits, pas ses configurations")
b.check("Ne classe pas" in p and "parcours TOUTES les pièces" in p,
        "prompt — relever sans classer, toutes les pièces")
b.check(not any(w in p for w in ("classeur", "horloge", "archétype", "matière")),
        "prompt — vocabulaire standard, sans jargon maison")
b.check(MODELE_INVENTAIRE == "deepseek-ai/DeepSeek-V4.1-Flash-1017" and MODELE_INVENTAIRE in MODEL_COSTS,
        f"modèle — V4.1 Flash, version FIGÉE, coût tabulé : {MODELE_INVENTAIRE}")
t = rendre_pieces(ENTRIES)
b.check(t.index("Pièce #997") < t.index("Pièce #1010") and "(2026-09-02)" in t and "Vera CPU" in t,
        "rendu — chaque pièce avec son numéro, son titre, sa date du document et son contenu, dans l'ordre")

sys.exit(b.summary())
