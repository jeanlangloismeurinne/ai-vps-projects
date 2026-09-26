"""La NOTE FLASH — l'agent qui LIT un dépôt dont la forme ne dit pas la substance (V3 lot 7, maillon 2
de la taxonomie des événements, `roadmap/V3/04-taxonomie-evenements.md` §10, convention #90).

Pourquoi il existe
------------------
Le maillon 1 (#89) range chaque dépôt 8-K/6-K par sa FORME : 2.03 est un financement, 2.02 des
résultats… Tout ce que la forme ne décide pas (8.01 « autre événement », 7.01 seul, 1.01 sans
financement, un 6-K) est `a_qualifier` et rouvre TOUTES les questions (arbitrage Q3). Sur le réel :
23 dépôts RVMD, 14 NVDA, 17 MSFT. Parmi eux, trois cas qui disent tout :
  · RVMD 26/08 (8.01) — la FDA approuve RASONQUE : réglementaire favorable, rouvre la défendabilité ;
  · NVDA 02/09 (8.01) — accord pour acquérir Hugging Face : changement de PÉRIMÈTRE, que la forme ne
    voit pas (l'item 2.01 ne viendra qu'à la clôture, en 2027) ;
  · MSFT 02/09 (7.01) — présentation des nouveaux segments de reporting : ne devrait rien rouvrir.
Ce que fait un vrai fonds : l'analyste lit le communiqué le jour même et écrit une note flash — les
points touchés, le passage qui le montre. C'est ce que fait cet agent, une fois par dépôt.

CE QUE LE MODÈLE VOIT — ET CE QU'IL NE VOIT PAS
-----------------------------------------------
Il voit l'entreprise (raison sociale, #86), la forme du dépôt, le TEXTE du dépôt (le formulaire et ses
communiqués EX-99, rien d'autre) et le catalogue des types d'événement — identifiant et libellé. Il ne
voit PAS ce que chaque type rouvre (`portee`, `rouverte_par`) : il dit ce qui s'est passé, jamais
combien de questions il veut rouvrir. Lui montrer la conséquence en ferait un levier sur l'exigence,
le levier que la V3 retire partout (#59, « tout levier du modèle sur l'exigence » est fermé).

CE QUE LE CODE TIENT (le pont `valider_note`)
---------------------------------------------
  · chaque type existe au catalogue du jour, et n'est ni `a_qualifier` (c'est « illisible », une
    autre forme de la sortie) ni un `surprise_*` (dérivé de la cause par le code, Q2) ;
  · chaque passage — et chaque passage de cause — est une citation LITTÉRALE du texte lu (casse,
    espaces et guillemets typographiques normalisés, rien d'autre). C'est une garde de FORME : elle
    prouve que le passage existe, pas qu'il justifie le type (`feedback_garde_structure_pas_sens`) ;
  · une note refusée par le pont n'est PAS persistée : le dépôt reste `a_qualifier`, il rouvre tout.
    L'échec se dit ; il ne devient jamais « ne rouvre rien ».

Ce qui est persisté (migration 050, `notes_flash`) : la note, une fois par dépôt et par version du
catalogue, append-only. La PORTÉE ne l'est jamais : `evenements.ancre_de_la_question` la recalcule à
chaque lecture contre le référentiel du jour (#53), à partir de `qualifications_de_l_emetteur`.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Optional

import asyncpg
import httpx

from app.agents.providers import ResolvedAgent, get_agent_provider
from app.agents.v2.frameworks import load_frameworks
from app.agents.v2.runner import AgentRunResult, run_json_agent
from app.config import settings
from app.contracts.framework_definition_schema import FrameworksFile
from app.contracts.note_flash_schema import SURPRISE, NoteFlashSortie, type_derive
from app.db.database import get_db_session
from app.knowledge.edgar_facts import _UA
from app.knowledge.edgar_feed import EdgarFeedUnavailable, IdentiteEmetteur, identite_de_l_emetteur
from app.knowledge.evenements import A_QUALIFIER, QualificationLue, types_du_depot
from app.knowledge.material_events import (
    MaterialEvent, MaterialEventLookup, material_anchor_for_ticker)
from app.knowledge.websearch import html_to_text

logger = logging.getLogger(__name__)

__all__ = [
    "DocumentDepot", "NoteRedigee", "NoteFlashImpossible", "NoteFlashRefusee",
    "extraire_documents", "types_proposables", "contexte_note_flash", "valider_note",
    "depots_a_lire", "telecharger_soumission", "rediger_note_flash", "persister_note",
    "qualifications_de_l_emetteur", "LectureDesDepots", "DepotTraite", "lire_les_depots_en_attente",
    "titres_suivis", "lecture_du_matin",
]


class NoteFlashImpossible(Exception):
    """Le dépôt n'a pas pu être LU (EDGAR injoignable, aucun document lisible). Le dépôt reste
    `a_qualifier` — on ne sait pas, donc il rouvre tout ; aucun appel modèle n'a été payé."""


