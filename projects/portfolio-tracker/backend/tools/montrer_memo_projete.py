"""Montre la NOTE DE COMITÉ telle qu'elle sort du classeur — en TEXTE, sans rien dépenser.

POURQUOI CET OUTIL EXISTE
--------------------------
Même raison que `montrer_dossier.py`, un cran plus loin dans la chaîne : le rendu d'un inventaire
est un PRODUCTEUR, et ce qu'il omet se lit comme une propriété du sujet
(`feedback_rendu_est_un_producteur`). Une note dont un chapitre manque se lit « rien à signaler
sur ce sujet » — le comité délibère alors sur une absence qu'il croit constatée. La seule façon de
le savoir est de lire la note **telle qu'elle part**, en texte.

C'est la frontière gratuite du lot (`feedback_frontiere_gratuite_avant_depense_modele`) : aucun
appel de modèle, aucune écriture. Lecture de `framework_answers` + `knowledge_entries`, puis
`projection_memo.servir_memo()`. À rejouer après CHAQUE correctif, pas une seule fois au début.

⚠️ CE QU'IL N'EST PAS. Il n'asserte rien et ne rend pas de verdict : c'est
`checks/check_memo_projete.py` qui juge. Un outil qui montre ET qui juge finit par montrer ce qu'il
sait juger.

    bash tools/montrer_memo_projete.sh RVMD

Codes : 0 = note dressée et imprimée · 1 = la projection a REFUSÉ · 2 = pas mesurable.
"""
from __future__ import annotations

import asyncio
import os
import sys
import traceback

from app.agents.v2.projection_memo import ProjectionRefusee, servir_memo
from app.contracts.memo_projete_schema import ETATS_RUBRIQUE
from app.db.database import close_pool, get_db_session, init_pool

LARGEUR = 78

# Un marqueur par état, et la couverture est VÉRIFIÉE au chargement plutôt que constatée par un
# `KeyError` au milieu d'une impression à moitié faite. Un rendu est un producteur : le jour où le
# contrat gagne un cinquième état, cet outil doit refuser d'imprimer, pas l'imprimer sans marque.
MARQUES = {
    "instruite": "✓",
    "sans_acquittement": "◦",
    "non_revalidable": "?",
    "pas_de_methodologie_approuvee": "·",
}
_absents = sorted(set(ETATS_RUBRIQUE) - set(MARQUES))
if _absents:
    raise SystemExit(f"tools/montrer_memo_projete.py : états sans marqueur — {_absents}")


def _coupe(texte: str, n: int) -> str:
    """Tronque en DISANT qu'on tronque — détenteur unique des six coupes de cet outil (#46).

    Les six `[:n]` étaient muets. Mesuré sur RVMD le 2026-09-24 : un motif d'actualité coupé rendait
    « (8-K du 2026-08-27 (déposé le 2026-0 », visiblement mutilé — donc inoffensif. Le cas dangereux
    est l'autre : une coupe qui tombe par chance sur une fin de mot se lit comme une phrase ENTIÈRE,
    et le lecteur attribue au sujet un silence qui est une propriété de notre affichage. C'est
    exactement `feedback_rendu_est_un_producteur`, que la docstring de ce fichier énonce trois
    lignes plus haut sans que le code la tienne.
    """
    return texte if len(texte) <= n else texte[:n] + " […tronqué à l'affichage]"


def _imprimer(memo) -> None:
    print(f"\n{'─' * LARGEUR}")
    print(f"NOTE DE COMITÉ (projetée) — {memo.ticker_id} · référentiel {memo.framework_version}")
    print(f"dressée le {memo.genere_le:%Y-%m-%d %H:%M} UTC · posture {memo.posture}")
    print(f"{'─' * LARGEUR}")

    for r in memo.rubriques:
        print(f"\n {MARQUES[r.etat]} {r.bloc.upper()}   [{r.etat}]")
        print(f"     {r.motif}")
        for p in r.points:
            a = p.answer
            print(f"\n     — {p.question_id} · {p.enonce}")
            print(f"       statut {a.statut}"
                  + (f" · analyste {a.analyste}" if a.analyste else "")
                  + (f" · ligne #{p.answer_id}" if p.answer_id is not None else ""))
            if a.reponse is not None:
                valeur = ("" if a.reponse.valeur is None
                          else f"  [{a.reponse.valeur} {a.reponse.unite}]")
                sens = "" if a.reponse.sens is None else f"  ({a.reponse.sens})"
                print(f"       {_coupe(a.reponse.verbatim, 300)}{valeur}{sens}")
            if a.sans_objet is not None:
                sub = (a.sans_objet.substitut_applique or
                       ("aucun substitut" if a.sans_objet.aucun_substitut else "?"))
                print(f"       hors-sujet motivé : {_coupe(a.sans_objet.motif, 250)}")
                print(f"       substitut : {sub}")
            if a.fondation is not None:
                print(f"       fondation : rang {a.fondation.rang_derive} · "
                      f"nature {a.fondation.nature_effective} · "
                      f"actualité {a.fondation.actualite} — "
                      f"{_coupe(a.fondation.motif_actualite, 120)}")
                print(f"       entries citées : {a.fondation.cited_entry_ids}")
            if a.approximation is not None:
                print(f"       approximation : {_coupe(a.approximation.methode, 180)}")
                print(f"       sensibilité : {_coupe(a.approximation.sensibilite, 180)}")

    # Le bandeau final DIT la forme de ce qu'il vient d'imprimer. Un bilan se reconnaît à sa forme
    # (`feedback_bilan_par_sa_forme`) : sans lui, une note vide et une note tronquée se lisent
    # pareil.
    par_etat: dict[str, int] = {}
    for r in memo.rubriques:
        par_etat[r.etat] = par_etat.get(r.etat, 0) + 1
    points = sum(len(r.points) for r in memo.rubriques)
    refusees = sum(r.reponses_non_acquittees for r in memo.rubriques)
    print(f"\n{'─' * LARGEUR}")
    print(f"BILAN — {len(memo.rubriques)} chapitre(s) : "
          + " · ".join(f"{n} {e}" for e, n in sorted(par_etat.items())))
    print(f"        {points} point(s) publié(s) · {refusees} réponse(s) au dossier non acquittée(s)")
    print(f"{'─' * LARGEUR}\n")


async def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    ticker_id = sys.argv[1]

    url = os.environ.get("DATABASE_URL") or ""
    if not url:
        print("DATABASE_URL manquante — la note n'est pas lisible, elle ne se devine pas.",
              file=sys.stderr)
        return 2

    await init_pool(url)
    try:
        async with get_db_session() as conn:
            memo = await servir_memo(conn, ticker_id)
    except ProjectionRefusee as e:
        # Un refus est un RÉSULTAT à lire, pas une panne de l'outil : il nomme une réponse qui ne
        # se range pas. Code 1, distinct du 2 « pas mesurable ».
        print(f"\nPROJECTION REFUSÉE — {e}\n", file=sys.stderr)
        return 1
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return 2
    finally:
        await close_pool()

    _imprimer(memo)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
