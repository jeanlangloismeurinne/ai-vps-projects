"""Recoupe CHAQUE nombre d'une réponse rédigée avec le texte des pièces qu'elle cite — en lecture
seule, sans modèle (méthode de relecture des jalons A3/A4 de `05-frameworks-complets.md`).

Pourquoi un outil : les quatre contrôles du manager gardent la STRUCTURE, jamais le sens (#78) ; un
`repondu` peut porter un chiffre calculé ou tiré d'une pièce NON citée (D-me6). Relire à la main
chaque nombre contre chaque pièce ne se refait pas deux fois de la même façon ; cet outil le refait
à l'identique (A10/A11 : comparer deux passages).

    bash tools/recouper_nombres.sh RVMD management_capital          # réponses courantes du chapitre
    bash tools/recouper_nombres.sh RVMD management_capital --ids 1451,1452

Pour chaque réponse : les nombres du texte rédigé (verbatim, effets des faits postérieurs, méthode
d'approximation) — chacun « retrouvé » dans une pièce citée, ou « ABSENT des pièces citées » avec,
s'il existe, l'id d'une pièce COURANTE du titre qui le porte (signe d'une citation manquante). Les
chiffres de l'encadré ne sont PAS recoupés : ceux du socle et les calculs sont produits par le code.

Tolérance : un nombre écrit avec d décimales est retrouvé si une pièce porte une valeur qui
l'arrondit à ±½ unité de sa dernière décimale, à un facteur d'unité près (k, M, Md). Un entier
qui est l'id d'une pièce citée est un renvoi (« source 1296 »), pas un chiffre. Les entiers
< 10 ne sont pas recoupés (trop communs) ; les années (1900-2100) le sont à l'identique.

⚠️ Il n'asserte rien : un ABSENT est une ligne À LIRE, pas un verdict (un pourcentage calculé par
l'analyste et annoncé comme tel est légitime). Codes : 0 = recoupé · 2 = pas lisible.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys

_GROUPES = re.compile(r"\d{1,3}(?:[   ]\d{3})+(?:,\d+)?")
_SIMPLE = re.compile(r"\d+(?:[.,]\d+)*")
_FACTEURS = (1, 1e3, 1e-3, 1e6, 1e-6, 1e9, 1e-9)


def _valeurs(jeton: str, francais: bool) -> list[tuple[float, int]]:
    """(valeur, nombre de décimales écrites) — plusieurs lectures si le séparateur est ambigu."""
    t = re.sub(r"[   ]", "", jeton)
    out: list[tuple[float, int]] = []
    if "," in t and "." in t:
        dec = "," if t.rfind(",") > t.rfind(".") else "."
        mil = "." if dec == "," else ","
        ent, _, fr = t.replace(mil, "").partition(dec)
        out.append((float(f"{ent}.{fr}"), len(fr)))
    elif "," in t or "." in t:
        sep = "," if "," in t else "."
        parts = t.split(sep)
        milliers = len(parts) > 1 and all(len(p) == 3 for p in parts[1:])
        if len(parts) == 2:
            # le séparateur décimal de la langue : virgule en français, point en anglais ;
            # l'autre ne sépare QUE des milliers (« 394,919 » anglais n'est jamais 394,919 décimal)
            decimal = (sep == ",") == francais
            if decimal:
                out.append((float(f"{parts[0]}.{parts[1]}"), len(parts[1])))
            elif milliers:
                out.append((float("".join(parts)), 0))
        elif milliers:
            out.append((float("".join(parts)), 0))
    else:
        out.append((float(t), 0))
    return out


def nombres(texte: str, francais: bool) -> list[tuple[str, list[tuple[float, int]]]]:
    vus: list[tuple[str, list[tuple[float, int]]]] = []
    pris = [False] * len(texte)
    for rx in (_GROUPES, _SIMPLE):
        for m in rx.finditer(texte):
            if any(pris[m.start():m.end()]):
                continue
            # un séparateur final (« 2026. ») n'appartient pas au nombre
            jeton = m.group().rstrip(".,")
            for i in range(m.start(), m.end()):
                pris[i] = True
            v = _valeurs(jeton, francais)
            if v:
                vus.append((jeton, v))
    return vus


def _recoupable(v: float, d: int) -> bool:
    return not (d == 0 and v < 10)


def _annee(v: float, d: int) -> bool:
    return d == 0 and 1900 <= v <= 2100


def retrouve(cible: list[tuple[float, int]], candidats: list[float]) -> bool:
    for x, d in cible:
        if _annee(x, d):
            if x in candidats:
                return True
            continue
        demi = 0.5 * 10 ** (-d) + 1e-9
        for y in candidats:
            for f in _FACTEURS:
                if abs(x - y * f) <= demi:
                    return True
    return False


def _texte_redige(a: dict) -> list[tuple[str, str]]:
    r = a.get("reponse") or {}
    parts = [("verbatim", r.get("verbatim") or "")]
    for f in r.get("faits_posterieurs") or []:
        parts.append((f"fait {f.get('depot')}", f.get("effet") or ""))
    ap = a.get("approximation") or {}
    for k in ("methode", "hypotheses", "verbatim"):
        v = ap.get(k)
        if isinstance(v, list):
            v = " ".join(map(str, v))
        if v:
            parts.append((f"approximation.{k}", str(v)))
    so = a.get("sans_objet") or {}
    if so.get("motif"):
        parts.append(("sans_objet", so["motif"]))
    return [p for p in parts if p[1]]


def _cites(a: dict) -> list[int]:
    ids = list((a.get("fondation") or {}).get("cited_entry_ids") or [])
    for f in (a.get("reponse") or {}).get("faits_posterieurs") or []:
        ids += f.get("cited_entry_ids") or []
    return sorted(set(ids))


async def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    ticker, fw = sys.argv[1], sys.argv[2]
    ids = None
    if "--ids" in sys.argv:
        ids = [int(x) for x in sys.argv[sys.argv.index("--ids") + 1].split(",")]
    import asyncpg

    url = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg", "postgresql")
    if not url:
        print("DATABASE_URL manquante", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(url)
    try:
        if ids:
            rows = await conn.fetch(
                "SELECT id, question_id, statut, answer_json FROM framework_answers "
                "WHERE id = ANY($1) ORDER BY question_id", ids)
        else:
            rows = await conn.fetch(
                "SELECT id, question_id, statut, answer_json FROM framework_answers "
                "WHERE ticker_id=$1 AND framework=$2 AND superseded_by IS NULL ORDER BY question_id",
                ticker, fw)
        corpus = await conn.fetch(
            "SELECT id, coalesce(title,'') || ' ' || coalesce(content,'') AS t FROM knowledge_entries "
            "WHERE ticker_id=$1 AND superseded_by IS NULL", ticker)
        idx = {r["id"]: [v for _, vs in nombres(r["t"], francais=False) for v, _ in vs]
               for r in corpus}
        n_abs = n_tot = 0
        for row in rows:
            a = row["answer_json"]
            if isinstance(a, str):
                a = json.loads(a)
            cites = _cites(a)
            print(f"\n── #{row['id']} {row['question_id']} [{row['statut']}] cite {cites}")
            manq = [c for c in cites if c not in idx]
            if manq:
                print(f"   ⚠ pièces citées hors du corpus courant du titre : {manq}")
            vals_cites = [v for c in cites for v in idx.get(c, [])]
            for lieu, txt in _texte_redige(a):
                for jeton, lect in nombres(txt, francais=True):
                    if not any(_recoupable(v, d) for v, d in lect):
                        continue
                    if any(d == 0 and int(v) in cites for v, d in lect):
                        continue
                    n_tot += 1
                    if retrouve(lect, vals_cites):
                        continue
                    n_abs += 1
                    ailleurs = [i for i, vs in idx.items() if i not in cites and retrouve(lect, vs)]
                    i0 = txt.find(jeton)
                    ctx = txt[max(0, i0 - 50): i0 + len(jeton) + 30].replace("\n", " ")
                    note = f" — porté par #{', #'.join(map(str, ailleurs[:4]))} (non citée)" if ailleurs else ""
                    print(f"   ABSENT [{lieu}] {jeton!r}{note}\n          « …{ctx}… »")
        print(f"\nBILAN — {len(rows)} réponse(s), {n_tot} nombre(s) recoupé(s), {n_abs} absent(s) des pièces citées")
    finally:
        await conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