class NoteFlashRefusee(Exception):
    """La lecture du modèle a été refusée par le pont (type hors catalogue, passage introuvable).
    Rien n'est persisté : le dépôt reste `a_qualifier`."""


# ── 1. Ce qu'on lit d'un dépôt ──────────────────────────────────────────────────────────────────────

# Le formulaire lui-même et ses communiqués (EX-99.x). Pas les contrats (EX-10), les actes (EX-1, EX-4),
# les avis juridiques (EX-5), ni le XBRL ou les images : un analyste lit le communiqué, pas l'indenture.
_TYPES_LUS = re.compile(r"^(8-K|8-K/A|6-K|6-K/A|EX-99(\.\d+)?)$")
_MAX_FORMULAIRE = 20_000
_MAX_PIECE = 15_000
_MAX_TOTAL = 45_000

_BLOC = re.compile(r"<DOCUMENT>(.*?)</DOCUMENT>", re.S | re.I)
_CHAMP = re.compile(r"<(TYPE|FILENAME)>([^\n<]*)", re.I)
_TEXTE = re.compile(r"<TEXT>(.*?)</TEXT>", re.S | re.I)
_PREMIER_ITEM = re.compile(r"\bItem\s*\d{1,2}\.\d{2}", re.I)
_EN_TETE_XBRL = re.compile(r"<ix:header>.*?</ix:header>", re.S | re.I)


@dataclass(frozen=True)
class DocumentDepot:
    """Un document d'un dépôt, tel que le modèle le lira."""
    type: str
    nom: str
    texte: str
    taille: int          # longueur du texte extrait AVANT troncature
    tronque: bool

    def meta(self) -> dict[str, Any]:
        return {"type": self.type, "nom": self.nom, "taille": self.taille, "tronque": self.tronque,
                "lu": len(self.texte)}


def extraire_documents(soumission: str) -> list[DocumentDepot]:
    """Les documents LISIBLES d'une soumission EDGAR complète (`<accession>.txt`), dans l'ordre du
    dépôt : le formulaire d'abord, puis ses communiqués. Fonction PURE.

    La soumission complète étiquette chaque document par son type SEC (`<TYPE>EX-99.1`) : on ne
    devine rien d'après les noms de fichiers. Le budget est borné (formulaire, pièce, total) et la
    troncature est DITE au modèle et persistée — une note écrite sur un communiqué coupé doit se savoir.
    """
    docs: list[DocumentDepot] = []
    reste = _MAX_TOTAL
    for bloc in _BLOC.findall(soumission or ""):
        champs = {k.upper(): v.strip() for k, v in _CHAMP.findall(bloc)}
        type_sec = champs.get("TYPE", "").upper()
        if not _TYPES_LUS.match(type_sec):
            continue
        brut = _TEXTE.search(bloc)
        brut = brut.group(1) if brut else ""
        # L'en-tête XBRL en ligne est MASQUÉ à l'affichage (contextes, membres) : il n'est pas du texte.
        brut = _EN_TETE_XBRL.sub(" ", brut)
        if re.search(r"<(html|body|div|p|table)\b", brut, re.I):
            _titre, texte = html_to_text(brut)
        else:
            texte = brut
        texte = re.sub(r"[ \t\u00a0\u2009\u202f]+", " ", texte).strip()
        if not type_sec.startswith("EX-"):
            # La page de garde du formulaire (adresse, cases à cocher, titres cotés) est identique d'un
            # dépôt à l'autre : la substance commence au premier item.
            debut = _PREMIER_ITEM.search(texte)
            texte = texte[debut.start():] if debut else texte
        if not texte or reste <= 0:
            continue
        plafond = min(_MAX_FORMULAIRE if not type_sec.startswith("EX-") else _MAX_PIECE, reste)
        docs.append(DocumentDepot(type=type_sec, nom=champs.get("FILENAME", ""),
                                  texte=texte[:plafond], taille=len(texte),
                                  tronque=len(texte) > plafond))
        reste -= min(len(texte), plafond)
    return docs


async def telecharger_soumission(cik: int, accession: str) -> str:
    """La soumission complète d'un dépôt. Lève `NoteFlashImpossible` : une panne n'est jamais une
    note (le dépôt reste à qualifier)."""
    url = (f"https://www.sec.gov/Archives/edgar/data/{cik}/"
           f"{accession.replace('-', '')}/{accession}.txt")
    try:
        async with httpx.AsyncClient(timeout=settings.SEARCH_TIMEOUT_S, follow_redirects=True,
                                     headers={"User-Agent": _UA}) as client:
            r = await client.get(url)
    except httpx.HTTPError as e:
        raise NoteFlashImpossible(f"EDGAR injoignable pour {accession} : {e}") from e
    if r.status_code != 200:
        raise NoteFlashImpossible(f"EDGAR {r.status_code} sur la soumission {accession}")
    return r.text


# ── 2. Quels dépôts lire ────────────────────────────────────────────────────────────────────────────

