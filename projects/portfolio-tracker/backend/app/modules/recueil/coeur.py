"""Le cœur de la collecte — l'intérieur du module (rien d'ici ne s'importe du dehors : `contrat.py`).

Il reçoit une demande nommée par un GENRE de document, la présente aux adaptateurs qui savent ce
genre, dans l'ordre d'autorité du référentiel (registre officiel, site de l'émetteur, web), range ce
qu'ils trouvent tel quel, et rend une réponse : des documents avec leur origine et ce que M1 en dit,
ou une indisponibilité nommée. Il ne connaît aucun formulaire, aucun registre, aucune société : ces
mots vivent dans le référentiel de chaque adaptateur.

Aucune horloge : la date de collecte est donnée par l'appelant.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

from app.modules.chef_de_dossier.contrat import (
    ACTE_HUMAIN,
    ECHEC,
    EN_COURS,
    FAIT,
    INDISPONIBLE,
    Contexte,
    Depense,
    Pas,
    Resultat,
)
from app.modules.emetteurs import contrat as E

from . import adaptateurs as A
from .contrat import (
    AUTEUR_DOCUMENTATION,
    ECHOUEE,
    LANCEE,
    ESSAIS_PAR_DEMANDE,
    REPONDUE,
    VERSION_CONTRAT,
    Demande,
    DemandeRefusee,
    Depot,
    Document,
    Envoi,
    Indisponibilite,
    Provenance,
    Qualification,
    Recueil,
    Reponse,
    VueTravaux,
)

A_EVALUER = "a_evaluer"
EVALUEE = "evaluee"
EN_ECHEC = "en_echec"      # l'évaluateur a planté deux fois sur cette source


# ── Le référentiel (donnée) ──────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def referentiel() -> Mapping[str, Any]:
    """Les genres de document, l'ordre des familles de sources, les raisons d'indisponibilité. Un
    référentiel incohérent se refuse au chargement."""
    ref = json.loads(Path(__file__).with_name("referentiel.json").read_text(encoding="utf-8"))
    defauts = []
    for nom, g in ref["genres"].items():
        if not _nature_connue_de_m1(g.get("nature")):
            defauts.append(f"genre « {nom} » : nature hors du vocabulaire de M1")
        if g.get("etendue") not in ("dernier", "depuis", "adresse"):
            defauts.append(f"genre « {nom} » : étendue inconnue")
    if set(ref["priorite_des_raisons"]) != set(ref["raisons"]):
        defauts.append("les raisons et leur priorité ne nomment pas les mêmes choses")
    if set(ref["familles_dans_l_ordre"]) != {A.REGISTRE, A.SITE, A.WEB}:
        defauts.append("familles de sources : registre, site, web, chacune une fois")
    if defauts:
        raise ValueError("référentiel de la collecte incohérent : " + " ; ".join(defauts))
    return ref


def _nature_connue_de_m1(nature: Any) -> bool:
    """La nature d'information d'un genre doit être une de celles que M1 qualifie : on le lui
    demande (son contrat refuse une nature inconnue), sans recopier son vocabulaire ici."""
    try:
        E.qualifier(E.Fiche(emetteur="x", raison_sociale="x"), "", nature)
    except ValueError:
        return False
    return True


def _niveau_illisible() -> str:
    """Le niveau que M1 donne à une adresse illisible : une telle origine ne s'évalue pas."""
    return E.qualifier(E.Fiche(emetteur="x", raison_sociale="x"), "", "mesure").niveau


def _date(texte: str, quoi: str) -> str:
    try:
        return date.fromisoformat(texte).isoformat()
    except ValueError:
        raise DemandeRefusee(f"{quoi} : une date AAAA-MM-JJ ; reçu {texte!r}") from None


def valider(demande: Demande) -> Mapping[str, Any]:
    genre = referentiel()["genres"].get(demande.genre)
    if genre is None:
        raise DemandeRefusee(f"genre de document inconnu : {demande.genre!r} ; connus : "
                             f"{', '.join(referentiel()['genres'])}")
    if not demande.emetteur.strip():
        raise DemandeRefusee("une demande nomme son émetteur")
    if demande.depuis:
        _date(demande.depuis, "depuis")
    if genre["etendue"] == "adresse" and not demande.adresse.strip():
        raise DemandeRefusee(f"le genre « {demande.genre} » se demande à une adresse")
    return genre


# ── (Dé)sérialisation ────────────────────────────────────────────────────────────────────────

