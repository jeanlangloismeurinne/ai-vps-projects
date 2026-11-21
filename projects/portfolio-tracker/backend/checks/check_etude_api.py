"""La FORME servie par `app/api/etude_v2.py` (M2 B12, M3 K12 : l'écran de la société mise à l'étude) —
hors ligne : aucune base, aucun réseau, aucun modèle. Rougi par `negatif_etude_api.sh`.

Le monde est celui de `check_etude.py` (société fictive, adaptateur et évaluateur simulés, dépôts en
mémoire, transaction en mémoire) ; la connexion est un faux et `monde_en_base` rend ce monde. Les
routes sont appelées par `TestClient` sur un `FastAPI()` local qui ne monte que ce routeur.

  [E1] une société non mise à l'étude se lit : étude vide, dossier vierge, ni collecte ni lecture
  [E2] mettre à l'étude : sans fiche, un 409 qui le dit ; un corps qui porte `par` ou `le`, un 422 ;
       sinon l'étude est signée de l'utilisateur et datée du jour du serveur ; deux fois : l'origine
  [E3] après les passages : l'acte qui vous revient se dit en mots de gérant (« Valider les documents
       trouvés ou introuvables »), avec la clé à renvoyer ; la collecte montre ses demandes, ses
       documents (origine, qualification, date) et sa dépense ; les documents lus et la lecture
       « sans objet » des données structurées se voient avec leur raison ; le passage est au journal
  [E4] les gestes : un acte non attendu et une pause non posée sont des 409 qui le disent ; l'acte
       attendu enregistré, le dossier va au bout au passage suivant
  [E5] une pièce se voit avec son extrait, ses lignes et ce que vaut sa source aujourd'hui
  [E6] les lignes d'un document lu se lisent (bornées) ; un document non lu de cet émetteur : 404
  [E7] la route n'importe des modules que leurs `contrat` (vérifié par `ast`)
"""
from __future__ import annotations

import ast
import asyncio
import json
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Bilan  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import check_etude as F  # noqa: E402 — le monde fictif du déclencheur (détenteur unique de la fixture)
from app.api import etude_v2 as A  # noqa: E402
from app.modules.connaissance import contrat as K  # noqa: E402
from app.modules.etude import contrat as T  # noqa: E402

LIBELLE = "Valider les documents trouvés ou introuvables"


class _FauxContexte:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, *exc):
        return False