def depots_a_lire(lookup: MaterialEventLookup, qualifications: dict[str, QualificationLue], *,
                  depuis: date) -> list[MaterialEvent]:
    """Les dépôts dont la forme ne décide pas la substance (`a_qualifier`) et qu'aucune note ne
    qualifie encore, publiés depuis `depuis`, du plus récent au plus ancien. Fonction PURE.

    Un dépôt lu mais jugé illisible porte une note (`{a_qualifier}`) : il n'est pas relu — le relire
    donnerait le même texte au même modèle. Une note écrite sous une AUTRE version du catalogue est à
    relire (`a_relire`) : la grille de lecture a changé, c'est la seule relecture qui se décide."""
    if lookup.status != "found":
        return []
    return [e for e in lookup.recents
            if e.event_date >= depuis and e.accession
            and (e.accession not in qualifications or qualifications[e.accession].a_relire)
            and A_QUALIFIER in types_du_depot(e)]


# ── 3. Ce que le modèle voit ────────────────────────────────────────────────────────────────────────

def types_proposables(fichier: FrameworksFile) -> list[dict[str, str]]:
    """Le catalogue tel que le modèle le voit : identifiant et libellé, SANS portée (cf. module).
    `a_qualifier` en est retiré (c'est la forme `lisible=false`), et les trois `surprise_*` sont
    remplacés par `surprise` + cause (le code dérive le type, Q2)."""
    out = [{"id": t.id, "libelle": t.libelle} for t in fichier.types_evenement
           if t.id != A_QUALIFIER and not t.id.startswith("surprise_")]
    out.append({"id": SURPRISE, "libelle": (
        "Écart des résultats ou des prévisions FINANCIERS (chiffre d'affaires, marge, résultat, "
        "guidance) à ce qu'annonçait la direction ou attendait le marché — y compris une annonce "
        "préliminaire. Un résultat clinique ou réglementaire, même meilleur ou pire qu'espéré, n'en "
        "est PAS un (c'est un type réglementaire). Donne sa `cause` : "
        "`secteur` (demande, cycle, change — commun aux concurrents), `concurrence` (propre à "
        "l'entreprise : parts perdues, prix cassés, client qui internalise), `execution` (retard, "
        "usine, produit), ou `non_dite` si le communiqué ne la donne pas")})
    return out


def contexte_note_flash(event: MaterialEvent, emetteur: IdentiteEmetteur,
                        documents: list[DocumentDepot], fichier: FrameworksFile) -> dict[str, Any]:
    """CE QUE LE MODÈLE VOIT — déterministe, lisible en texte avant toute dépense."""
    return {
        "entreprise": {"raison_sociale": emetteur.raison_sociale, "symbole": emetteur.symbole},
        "depot": {"formulaire": event.form, "date_evenement": event.event_date.isoformat(),
                  "date_depot": event.filing_date.isoformat(),
                  "items": [{"item": i, "libelle": lib} for i, lib in _libelles(event)]},
        "types_evenement": types_proposables(fichier),
        "documents": [{"type": d.type, "nom": d.nom, "tronque": d.tronque, "texte": d.texte}
                      for d in documents],
    }


def _libelles(event: MaterialEvent) -> list[tuple[str, str]]:
    from app.knowledge.material_events import ITEM_LABELS
    return [(i, ITEM_LABELS.get(i, "non répertorié")) for i in event.items]


_NOTE_FLASH_SYSTEM_PROMPT = (
    "Tu es l'ANALYSTE qui couvre une entreprise cotée pour un fonds d'investissement fondamental. "
    "Elle vient de publier un dépôt auprès de la SEC (8-K ou 6-K). Tu en écris la NOTE FLASH : de "
    "quel TYPE d'événement s'agit-il, et quel PASSAGE du dépôt le montre. Tu ne juges pas la thèse, "
    "tu ne dis pas ce qu'il faut revoir : tu dis ce qui s'est passé.\n\n"
    "L'entreprise est celle de `entreprise.raison_sociale`, jamais celle que suggère le sigle.\n\n"
    "LES TYPES. Range le dépôt dans un ou plusieurs types de `types_evenement` (identifiant repris "
    "tel quel — n'en invente aucun). Un dépôt peut en porter plusieurs (un communiqué de résultats "
    "qui annonce aussi une acquisition : `resultats` ET `perimetre`). Une acquisition ou une cession "
    "ANNONCÉE (accord signé, même non encore conclu) est un `perimetre`. Un dépôt qui ne porte "
    "aucune information de fond (présentation sans chiffre neuf, calendrier, pure formalité) est "
    "`routine`.\n\n"
    "L'ÉCART AUX ATTENTES. Si le dépôt révèle des résultats ou une prévision qui s'écartent de ce "
    "qu'annonçait la direction ou de ce qu'attendait le marché, utilise le type `surprise` et dis sa "
    "`cause`. La question à te poser : « est-ce l'entreprise, ou tout le secteur ? ». Ne choisis "
    "`secteur`, `concurrence` ou `execution` que si le dépôt DIT la cause — cite alors ce passage "
    "dans `passage_cause`. Sinon la cause est `non_dite` (sans `passage_cause`).\n\n"
    "CHAQUE TYPE SE CITE. Pour chaque élément, `passage` est une citation LITTÉRALE du texte des "
    "documents (au moins une phrase, copiée mot pour mot dans sa langue d'origine, sans traduction "
    "ni coupure au milieu). Une citation qui n'est pas dans le texte fait refuser ta note.\n\n"
    "SI TU NE PEUX PAS TRANCHER (texte vide, coupé avant l'essentiel, ou sans rapport lisible avec "
    "un type), ne devine pas : rends `lisible: false` et un `motif` d'une phrase. Le point restera "
    "ouvert, ce qui est le bon résultat quand on ne sait pas.\n\n"
    "FORMAT. Réponds UNIQUEMENT par un objet JSON :\n"
    '{"lisible": true, "elements": [{"type": "<id>", "passage": "<citation>"}, '
    '{"type": "surprise", "passage": "<citation>", "cause": "execution", '
    '"passage_cause": "<citation>"}]}\n'
    'ou {"lisible": false, "elements": [], "motif": "<pourquoi>"}'
)