def _document(d: Mapping[str, Any]) -> Document:
    return Document(empreinte=d["empreinte"], emetteur=d["emetteur"], genre=d["genre"],
                    provenance=Provenance(**d["provenance"]), type_media=d["type_media"], taille=int(d["taille"]),
                    qualification=Qualification(**d["qualification"]), collecte_le=d["collecte_le"])


def _reponse(r: Mapping[str, Any], documents: Sequence[Document]) -> Reponse:
    ind = r.get("indisponibilite")
    return Reponse(demande=Demande(**r["demande"]), documents=tuple(documents),
                   indisponibilite=None if ind is None else Indisponibilite(
                       **{**ind, "essais": tuple(tuple(e) for e in ind["essais"])}),
                   depense=Depense(**r["depense"]), collecte_le=r["collecte_le"],
                   acte_attendu=r.get("acte_attendu", ""), identite=r.get("identite") or {},
                   essais=tuple(tuple(e) for e in r.get("essais") or ()))


def _vers_dict(rep: Reponse) -> dict[str, Any]:
    return {
        "version_contrat": VERSION_CONTRAT,
        "demande": asdict(rep.demande),
        "documents": [d.empreinte for d in rep.documents],
        "indisponibilite": None if rep.indisponibilite is None else asdict(rep.indisponibilite),
        "depense": {"modeles_usd": rep.depense.modeles_usd, "web_usd": rep.depense.web_usd},
        "collecte_le": rep.collecte_le,
        "acte_attendu": rep.acte_attendu,
        "identite": dict(rep.identite),
        "essais": [list(e) for e in rep.essais],
    }


async def _documents(depot: Depot, empreintes: Sequence[str]) -> list[Document]:
    rendus = []
    for e in empreintes:
        d = await depot.document(e)
        if d is None:
            raise ValueError(f"réponse rangée qui cite un document absent : {e}")
        rendus.append(_document(d))
    return rendus


# ── La collecte d'une demande ────────────────────────────────────────────────────────────────

def _adaptateurs(outils: Any) -> list[Any]:
    tous = list(getattr(outils, "adaptateurs", None) or A.tous())
    ordre = referentiel()["familles_dans_l_ordre"]
    return sorted(tous, key=lambda a: ordre.index(a.famille))


def _raison(raisons: Sequence[str]) -> str:
    prio = referentiel()["priorite_des_raisons"]
    connues = [r for r in raisons if r in prio]
    inconnues = [r for r in raisons if r not in prio]
    if inconnues:
        raise ValueError(f"raison d'indisponibilité hors du référentiel : {inconnues}")
    return min(connues, key=prio.index) if connues else "non_applicable"


async def _identifier(adaptateur: Any, fiche: Any, demande: Demande, *, emetteurs_depot: Any, outils: Any,
                      le: str) -> tuple[Any, dict[str, Any], str, tuple[str, str] | None]:
    """Consulte le registre sur l'identité de l'émetteur (#147). Rend la fiche (relue si complétée),
    ce qui a été fait, l'acte attendu (homonyme) et l'essai à noter s'il n'a rien donné."""
    ident = await adaptateur.identifier(fiche, outils.transport)
    if ident.issue == "trouvee":
        fait = await E.completer_identite(
            emetteurs_depot, demande.emetteur, raison_sociale=ident.raison_sociale, pays=ident.pays,
            cotations=list(ident.cotations), references=list(ident.references), auteur=AUTEUR_DOCUMENTATION,
            motif=f"identité lue au {ident.registre}, consulté le {le}", le=le)
        if fait["issue"] == "completee":
            fiche = await E.lire_fiche(emetteurs_depot, demande.emetteur)
        return fiche, {"registre": ident.registre, **fait}, "", None
    if ident.issue == "homonyme":
        acte = (f"dire quelle société est « {demande.emetteur} » : le {ident.registre} en connaît "
                f"plusieurs ({' ; '.join(ident.candidats)}) — corriger sa fiche (numéro au registre)")
        return fiche, {}, acte, (adaptateur.nom, f"homonyme : {ident.detail}")
    raison = "injoignable" if ident.issue == "injoignable" else "non_applicable"
    return fiche, {}, "", (adaptateur.nom, f"{raison} : identité — {ident.detail}")


