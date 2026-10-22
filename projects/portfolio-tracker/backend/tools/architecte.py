"""Lanceur de l'agent ARCHITECTE (lot M3, roadmap V3 `12-lot-M3-architecte.md` §7).

  python tools/architecte.py TICKER [--matiere-seule] [--hors-porte] [--ecrire] [--sortie FICHIER]

  · --matiere-seule (GRATUIT, lecture seule) : la porte question par question, puis la matière
    EXACTE envoyée au modèle, sa taille en caractères et une estimation en jetons (÷4, grossière).
  · défaut (à blanc, payant ~centimes) : un appel modèle (+ un renvoi au plus), l'architecture
    rendue en français, les signaux, le coût ; RIEN n'est écrit. `--sortie FICHIER` garde le JSON
    de l'`Architecture` posée (en-tête + sortie du modèle).
  · --hors-porte : admis seulement à blanc (`--ecrire` + `--hors-porte` est refusé).
  · --ecrire : réservé à Opus après lecture d'un passage à blanc — ÉCRIT (`architectures_modele`).

Bilan, reconnaissable par `grep -E` : `BILAN architecte <T> : ...` (voir `_bilan`).
Codes : 0 = bilan dressé (quel que soit son contenu) · 2 = pas mesurable (porte fermée, env absent…).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import traceback

from app.modele_entreprise.architecte import (
    ArchitectureRefusee, PorteFermee, proposer_architecture_du_titre,
)
from app.modele_entreprise.matiere import charger_matiere, rendre_matiere
from app.modele_entreprise.porte import porte_de_l_architecte
from app.modele_entreprise.referentiel import load_referentiel
from app.db.database import close_pool, get_db_session, init_pool


def _rendre_porte(porte) -> list[str]:
    out = []
    for q in porte.questions:
        out.append(f"  {q.question_id} ({q.framework_id}) — {'OUVRE' if q.ouvre else 'FERME'} — {q.raison}")
    etat = "ouverte" if porte.ouverte else f"fermée ({sum(1 for q in porte.questions if not q.ouvre)})"
    if porte.raison:
        etat += f" — {porte.raison}"
    elif not porte.ouverte and porte.archetype is None:
        etat += " — émetteur non classé"
    out.insert(0, f"Porte : {etat}")
    return out


def _rendre_architecture(arch) -> list[str]:
    out = [f"Architecture {arch.ticker_id} v{arch.version} (archétype {arch.archetype}, "
          f"famille {arch.famille}, référentiel {arch.version_referentiel})"]
    par_bloc = {b.id: b for b in arch.blocs}

    def _ligne_bloc(b, indent=0) -> None:
        prefixe = "  " * (indent + 1)
        if b.rattachement.type == "publie":
            ratt = f"publié (axe={b.rattachement.axe}, membre={b.rattachement.membre})"
        elif b.rattachement.type == "parent":
            ratt = f"estimé, enfant de `{b.rattachement.bloc}`"
        else:
            ratt = f"estimé, agrégé → `{b.rattachement.ligne}`"
        out.append(f"{prefixe}· {b.id} [{b.role}/{b.statut}/{b.maille}] — {ratt}")
        out.append(f"{prefixe}  motif : {b.motif}")
        if b.pieces:
            out.append(f"{prefixe}  pièces : {b.pieces}")
        out.append(f"{prefixe}  variables : {b.variables}")
        for enfant in arch.blocs:
            if enfant.rattachement.type == "parent" and enfant.rattachement.bloc == b.id:
                _ligne_bloc(enfant, indent + 1)

    premiers = [b for b in arch.blocs if b.rattachement.type != "parent"]
    for b in premiers:
        _ligne_bloc(b)
    if arch.variables_propres:
        out.append("Variables propres :")
        for v in arch.variables_propres:
            out.append(f"  · {v.id} ({v.libelle}) — {v.motif}")
    out.append("Passage à l'agrégé :")
    for p in arch.passage_a_l_agrege:
        out.append(f"  · {p.ligne} = {p.formule}")
    out.append("Cellules attendues :")
    par_auteur: dict[str, list[str]] = {}
    for c in arch.cellules_attendues:
        auteur = (f"question {c.auteur.question_id}" if c.auteur.type == "question" else "demande ciblée")
        par_auteur.setdefault(auteur, []).append(f"{c.bloc}.{c.variable} [{', '.join(c.periodes)}]")
    for auteur, lignes in sorted(par_auteur.items()):
        out.append(f"  · {auteur} :")
        for l in lignes:
            out.append(f"      {l}")
    return out


def _bilan(ticker: str, porte, statut: str, *, n_blocs=0, n_publies=0, n_estimes=0, n_cellules=0,
          n_signaux=0, cout=0.0) -> str:
    porte_txt = "ouverte" if porte.ouverte else f"fermée ({sum(1 for q in porte.questions if not q.ouvre)})"
    if porte.raison:
        porte_txt += f" ({porte.raison})"
    return (f"BILAN architecte {ticker} : porte {porte_txt} — {statut} — "
           f"{n_blocs} blocs ({n_publies} publiés / {n_estimes} estimés), {n_cellules} cellules "
           f"attendues, {n_signaux} signaux, {cout:.4f} $")


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--matiere-seule", action="store_true")
    ap.add_argument("--hors-porte", action="store_true")
    ap.add_argument("--ecrire", action="store_true")
    ap.add_argument("--sortie")
    args = ap.parse_args()

    if args.ecrire and args.hors_porte:
        print("`--ecrire` et `--hors-porte` ensemble sont refusés.", file=sys.stderr)
        return 2

    url = os.environ.get("DATABASE_URL") or ""
    if not url:
        print("DATABASE_URL manquante.", file=sys.stderr)
        return 2
    if not args.matiere_seule and not os.environ.get("DEEPINFRA_API_KEY"):
        print("DEEPINFRA_API_KEY manquante — l'appel modèle ne se simule pas.", file=sys.stderr)
        return 2

    await init_pool(url)
    try:
        ref = load_referentiel()
        async with get_db_session() as conn:
            from app.agents.v2.parcours import charger_etat_dossier
            etat = await charger_etat_dossier(conn, args.ticker)
            porte = porte_de_l_architecte(etat, ref)
            print("\n".join(_rendre_porte(porte)))

            if args.matiere_seule:
                try:
                    matiere = await charger_matiere(conn, args.ticker, publier=False)
                except Exception as e:  # noqa: BLE001
                    print(f"\nmatière non constructible : {e}")
                    print(_bilan(args.ticker, porte, "matière non constructible"))
                    return 0
                texte = rendre_matiere(matiere)
                print(f"\n{texte}\n")
                print(f"Taille de la matière : {len(texte)} caractères, ~{len(texte) // 4} jetons estimés.")
                print(_bilan(args.ticker, porte, "à blanc (matière seule)"))
                return 0

        try:
            resultat = await proposer_architecture_du_titre(
                args.ticker, ecrire=args.ecrire, hors_porte=args.hors_porte)
        except PorteFermee as e:
            print(f"\nporte fermée : {e}")
            print(_bilan(args.ticker, porte, "porte fermée"))
            return 2
        except ArchitectureRefusee as e:
            print(f"\narchitecture refusée après renvoi : {e.motifs}")
            print(f"coût cumulé : {e.cost_usd:.4f} $ ({e.attempts} tentative(s))")
            print(_bilan(args.ticker, porte, "refusée", cout=e.cost_usd))
            return 1

        arch = resultat.architecture
        print("\n" + "\n".join(_rendre_architecture(arch)))
        if resultat.signaux:
            print("\nSignaux :")
            for s in resultat.signaux:
                print(f"  · {s}")
        cout = resultat.run.cost_usd if resultat.run else 0.0
        print(f"\nCoût : {cout:.4f} $ ({resultat.run.attempts if resultat.run else 0} tentative(s))")

        if args.sortie:
            with open(args.sortie, "w", encoding="utf-8") as f:
                json.dump(arch.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
            print(f"JSON écrit dans {args.sortie}")

        n_publies = sum(1 for b in arch.blocs if b.maille == "publie")
        statut = (f"proposée v{arch.version}" + (" (écrite)" if resultat.ecrite_sous_id else "")
                 if not args.ecrire else f"écrite v{arch.version} (#{resultat.ecrite_sous_id})")
        print(_bilan(args.ticker, porte, statut if args.ecrire else f"proposée v{arch.version}",
                    n_blocs=len(arch.blocs), n_publies=n_publies, n_estimes=len(arch.blocs) - n_publies,
                    n_cellules=len(arch.cellules_attendues), n_signaux=len(resultat.signaux), cout=cout))
        return 0
    finally:
        await close_pool()


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(2)