def _message(contexte: dict[str, Any]) -> str:
    return ("[mode: note flash]\n\n"
            f"{json.dumps(contexte, ensure_ascii=False, indent=1)}\n\n"
            "Écris la note flash de ce dépôt : l'objet JSON demandé, rien d'autre.")


# ── 4. Le pont ──────────────────────────────────────────────────────────────────────────────────────

_GUILLEMETS = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"',
                             "–": "-", "—": "-", " ": " "})


def _normaliser(texte: str) -> str:
    """Normalisation minimale pour comparer une citation au texte : forme Unicode, guillemets et
    tirets typographiques, espaces, casse. Rien d'autre — une paraphrase ne doit pas passer."""
    t = unicodedata.normalize("NFKC", texte).translate(_GUILLEMETS)
    return re.sub(r"\s+", " ", t).strip().casefold()


@dataclass(frozen=True)
class NoteValidee:
    lisible: bool
    types: tuple[str, ...]
    elements: list[dict[str, Any]]
    motif: Optional[str]


def valider_note(sortie: NoteFlashSortie, documents: list[DocumentDepot],
                 fichier: FrameworksFile) -> NoteValidee:
    """Le PONT de la note flash (cf. module). Lève `NoteFlashRefusee` en nommant CHAQUE défaut."""
    if not sortie.lisible:
        return NoteValidee(lisible=False, types=(A_QUALIFIER,), elements=[], motif=sortie.motif)
    permis = {t["id"] for t in types_proposables(fichier)}
    corpus = _normaliser("\n".join(d.texte for d in documents))
    defauts: list[str] = []
    for n, el in enumerate(sortie.elements, 1):
        if el.type not in permis:
            defauts.append(f"élément {n} : type `{el.type}` absent du catalogue proposé")
        for champ in ("passage", "passage_cause"):
            cite = getattr(el, champ)
            if cite is not None and _normaliser(cite) not in corpus:
                defauts.append(f"élément {n} : `{champ}` introuvable dans le dépôt (« {cite[:80]}… »)")
    if defauts:
        raise NoteFlashRefusee(" ; ".join(defauts))
    types = tuple(sorted({type_derive(el) for el in sortie.elements}))
    return NoteValidee(lisible=True, types=types, motif=None,
                       elements=[el.model_dump(mode="json", exclude_none=True)
                                 for el in sortie.elements])


# ── 5. Rédiger, persister, relire ───────────────────────────────────────────────────────────────────

@dataclass
class NoteRedigee:
    ticker_id: str
    cik: int
    event: MaterialEvent
    catalogue_version: str
    note: NoteValidee
    documents: list[dict[str, Any]]
    modele: str
    runs: list[AgentRunResult] = field(default_factory=list)


async def _resoudre_agent() -> ResolvedAgent:
    """Provider + modèle de l'ingestion-agent (config en DB), prompt de la note flash — même montage
    que le traducteur : le prompt vit dans le code tant qu'aucune migration ne l'exige (#19/#39)."""
    base = await get_agent_provider("ingestion-agent", "v2")
    return ResolvedAgent(agent_name="ingestion-agent", flow_version="v2", provider=base.provider,
                         model=base.model, system_prompt=_NOTE_FLASH_SYSTEM_PROMPT)


