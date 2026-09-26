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

import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

import httpx

from app.agents.providers import ResolvedAgent, get_agent_provider
from app.agents.v2.frameworks import load_frameworks
from app.agents.v2.runner import AgentRunResult, run_json_agent
from app.config import settings
from app.contracts.framework_definition_schema import FrameworksFile
from app.contracts.note_flash_schema import SURPRISE, NoteFlashSortie, type_derive
from app.knowledge.edgar_facts import _UA
from app.knowledge.edgar_feed import IdentiteEmetteur
from app.knowledge.evenements import A_QUALIFIER, QualificationLue, types_du_depot
from app.knowledge.material_events import MaterialEvent, MaterialEventLookup
from app.knowledge.websearch import html_to_text

logger = logging.getLogger(__name__)

__all__ = [
    "DocumentDepot", "NoteRedigee", "NoteFlashImpossible", "NoteFlashRefusee",
    "extraire_documents", "types_proposables", "contexte_note_flash", "valider_note",
    "depots_a_lire", "telecharger_soumission", "rediger_note_flash", "persister_note",
    "qualifications_de_l_emetteur",
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
