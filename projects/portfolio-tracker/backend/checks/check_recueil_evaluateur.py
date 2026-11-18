"""Contrôle du module M2 « recueil » — le moteur de recherche réel (Exa), le modèle réel (DeepInfra)
et l'évaluateur réel des sources inconnues (#145), SANS réseau ni dépense : le transport est simulé
et rend des réponses COPIÉES DE LA FORME RÉELLE relevée le 2026-11-18 (Exa : `results[].id/url/
title/publishedDate`, `costDollars.total`, `statuses[]` ; DeepInfra : `choices[0].message.content`,
`finish_reason`, `usage.estimated_cost` ; Reuters répond 401 à la lecture directe).

  [X1] Exa — une recherche : la demande porte la requête, le nombre, les domaines et la catégorie
       traduite par le référentiel ; chaque résultat garde son adresse, son titre et son jour ; la
       dépense est celle qu'Exa déclare
  [X2] Exa — une réponse sans coût déclaré prend le coût de repli du référentiel, jamais 0
  [X3] Exa — un refus ou un silence est une `MoteurInjoignable` nommée ; l'adaptateur web en fait
       une indisponibilité « injoignable » qui nomme le moteur, jamais une exception ni un « rien »
  [X4] Exa — le texte des pages : rendu sous l'adresse DEMANDÉE ; une page en erreur est absente ;
       la dépense est comptée
  [M1] modèle — l'objet JSON est rendu avec la dépense déclarée ; à défaut, les jetons au prix du
       référentiel ; un modèle sans prix connu prend le prix de repli
  [M2] modèle — « occupé » se reprend après chaque pause du référentiel, puis l'échec est nommé ;
       un refus définitif (clef) n'est pas repris
  [M3] modèle — réponse coupée ou qui n'est pas un objet JSON : échec nommé, la dépense déjà
       engagée part avec lui
  [V1] l'évaluateur lit autant de publications que la grille de M1 en exige, de la source seule :
       celles rencontrées d'abord, puis une recherche limitée à son domaine ; ni page d'accueil, ni
       page d'un autre site ; les pages datées passent devant les pages de rubrique
  [V2] une page refusée en lecture directe est relue par le moteur, seulement ce qui manque (plus
       une) ; s'il manque encore des publications : échec nommé, le modèle n'est pas appelé
  [V3] le modèle reçoit la grille et les critères tels que M1 les écrit (sauf celui des pages de
       relations investisseurs, qui ne se juge pas), et le texte de chaque publication
  [V4] un critère choisi fixe les natures et le niveau (ceux que le critère accorde) : le modèle n'a
       pas de levier sur le niveau ; sans critère, ses propositions sont vérifiées contre l'échelle
  [V5] une réponse hors forme (page qu'on ne lui a pas donnée, question sans réponse, constat vide,
       critère inconnu, publication oubliée) est un échec nommé avec la dépense, jamais transmise à M1
  [V6] de bout en bout par le contrat : une bonne source est admise, une faible mise en suspens ;
       la dépense de la source = recherche + pages + modèle ; un essai manqué garde ce qu'il a payé,
       deux essais manqués = échec nommé
  [V7] le modèle et sa consigne sont au référentiel de l'évaluateur, aucun nom de modèle dans le code

    python3 checks/check_recueil_evaluateur.py
"""
from __future__ import annotations

import ast
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import strip_code  # noqa: E402
from check_recueil import Bilan2, Plante, run  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.modules.chef_de_dossier import contrat as CD  # noqa: E402
from app.modules.emetteurs import contrat as E  # noqa: E402
from app.modules.recueil import adaptateurs as AD  # noqa: E402
from app.modules.recueil import contrat as R  # noqa: E402
from app.modules.recueil import evaluateur as EV  # noqa: E402
from app.modules.recueil.adaptateurs import deepinfra as DI  # noqa: E402
from app.modules.recueil.adaptateurs import exa as X  # noqa: E402
from app.modules.recueil.adaptateurs.web import Web  # noqa: E402

MODULE = BACKEND / "app" / "modules" / "recueil"
JOUR = "2026-11-18"
EXA = json.loads((MODULE / "adaptateurs" / "exa.json").read_text(encoding="utf-8"))
DIJ = json.loads((MODULE / "adaptateurs" / "deepinfra.json").read_text(encoding="utf-8"))
EVJ = json.loads((MODULE / "evaluateur.json").read_text(encoding="utf-8"))
GRILLE = E.grille_d_evaluation()
QUESTIONS = list(GRILLE["questions"])
N = GRILLE["exemples_min"]