async def rediger_note_flash(event: MaterialEvent, *, ticker_id: str, cik: int,
                             emetteur: IdentiteEmetteur, fichier: Optional[FrameworksFile] = None,
                             agent: Optional[ResolvedAgent] = None,
                             soumission: Optional[str] = None) -> NoteRedigee:
    """Lit UN dépôt et rend sa note VALIDÉE (non persistée). Ordre : (1) télécharger et extraire —
    échec ⟹ `NoteFlashImpossible` AVANT toute dépense ; (2) le modèle lit ; (3) le pont ; un refus du
    pont est renvoyé UNE fois au modèle avec ses défauts, puis `NoteFlashRefusee`."""
    fichier = fichier or load_frameworks()
    if not event.accession:
        raise NoteFlashImpossible("dépôt sans numéro d'accession : rien à télécharger")
    soumission = soumission if soumission is not None else await telecharger_soumission(
        cik, event.accession)
    documents = extraire_documents(soumission)
    if not documents:
        raise NoteFlashImpossible(f"{event.accession} : aucun document lisible (formulaire ou EX-99)")
    agent = agent or await _resoudre_agent()
    messages = [{"role": "user", "content": _message(
        contexte_note_flash(event, emetteur, documents, fichier))}]
    runs: list[AgentRunResult] = []
    for essai in (1, 2):
        run = await run_json_agent(agent, messages, NoteFlashSortie, json_object=False,
                                   temperature=0.0)
        runs.append(run)
        try:
            note = valider_note(run.parsed, documents, fichier)
            break
        except NoteFlashRefusee as e:
            if essai == 2:
                raise
            messages = messages + [
                {"role": "assistant", "content": run.raw_content},
                {"role": "user", "content": f"Ta note est refusée : {e}. Corrige : chaque passage doit "
                                            "être copié mot pour mot du texte, chaque type pris dans "
                                            "`types_evenement`. Rends l'objet JSON complet."}]
    return NoteRedigee(ticker_id=ticker_id, cik=cik, event=event,
                       catalogue_version=fichier.types_evenement_version, note=note,
                       documents=[d.meta() for d in documents],
                       modele=runs[-1].completion.model or agent.model, runs=runs)


async def persister_note(conn, redigee: NoteRedigee) -> int:
    """Écrit la note (append-only, migration 050). Une seconde note pour le même dépôt sous la même
    version du catalogue est refusée par la base (`notes_flash_une_lecture`). Les JSONB passent en
    objets Python : le pool porte le codec (convention #1 — un `json.dumps` les écrirait en chaîne)."""
    e, n = redigee.event, redigee.note
    return await conn.fetchval(
        """
        INSERT INTO notes_flash (ticker_id, cik, accession, form, items, event_date, filing_date,
                                 catalogue_version, lisible, types, elements, motif, documents, modele)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        RETURNING id
        """,
        redigee.ticker_id, redigee.cik, e.accession, e.form, list(e.items), e.event_date,
        e.filing_date, redigee.catalogue_version, n.lisible, list(n.types),
        n.elements, n.motif, redigee.documents, redigee.modele)


_EXTRAIT = 160


def relire_note(row: dict[str, Any], fichier: FrameworksFile) -> QualificationLue:
    """Une ligne `notes_flash` → ce que le point de lecture en retient. Fonction PURE.

    Un type que le référentiel du jour ne connaît plus ramène la note à `a_qualifier` : un type
    disparu ne doit jamais devenir « ne rouvre rien » (même doctrine que `TYPE_PAR_ITEM`)."""
    connus = {t.id for t in fichier.types_evenement}
    types = frozenset(row["types"])
    date_note = row["redigee_le"].date().isoformat() if row.get("redigee_le") else "?"
    version = row.get("catalogue_version")
    a_relire = version != fichier.types_evenement_version
    ancienne = f" (lue sous le catalogue {version}, à relire)" if a_relire else ""
    if not types <= connus:
        inconnus = ", ".join(sorted(types - connus))
        return QualificationLue(types=frozenset({A_QUALIFIER}), a_relire=True, resume=(
            f"note flash du {date_note} sur des types que le référentiel ne connaît plus "
            f"({inconnus}) — à relire"))
    if not row["lisible"]:
        return QualificationLue(types=types, a_relire=a_relire, resume=(
            f"note flash du {date_note} : dépôt lu, portée indéterminable — {row['motif']}{ancienne}"))
    elements = row["elements"] or []
    passage = elements[0]["passage"] if elements else ""
    extrait = passage if len(passage) <= _EXTRAIT else passage[:_EXTRAIT].rstrip() + "…"
    return QualificationLue(types=types, a_relire=a_relire,
                            resume=f"note flash du {date_note} : « {extrait} »{ancienne}")


async def qualifications_de_l_emetteur(conn, cik: Optional[int],
                                       fichier: FrameworksFile) -> dict[str, QualificationLue]:
    """DÉTENTEUR UNIQUE (#46) de « qu'ont lu les notes flash des dépôts de cet émetteur ? » — l'argument
    `qualifications` de `evenements.ancre_de_la_question`. Par dépôt : la note écrite sous la version
    du catalogue du jour si elle existe, sinon la plus récente. `cik=None` (ancre indisponible) ⟹ `{}`."""
    if cik is None:
        return {}
    rows = await conn.fetch(
        """
        SELECT DISTINCT ON (accession) accession, catalogue_version, lisible, types, elements,
               motif, redigee_le
          FROM notes_flash
         WHERE cik = $1
         ORDER BY accession, (catalogue_version = $2) DESC, redigee_le DESC, id DESC
        """, cik, fichier.types_evenement_version)
    return {r["accession"]: relire_note(dict(r), fichier) for r in rows}


