"""`fetch_url` avec question — en conditions réelles (réseau + clé Exa + embeddings).

Rejoue les trois cas qui avaient mis la troncature en tête en défaut, et vérifie que l'information
attendue est cette fois DANS le texte rendu — alors qu'elle se trouve au-delà du plafond de 20 000
caractères qui s'appliquait avant.
"""
import asyncio
import sys

sys.path.insert(0, ".")

from app.knowledge.websearch import fetch_url  # noqa: E402

CAS = [
    (
        "10-K NVDA FY2026 (sec.gov, direct, 362 k car.)",
        "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm",
        "customer concentration percentage of total revenue direct customers",
        ["22%", "14%"],
    ),
    (
        # Le comparatif Google → AWS → Meta → Microsoft : information distribuée par construction,
        # c'est LE cas qui condamne toute troncature en tête (« Maia » à 71,5 % du texte).
        "article CNBC (403 en direct → cache Exa)",
        "https://www.cnbc.com/2025/11/21/nvidia-gpus-google-tpus-aws-trainium-comparing-the-top-ai-chips.html",
        "custom AI chips developed by hyperscalers Maia Trainium MTIA share of accelerators",
        ["Maia"],
    ),
]


async def main() -> int:
    echecs = 0
    for label, url, question, attendus in CAS:
        print(f"\n── {label}")
        print(f"   ? {question}")
        try:
            r = await fetch_url(url, query=question)
        except Exception as e:  # noqa: BLE001
            print(f"   ÉCHEC fetch : {e}")
            echecs += 1
            continue
        x = r.get("extract") or {}
        print(f"   via={r['via']} mode={x.get('mode')} "
              f"{x.get('chars_total')} car. → {x.get('chars_returned')} "
              f"({x.get('chunks_selected')}/{x.get('chunks_total')} passages)")
        for s in (x.get("spans") or [])[:6]:
            pos = s["start"] / max(x.get("chars_total") or 1, 1)
            print(f"     passage à {pos:6.1%} du document (score {s.get('score')})")
        for attendu in attendus:
            present = attendu in r["text"]
            print(f"   {'✓' if present else '✗'} {attendu!r} dans le texte rendu")
            echecs += 0 if present else 1
        # Le point de comparaison : ce que l'ancien comportement (tête à 20 000) aurait rendu.
        manques = [a for a in attendus if a not in r["text"][:0] and a in r["text"]]
        print(f"   note : {r.get('note', '(document rendu entier)')[:120]}")
        _ = manques

    print(f"\n{'=' * 60}\n{'OK' if not echecs else f'{echecs} problème(s)'}")
    return 1 if echecs else 0


sys.exit(asyncio.run(main()))
