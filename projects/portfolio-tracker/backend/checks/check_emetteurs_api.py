"""La FORME servie par `app/api/emetteurs_v2.py` — hors ligne : aucune base, aucun réseau, aucun modèle.

La connexion est remplacée par un faux (contexte async, `.transaction()` sans effet) et le dépôt par
un `DepotMemoire` unique ; les routes sont appelées par `TestClient` sur un `FastAPI()` local qui ne
monte que ce routeur (aucun import de `app.main`, donc aucune variable d'environnement exigée).
Sociétés et domaines inventés (`.example` est un domaine réservé).

  [P1] le PUT crée la fiche d'une société fictive, le GET la relit
  [P2] un corps qui porte `auteur` ou `le` est refusé (422)
  [P3] l'auteur rangé est toujours « utilisateur » ; la date est celle du serveur
  [P4] le GET d'un émetteur sans fiche est un 404 qui le dit
  [P5] admettre puis révoquer : le journal porte les deux actes, `en_vigueur` faux sur l'admission
  [P6] un acte refusé est un 409 avec le motif en clair
  [P7] qualification : le site de la société est admis, une adresse inconnue non, une nature inconnue 422
  [P8] le fichier de route n'importe du module que `contrat` (vérifié par `ast`)
  [P9] la liste et l'état du dossier se servent sans base (dossier vierge : aucun arrêt)
"""
from __future__ import annotations

import ast
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

from app.api import emetteurs_v2 as R  # noqa: E402
from app.modules.emetteurs import contrat as C  # noqa: E402

SOCIETE = "FICTIVE-ALPHA"
SITE = "alpha-fictive.example"
PRESSE = "presse-fictive.example"


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FausseConnexion:
    def transaction(self):
        return _Transaction()

    async def fetchrow(self, *_a, **_k):   # le dossier n'a jamais avancé
        return None


class _FauxContexte:
    async def __aenter__(self):
        return _FausseConnexion()

    async def __aexit__(self, *exc):
        return False