# ── 6. Lire les dépôts en attente — le GESTE de l'analyste, détenteur unique ────────────────────────
#
# Arbitrage de l'utilisateur (2026-09-26, option c) : l'analyste lit un communiqué À DEUX MOMENTS —
#   · CHAQUE MATIN, pour tout titre suivi (portefeuille et liste de surveillance), dès sa publication :
#     c'est ce que fait un fonds pour une position détenue. Dépense automatique quotidienne, donc placée
#     sous le réglage qui encadre toute dépense non supervisée (`v2_auto_enabled`, FALSE par défaut) :
#     réglage coupé ⟹ AUCUN appel modèle, les dépôts non lus sont SIGNALÉS (un report, jamais un abandon —
#     même doctrine que `event_router_v2`) ;
#   · À CHAQUE PASSAGE DE LA CHAÎNE sur un titre (`executer_chaine`, `boucler_renvois`), avant de charger
#     le dossier : on ne rouvre pas un dossier devant le comité sans avoir lu ce que l'émetteur a publié.
#     Le passage est lancé par un humain, sa dépense est décidée par lui.
# Les trois appelants passent par cette fonction : la règle « quoi lire, dans quel ordre, que faire d'un
# refus » n'a qu'un détenteur (#46). Un dépôt que la lecture n'a pas pu qualifier reste `a_qualifier` —
# il rouvre tout (Q3) ; l'échec est NOMMÉ, jamais converti en « ne rouvre rien ».

FENETRE = timedelta(days=400)
LIMITE_PAR_PASSAGE = 20
# Une lecture (téléchargement OU rédaction) qui ne rend pas la main est un échec NOMMÉ du dépôt, pas un
# passage du matin qui ne finit jamais (`feedback_blocage_est_etat_muet`).
BORNE_PAR_ETAPE_S = 600
_PAUSE_EDGAR_S = 0.3   # accès équitable à EDGAR : jamais deux soumissions dans la même seconde


@dataclass
class DepotTraite:
    """Un dépôt `a_qualifier` rencontré par un passage, et ce qu'il en est advenu."""
    event: MaterialEvent
    documents: list[DocumentDepot] = field(default_factory=list)
    apercu: Optional[str] = None
    note: Optional[NoteValidee] = None
    note_id: Optional[int] = None
    corrigee: bool = False
    refus: Optional[str] = None


@dataclass
class LectureDesDepots:
    """Le compte rendu d'un passage de lecture sur UN titre. Non persisté : les notes le sont."""
    ticker_id: str
    ecrire: bool
    depuis: date
    catalogue_version: str
    cik: Optional[int] = None
    raison_sociale: Optional[str] = None
    hors_flux: Optional[str] = None      # EDGAR ne sert rien pour ce titre (non déposant SEC, panne…)
    deja_lus: int = 0
    en_attente: int = 0                  # dépôts à lire dans la fenêtre, AVANT la limite du passage
    depots: list[DepotTraite] = field(default_factory=list)
    cout_usd: float = 0.0

    @property
    def ecrits(self) -> list[DepotTraite]:
        return [d for d in self.depots if d.note_id is not None]

    @property
    def refus(self) -> list[DepotTraite]:
        return [d for d in self.depots if d.refus]

    @property
    def reportes(self) -> int:
        """Dépôts en attente laissés à un passage suivant par la limite."""
        return max(self.en_attente - len(self.depots), 0)

    def texte(self) -> str:
        L = 78
        qui = f"{self.raison_sociale} ({self.ticker_id}" if self.raison_sociale else f"({self.ticker_id}"
        lignes = [f"{'─' * L}", f"NOTES FLASH — {qui}{f', CIK {self.cik}' if self.cik else ''}) · "
                  f"catalogue d'événements {self.catalogue_version}"]
        if self.hors_flux:
            lignes += [f"  hors flux : {self.hors_flux}", f"{'─' * L}"]
            return "\n".join(lignes)
        lignes.append(f"  {self.en_attente} dépôt(s) à lire depuis le {self.depuis} · {self.deja_lus} "
                      f"déjà lu(s) · mode {'ÉCRITURE' if self.ecrire else 'lecture gratuite'}"
                      + (f" · {self.reportes} reporté(s) au passage suivant (limite)" if self.reportes else ""))
        lignes.append("─" * L)
        for d in self.depots:
            lignes.append(f"\n▸ {d.event.resume()}  [{d.event.accession}]")
            for doc in d.documents:
                lignes.append(f"    {doc.type:<8} {doc.nom:<28} {doc.taille:>6} car."
                              f"{' (TRONQUÉ)' if doc.tronque else ''}")
            if d.apercu:
                lignes.append(f"    « {d.apercu} »")
            if d.note is not None:
                if d.note.lisible:
                    for el in d.note.elements:
                        cause = f" · cause {el['cause']}" if el.get("cause") else ""
                        lignes.append(f"    → {el['type']}{cause} : « {el['passage'][:220]} »")
                        if el.get("passage_cause"):
                            lignes.append(f"        cause citée : « {el['passage_cause'][:200]} »")
                else:
                    lignes.append(f"    → ILLISIBLE : {d.note.motif}")
            if d.note_id is not None:
                lignes.append(f"    ✔ note #{d.note_id} — types retenus : {', '.join(d.note.types)}"
                              f"{' (après une correction)' if d.corrigee else ''}")
            if d.refus:
                lignes.append(f"    ✘ {d.refus} — le dépôt reste à qualifier")
        lignes.append(f"\n{'─' * L}\nINVENTAIRE — {len(self.ecrits)} note(s) écrite(s), {len(self.refus)} "
                      f"refus, coût modèle ${self.cout_usd:.4f}\n{'─' * L}")
        for d in self.ecrits:
            lignes.append(f"  notes_flash #{d.note_id}  {d.event.accession}  {', '.join(d.note.types)}")
        for d in self.refus:
            lignes.append(f"  REFUS  {d.event.accession}  {d.refus[:160]}")
        return "\n".join(lignes)


