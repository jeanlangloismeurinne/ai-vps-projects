"""fetch_url en conditions réelles (réseau ouvert, aucune clé requise)."""
import asyncio, json
from app.agents.v2.tools import exec_fetch_url, exec_web_search

URLS = [
    "https://investor.nvidia.com/financial-info/financial-reports/default.aspx",
    "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=NVDA&type=10-K",
    "https://example.com/",
]

async def main():
    for u in URLS:
        r = await exec_fetch_url({"url": u})
        if "error" in r:
            print(f"\n✗ {u}\n   erreur : {r['error']}")
            continue
        print(f"\n✓ {u}")
        print(f"   final={r['final_url'][:90]}")
        print(f"   type={r['content_type']} | titre={r['title'][:70]!r}")
        print(f"   source_type_max={r['source_type_max']} | {len(r['text'])} car. | tronqué={r['truncated']}")
        print(f"   extrait : {r['text'][:220].replace(chr(10),' | ')!r}")

    print("\n— erreurs attendues —")
    print(" url vide   :", (await exec_fetch_url({"url": ""}))["error"])
    print(" non-http   :", (await exec_fetch_url({"url": "ftp://x/y"}))["error"])
    print(" 404        :", (await exec_fetch_url({"url": "https://www.sec.gov/nexistepas-xyz"}))["error"])
    ws = await exec_web_search({"query": "test"})
    print(" web_search sans clé :", json.dumps(ws, ensure_ascii=False)[:200])

asyncio.run(main())
