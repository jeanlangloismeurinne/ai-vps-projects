"""Essai réel de l'évaluateur des sources inconnues (M2, B6 « réel ») — EN MÉMOIRE : aucune écriture
au journal des sources de production (il est en ajout seul : un essai y resterait).

Lit les publications par le vrai réseau et le vrai moteur (Exa), juge par le vrai modèle (DeepInfra),
puis range le jugement dans un dépôt M1 EN MÉMOIRE pour que M1 calcule la note et l'issue. Imprime
les publications lues, chaque réponse, la note, l'issue et la dépense. Coût mesuré le 2026-11-18 :
quelques millièmes de dollar par source.

    bash tools/essai_evaluateur.sh <domaine> [adresse rencontrée …] [--repetitions=N]

`--repetitions=N` : les publications sont lues UNE fois, puis le modèle juge N fois les mêmes textes
(stabilité du verdict à entrée identique) ; seule la dernière passe est rangée en mémoire.
`--modele=<nom DeepInfra>` : juge avec un autre modèle que celui du référentiel (comparaison de
modèles), sans toucher à `evaluateur.json`.
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.modules.emetteurs import contrat as E  # noqa: E402
from app.modules.recueil import contrat as R  # noqa: E402


class _Memo:
    """Garde les publications lues à la première passe : les suivantes rejugent les mêmes textes."""

    def __init__(self, evaluateur) -> None:
        self._e, self._lu = evaluateur, None
        self._orig = evaluateur._publications

    async def publications(self, source, adresses, n):
        if self._lu is None:
            self._lu = await self._orig(source, adresses, n)
            for t in self._lu[0]:
                print(f"lue : {t.adresse} — {len(t.texte)} caractères"
                      + (f" — reprise lue chez {t.lu_chez}" if t.lu_chez else "") + f" — fin : {t.texte[-50:]!r}")
            for a, d in self._lu[3].items():
                print(f"suivie sans reprise : {a} — {d}")
            print(f"lecture : {self._lu[1]}")
            return self._lu
        return self._lu[0], type(self._lu[1])(), *self._lu[2:]


async def main(source: str, adresses: list[str], repetitions: int, modele: str | None) -> int:
    if modele:
        from app.modules.recueil import evaluateur as ev_mod
        lire = ev_mod.referentiel
        ev_mod.referentiel = lambda: {**lire(), "modele": modele}
        print(f"modèle d'essai : {modele}")
    outils = R.outils_reels(clef_moteur=os.environ.get("EXA_API_KEY", ""))
    evaluateur = R.evaluateur_reel(outils, clef_modele=os.environ.get("DEEPINFRA_API_KEY", ""))
    evaluateur._publications = _Memo(evaluateur).publications
    for passe in range(1, repetitions + 1):
        try:
            evaluation, depense = await evaluateur(source, adresses)
        except Exception as exc:  # noqa: BLE001 — on imprime l'échec nommé et ce qu'il a coûté
            print(f"ÉCHEC {type(exc).__name__}: {exc}")
            print(f"dépense : {getattr(exc, 'depense', None)}")
            return 1
        if repetitions > 1:
            oui = sum(r.oui for ex in evaluation.exemples for r in ex.reponses)
            total = sum(len(ex.reponses) for ex in evaluation.exemples)
            non = sorted({r.question for ex in evaluation.exemples for r in ex.reponses if not r.oui})
            print(f"passe {passe} : critère « {evaluation.critere or '(aucun)'} » — {oui}/{total} oui — "
                  f"non sur : {', '.join(non) or '—'} — modèle {depense.modeles_usd} $")
    print(f"source {evaluation.source} — critère proposé « {evaluation.critere or '(aucun)'} » — "
          f"natures {', '.join(evaluation.natures)} — niveau {evaluation.niveau}")
    for ex in evaluation.exemples:
        print(f"\n## {ex.adresse}")
        for r in ex.reponses:
            print(f"  [{'oui' if r.oui else 'non'}] {r.question} — {r.constat}")
    issue = await E.evaluer_source(E.DepotMemoire(), evaluation, le=date.today().isoformat())
    print(f"\nissue (dépôt en mémoire) : {issue['issue']} — {issue['motif']}")
    print(f"dépense : modèles {depense.modeles_usd} $, web {depense.web_usd} $")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    reps = [int(a.split("=", 1)[1]) for a in sys.argv[2:] if a.startswith("--repetitions=")]
    modeles = [a.split("=", 1)[1] for a in sys.argv[2:] if a.startswith("--modele=")]
    args = [a for a in sys.argv[2:] if not a.startswith("--")]
    sys.exit(asyncio.run(main(sys.argv[1], args, reps[0] if reps else 1, modeles[0] if modeles else None)))
