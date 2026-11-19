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
  [V8] un aperçu n'est pas une publication (arbitrage du 2026-11-18) : le modèle dit pour chaque texte
       s'il est complet (question du référentiel, réponse motivée exigée) ; une publication déclarée
       incomplète ne compte pas : échec nommé qui la désigne, avec la dépense, rien n'est transmis à
       M1 ; la coupe faite par l'équipe est dite au modèle, une page courte n'en porte pas mention

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
from app.modules.recueil.adaptateurs import apercus as AP  # noqa: E402
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
                   sans=None, constat="constaté dans le texte", incompletes=(), complet=True):
    return {"critere": critere, "natures": list(natures), "niveau": niveau,
            "publications": [{"numero": i + 1,
                              **({"texte_complet": {"oui": a not in incompletes,
                                                    "constat": "aperçu coupé avant le corps" if a in incompletes
                                                    else "corps de l'article présent"}} if complet else {}),
                              "reponses": {q: {"oui": oui if i == 0 else True, "constat": constat}
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
    f = DIJ["facteur_du_niveau_de_service"]
    b.check(dep == CD.Depense(modeles_usd=(prix[connu]["entree"] + prix[connu]["sortie"]) * f),
            "[M1] sans coût déclaré, les jetons au prix du référentiel", f"{dep}")
    _, _, dep, _ = run(completer([di({"ok": 1}, cout=None, jetons=(1_000_000, 0))], modele="inconnu/modele"), n=4)
    b.check(dep == CD.Depense(modeles_usd=DIJ["prix_de_repli"]["entree"] * f),
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
    mal(lambda: {**reponse_modele(attendues), "publications": [{**x, "numero": str(x["numero"])}
                                                                for x in reponse_modele(attendues)["publications"]]},
        "un numéro de publication écrit en texte")
    mal(lambda: {**reponse_modele(attendues), "publications": [{**x, "numero": True if x["numero"] == 1 else x["numero"]}
                                                                for x in reponse_modele(attendues)["publications"]]},
        "un numéro de publication booléen")
    mal(lambda: reponse_modele(attendues, sans=QUESTIONS[0]), "une question sans réponse")
    mal(lambda: reponse_modele(attendues, constat="  "), "un constat vide")
    mal(lambda: reponse_modele(attendues, critere="relations_investisseurs_d_une_autre_societe"),
        "le critère réservé aux pages de relations investisseurs")
    mal(lambda: reponse_modele(attendues[:-1]), "une publication oubliée")
    mal(lambda: {**reponse_modele(attendues), "publications": reponse_modele(attendues)["publications"][:1] * 2},
        "deux réponses pour la même publication")
    mal(lambda: reponse_modele(attendues, complet=False), "[V8] « texte complet » sans réponse")

    # ── [V8] un aperçu n'est pas une publication ──────────────────────────────────────────
    net = monde(modele=[di(reponse_modele(attendues, incompletes=attendues[1:2]), cout=0.0004)])
    e, dep, err = run(evaluer(net), n=3)
    b.check(e is None and err is not None and attendues[1] in str(err) and "aperçu coupé" in str(err)
            and f"{N - 1} publication(s) complète(s)" in str(err),
            "[V8] une publication déclarée incomplète ne compte pas : échec nommé qui la désigne", f"{err}")
    b.check(dep.modeles_usd == 0.0004 and dep.web_usd == 0.014,
            "[V8] l'échec porte la dépense du modèle, de la recherche et du suivi de l'aperçu", f"{dep}")
    msg = net.vers(U_DI)[0]["messages"][1]["content"] if net.vers(U_DI) else ""
    b.check(EVJ["question_texte_complet"] in msg and '"texte_complet"' in msg,
            "[V8] le modèle reçoit la question du texte complet, telle qu'au référentiel", "")
    mention = EVJ["mention_coupe"].format(n=EVJ["caracteres_par_publication"])
    b.check(mention not in msg and EVJ["entete_coupe"].split("{")[0] not in msg,
            "[V8] une page courte ne porte pas la mention de coupe", "")
    long_txt = "x" * (EVJ["caracteres_par_publication"] + 50)
    net = monde(pages_ok=False, contenus=[exa_contenus({f"https://{S}/a1": long_txt, f"https://{S}/a2": long_txt,
                                                        f"https://{S}/a3": long_txt})],
                modele=[di(reponse_modele(assez))])
    e, dep, err = run(evaluer(net, adresses=assez), n=3)
    msg = net.vers(U_DI)[0]["messages"][1]["content"] if net.vers(U_DI) else ""
    entete = EVJ["entete_coupe"].format(n=EVJ["caracteres_par_publication"])
    b.check(e is not None and msg.count(mention) == N and msg.count(entete) == N and long_txt not in msg,
            "[V8] la coupe faite par l'équipe est dite au modèle, sur chaque texte coupé", f"{msg.count(mention)} {err}")

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
    src, actes = run(bout_en_bout([di(reponse_modele(attendues, incompletes=attendues[:1]))]), n=2)
    b.check(src.get("issue") != "admise" and src.get("statut") != "evaluee" and "incomplète" in src.get("motif", "")
            and not actes, "[V8] de bout en bout : un aperçu ne fait ni admettre ni suspendre, le motif le dit", f"{src}")
    src, actes = run(bout_en_bout([OCCUPE], passes=2), n=2)
    b.check(src.get("statut") != "evaluee" and int(src.get("essais", 0)) == 2 and "429" in src.get("motif", "")
            and not actes, "[V6] deux essais manqués : échec nommé, rien n'est acté", f"{src}")
    b.check((src.get("depense") or {}).get("web_usd", 0) == 0.014,
            "[V6] chaque essai manqué garde ce qu'il a payé (deux recherches)", f"{src.get('depense')}")


    # ── [X5] [P1]-[P7] un aperçu est un signal (M2 §7) ─────────────────────────────────────
    REEL = json.loads((BACKEND / "checks" / "fixtures" / "recueil" / "apercu_reuters.json").read_text(encoding="utf-8"))
    AJ = json.loads((MODULE / "adaptateurs" / "apercus.json").read_text(encoding="utf-8"))
    AP_U, AP_T, AP_TXT = REEL["apercu"]["url"], REEL["apercu"]["title"], REEL["apercu"]["text"]
    R_REPRISE = [r["url"] for r in REEL["resultats"] if "investing.com/news/stock-market" in r["url"]][0]
    R_SEC = [r["url"] for r in REEL["resultats"] if "sec.gov" in r["url"]][0]
    R_SANS = [r["url"] for r in REEL["resultats"] if "investing.com/news/earnings" in r["url"]][0]

    def exa_textes(resultats, cout=0.009):
        return js({"requestId": "s", "results": [{"id": r["url"], "url": r["url"], "title": r.get("title"),
                                                  "publishedDate": r.get("publishedDate"), "text": r["text"]}
                                                 for r in resultats], "costDollars": {"total": cout}})

    async def s_x5():
        net = Reseau(envois={U_RECH: [exa_textes(REEL["resultats"][:2])]})
        res, _ = await X.MoteurExa(net, "clef").rechercher("t", exclus=["reuters.com"], avec_texte=True)
        net2 = Reseau(envois={U_RECH: [exa_textes(REEL["resultats"][:1])]})
        res2, _ = await X.MoteurExa(net2, "clef").rechercher("t")
        return net.vers(U_RECH)[0], res, net2.vers(U_RECH)[0], res2
    c5, res5, c5b, res5b = run(s_x5(), n=4)
    b.check(c5.get("excludeDomains") == ["reuters.com"] and c5.get("contents", {}).get("text", {}).get("maxCharacters")
            == EXA["caracteres_par_page"] and res5 and res5[0].texte == REEL["resultats"][0]["text"].strip(),
            "[X5] Exa : domaines écartés et texte demandé, le texte revient avec chaque résultat", f"{c5}")
    b.check("contents" not in c5b and "excludeDomains" not in c5b and res5b and res5b[0].texte == "",
            "[X5] Exa : sans demande, ni texte ni exclusion (une recherche ordinaire ne paie pas les textes)", f"{c5b}")

    apercu = AD.Texte(AP_U, AP_TXT, AP_T, "2026-10-27")
    par_url = {r["url"]: AD.Resultat(r["url"], r.get("title") or "", "", r["text"]) for r in REEL["resultats"]}
    b.check(AP.reprise_reconnue(apercu, "reuters.com", par_url[R_REPRISE]) != "",
            "[P3] la reprise réelle est reconnue (nomme l'agence, phrase entière commune, plus longue)",
            f"{AP.phrases(AP_TXT)}")
    b.check(AP.reprise_reconnue(apercu, "reuters.com", par_url[R_SEC]) == ""
            and AP.reprise_reconnue(apercu, "reuters.com", par_url[R_SANS]) == "",
            "[P3] la pièce d'origine (8-K) et un article qui nomme l'agence sans phrase commune ne sont pas des reprises")
    vraie = par_url[R_REPRISE]
    sans_nom = AD.Resultat(vraie.adresse, "", "", AP.re.sub(r"(?i)reuters", "agence", vraie.texte))
    courte = AD.Resultat(vraie.adresse, "", "", vraie.texte[: len(AP_TXT)])
    phrase = AP.phrase_commune(AP_TXT, vraie.texte)
    mots_courts = AD.Resultat(vraie.adresse, "", "", "Reuters. " + " ".join(phrase.split()[: AJ["mots_min_par_phrase"] - 1])
                              + ". " + "remplissage " * 400)
    b.check(AP.reprise_reconnue(apercu, "reuters.com", sans_nom) == "",
            "[P3] une copie qui ne nomme pas l'agence n'est pas une reprise", "")
    b.check(AP.reprise_reconnue(apercu, "reuters.com", courte) == "",
            "[P3] un texte pas plus long que l'aperçu n'est pas une reprise (c'est un autre aperçu)", "")
    b.check(phrase and AP.reprise_reconnue(apercu, "reuters.com", mots_courts) == "",
            "[P3] une phrase de moins de mots_min_par_phrase mots n'identifie rien", "")
    b.check(AP.nom_de_l_agence("lesechos.fr") == "lesechos" and AP.nomme("lesechos.fr", "selon Les Echos, hier")
            and AP.nom_de_l_agence("nikkei.co.jp") == "nikkei" and AP.nom_de_l_agence("markets.ft.com") == "ft",
            "[P3] l'agence se nomme depuis son domaine, mots accolés compris", "")

    class Lieu:
        def __init__(self, adresse):
            self.adresse = adresse

    class FicheV:
        raison_sociale = "Visa Inc."
        lieux = (Lieu("investor.visa.com/news"),)

    ORIG = "https://investor.visa.com/news/q4-2026-results"
    vide = exa_recherche()

    def monde_web(suivis, refus=(AP_U,), pages_extra=None, titre=AP_T):
        pages = {u: AD.Lu(401) for u in refus}
        pages.update(pages_extra or {})
        ouverts = exa_recherche(*[(u, titre if u == AP_U else "T", "2026-10-27") for u in refus])
        envois = {U_RECH: [vide, ouverts, *suivis],
                  U_CONT: [exa_contenus({u: AP_TXT for u in refus})]}
        return Reseau(pages, envois)

    async def web(net, fiche=FicheV()):
        appel = AD.Appel(demande=R.Demande("annonces_importantes", "V"), fiche=fiche, genre={}, transport=net,
                         moteur=X.MoteurExa(net, "clef"), deja=lambda _: _vide(), le=JOUR)
        return await Web().chercher(appel)

    # [P1] [P5] rien de reconnu : l'aperçu n'est pas rangé, l'indisponibilité le nomme, le suivi est payé.
    net = monde_web([exa_textes([r for r in REEL["resultats"] if r["url"] in (R_SEC, R_SANS)])])
    tr = run(web(net), n=5)
    b.check(not tr.trouves and tr.raison == "apercu" and AP_U in tr.detail,
            "[P1] [P5] un aperçu sans suite n'est jamais rangé : indisponibilité « aperçu » qui le désigne",
            f"{tr.raison} {tr.detail} {[t.provenance.adresse for t in tr.trouves]}")
    b.check(abs(tr.depense.web_usd - (0.007 * 2 + 0.001 + 0.009)) < 1e-9,
            "[P5] le suivi est payé et compté (texte de l'aperçu + une recherche)", f"{tr.depense}")
    sv = [c for c in net.vers(U_RECH) if c.get("excludeDomains")]
    b.check(len(sv) == 1 and sv[0]["query"] == AP_T and sv[0]["excludeDomains"] == ["reuters.com"],
            "[P2] UNE recherche par le titre de l'aperçu, hors du domaine de l'agence", f"{sv}")

    # [P3] [P4] la reprise reconnue est rangée sous l'adresse de l'aperçu, lue chez le diffuseur.
    net = monde_web([exa_textes(REEL["resultats"])],
                    pages_extra={R_REPRISE: article("reprise lue directement", 3000)})
    tr = run(web(net), n=5)
    t0 = tr.trouves[0] if tr.trouves else None
    b.check(t0 is not None and t0.provenance.adresse == AP_U and t0.provenance.identifiant == R_REPRISE
            and "reprise sous licence" in t0.provenance.mention and b"reprise lue directement" in (t0.contenu or b""),
            "[P3] la reprise est rangée sous l'adresse de l'agence, lue chez le diffuseur (identifiant, mention)",
            f"{t0}")
    b.check(not any(E.domaine(a) == "investing.com" for a in tr.rencontrees),
            "[P4] le diffuseur n'est pas une source rencontrée", f"{tr.rencontrees}")
    b.check(all(b"opens new tab" not in (t.contenu or b"") for t in tr.trouves),
            "[P1] le texte de l'aperçu n'est jamais rangé", "")
    net = monde_web([exa_textes([r for r in REEL["resultats"] if r["url"] == R_REPRISE])])
    tr = run(web(net), n=5)
    t0 = tr.trouves[0] if tr.trouves else None
    b.check(t0 is not None and t0.type_media.startswith("text/plain") and t0.provenance.identifiant == R_REPRISE,
            "[P3] le diffuseur refuse la lecture directe : le texte du moteur, dit en texte brut", f"{t0}")

    # [P2] la pièce d'origine sur un lieu de la fiche passe devant la reprise.
    orig = {"url": ORIG, "title": "Visa Reports Fiscal Fourth Quarter", "publishedDate": "2026-10-27T20:05:00.000Z",
            "text": "Visa Inc. reported fiscal fourth quarter results."}
    net = monde_web([exa_textes([*REEL["resultats"], orig])], pages_extra={ORIG: article("communiqué Visa")})
    tr = run(web(net), n=5)
    t0 = tr.trouves[0] if tr.trouves else None
    b.check(t0 is not None and t0.provenance.adresse == ORIG and "signalée par" in t0.provenance.mention
            and AP_U in t0.provenance.mention and len(tr.trouves) == 1,
            "[P2] la pièce d'origine, sur un lieu de la fiche, est rangée et passe devant la reprise", f"{tr.trouves}")
    net = monde_web([exa_textes([*REEL["resultats"], orig])])
    tr = run(web(net), n=5)
    t0 = tr.trouves[0] if tr.trouves else None
    b.check(t0 is not None and t0.provenance.adresse == ORIG and t0.type_media.startswith("text/plain")
            and t0.contenu == orig["text"].encode(),
            "[P2] la pièce d'origine qui refuse la lecture directe : le texte rendu par la recherche, en texte brut",
            f"{t0}")
    net = monde_web([exa_textes([*REEL["resultats"], {**orig, "text": ""}])])
    tr = run(web(net), n=5)
    t0 = tr.trouves[0] if tr.trouves else None
    b.check(t0 is not None and t0.provenance.identifiant == R_REPRISE,
            "[P2] une pièce d'origine sans texte lisible laisse place à la reprise", f"{t0}")

    # [P5] borne et aperçu sans titre.
    trois = [f"https://www.reuters.com/x{i}" for i in range(AJ["suivis_max_par_demande"] + 1)]
    net = monde_web([exa_textes([])], refus=trois)
    tr = run(web(net), n=5)
    b.check(len([c for c in net.vers(U_RECH) if c.get("excludeDomains")]) == AJ["suivis_max_par_demande"]
            and "non suivi" in tr.detail, "[P5] au plus suivis_max_par_demande suivis par demande", f"{tr.detail}")
    net = monde_web([exa_textes(REEL["resultats"])], titre="")
    net.envois[U_CONT] = [js({"results": [{"id": AP_U, "url": AP_U, "title": "", "text": AP_TXT}], "costDollars": {"total": 0.001}})]
    tr = run(web(net), n=5)
    b.check(not tr.trouves and "sans titre" in tr.detail and not [c for c in net.vers(U_RECH) if c.get("excludeDomains")],
            "[P5] un aperçu sans titre : nommé, aucune recherche payée", f"{tr.detail}")

    # [P6] l'évaluateur remplace l'aperçu par sa reprise et rejuge une fois.
    SR = "reuters.com"
    pubs = [f"https://www.{SR}/a{i}" for i in range(1, N + 1)]

    def monde_ev(modele, suivis, refus=1):
        pages = {u: article(u) for u in pubs}
        for u in pubs[:refus]:
            pages[u] = AD.Lu(401)
        envois = {U_CONT: [js({"results": [{"id": u, "url": u, "title": AP_T, "text": AP_TXT} for u in pubs[:refus]],
                               "costDollars": {"total": 0.001 * refus}})],
                  U_RECH: list(suivis), U_DI: modele}
        return Reseau(pages, envois)

    # Ordre du message : les pages lues en direct d'abord, la page refusée relue par le moteur ensuite.
    net = monde_ev([di(reponse_modele(pubs[1:] + pubs[:1], incompletes=pubs[:1]), cout=0.0004),
                    di(reponse_modele(pubs), cout=0.0002)],
                   [exa_textes(REEL["resultats"])])
    e, dep, err = run(evaluer(net, adresses=pubs, source=SR), n=6)
    appels = net.vers(U_DI)
    m2 = appels[1]["messages"][1]["content"] if len(appels) > 1 else ""
    b.check(e is not None and len(appels) == 2 and sorted(x.adresse for x in e.exemples) == sorted(pubs),
            "[P6] l'aperçu est remplacé par sa reprise reconnue, le modèle rejuge une fois", f"{err}")
    b.check(EVJ["entete_reprise"].format(lieu=R_REPRISE) in m2 and m2.index(pubs[1]) < m2.index(pubs[0]),
            "[P6] le modèle sait où la reprise a été lue", "")
    b.check(abs(dep.modeles_usd - 0.0006) < 1e-9 and abs(dep.web_usd - 0.010) < 1e-9,
            "[P6] dépense = deux jugements + texte de l'aperçu + une recherche", f"{dep}")
    # L'aperçu lu EN DIRECT (page servie, texte coupé) arrive en tête : après remplacement, il passe en dernier.
    html = AD.Lu(200, ("<html><body>" + AP_TXT.replace("\n\n", "<p>") + "</body></html>").encode(), "text/html")
    net = Reseau({**{u: article(u) for u in pubs}, pubs[0]: html},
                 {U_RECH: [exa_recherche(*[(u, AP_T, "2026-10-27") for u in pubs]), exa_textes(REEL["resultats"])],
                  U_DI: [di(reponse_modele(pubs, incompletes=pubs[:1])), di(reponse_modele(pubs))]})
    e, dep, err = run(evaluer(net, adresses=[], source=SR), n=6)
    msgs = [a["messages"][1]["content"] for a in net.vers(U_DI)]
    b.check(e is not None and len(msgs) == 2 and msgs[0].index(pubs[0]) < msgs[0].index(pubs[1])
            and msgs[1].index(pubs[1]) < msgs[1].index(pubs[2]) < msgs[1].index(pubs[0]),
            "[P6] les publications inchangées d'abord, dans leur ordre (le début du message reste en cache)",
            f"{err} {len(msgs)}")
    net = monde_ev([di(reponse_modele(pubs[2:] + pubs[:2], incompletes=pubs[:2]), cout=0.0004)], [exa_textes([])], refus=2)
    e, dep, err = run(evaluer(net, adresses=pubs, source=SR), n=6)
    b.check(e is None and err is not None and "reprises cherchées" in str(err) and len(net.vers(U_DI)) == 1
            and len(net.vers(U_RECH)) == 1,
            "[P6] sans reprise pour chaque aperçu : échec nommé (V8) qui dit ce qui a été cherché ; un seul jugement, "
            "les recherches s'arrêtent au premier manque", f"{err} {len(net.vers(U_RECH))}")

    # [P7] DeepInfra : niveau de service, cache, préfixe commun ; aucun modèle dans le suivi.
    net, _, _, _ = run(completer([di({"ok": True})]), n=4)
    b.check((net.vers(U_DI) or [{}])[0].get("service_tier") == DIJ["niveau_de_service"],
            "[P7] la demande porte le niveau de service du référentiel", "")
    _, _, dep, _ = run(completer([js({"choices": [{"finish_reason": "stop", "message": {"content": "{}"}}],
                                      "usage": {"prompt_tokens": 1_000_000, "completion_tokens": 0,
                                                "prompt_tokens_details": {"cached_tokens": 1_000_000}}})],
                                 modele="deepseek-ai/DeepSeek-V4.1-Flash-1017"), n=4)
    p41 = prix["deepseek-ai/DeepSeek-V4.1-Flash-1017"]
    b.check(abs(dep.modeles_usd - p41["entree_en_cache"] * f) < 1e-12,
            "[P7] sans coût déclaré, les jetons servis par le cache à leur prix", f"{dep}")
    t = [AD.Texte("https://a.example/1", "x" * 600)]
    ma, mb = EV.message("a.example", GRILLE, t), EV.message("tout-autre.example", GRILLE, t)
    commun = len(next((ma[:i] for i in range(len(ma), 0, -1) if mb.startswith(ma[:i])), ""))
    b.check('"numero": 1' in ma and "nombre entier" in ma,
            "[V5] le format montre le numéro de publication comme un entier (mesuré : un gabarit entre guillemets "
            "fait écrire « \"1\" »)", "")
    b.check(commun >= ma.index("Source à juger") and all(c["texte"] in ma[:commun] for c in GRILLE["criteres"].values())
            and '"texte_complet"' in ma[:commun],
            "[P7] critères, questions et format précèdent la source : deux sources partagent ce début", f"{commun}")
    src_ap = strip_code((MODULE / "adaptateurs" / "apercus.py").read_text(encoding="utf-8"))
    b.check("deepinfra" not in src_ap and "completer" not in src_ap and "modele" not in src_ap.lower(),
            "[P7] aucun appel au modèle dans le suivi des aperçus", "")

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