def main() -> int:
    b = F.Bilan2()
    monde, _ = asyncio.run(F.nouveau_monde())
    A.get_db_session = lambda: _FauxContexte()
    A.T.monde_en_base = lambda _conn, **_kw: monde
    app = FastAPI()
    app.include_router(A.router)
    cl = TestClient(app)
    url = f"/v2/emetteurs/{F.EMETTEUR}/etude"

    # [E1]
    r = cl.get(url)
    v = r.json() if r.status_code == 200 else {}
    e = v.get("etude", {})
    b.check(r.status_code == 200 and e.get("etude") is None and e.get("etat", {}).get("arret") is None
            and e.get("etat", {}).get("faits") == [] and e.get("passages") == [],
            "[E1] société non mise à l'étude : étude vide, dossier vierge", f"{r.status_code} {r.text[:300]}")
    b.check(v.get("collecte", {}).get("reponses") == [] and v.get("connaissance", {}).get("lectures") == [],
            "[E1] ni collecte ni lecture", f"{v.get('collecte')} {v.get('connaissance')}")

    # [E2]
    r = cl.post("/v2/emetteurs/SANS-FICHE/etude", json={"motif": "essai"})
    b.check(r.status_code == 409 and "fiche" in r.json().get("detail", ""),
            "[E2] sans fiche : 409 qui le dit", f"{r.status_code} {r.text[:200]}")
    for intrus in ({"par": "quelqu'un"}, {"le": "2001-01-01"}):
        r = cl.post(url, json={"motif": "initiation", **intrus})
        b.check(r.status_code == 422, f"[E2] un corps qui porte {list(intrus)[0]} est refusé (422)", f"{r.status_code}")
    r = cl.post(url, json={"motif": "initiation"})
    et = r.json().get("etude") if r.status_code == 200 else None
    b.check(et and et["par"] == "utilisateur" and et["mise_le"] == date.today().isoformat() and et["motif"] == "initiation",
            "[E2] l'étude est signée de l'utilisateur, datée du jour du serveur", f"{r.status_code} {r.text[:300]}")
    r = cl.post(url, json={"motif": "encore"})
    b.check(r.status_code == 200 and r.json()["etude"]["motif"] == "initiation",
            "[E2] mise à l'étude deux fois : l'étude d'origine", f"{r.text[:200]}")

    # [E3] — la tâche de fond passe jusqu'à l'arrêt qui vous revient
    for _ in range(6):
        asyncio.run(T.traiter_les_dossiers(monde, le=F.JOUR))
        arret = cl.get(url).json()["etude"]["etat"]["arret"]
        if arret and arret["motif"] == "acte_humain":
            break
    v = cl.get(url).json()
    arret = v["etude"]["etat"]["arret"] or {}
    b.check(arret.get("motif") == "acte_humain" and arret.get("cle") == "lecture:collecte"
            and arret.get("libelle") == LIBELLE,
            "[E3] l'acte qui vous revient : en mots de gérant, avec sa clé", f"{arret}")
    b.check(all(x.get("libelle") for x in arret.get("attentes", []) if x.get("acte")),
            "[E3] chaque attente d'un acte porte son libellé", f"{arret.get('attentes')}")
    col = v["collecte"]
    docs = [d for rep in col.get("reponses", []) for d in rep.get("documents", [])]
    b.check({rep["demande"]["genre"] for rep in col.get("reponses", [])}
            == {"derniers_comptes_annuels", "donnees_comptables_structurees"},
            "[E3] la collecte montre ses demandes", f"{col.get('reponses')}")
    b.check(docs and all(d["provenance"]["adresse"] and "admise" in d["qualification"] and d["collecte_le"] for d in docs),
            "[E3] chaque document dit son origine, sa qualification, sa date", f"{docs[:1]}")
    b.check("depense" in col and set(col["depense"]) == {"modeles_usd", "web_usd"}, "[E3] la dépense de la collecte")
    con = v["connaissance"]
    statuts = sorted(l["statut"] for l in con.get("lectures", []))
    b.check(statuts.count("lue") >= 1 and "sans_objet" in statuts and con.get("raisons", {}).get("sans_objet"),
            "[E3] documents lus, et la lecture sans objet avec sa raison", f"{statuts} {con.get('raisons')}")
    ranges = asyncio.run(monde.etude.passages(F.EMETTEUR))
    b.check(len(ranges) >= 2 and v["etude"]["passages"] == json.loads(json.dumps(list(reversed(ranges))))
            and v["etude"]["passages"][0]["issue"] == "avance",
            "[E3] les passages qui ont fait quelque chose sont au journal, le plus récent d'abord",
            f"{len(ranges)} {v['etude']['passages'][:1]}")

    # [E4]
    r = cl.post(f"{url}/acte", json={"cle": "lecture:autre_chose"})
    b.check(r.status_code == 409 and r.json().get("detail"), "[E4] acte non attendu : 409 qui le dit", f"{r.status_code} {r.text[:200]}")
    r = cl.post(f"{url}/pause", json={})
    b.check(r.status_code == 409 and r.json().get("detail"), "[E4] pause non posée : 409 qui le dit", f"{r.status_code} {r.text[:200]}")
    r = cl.post(f"{url}/acte", json={"cle": "lecture:collecte"})
    b.check(r.status_code == 200 and "lecture:collecte" in r.json()["etat"]["actes_accomplis"],
            "[E4] l'acte attendu est enregistré", f"{r.status_code} {r.text[:300]}")
    asyncio.run(T.traiter_les_dossiers(monde, le=F.JOUR))
    fin = cl.get(url).json()["etude"]["etat"]["arret"] or {}
    b.check(fin.get("motif") == "parcours_termine", "[E4] le passage suivant mène le dossier au bout", f"{fin}")

    # [E5]
    lue = next((l for l in con.get("lectures", []) if l["statut"] == "lue" and F.SITE in l["adresse"]), None)
    piece = None
    if lue:
        piece = asyncio.run(K.citer(monde.connaissance, emetteur=F.EMETTEUR, empreinte=lue["empreinte"],
                                    extrait="Fictive Etude Corp annual report.", auteur="essai", le=F.JOUR))
    pieces = cl.get(url).json()["connaissance"]["pieces"]
    p = pieces[0] if pieces else {}
    b.check(piece and len(pieces) == 1 and p.get("extrait") and p.get("ligne_debut") >= 1
            and p.get("valeur", {}).get("admise") is True and p["valeur"].get("niveau"),
            "[E5] la pièce : extrait, lignes, ce que vaut sa source aujourd'hui", f"{pieces}")

    # [E6]
    if lue:
        A.LIGNES_MAX = 1   # la borne, éprouvée sur un document court
        debut = p.get("ligne_debut", 1)
        r = cl.get(f"/v2/emetteurs/{F.EMETTEUR}/lectures/{lue['empreinte']}", params={"debut": debut, "fin": 100000})
        j = r.json() if r.status_code == 200 else {}
        b.check(r.status_code == 200 and len(j.get("lignes", [])) == 1 and j.get("debut") == debut
                and j.get("nb_lignes") == lue["nb_lignes"] and "annual report" in j["lignes"][0],
                "[E6] les lignes d'un document lu se lisent, bornées", f"{r.status_code} {r.text[:300]}")
        r = cl.get(f"/v2/emetteurs/{F.AUTRE}/lectures/{lue['empreinte']}")
        b.check(r.status_code == 404, "[E6] le document d'un autre émetteur : 404", f"{r.status_code}")
    sans_objet = next((l for l in con.get("lectures", []) if l["statut"] == "sans_objet"), None)
    r = cl.get(f"/v2/emetteurs/{F.EMETTEUR}/lectures/{sans_objet['empreinte'] if sans_objet else 'x'}")
    b.check(r.status_code == 404, "[E6] un document sans lecture en lignes : 404", f"{r.status_code}")

    # [E7]
    tree = ast.parse((BACKEND / "app/api/etude_v2.py").read_text(encoding="utf-8"))
    importes = []
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and (n.module or "").startswith("app.modules"):
            importes += [f"{n.module}.{a.name}" for a in n.names]
        elif isinstance(n, ast.Import):
            importes += [a.name for a in n.names if a.name.startswith("app.modules")]
    b.require(importes, 4, "[E7] imports de modules dans la route")
    b.check(all(m.endswith(".contrat") for m in importes), "[E7] seuls les `contrat` sont importés", f"{importes}")
    return b.summary()


if __name__ == "__main__":
    sys.exit(main())