async def collecter(demande: Demande, *, depot: Depot, emetteurs_depot: Any, outils: Any, le: str) -> Reponse:
    genre = valider(demande)
    le = _date(le, "date de collecte")
    ref = referentiel()
    try:
        fiche = await E.lire_fiche(emetteurs_depot, demande.emetteur)
    except E.FicheAbsente:
        rep = Reponse(demande, (), Indisponibilite(demande.genre, demande.emetteur, "fiche_absente",
                                                   ref["raisons"]["fiche_absente"]), Depense(), le)
        await depot.ajouter_reponse(_vers_dict(rep))
        return rep

    essais: list[tuple[str, str]] = []
    raisons: list[str] = []
    depense = Depense()
    rencontrees: list[str] = []
    identite: dict[str, Any] = {}
    acte = ""
    trouves: list[A.Trouve] = []
    retenu = None

    def deja_pour(nom: str):
        async def deja(identifiant: str) -> Mapping[str, str]:
            return await depot.parties_rangees(demande.emetteur, nom, identifiant)
        return deja

    for adaptateur in _adaptateurs(outils):
        if not adaptateur.sait(demande.genre):
            continue
        if adaptateur.famille == A.REGISTRE and hasattr(adaptateur, "identifier"):
            fiche, fait, acte_registre, essai = await _identifier(
                adaptateur, fiche, demande, emetteurs_depot=emetteurs_depot, outils=outils, le=le)
            identite = identite or fait
            acte = acte or acte_registre
            if essai is not None and acte_registre:
                essais.append(essai)
                raisons.append("homonyme")
                continue
            if essai is not None and essai[1].startswith("injoignable"):
                essais.append(essai)   # le registre ne répond pas : on ne le relit pas pour chercher
                raisons.append("injoignable")
                continue
            if essai is not None:
                essais.append(essai)   # le registre ne connaît pas la société ; il le redira en cherchant
        tr = await adaptateur.chercher(A.Appel(demande=demande, fiche=fiche, genre=genre,
                                               transport=outils.transport, moteur=getattr(outils, "moteur", None),
                                               deja=deja_pour(adaptateur.nom), le=le))
        depense = depense.plus(tr.depense)
        rencontrees.extend(tr.rencontrees)
        if tr.trouves:
            trouves, retenu = tr.trouves, adaptateur
            break
        if tr.raison not in ref["raisons"]:
            raise ValueError(f"l'adaptateur {adaptateur.nom} rend une raison hors du référentiel : {tr.raison!r}")
        essais.append((adaptateur.nom, f"{tr.raison} : {tr.detail}"))
        raisons.append(tr.raison)

    documents: list[Document] = []
    for t in trouves:
        if t.empreinte_connue:
            d = await depot.document(t.empreinte_connue)
            if d is not None:
                documents.append(_document(d))
                continue
        contenu = t.contenu or b""
        if len(contenu) > ref["taille_max_octets"]:
            essais.append((retenu.nom, f"trop_volumineux : {t.provenance.adresse} ({len(contenu)} octets)"))
            raisons.append("trop_volumineux")
            continue
        if not contenu.strip():
            essais.append((retenu.nom, f"illisible : {t.provenance.adresse} (contenu vide)"))
            raisons.append("illisible")
            continue
        q = E.qualifier(fiche, t.provenance.adresse, genre["nature"])
        empreinte = hashlib.sha256(contenu).hexdigest()
        fiche_doc = {"empreinte": empreinte, "emetteur": demande.emetteur, "genre": demande.genre,
                     "provenance": asdict(t.provenance), "type_media": t.type_media, "taille": len(contenu),
                     "qualification": {"admise": q.admise, "niveau": q.niveau, "motif": q.motif, "source": q.source},
                     "collecte_le": le, "version_contrat": VERSION_CONTRAT}
        if not await depot.ranger_document(fiche_doc, contenu):
            fiche_doc = dict(await depot.document(empreinte))   # même contenu déjà rangé : on le cite
        documents.append(_document(fiche_doc))

    # Les sources inconnues rencontrées partent à l'évaluateur (B6) ; la réponse ne l'attend pas.
    illisible = _niveau_illisible()
    for d in documents:
        q = d.qualification
        if not q.admise and not q.source and q.niveau != illisible:
            source = E.domaine(d.provenance.adresse)
            if source:
                await depot.noter_source_rencontree({
                    "source": source, "emetteur": demande.emetteur, "nature": genre["nature"],
                    "adresses": [d.provenance.adresse], "vue_le": le, "statut": A_EVALUER,
                    "travail": demande.cle, "essais": 0, "motif": ""})

    # Les pages de relations investisseurs d'AUTRES sociétés : admises au fil de l'eau (B7).
    siens = {E.domaine(l.adresse) for l in fiche.lieux}
    autres = [a for a in rencontrees
              if (dom := E.domaine(a)) and not any(dom == s or dom.endswith("." + s) for s in siens if s)]
    if autres:
        await E.admettre_pages_investisseurs(emetteurs_depot, autres, le=le)

    if documents:
        rep = Reponse(demande, tuple(documents), None, depense, le, acte_attendu=acte, identite=identite,
                      essais=tuple(essais))
    else:
        if not essais:
            essais.append(("—", "non_applicable : aucun adaptateur ne sait ce genre de document"))
        raison = _raison(raisons)
        rep = Reponse(demande, (), Indisponibilite(
            demande.genre, demande.emetteur, raison,
            f"{ref['raisons'][raison]} — " + " | ".join(f"{a} → {m}" for a, m in essais), tuple(essais)),
            depense, le, acte_attendu=acte, identite=identite, essais=tuple(essais))
    await depot.ajouter_reponse(_vers_dict(rep))
    return rep