async def lire_les_depots_en_attente(
    conn, ticker_id: str, *, ecrire: bool, depuis: Optional[date] = None,
    limite: int = LIMITE_PAR_PASSAGE, apercu: bool = False,
    fichier: Optional[FrameworksFile] = None, agent: Optional[ResolvedAgent] = None,
) -> LectureDesDepots:
    """Lit (`ecrire=True`) ou recense (`ecrire=False`) les dépôts `a_qualifier` non encore lus d'un titre.

    `ecrire=False` ne dépense RIEN : sans `apercu`, il ne télécharge même pas (le passage du matin
    réglage coupé ne fait que compter) ; avec `apercu`, il télécharge et montre ce que le modèle lirait
    (la frontière gratuite de l'outil). Chaque note est persistée dans SA transaction : un refus, une
    panne ou une borne dépassée sur un dépôt n'empêche jamais la lecture des suivants."""
    fichier = fichier or load_frameworks()
    depuis = depuis or (date.today() - FENETRE)
    lecture = LectureDesDepots(ticker_id=ticker_id, ecrire=ecrire, depuis=depuis,
                               catalogue_version=fichier.types_evenement_version)
    flux = await material_anchor_for_ticker(conn, ticker_id)
    if flux.status != "found" or flux.cik is None:
        lecture.hors_flux = f"flux EDGAR {flux.status} : {flux.raison or 'aucun dépôt'}"
        return lecture
    lecture.cik = flux.cik
    deja = await qualifications_de_l_emetteur(conn, flux.cik, fichier)
    lecture.deja_lus = len(deja)
    tous = depots_a_lire(flux, deja, depuis=depuis)
    lecture.en_attente = len(tous)
    a_lire = tous[:max(limite, 0)]
    if not ecrire and not apercu:
        lecture.depots = [DepotTraite(event=e) for e in a_lire]
        return lecture
    if not a_lire:
        return lecture
    try:
        emetteur = await identite_de_l_emetteur(conn, ticker_id)
    except EdgarFeedUnavailable as ex:
        lecture.depots = [DepotTraite(event=e, refus=f"identité de l'émetteur introuvable : {ex}")
                          for e in a_lire]
        return lecture
    lecture.raison_sociale = emetteur.raison_sociale
    if ecrire:
        agent = agent or await _resoudre_agent()
    for e in a_lire:
        d = DepotTraite(event=e)
        lecture.depots.append(d)
        etape = "téléchargement"
        try:
            soum = await asyncio.wait_for(telecharger_soumission(flux.cik, e.accession),
                                          BORNE_PAR_ETAPE_S)
            await asyncio.sleep(_PAUSE_EDGAR_S)
            d.documents = extraire_documents(soum)
            if not ecrire:
                if d.documents:
                    d.apercu = d.documents[0].texte[:420].replace("\n", " ")
                continue
            etape = "lecture par le modèle"
            red = await asyncio.wait_for(
                rediger_note_flash(e, ticker_id=ticker_id, cik=flux.cik, emetteur=emetteur,
                                   fichier=fichier, agent=agent, soumission=soum),
                BORNE_PAR_ETAPE_S)
            lecture.cout_usd += sum(r.cost_usd for r in red.runs)
            d.note, d.corrigee = red.note, len(red.runs) > 1
            etape = "écriture"
            async with conn.transaction():
                d.note_id = await persister_note(conn, red)
        except (NoteFlashImpossible, NoteFlashRefusee) as ex:
            d.refus = f"{type(ex).__name__} : {ex}"
        except asyncio.TimeoutError:
            d.refus = f"{etape} non terminé(e) en {BORNE_PAR_ETAPE_S} s"
        except asyncpg.UniqueViolationError:
            d.refus = ("déjà lu sous ce catalogue par un passage concurrent — la note existante fait "
                       "foi, celle-ci n'est pas écrite")
        except Exception as ex:  # noqa: BLE001 — une panne d'un dépôt ne tait jamais les suivants
            logger.exception("note flash %s %s : panne à l'étape %s", ticker_id, e.accession, etape)
            d.refus = f"panne à l'étape {etape} ({type(ex).__name__}) : {ex}"
    return lecture


