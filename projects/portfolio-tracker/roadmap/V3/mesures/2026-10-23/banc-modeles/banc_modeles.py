"""Banc à blanc : l'architecte, même matière, même prompt, mêmes contrôles — seul le MODÈLE change.
Option ANON=1 : noms de société / produits / molécules remplacés par des noms fictifs dans TOUTE la
matière (le contrôle [S14] compare au verbatim anonymisé : cohérent). Rien n'est écrit en base.

  python banc_modeles.py TICKER MODELE SORTIE_JSON
"""
import asyncio, dataclasses, json, os, re, sys

sys.path.insert(0, "/app")
import app.modele_entreprise.architecte as A
from app.agents.providers import get_provider
from app.db.database import close_pool, init_pool

ANON = {
    "NVDA": [("NVIDIA CORP", "HALCYON CORP"), ("NVIDIA", "Halcyon"), ("Nvidia", "Halcyon"),
             ("Vera Rubin", "Kestrel"), ("Vera CPU", "Kestrel CPU"), ("Rubin", "Kestrel"),
             ("Vera", "Kestrel"), ("Blackwell", "Osprey"), ("Hugging Face", "OpenLattice"),
             ("Jensen Huang", "le PDG"), ("NVLink", "HLink"), ("CUDA", "HSDK"), ("GeForce", "HForce"),
             ("Noetra", "Tsubaki Corp"), ("NAVER", "Hanul"), ("FRONTia", "PROJ-J")],
    "RVMD": [("Revolution Medicines", "Meridian Therapeutics"), ("REVOLUTION MEDICINES", "MERIDIAN THERAPEUTICS"),
             ("RASONQUE", "VELTRIQ"), ("daraxonrasib", "velotrasib"), ("Daraxonrasib", "Velotrasib"),
             ("zoldonrasib", "corvitasib"), ("Zoldonrasib", "Corvitasib"),
             ("elironrasib", "amberasib"), ("Elironrasib", "Amberasib"),
             ("RASolute", "MERIDIAN-P"), ("RASolve", "MERIDIAN-L"),
             ("RMC-6236", "MTX-101"), ("RMC-6291", "MTX-102"), ("RMC-9805", "MTX-103"),
             ("RMC-5127", "MTX-204"), ("RMC-0708", "MTX-305"), ("RMC-8839", "MTX-306"), ("RM-055", "MTX-407"),
             ("Goldsmith", "le PDG")],
}


def _sub(s, paires):
    for a, b in paires:
        s = s.replace(a, b)
    return s


def _anon(m, paires):
    ch = {}
    for f in dataclasses.fields(m):
        v = getattr(m, f.name)
        if f.name == "ticker_id":
            continue
        if isinstance(v, str):
            ch[f.name] = _sub(v, paires)
        elif isinstance(v, tuple) and all(isinstance(x, str) for x in v):
            ch[f.name] = tuple(_sub(x, paires) for x in v)
    return dataclasses.replace(m, **ch)


async def main():
    ticker, modele, sortie = sys.argv[1], sys.argv[2], sys.argv[3]
    anon = os.environ.get("ANON") == "1"
    if anon:
        orig_charger, orig_rendre = A.charger_matiere, A.rendre_matiere
        async def charger(conn, t, **kw):
            return _anon(await orig_charger(conn, t, **kw), ANON[ticker])
        A.charger_matiere = charger
        A.rendre_matiere = lambda m: orig_rendre(m).replace(f"ticker {m.ticker_id}", "ticker XXXX")
    base = await A._resolve_architecte_agent()
    agent = dataclasses.replace(base, model=modele, provider=get_provider("deepinfra"))
    res = {"ticker": ticker, "modele": modele, "anon": anon}
    try:
        r = await A.proposer_architecture_du_titre(ticker, agent=agent, hors_porte=True)
        a = r.architecture
        res.update(etat="acceptee", tokens_in=r.run.tokens_in, tokens_out=r.run.tokens_out,
                   tentatives=r.run.attempts, architecture=a.model_dump(mode="json"))
    except A.ArchitectureRefusee as e:
        res.update(etat="refusee", motif=str(getattr(e, "motifs", e)), tokens_in=e.tokens_in,
                   tokens_out=e.tokens_out, sorties=[s for s in getattr(e, "sorties", ())])
    except Exception as e:  # noqa
        res.update(etat="erreur", motif=f"{type(e).__name__}: {e}"[:3000])
    json.dump(res, open(sortie, "w"), ensure_ascii=False, indent=2, default=str)
    print("BILAN", ticker, modele, "anon" if anon else "noms-reels", res["etat"],
          res.get("tokens_in"), res.get("tokens_out"))


async def run():
    await init_pool(os.environ["DATABASE_URL"])
    try:
        await main()
    finally:
        await close_pool()

asyncio.run(run())