# ── La lecture ───────────────────────────────────────────────────────────────────────────────

async def lire_recueil(depot: Depot, emetteur: str) -> Recueil:
    dernieres: dict[str, Mapping[str, Any]] = {}
    depense = Depense()
    for r in await depot.reponses(emetteur):
        if r.get("version_contrat") != VERSION_CONTRAT:
            raise ValueError(f"réponse en version {r.get('version_contrat')!r}, attendu {VERSION_CONTRAT!r}")
        dernieres[Demande(**r["demande"]).cle] = r
        depense = depense.plus(Depense(**r["depense"]))
    for s in await depot.sources_rencontrees():
        if s["emetteur"] == emetteur and s.get("depense"):
            depense = depense.plus(Depense(**s["depense"]))
    reponses = [_reponse(r, await _documents(depot, r["documents"])) for r in dernieres.values()]
    en_cours = tuple(Demande(**t["demande"]) for t in await depot.travaux(emetteur) if t["statut"] == LANCEE)
    return Recueil(emetteur=emetteur, reponses=tuple(reponses), en_cours=en_cours, depense=depense)


# ── La tâche de fond ─────────────────────────────────────────────────────────────────────────

async def traiter_les_travaux(*, depot: Depot, emetteurs_depot: Any, outils: Any, le: str,
                              emetteur: str | None = None) -> list[dict[str, Any]]:
    lignes = []
    for t in await depot.travaux(emetteur):
        if t["statut"] != LANCEE:
            continue
        demande = Demande(**t["demande"])
        try:
            rep = await collecter(demande, depot=depot, emetteurs_depot=emetteurs_depot, outils=outils, le=le)
        except Exception as exc:  # noqa: BLE001 — une panne d'infrastructure est un échec NOMMÉ du travail
            t = {**t, "statut": ECHOUEE, "essais": int(t.get("essais", 0)) + 1,
                 "motif": f"{type(exc).__name__}: {exc}"}
        else:
            t = {**t, "statut": REPONDUE, "motif": "",
                 "depense": asdict(Depense(**t.get("depense", {})).plus(rep.depense)),
                 "acte_attendu": rep.acte_attendu,
                 "indisponible": None if rep.indisponibilite is None else
                 f"{rep.indisponibilite.raison} : {rep.indisponibilite.detail}"}
        await depot.ecrire_travail(t)
        lignes.append({"demande": demande.cle, "statut": t["statut"], "motif": t.get("motif", "")})
    return lignes