# ── Le monde simulé ─────────────────────────────────────────────────────────────────────────

def js(obj, statut: int = 200) -> AD.Lu:
    return AD.Lu(statut, json.dumps(obj).encode(), "application/json")


def article(titre: str, n: int = 900) -> AD.Lu:
    corps = " ".join(f"Phrase {i} de l'article {titre}, chiffres et sources." for i in range(n // 40))
    return AD.Lu(200, f"<html><head><script>var x=1;</script></head><body><h1>{titre}</h1><p>{corps}</p></body></html>"
                 .encode(), "text/html; charset=utf-8")


class Reseau:
    """Lectures : adresse → réponse. Envois : (adresse du service) → réponses successives."""

    def __init__(self, pages=None, envois=None) -> None:
        self.pages = dict(pages or {})
        self.envois = {k: list(v) for k, v in (envois or {}).items()}
        self.lus: list[str] = []
        self.envoyes: list[tuple[str, dict, dict]] = []

    async def lire(self, adresse):
        self.lus.append(adresse)
        return self.pages.get(adresse, AD.Lu(404))

    async def envoyer(self, adresse, corps, *, en_tetes, delai_s=60):
        self.envoyes.append((adresse, json.loads(json.dumps(corps)), dict(en_tetes)))
        file = self.envois.get(adresse) or [AD.Lu(0)]
        return file.pop(0) if len(file) > 1 else file[0]

    def vers(self, adresse):
        return [c for a, c, _ in self.envoyes if a == adresse]


U_RECH, U_CONT, U_DI = EXA["adresses"]["recherche"], EXA["adresses"]["contenus"], DIJ["adresse"]


def exa_recherche(*resultats, cout=0.007):
    rep = {"requestId": "r", "resolvedSearchType": "neural", "searchTime": 1.0,
           "results": [{"id": u, "title": t, "url": u, **({"publishedDate": d + "T09:15:06.000Z"} if d else {})}
                       for u, t, d in resultats]}
    if cout is not None:
        rep["costDollars"] = {"total": cout, "search": {"neural": cout}}
    return js(rep)


def exa_contenus(textes: dict[str, str], erreurs=(), normalise=False):
    res = [{"id": u, "url": (u.rstrip("/") + "/?amp" if normalise else u), "title": "T", "author": None,
            "publishedDate": "2026-08-04T20:41:04.000Z", "text": t} for u, t in textes.items()]
    st = [{"id": u, "status": "success", "source": "cached"} for u in textes] + [
        {"id": u, "status": "error", "error": {"httpStatusCode": 500, "tag": "CRAWL_UNKNOWN_ERROR"}} for u in erreurs]
    return js({"requestId": "c", "results": res, "statuses": st, "searchTime": 1.0,
               "costDollars": {"total": round(0.001 * len(textes), 6), "contents": {"text": 0.001}}})


def di(objet, *, cout=0.0003, fin="stop", jetons=(4000, 600), contenu=None):
    usage = {"prompt_tokens": jetons[0], "completion_tokens": jetons[1], "total_tokens": sum(jetons),
             "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": None}}
    if cout is not None:
        usage["estimated_cost"] = cout
    return js({"id": "x", "object": "chat.completion", "model": EVJ["modele"],
               "choices": [{"index": 0, "finish_reason": fin,
                            "message": {"role": "assistant", "content": contenu if contenu is not None else json.dumps(objet)}}],
               "usage": usage})


OCCUPE = js({"error": {"message": "Model busy, retry later", "type": "invalid_request_error", "param": None,
                       "code": "engine_overloaded"}}, 429)


def reponse_modele(adresses, *, oui=True, critere="presse_financiere", niveau="A", natures=("mesure",),
                   sans=None, constat="constaté dans le texte"):
    return {"critere": critere, "natures": list(natures), "niveau": niveau,
            "publications": [{"adresse": a, "reponses": {q: {"oui": oui if i == 0 else True, "constat": constat}
                                                         for q in QUESTIONS if q != sans}}
                             for i, a in enumerate(adresses)]}


class Fiche:
    raison_sociale = "Société Fictive Privée"
    lieux = ()


async def _sans_pause(_):
    return None


def main() -> int:
    b = Bilan2()
    DI.asyncio.sleep = _sans_pause   # les pauses du référentiel ne ralentissent pas le contrôle
    b.check(N >= 2 and len(QUESTIONS) >= 3, "[V3] la grille de M1 a été lue (au moins 2 publications, 3 questions)",
            f"{N}, {QUESTIONS}")

    # ── [X1]-[X4] le moteur ────────────────────────────────────────────────────────────────
    async def s_x1():
        net = Reseau(envois={U_RECH: [exa_recherche(("https://presse.example/a1", " Titre A ", "2026-08-05"),
                                                    ("https://presse.example/rubrique/", "Rubrique", ""))]})
        m = X.MoteurExa(net, "clef")
        res, dep = await m.rechercher("q", domaines=["presse.example"], nombre=4, categorie="actualites")
        return net, res, dep
    net, res, dep = run(s_x1())
    corps = (net.vers(U_RECH) or [Plante(KeyError("aucun envoi"))])[0]
    b.check(corps.get("query") == "q" and corps.get("numResults") == 4 and corps.get("includeDomains") == ["presse.example"]
            and corps.get("category") == EXA["categories"]["actualites"] and corps.get("type") == EXA["type_de_recherche"],
            "[X1] la demande porte la requête, le nombre, les domaines et la catégorie traduite", f"{corps}")
    b.check(net.envoyes and net.envoyes[0][2].get("x-api-key") == "clef", "[X1] la clef part dans l'en-tête")
    b.check([(r.adresse, r.titre, r.publie_le) for r in res] == [("https://presse.example/a1", "Titre A", "2026-08-05"),
                                                                 ("https://presse.example/rubrique/", "Rubrique", "")],
            "[X1] chaque résultat garde son adresse, son titre et son jour", f"{res}")
    b.check(dep == CD.Depense(web_usd=0.007), "[X1] la dépense est celle qu'Exa déclare", f"{dep}")

    async def s_x2():
        net = Reseau(envois={U_RECH: [exa_recherche(("https://presse.example/a1", "A", ""), cout=None)]})
        _, dep = await X.MoteurExa(net, "clef").rechercher("q")
        sans_cat = net.vers(U_RECH)[0]
        return dep, sans_cat
    dep, sans_cat = run(s_x2(), n=2)
    b.check(dep == CD.Depense(web_usd=EXA["cout_de_repli_usd"]["recherche"]) and dep.web_usd > 0,
            "[X2] sans coût déclaré, le coût de repli du référentiel (jamais 0)", f"{dep}")
    b.check("category" not in sans_cat and "includeDomains" not in sans_cat,
            "[X1] sans catégorie ni domaine, la demande n'en porte pas", f"{sans_cat}")

    async def s_x3():
        issues = []
        for lu in (js({"error": "Payment required", "tag": "X402_PAYMENT_REQUIRED"}, 402), AD.Lu(0)):
            try:
                await X.MoteurExa(Reseau(envois={U_RECH: [lu]}), "clef").rechercher("q")
                issues.append("aucune exception")
            except AD.MoteurInjoignable as exc:
                issues.append(str(exc))
        try:
            await X.MoteurExa(Reseau(), "").rechercher("q")
            issues.append("aucune exception")
        except AD.MoteurInjoignable as exc:
            issues.append(str(exc))
        web = Web()
        moteur = X.MoteurExa(Reseau(envois={U_RECH: [js({"error": "x"}, 402)]}), "clef")
        appel = AD.Appel(demande=R.Demande("annonces_importantes", "FICTIVE-PRIVEE"), fiche=Fiche(), genre={},
                         transport=Reseau(), moteur=moteur, deja=lambda _: _vide(), le=JOUR)
        tr = await web.chercher(appel)
        return issues, tr
    issues, tr = run(s_x3(), n=2)
    b.check(len(issues) == 3 and "402" in issues[0] and "statut 0" in issues[1] and "clef" in issues[2],
            "[X3] refus, silence ou clef absente : MoteurInjoignable nommée", f"{issues}")
    b.check(tr.raison == "injoignable" and "moteur" in tr.detail and "402" in tr.detail and not tr.trouves,
            "[X3] l'adaptateur web nomme l'indisponibilité du moteur (ni exception, ni « rien publié »)",
            f"{getattr(tr, 'raison', tr)} / {getattr(tr, 'detail', '')}")

    async def s_x4():
        a, b_, c = "https://presse.example/a", "https://presse.example/b", "https://presse.example/c"
        net = Reseau(envois={U_CONT: [exa_contenus({a: "texte A", b_: "texte B"}, erreurs=[c], normalise=True)]})
        textes, dep = await X.MoteurExa(net, "clef").contenus([a, b_, c, a])
        return net, textes, dep
    net, textes, dep = run(s_x4(), n=3)
    b.check(sorted((t.adresse, t.texte) for t in textes) == [("https://presse.example/a", "texte A"),
                                                            ("https://presse.example/b", "texte B")],
            "[X4] le texte revient sous l'adresse demandée ; la page en erreur est absente", f"{textes}")
    b.check(net.vers(U_CONT) and net.vers(U_CONT)[0]["urls"] == ["https://presse.example/a", "https://presse.example/b",
                                                                   "https://presse.example/c"],
            "[X4] chaque adresse n'est demandée qu'une fois", f"{net.vers(U_CONT)}")
    b.check(dep == CD.Depense(web_usd=0.002), "[X4] la dépense des pages est comptée", f"{dep}")

    # ── [M1]-[M3] le modèle ───────────────────────────────────────────────────────────────
    prix = DIJ["prix_usd_par_million_de_jetons"]
    connu = next(iter(prix))

    async def completer(lus, modele=connu):
        net = Reseau(envois={U_DI: list(lus)})
        try:
            obj, dep = await DI.ModeleDeepInfra(net, "clef").completer(modele=modele, consigne="c", message="m",
                                                                       temperature=0, max_jetons=100)
            return net, obj, dep, None
        except DI.ModeleEnEchec as exc:
            return net, None, exc.depense, exc

    net, obj, dep, err = run(completer([di({"ok": True}, cout=0.00042)]), n=4)
    envoi = (net.vers(U_DI) or [{}])[0]
    b.check(obj == {"ok": True} and dep == CD.Depense(modeles_usd=0.00042) and err is None,
            "[M1] l'objet JSON et la dépense déclarée", f"{obj} {dep} {err}")
    b.check(envoi.get("model") == connu and envoi.get("response_format") == {"type": "json_object"}
            and [m["role"] for m in envoi.get("messages", [])] == ["system", "user"]
            and net.envoyes[0][2].get("Authorization") == "Bearer clef",
            "[M1] la demande nomme le modèle, exige un objet JSON, porte consigne et message", f"{envoi}")
    _, _, dep, _ = run(completer([di({"ok": 1}, cout=None, jetons=(1_000_000, 1_000_000))]), n=4)
    b.check(dep == CD.Depense(modeles_usd=prix[connu]["entree"] + prix[connu]["sortie"]),
            "[M1] sans coût déclaré, les jetons au prix du référentiel", f"{dep}")
    _, _, dep, _ = run(completer([di({"ok": 1}, cout=None, jetons=(1_000_000, 0))], modele="inconnu/modele"), n=4)
    b.check(dep == CD.Depense(modeles_usd=DIJ["prix_de_repli"]["entree"]),
            "[M1] un modèle sans prix connu prend le prix de repli", f"{dep}")

    pauses = DIJ["pauses_avant_reprise_s"]
    net, obj, _, err = run(completer([OCCUPE] * len(pauses) + [di({"ok": True})]), n=4)
    b.check(obj == {"ok": True} and len(net.vers(U_DI)) == len(pauses) + 1,
            "[M2] « occupé » se reprend après chaque pause du référentiel", f"{len(net.vers(U_DI))} {err}")
    net, obj, _, err = run(completer([OCCUPE]), n=4)
    b.check(obj is None and err is not None and "429" in str(err) and len(net.vers(U_DI)) == len(pauses) + 1,
            "[M2] toujours occupé : l'échec est nommé après les reprises, jamais une boucle",
            f"{len(net.vers(U_DI))} {err}")
    net, obj, _, err = run(completer([js({"error": {"message": "missing API key"}}, 401)]), n=4)
    b.check(obj is None and err is not None and "401" in str(err) and len(net.vers(U_DI)) == 1,
            "[M2] un refus définitif n'est pas repris", f"{len(net.vers(U_DI))} {err}")

    _, obj, dep, err = run(completer([di({"ok": True}, fin="length", cout=0.0009)]), n=4)
    b.check(obj is None and err is not None and "coupée" in str(err) and dep == CD.Depense(modeles_usd=0.0009),
            "[M3] réponse coupée : échec nommé, la dépense part avec lui", f"{err} {dep}")
    _, obj, dep, err = run(completer([di(None, contenu="Voici la réponse : oui", cout=0.0001)]), n=4)
    b.check(obj is None and err is not None and "JSON" in str(err) and dep == CD.Depense(modeles_usd=0.0001),
            "[M3] du texte libre : échec nommé, la dépense part avec lui", f"{err} {dep}")
    _, obj, dep, err = run(completer([di(None, contenu="[1, 2]")]), n=4)
    b.check(obj is None and err is not None, "[M3] un JSON qui n'est pas un objet : échec nommé", f"{err}")

    # ── [V1]-[V5] l'évaluateur ────────────────────────────────────────────────────────────
    S = "presse.example"
    rencontrees = [f"https://www.{S}/rencontree", f"https://autre.example/{S}/x", f"https://{S}/"]
    trouves = [(f"https://{S}/rubrique/", "Rubrique", ""), (f"https://ailleurs.example/a", "Ailleurs", "2026-08-01"),
               (f"https://{S}/a1", "A1", "2026-08-05"), (f"https://{S}/a2", "A2", "2026-08-06"),
               (f"https://{S}/a3", "A3", "2026-08-07")]

    def monde(pages_ok=True, refus=(), contenus=None, modele=None, rech=None):
        pages = {}
        for u in [f"https://www.{S}/rencontree", f"https://{S}/a1", f"https://{S}/a2", f"https://{S}/a3",
                  f"https://{S}/rubrique/", "https://ailleurs.example/a", f"https://autre.example/{S}/x", f"https://{S}/"]:
            pages[u] = article(u) if pages_ok else AD.Lu(401)
        for u in refus:
            pages[u] = AD.Lu(401)
        envois = {U_RECH: rech or [exa_recherche(*trouves)], U_CONT: contenus or [exa_contenus({})]}
        if modele is not None:
            envois[U_DI] = modele
        return Reseau(pages, envois)

    async def evaluer(net, adresses=rencontrees, source=S):
        m = X.MoteurExa(net, "clef")
        ev = EV.EvaluateurDeSources(transport=net, moteur=m, modele=DI.ModeleDeepInfra(net, "clef"))
        try:
            e, dep = await ev(source, adresses)
            return e, dep, None
        except EV.EvaluationImpossible as exc:
            return None, exc.depense, exc

    attendues = [f"https://www.{S}/rencontree", f"https://{S}/a1", f"https://{S}/a2"][:N]
    net = monde(modele=[di(reponse_modele(attendues), cout=0.0003)])
    e, dep, err = run(evaluer(net), n=3)
    lues = [ex.adresse for ex in getattr(e, "exemples", ())]
    b.check(lues == attendues, "[V1] la rencontrée d'abord, puis les pages datées de la recherche, de la source seule",
            f"{lues} {err}")
    b.check(not any("ailleurs.example" in u or "autre.example" in u or u == f"https://{S}/" or "rubrique" in u
                    for u in net.lus),
            "[V1] ni page d'un autre site, ni page d'accueil, ni rubrique non datée n'est lue", f"{net.lus}")
    rech = net.vers(U_RECH)
    b.check(len(rech) == 1 and rech[0].get("includeDomains") == [S]
            and rech[0].get("category") == EXA["categories"][EVJ["recherches"][0]["categorie"]],
            "[V1] une seule recherche, limitée au domaine de la source, dans la catégorie du référentiel", f"{rech}")
    b.check(dep == CD.Depense(modeles_usd=0.0003, web_usd=0.007), "[V6] dépense = recherche + modèle", f"{dep}")

    # Assez de publications rencontrées : pas de recherche.
    assez = [f"https://{S}/a1", f"https://{S}/a2", f"https://{S}/a3"][:N]
    net = monde(modele=[di(reponse_modele(assez))])
    e, dep, err = run(evaluer(net, adresses=assez), n=3)
    b.check(e is not None and not net.vers(U_RECH) and dep.web_usd == 0,
            "[V1] assez de publications rencontrées et lisibles : aucune recherche payée", f"{net.vers(U_RECH)} {err}")

    # [V3] le message.
    msg = net.vers(U_DI)[0]["messages"][1]["content"] if net.vers(U_DI) else ""
    sysmsg = net.vers(U_DI)[0]["messages"][0]["content"] if net.vers(U_DI) else ""
    b.check(all(GRILLE["questions"][q] in msg and q in msg for q in QUESTIONS)
            and all(c["texte"] in msg and k in msg for k, c in GRILLE["criteres"].items()),
            "[V3] chaque question et chaque critère de M1, tels qu'écrits", "")
    b.check(E.CRITERE_PAGES_INVESTISSEURS not in msg and E.CRITERE_PAGES_INVESTISSEURS not in GRILLE["criteres"],
            "[V3] le critère des pages de relations investisseurs n'est pas proposé au modèle")
    b.check(all(f"article {a}" in msg for a in assez) and "var x=1" not in msg,
            "[V3] le texte de chaque publication, sans les scripts de la page")
    b.check(sysmsg == EVJ["consigne"] and net.vers(U_DI)[0]["model"] == EVJ["modele"],
            "[V7] la consigne et le modèle sont ceux du référentiel de l'évaluateur")

    # [V2] lecture directe refusée → texte du moteur, seulement ce qui manque (+1).
    long_txt = "texte lu par le moteur " * 60
    net = monde(pages_ok=False, contenus=[exa_contenus({u: long_txt for u in [f"https://www.{S}/rencontree"]}),
                                          exa_contenus({f"https://{S}/a1": long_txt, f"https://{S}/a2": long_txt})],
                modele=[di(reponse_modele(attendues))])
    e, dep, err = run(evaluer(net), n=3)
    demandes = [c["urls"] for c in net.vers(U_CONT)]
    b.check(e is not None and [ex.adresse for ex in e.exemples] == attendues,
            "[V2] des pages refusées en direct sont jugées sur le texte du moteur", f"{err}")
    b.check(len(demandes) == 2 and demandes[0] == [f"https://www.{S}/rencontree"]
            and len(demandes[1]) == N - 1 + 1 and demandes[1][0] == f"https://{S}/a1",
            "[V2] au moteur, seulement les pages qui manquent, plus une", f"{demandes}")

    net = monde(pages_ok=False, contenus=[exa_contenus({})], modele=[di(reponse_modele(attendues))])
    e, dep, err = run(evaluer(net), n=3)
    b.check(e is None and err is not None and "lisible" in str(err) and not net.vers(U_DI),
            "[V2] trop peu de publications lisibles : échec nommé, le modèle n'est pas appelé", f"{err}")
    b.check(dep.web_usd > 0 and dep.modeles_usd == 0, "[V2] l'échec porte ce que la recherche a coûté", f"{dep}")
    b.check(len(net.vers(U_RECH)) == len(EVJ["recherches"]),
            "[V2] les recherches du référentiel sont toutes essayées avant de renoncer", f"{len(net.vers(U_RECH))}")

    # [V4] le critère fixe le niveau et les natures.
    net = monde(modele=[di(reponse_modele(attendues, critere="presse_financiere", niveau="A", natures=("mesure",)))])
    e, _, err = run(evaluer(net), n=3)
    c = GRILLE["criteres"]["presse_financiere"]
    b.check(e is not None and e.niveau == c["niveau_max"] and list(e.natures) == list(c["natures"])
            and e.critere == "presse_financiere",
            "[V4] le critère choisi fixe le niveau et les natures (le modèle demandait A, mesure seule)",
            f"{getattr(e, 'niveau', '')} {getattr(e, 'natures', '')} {err}")
    net = monde(modele=[di(reponse_modele(attendues, critere="", niveau="C+", natures=("interpretation",)))])
    e, _, err = run(evaluer(net), n=3)
    b.check(e is not None and e.critere == "" and e.niveau == "C+" and e.natures == ("interpretation",),
            "[V4] sans critère, les propositions du modèle sont gardées pour votre arbitrage", f"{err}")
    for niveau, natures, quoi in (("A+++", ("interpretation",), "un niveau"), ("C+", ("rumeur",), "une nature")):
        net = monde(modele=[di(reponse_modele(attendues, critere="", niveau=niveau, natures=natures))])
        e, _, err = run(evaluer(net), n=3)
        b.check(e is None and err is not None, f"[V4] sans critère, {quoi} hors échelle est refusé(e)", f"{err}")

    # [V5] les réponses hors forme.
    def mal(objet_fn, label):
        net = monde(modele=[di(objet_fn(), cout=0.0005)])
        e, dep, err = run(evaluer(net), n=3)
        b.check(e is None and err is not None and dep.modeles_usd == 0.0005,
                f"[V5] {label} : échec nommé, avec la dépense du modèle", f"{err} {dep}")

    # Une page inventée EN PLUS des pages données (du même site : M1 ne la refuserait pas).
    mal(lambda: reponse_modele(attendues + ["https://presse.example/inventee"]), "une page qu'on ne lui a pas donnée")
    mal(lambda: reponse_modele(attendues, sans=QUESTIONS[0]), "une question sans réponse")
    mal(lambda: reponse_modele(attendues, constat="  "), "un constat vide")
    mal(lambda: reponse_modele(attendues, critere="relations_investisseurs_d_une_autre_societe"),
        "le critère réservé aux pages de relations investisseurs")
    mal(lambda: reponse_modele(attendues[:-1]), "une publication oubliée")
    mal(lambda: {**reponse_modele(attendues), "publications": reponse_modele(attendues)["publications"][:1] * 2},
        "deux réponses pour la même publication")

    # ── [V6] de bout en bout, par le contrat ───────────────────────────────────────────────
    async def bout_en_bout(lus_modele, passes=1):
        net = monde(modele=lus_modele)
        ed, rd = E.DepotMemoire(), R.DepotMemoire()
        await rd.noter_source_rencontree({"source": S, "emetteur": "FICTIVE-PRIVEE", "nature": "evenement",
                                          "adresses": [f"https://www.{S}/rencontree"], "vue_le": JOUR,
                                          "statut": "a_evaluer", "travail": "t", "essais": 0, "motif": ""})
        ev = EV.EvaluateurDeSources(transport=net, moteur=X.MoteurExa(net, "clef"), modele=DI.ModeleDeepInfra(net, "clef"))
        for _ in range(passes):
            await R.evaluer_les_sources_rencontrees(depot=rd, emetteurs_depot=ed, evaluateur=ev, le=JOUR)
        fiche = await E.lire_fiche(ed, "FICTIVE-PRIVEE") if False else None
        return (await rd.sources_rencontrees())[0], await ed.actes()

    src, actes = run(bout_en_bout([di(reponse_modele(attendues), cout=0.0003)]), n=2)
    b.check(src.get("issue") == "admise" and any(a["acte"] == E.ADMETTRE and a["source"] == S for a in actes),
            "[V6] une bonne source est admise par le système", f"{src}")
    b.check(src.get("depense") == {"modeles_usd": 0.0003, "web_usd": 0.007},
            "[V6] la dépense de la source = recherche + modèle", f"{src.get('depense')}")
    src, actes = run(bout_en_bout([di(reponse_modele(attendues, oui=False), cout=0.0003)]), n=2)
    b.check(src.get("issue") == "en_suspens" and any(a["acte"] == E.SUSPENDRE for a in actes),
            "[V6] une source faible est mise en suspens, pour votre arbitrage", f"{src}")
    src, actes = run(bout_en_bout([OCCUPE], passes=2), n=2)
    b.check(src.get("statut") != "evaluee" and int(src.get("essais", 0)) == 2 and "429" in src.get("motif", "")
            and not actes, "[V6] deux essais manqués : échec nommé, rien n'est acté", f"{src}")
    b.check((src.get("depense") or {}).get("web_usd", 0) == 0.014,
            "[V6] chaque essai manqué garde ce qu'il a payé (deux recherches)", f"{src.get('depense')}")

    # ── [V7] aucun nom de modèle dans le code ─────────────────────────────────────────────
    noms = [EVJ["modele"], *DIJ["prix_usd_par_million_de_jetons"]]
    fautifs = [f"{f.relative_to(BACKEND)} : {n}" for f in MODULE.rglob("*.py") if "__pycache__" not in f.parts
               for n in noms if n in strip_code(f.read_text(encoding="utf-8"))]
    b.check(not fautifs, "[V7] aucun nom de modèle dans le code du module (référentiels seulement)", "; ".join(fautifs))
    arbre = ast.parse((MODULE / "evaluateur.py").read_text(encoding="utf-8"))
    b.check(not any(isinstance(n, ast.Constant) and isinstance(n.value, str) and "Vous évaluez" in n.value
                    for n in ast.walk(arbre)), "[V7] la consigne n'est pas écrite dans le code")

    return b.summary()


async def _vide():
    return {}


if __name__ == "__main__":
    sys.exit(main())