def main() -> int:
    b = Bilan()
    depot = C.DepotMemoire()
    R.get_db_session = lambda: _FauxContexte()
    R.contrat.depot_base = lambda _conn: depot   # le même objet `contrat` : restauré en fin de course
    app = FastAPI()
    app.include_router(R.router)
    cl = TestClient(app)

    # [P1]
    corps = {"raison_sociale": "Alpha Fictive SA", "motif": "société d'essai", "pays": "ZZ",
             "lieux": [["site", SITE]], "cotations": [["Bourse Fictive", "ALPH"]]}
    r = cl.put(f"/v2/emetteurs/{SOCIETE}", json=corps)
    b.check(r.status_code == 200, f"[P1] PUT crée la fiche (statut {r.status_code} : {r.text[:200]})")
    b.check(r.json().get("fiche", {}).get("raison_sociale") == "Alpha Fictive SA",
            "[P1] le PUT rend la vue de l'émetteur")
    g = cl.get(f"/v2/emetteurs/{SOCIETE}")
    j = g.json() if g.status_code == 200 else {}
    f = j.get("fiche", {})
    b.check(g.status_code == 200 and f.get("emetteur") == SOCIETE and f.get("pays") == "ZZ"
            and f.get("revision") == 1, "[P1] le GET relit la fiche établie")
    b.check(f.get("lieux") == [{"genre": "site", "adresse": SITE}]
            and f.get("cotations") == [{"place": "Bourse Fictive", "symbole": "ALPH"}],
            "[P1] lieux et cotations relus tels que saisis")
    b.check(all(k in j for k in ("emetteurs", "journal_des_sources", "referentiel", "revisions")),
            "[P1] la vue porte liste, journal, référentiel et révisions")
    b.check(all(k in j.get("referentiel", {}) for k in ("natures", "niveaux", "criteres")),
            "[P1] le référentiel porte natures, niveaux et critères")

    # [P2]
    for extra in ({"auteur": "systeme:analyste"}, {"le": "2001-01-01"}):
        r = cl.put(f"/v2/emetteurs/{SOCIETE}", json={**corps, **extra})
        b.check(r.status_code == 422, f"[P2] le PUT refuse {list(extra)[0]} (statut {r.status_code})")
    adm = {"source": PRESSE, "portee": "generale", "natures": ["interpretation"], "niveau": "B",
           "motif": "rédaction identifiée"}
    for extra in ({"auteur": "systeme:analyste"}, {"le": "2001-01-01"}):
        r = cl.post("/v2/sources/admettre", json={**adm, **extra})
        b.check(r.status_code == 422, f"[P2] l'admission refuse {list(extra)[0]} (statut {r.status_code})")
    r = cl.post("/v2/sources/revoquer", json={"source": PRESSE, "portee": "generale", "motif": "x",
                                              "auteur": "utilisateur"})
    b.check(r.status_code == 422, "[P2] la révocation refuse `auteur`")
    b.check(len(cl.get(f"/v2/emetteurs/{SOCIETE}").json()["revisions"]) == 1,
            "[P2] les corps refusés n'ont rien écrit")

    # [P3]
    rev = cl.get(f"/v2/emetteurs/{SOCIETE}").json()
    b.check(rev["fiche"]["auteur"] == C.UTILISATEUR == "utilisateur", "[P3] fiche : auteur « utilisateur »")
    b.check(rev["fiche"]["le"] == date.today().isoformat(), "[P3] fiche : date du serveur")
    r = cl.post("/v2/sources/admettre", json=adm)
    b.check(r.status_code == 200 and r.json() == {"rang": 1}, f"[P5] admettre rend le rang ({r.text[:200]})")
    acte = (cl.get("/v2/emetteurs").json()["journal_des_sources"] or [{}])[0]
    b.check(acte.get("auteur") == "utilisateur" and acte.get("le") == date.today().isoformat(),
            "[P3] journal : auteur « utilisateur », date du serveur")

    # [P4]
    r = cl.get("/v2/emetteurs/FICTIVE-INCONNUE")
    b.check(r.status_code == 404 and "FICTIVE-INCONNUE" in r.json()["detail"],
            f"[P4] émetteur sans fiche : 404 qui le nomme (statut {r.status_code})")
    r = cl.get("/v2/emetteurs/FICTIVE-INCONNUE/qualification", params={"adresse": SITE, "nature": "mesure"})
    b.check(r.status_code == 404, "[P4] qualification d'un émetteur sans fiche : 404")

    # [P5]
    journal = cl.get("/v2/emetteurs").json()["journal_des_sources"]
    b.require(journal, 1, "[P5] journal après admission")
    b.check(bool(journal) and journal[0]["acte"] == "admettre" and journal[0]["en_vigueur"] is True,
            "[P5] l'admission est en vigueur tant qu'elle n'est pas révoquée")
    r = cl.post("/v2/sources/revoquer", json={"source": PRESSE, "portee": "generale", "motif": "ligne éditoriale changée"})
    b.check(r.status_code == 200 and r.json() == {"rang": 2}, f"[P5] révoquer rend le rang ({r.text[:200]})")
    journal = cl.get("/v2/emetteurs").json()["journal_des_sources"]
    if b.require(journal, 2, "[P5] journal après révocation"):  # sans les deux actes, rien d'autre à lire
        b.check([a["acte"] for a in journal] == ["admettre", "revoquer"], "[P5] le journal porte les deux actes, dans l'ordre")
        b.check(journal[0]["en_vigueur"] is False, "[P5] `en_vigueur` est faux sur l'admission révoquée")
        b.check(journal[1]["motif"] == "ligne éditoriale changée", "[P5] le motif de la révocation est rangé")

    # [P6]
    r = cl.post("/v2/sources/revoquer", json={"source": "jamais-admise.example", "portee": "generale", "motif": "essai"})
    b.check(r.status_code == 409 and len(r.json().get("detail", "")) > 10,
            f"[P6] révoquer une source non admise : 409 avec motif ({r.status_code} : {r.text[:200]})")
    r = cl.post("/v2/sources/admettre", json={**adm, "portee": "emetteur:FICTIVE-INCONNUE"})
    b.check(r.status_code == 409 and "FICTIVE-INCONNUE" in r.json().get("detail", ""),
            "[P6] portée sur un émetteur sans fiche : 409 qui le nomme")
    r = cl.put(f"/v2/emetteurs/{SOCIETE}", json={**corps, "motif": "  "})
    b.check(r.status_code == 409, f"[P6] correction sans motif : 409 (statut {r.status_code})")

    # [P7]
    q = cl.get(f"/v2/emetteurs/{SOCIETE}/qualification", params={"adresse": f"https://{SITE}/communiques", "nature": "mesure"})
    b.check(q.status_code == 200 and q.json().get("admise") is True and q.json().get("niveau"),
            f"[P7] le site de la société est admis ({q.status_code} : {q.text[:200]})")
    q = cl.get(f"/v2/emetteurs/{SOCIETE}/qualification", params={"adresse": "inconnu.example", "nature": "mesure"})
    b.check(q.status_code == 200 and q.json().get("admise") is False and q.json().get("motif"),
            "[P7] une adresse inconnue n'est pas admise, et le motif le dit")
    b.check(set(q.json()) == {"admise", "niveau", "motif", "source"}, "[P7] la qualification porte quatre clés")
    q = cl.get(f"/v2/emetteurs/{SOCIETE}/qualification", params={"adresse": SITE, "nature": "inconnue"})
    b.check(q.status_code == 422, f"[P7] nature inconnue : 422 (statut {q.status_code})")

    # [P9]
    liste = cl.get("/v2/emetteurs").json()["emetteurs"]
    b.check([e["emetteur"] for e in liste] == [SOCIETE], "[P9] la liste porte l'émetteur établi")
    d = cl.get(f"/v2/emetteurs/{SOCIETE}/dossier")
    b.check(d.status_code == 200 and d.json().get("dossier") == SOCIETE and d.json().get("arret") is None
            and d.json().get("faits") == [], f"[P9] état du dossier vierge ({d.status_code})")

    # [P8]
    tree = ast.parse((BACKEND / "app/api/emetteurs_v2.py").read_text(encoding="utf-8"))
    importes = []
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and (n.module or "").startswith("app.modules"):
            importes.append((n.module, tuple(a.name for a in n.names)))
        elif isinstance(n, ast.Import):
            importes += [(a.name, ()) for a in n.names if a.name.startswith("app.modules")]
    b.require(importes, 2, "[P8] imports de modules dans la route")
    b.check(all(m in ("app.modules.emetteurs.contrat", "app.modules.chef_de_dossier.contrat")
               or (m, noms) in (("app.modules.emetteurs", ("contrat",)),) for m, noms in importes),
            f"[P8] seuls les `contrat` sont importés : {importes}")
    b.check(all(m.endswith(".contrat") or noms == ("contrat",) for m, noms in importes),
            "[P8] aucun import de `regles` ni de `depot_base`")
    return b.summary()


if __name__ == "__main__":
    sys.exit(main())