async def evaluer_les_sources_rencontrees(*, depot: Depot, emetteurs_depot: Any, evaluateur: Any,
                                          le: str, emetteur: str | None = None) -> list[dict[str, Any]]:
    lignes = []
    for s in await depot.sources_rencontrees():
        if s["statut"] != A_EVALUER or (emetteur is not None and s["emetteur"] != emetteur):
            continue
        try:
            evaluation, depense = await evaluateur(s["source"], list(s["adresses"]))
        except Exception as exc:  # noqa: BLE001 — l'évaluateur qui plante laisse la source à évaluer
            essais = int(s.get("essais", 0)) + 1
            statut = EN_ECHEC if essais >= ESSAIS_PAR_DEMANDE else A_EVALUER
            # Ce qu'un essai manqué a déjà payé (recherche, modèle) reste compté (B9).
            paye = getattr(exc, "depense", None)
            cumul = Depense(**s.get("depense", {})).plus(paye if isinstance(paye, Depense) else Depense())
            await depot.marquer_source(s["source"], {"essais": essais, "statut": statut, "depense": asdict(cumul),
                                                     "motif": f"{type(exc).__name__}: {exc}"})
            lignes.append({"source": s["source"], "issue": statut, "motif": str(exc)})
            continue
        try:
            r = await E.evaluer_source(emetteurs_depot, evaluation, le=le)
            champs = {"statut": EVALUEE, "issue": r["issue"], "motif": r.get("motif", "")}
        except E.ActeRefuse as exc:
            champs = {"statut": EVALUEE, "issue": "refusee", "motif": str(exc)}
        # La dépense reste sur la source ; le pas d'évaluation du dossier la déclare au chef.
        cumul = Depense(**s.get("depense", {})).plus(depense)
        await depot.marquer_source(s["source"], {**champs, "depense": asdict(cumul)})
        lignes.append({"source": s["source"], **champs})
    return lignes


# ── L'écran ──────────────────────────────────────────────────────────────────────────────────

async def vue_ecran(depot: Depot, emetteur: str) -> dict[str, Any]:
    recueil = await lire_recueil(depot, emetteur)
    return {
        "version_contrat": VERSION_CONTRAT,
        "emetteur": emetteur,
        "travaux": [dict(t) for t in await depot.travaux(emetteur)],
        "reponses": [{**_vers_dict(r), "documents": [asdict(d) for d in r.documents]} for r in recueil.reponses],
        "sources_rencontrees": [dict(s) for s in await depot.sources_rencontrees() if s["emetteur"] == emetteur],
        "depense": {"modeles_usd": recueil.depense.modeles_usd, "web_usd": recueil.depense.web_usd},
        "referentiel": {k: referentiel()[k] for k in ("version", "genres", "raisons")},
    }


# ── Le pas du chef de dossier ────────────────────────────────────────────────────────────────

async def ranger_envoi(depot: Depot, envoi: Envoi) -> None:
    existants = {t["cle"]: t for t in await depot.travaux()}
    for d in envoi.a_lancer:
        anc = existants.get(d.cle, {})
        await depot.ecrire_travail({
            "cle": d.cle, "demande": asdict(d), "statut": LANCEE, "motif": "",
            "essais": int(anc.get("essais", 0)), "depense": anc.get("depense") or asdict(Depense()),
            "declare": anc.get("declare") or asdict(Depense()),
            "actes_traites": envoi.actes_traites.get(d.cle, int(anc.get("actes_traites", 0)))})
        existants[d.cle] = {**anc, "cle": d.cle}
    for cle, dep in envoi.declare.items():
        t = {t["cle"]: t for t in await depot.travaux()}[cle]
        await depot.ecrire_travail({**t, "declare": asdict(dep)})
    for source in envoi.sources_a_relancer:
        await depot.marquer_source(source, {"statut": A_EVALUER, "essais": 0})
    for source, dep in envoi.declare_sources.items():
        await depot.marquer_source(source, {"declare": asdict(dep)})