# ── 7. Le passage du matin ──────────────────────────────────────────────────────────────────────────

async def titres_suivis(conn) -> list[str]:
    """Les titres dont le fonds lit les communiqués : ceux détenus et ceux sous surveillance. Un titre
    hors EDGAR (coté à Paris, non coté) y figure : `lire_les_depots_en_attente` le dit « hors flux »."""
    rows = await conn.fetch(
        "SELECT id FROM tickers WHERE status IN ('portfolio', 'watchlist') ORDER BY id")
    return [r["id"] for r in rows]


def message_du_matin(lectures: list[LectureDesDepots], *, auto: bool, today: date) -> Optional[str]:
    """Ce que le gérant reçoit le matin. Fonction PURE. `None` = rien à dire (aucun bruit quotidien).

    Réglage ouvert : les notes écrites et les refus (un refus laisse le dépôt rouvrir tout le dossier).
    Réglage coupé : seulement les dépôts NON LUS publiés depuis la veille — l'arriéré, lui, est connu
    et ne se re-signale pas chaque matin."""
    if auto:
        ecrits = [(l, d) for l in lectures for d in l.ecrits]
        refus = [(l, d) for l in lectures for d in l.refus]
        if not ecrits and not refus:
            return None
        lignes = [f"📰 Notes flash du {today:%d/%m} — {len(ecrits)} communiqué(s) lu(s)"
                  + (f", {len(refus)} non qualifié(s)" if refus else "")]
        for l, d in ecrits:
            passage = d.note.elements[0]["passage"][:160] if d.note.elements else (d.note.motif or "")
            lignes.append(f"• {l.ticker_id} {d.event.resume()} → {', '.join(d.note.types)} : « {passage} »")
        for l, d in refus:
            lignes.append(f"• {l.ticker_id} {d.event.resume()} — NON QUALIFIÉ ({d.refus[:140]}) : "
                          "il rouvre toutes les questions du dossier jusqu'à sa lecture")
        return "\n".join(lignes)
    hier = today - timedelta(days=1)
    neufs = [(l, d) for l in lectures for d in l.depots
             if d.note_id is None and d.event.filing_date and d.event.filing_date >= hier]
    if not neufs:
        return None
    lignes = [f"🔔 [En attente] {len(neufs)} communiqué(s) publié(s) depuis hier NON LU(S) — la lecture "
              "automatique est coupée (`v2_auto_enabled=FALSE`). Tant qu'ils ne sont pas lus, ils "
              "rouvrent toutes les questions du dossier :"]
    for l, d in neufs:
        lignes.append(f"• {l.ticker_id} {d.event.resume()} — `bash tools/rediger_notes_flash.sh "
                      f"{l.ticker_id} --ecrire`")
    return "\n".join(lignes)


async def _notifier_slack(message: str) -> None:
    """Une notification qui échoue ne fait jamais échouer le passage (les notes sont déjà écrites)."""
    try:
        from app.notifications.slack_webhook import SlackWebhook
        await SlackWebhook().send(message)
    except Exception as e:  # noqa: BLE001
        logger.warning("notes flash du matin — notification Slack non envoyée : %s", e)


async def lecture_du_matin(today: Optional[date] = None, *, notifier=None) -> list[LectureDesDepots]:
    """Le passage quotidien (job `notes_flash_matin`) : pour chaque titre suivi, lire les dépôts à
    qualifier — SI ET SEULEMENT SI `v2_auto_enabled` ; sinon les recenser, sans rien dépenser. Un titre
    en panne est nommé dans son compte rendu, il n'empêche pas les suivants."""
    today = today or date.today()
    notifier = notifier or _notifier_slack
    async with get_db_session() as conn:
        auto = bool(await conn.fetchval("SELECT v2_auto_enabled FROM portfolio_settings LIMIT 1"))
        titres = await titres_suivis(conn)
    fichier = load_frameworks()
    lectures: list[LectureDesDepots] = []
    for t in titres:
        try:
            async with get_db_session() as conn:
                lecture = await lire_les_depots_en_attente(
                    conn, t, ecrire=auto, depuis=today - FENETRE, fichier=fichier)
        except Exception as ex:  # noqa: BLE001 — un titre en panne n'arrête pas les suivants
            logger.exception("notes flash du matin — %s en panne", t)
            lecture = LectureDesDepots(ticker_id=t, ecrire=auto, depuis=today - FENETRE,
                                       catalogue_version=fichier.types_evenement_version,
                                       hors_flux=f"panne ({type(ex).__name__}) : {ex}")
        lectures.append(lecture)
    logger.info("notes flash du matin (%s) — %s", "lecture" if auto else "recensement seul",
                {l.ticker_id: (len(l.ecrits), len(l.refus), l.en_attente) for l in lectures
                 if not l.hors_flux})
    message = message_du_matin(lectures, auto=auto, today=today)
    if message:
        await notifier(message)
    return lectures