def pas_collecte(nom: str, demandes: Sequence[Demande], vue: VueTravaux, envoi: Envoi, *,
                 apres: tuple[str, ...] = (), cout_estime_usd: float = 0.0) -> Pas:
    for d in demandes:
        valider(d)
    if len({d.cle for d in demandes}) != len(demandes) or not demandes:
        raise DemandeRefusee("un pas de collecte porte au moins une demande, chacune une fois")

    def travail(d: Demande) -> Mapping[str, Any] | None:
        return vue.travaux.get(d.cle)

    def executer(ctx: Contexte) -> Resultat:
        actes = sum(1 for a in ctx.actes_accomplis if a.startswith(f"acte:{nom}:"))
        a_lancer = []
        for d in demandes:
            t = travail(d)
            if t is None or t["statut"] == ECHOUEE:
                a_lancer.append(d)
            elif t["statut"] == REPONDUE and t.get("acte_attendu") and int(t.get("actes_traites", 0)) < actes:
                a_lancer.append(d)         # votre acte est enregistré : on recollecte avec la fiche corrigée
                envoi.actes_traites[d.cle] = actes
        if a_lancer:
            envoi.a_lancer.extend(x for x in a_lancer if x not in envoi.a_lancer)
            return Resultat(issue=EN_COURS, motif=f"collecte lancée : {len(a_lancer)} demande(s) "
                                                  f"({', '.join(x.genre for x in a_lancer)})")
        return suivre(ctx)

    def suivre(ctx: Contexte) -> Resultat:
        nouvelle = Depense()
        for d in demandes:
            t = travail(d)
            if t is None:
                continue
            dep, decl = Depense(**t.get("depense", {})), Depense(**t.get("declare", {}))
            if dep != decl:
                nouvelle = nouvelle.plus(Depense(max(0.0, dep.modeles_usd - decl.modeles_usd),
                                                 max(0.0, dep.web_usd - decl.web_usd)))
                envoi.declare[d.cle] = dep
        etats = [(d, travail(d)) for d in demandes]
        echouees = [(d, t) for d, t in etats if t is not None and t["statut"] == ECHOUEE]
        if echouees:
            d, t = echouees[0]
            return Resultat(issue=ECHEC, depense=nouvelle, motif=f"collecte de « {d.genre} » en échec : {t['motif']}")
        attendues = [d for d, t in etats if t is None or t["statut"] != REPONDUE]
        if attendues:
            return Resultat(issue=EN_COURS, depense=nouvelle,
                            motif=f"collecte : {len(demandes) - len(attendues)}/{len(demandes)} demandes répondues")
        actes = [t["acte_attendu"] for _, t in etats if t.get("acte_attendu")]
        if actes:
            return Resultat(issue=ACTE_HUMAIN, depense=nouvelle, acte=actes[0],
                            motif="la collecte attend votre acte sur l'identité de l'émetteur")
        manques = [f"{d.genre} — {t['indisponible']}" for d, t in etats if t.get("indisponible")]
        if manques:
            return Resultat(issue=INDISPONIBLE, depense=nouvelle, motif="indisponible : " + " ; ".join(manques))
        return Resultat(issue=FAIT, depense=nouvelle)

    # La collecte vient toujours après la fiche : sans elle on ne sait ni qui est l'émetteur ni où il
    # publie, et le chef de dossier doit s'arrêter sur l'acte qui l'établit (B2), pas collecter à vide.
    apres = tuple(dict.fromkeys((E.NOM_DU_PAS,) + tuple(apres)))
    return Pas(nom=nom, module="recueil", apres=apres, executer=executer, suivre=suivre,
               cout_estime_usd=cout_estime_usd)


def pas_evaluation(nom: str, emetteur: str, vue: VueTravaux, envoi: Envoi, *, apres: tuple[str, ...] = (),
                   cout_estime_usd: float = 0.0) -> Pas:
    def nouvelle_depense() -> Depense:
        nouvelle = Depense()
        for src, s in vue.sources.items():
            dep, decl = Depense(**s.get("depense", {})), Depense(**s.get("declare", {}))
            if dep != decl:
                nouvelle = nouvelle.plus(Depense(max(0.0, dep.modeles_usd - decl.modeles_usd),
                                                 max(0.0, dep.web_usd - decl.web_usd)))
                envoi.declare_sources[src] = dep
        return nouvelle

    def executer(ctx: Contexte) -> Resultat:
        relancer = [src for src, s in vue.sources.items() if s["statut"] == EN_ECHEC]
        if relancer:
            envoi.sources_a_relancer.extend(x for x in relancer if x not in envoi.sources_a_relancer)
            return Resultat(issue=EN_COURS, motif=f"évaluation relancée : {', '.join(relancer)}")
        return suivre(ctx)

    def suivre(ctx: Contexte) -> Resultat:
        depense = nouvelle_depense()
        en_echec = [s for s in vue.sources.values() if s["statut"] == EN_ECHEC
                    and s["source"] not in envoi.sources_a_relancer]
        if en_echec:
            return Resultat(issue=ECHEC, depense=depense,
                            motif=f"l'évaluateur a échoué sur {en_echec[0]['source']} : {en_echec[0].get('motif', '')}")
        attendues = [s["source"] for s in vue.sources.values() if s["statut"] in (A_EVALUER, EN_ECHEC)]
        if attendues:
            return Resultat(issue=EN_COURS, depense=depense,
                            motif=f"{len(attendues)} source(s) inconnue(s) en cours d'évaluation : {', '.join(attendues)}")
        return Resultat(issue=FAIT, depense=depense)

    return Pas(nom=nom, module="recueil", apres=apres, executer=executer, suivre=suivre,
               cout_estime_usd=cout_estime_usd)
