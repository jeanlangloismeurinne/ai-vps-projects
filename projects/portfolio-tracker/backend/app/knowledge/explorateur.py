"""L'EXPLORATEUR DU DOSSIER — lot B4f (roadmap V3 `16-lot-B4f-explorateur.md`), brique COMMUNE aux
agents, branchée d'abord sur l'architecte (`app/modele_entreprise/architecte.py`, interrupteur
`acces_au_dossier`).

CE QUE FERAIT UN VRAI FONDS (spec, en-tête) : l'analyste qui bâtit le classeur a le dossier sous la
main — la table des matières, les notes de ses collègues, et derrière chaque note les pièces qui la
fondent. Il ouvre l'original quand une note ne suffit pas ; il voit qu'une note a été écrite avant un
événement et la lit comme l'état d'avant ; il consulte l'ancien seulement comme historique.

DEUX MOITIÉS (même frontière que `matiere.py`) :
  · `charger_dossier_explorable(conn, ticker_id)` — la SEULE moitié qui lit (base). Assemble TOUTES
    les notes (réponses des questions sources, tenante ou non) et TOUTES les pièces (en vigueur ET
    historiques — un numéro remplacé doit rester ouvrable, marqué).
  · Le reste de ce module est PUR : rendu de la table des matières, d'une note, d'une pièce, état
    d'une pièce au jour de la lecture (#79 : deux dates nommées, jamais recalculées ailleurs).

INTERDITS (spec §1) : aucun état temporel STOCKÉ (calculé à la lecture, #53/#77) ; aucune fusion des
signaux vectoriel et texte (#22 — `rechercher` délègue à `query_knowledge`, détenteur unique) ; aucun
ticker ni libellé dans le code ; la portée de lecture est FERMÉE dans l'exécuteur (`ticker_id` n'est
jamais un argument du modèle, comme `make_query_knowledge_executor`, #46).

LES CITATIONS (spec §3) : `pieces_citables` d'un passage = celles de la matière (B4d §2) ∪ les
numéros OUVERTS ou rendus par un outil pendant le passage — `pieces_citables_effectif` ci-dessous,
détenteur unique de cette union. Un seul détenteur en aval contrôle contre elle : [S6] de
`app/modele_entreprise/structure.py`, qui reçoit une `Matiere` dont `pieces_citables` a déjà été
augmentée par cette union (`architecte.py` appelle `pieces_citables_effectif` puis
`dataclasses.replace` — ni second contrôle, ni second détenteur).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as _date
from typing import Any, Awaitable, Callable, Optional

__all__ = [
    "PieceDossier", "NoteDossier", "DossierExplorable", "JournalExploration",
    "EXPLORATEUR_TOOLS",
    "etat_piece", "rendre_table_des_matieres", "rendre_note", "ouvrir_piece",
    "rendre_resultats_recherche", "pieces_citables_effectif",
    "make_rechercher_executor", "make_explorateur_tool_executors", "charger_dossier_explorable",
]

ToolExecutor = Callable[[dict[str, Any]], Awaitable[Any]]

# Budget de rendu — spec §2.
_LIGNES_PAR_PAGE = 200
_CARACTERES_PIECE = 6000
_RESULTATS_RECHERCHE = 10


def _titre_court(titre: Optional[str]) -> str:
    if not titre:
        return "(sans titre)"
    return titre if len(titre) <= 120 else titre[:120] + "…"


@dataclass(frozen=True)
class PieceDossier:
    """Une pièce du dossier — en vigueur ou historique (remplacée). `contenu` est le texte intégral,
    jamais tronqué ici : la troncature/sélection est le rôle de `ouvrir_piece` (#27)."""
    numero: int
    titre: Optional[str]
    contenu: str
    type_source: Optional[str] = None
    date_du_fait: Optional[_date] = None
    source_date: Optional[_date] = None
    superseded_by: Optional[int] = None


@dataclass(frozen=True)
class NoteDossier:
    """Une note d'analyste — la réponse TENANTE (ou la plus récente) d'une question source,
    #79/#53 : `actualite`/`motif_actualite` sont LUS (déjà calculés par `parcours.py`/`actualite.py`),
    jamais recalculés une seconde fois ici."""
    question_id: str
    framework_id: str
    statut: Optional[str] = None
    verdict: Optional[str] = None
    actualite: Optional[str] = None          # None = aucune réponse instruite
    motif_actualite: Optional[str] = None
    verbatim: Optional[str] = None
    pieces: frozenset[int] = field(default_factory=frozenset)
    fait_posterieur_effet: Optional[str] = None


@dataclass(frozen=True)
class DossierExplorable:
    """Tout ce que l'explorateur peut ouvrir pour UN titre — fermé sur `ticker_id` à la construction
    (`charger_dossier_explorable`) : aucun exécuteur ne reçoit le ticker en argument du modèle."""
    ticker_id: str
    notes: tuple[NoteDossier, ...]
    pieces: dict[int, PieceDossier]   # TOUTES les pièces, numéro → pièce (en vigueur + historiques)


@dataclass
class JournalExploration:
    """Ce que les outils ont RÉELLEMENT ouvert/rendu pendant le passage — même patron que
    `app/agents/v2/tools.RetrievalLog` : un journal mutable, fermé dans les exécuteurs, qui nourrit
    `pieces_citables_effectif` (spec §3) et le décompte des appels (budget, spec §2)."""
    pieces_ouvertes: dict[int, str] = field(default_factory=dict)   # numéro → texte RENDU
    appels: dict[str, int] = field(default_factory=dict)

    def record_call(self, name: str) -> None:
        self.appels[name] = self.appels.get(name, 0) + 1

    def record_piece(self, numero: int, texte: str) -> None:
        if texte:
            self.pieces_ouvertes[numero] = texte


# ── Les 4 outils (spec §2) ───────────────────────────────────────────────────────────────────────

EXPLORATEUR_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "table_des_matieres",
            "description": (
                "La table des matières du dossier : les notes d'analyste (question, statut, "
                "actualité) et les pièces EN VIGUEUR (numéro, titre, dates, type de source). "
                "Paginée, 200 lignes par appel."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "etage": {"type": "string",
                              "description": "Facultatif : `notes` ou `pieces` — les deux par défaut."},
                    "sujet": {"type": "string",
                              "description": "Facultatif : mots du titre/de la question à filtrer."},
                    "page": {"type": "integer", "default": 1},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ouvrir_note",
            "description": (
                "La réponse EN VIGUEUR d'une question source (verbatim, encadré, actualité, faits "
                "postérieurs) et la liste de ses pièces avec titre et état."
            ),
            "parameters": {
                "type": "object",
                "properties": {"question_id": {"type": "string"}},
                "required": ["question_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ouvrir_piece",
            "description": (
                "Le contenu d'une pièce (et son état). Au-delà de 6000 caractères, rend les "
                "passages qui répondent à `chercher`. Une pièce REMPLACÉE s'ouvre, marquée "
                "« historique », avec sa remplaçante."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "numero": {"type": "integer", "description": "Numéro de la pièce (`#N`)."},
                    "chercher": {
                        "type": "string",
                        "description": ("Facultatif : ce que tu cherches DANS cette pièce, dans ses "
                                        "mots (intitulé de section, titre de tableau)."),
                    },
                },
                "required": ["numero"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rechercher",
            "description": (
                "Les pièces EN VIGUEUR les plus proches d'un sujet (vectoriel, sinon texte, mode "
                "tracé) — titre + 300 caractères + état. 10 résultats au plus."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sujet": {"type": "string"},
                    "limite": {"type": "integer", "default": _RESULTATS_RECHERCHE},
                },
                "required": ["sujet"],
            },
        },
    },
]


# ── État d'une pièce au jour de la lecture (#79) ────────────────────────────────────────────────

def etat_piece(numero: int, dossier: DossierExplorable) -> str:
    """`en vigueur` ; `remplacé par #id (date)` ; `numéro inconnu`. PURE — aucun second calcul de
    l'actualité (réservée aux NOTES, #53) : une pièce n'a que ces deux états."""
    p = dossier.pieces.get(numero)
    if p is None:
        return "numéro inconnu"
    if p.superseded_by is None:
        return "en vigueur"
    remplacante = dossier.pieces.get(p.superseded_by)
    dt = (remplacante.date_du_fait or remplacante.source_date) if remplacante is not None else None
    return f"remplacé par #{p.superseded_by}" + (f" ({dt.isoformat()})" if dt else "")


# ── `table_des_matieres` ────────────────────────────────────────────────────────────────────────

def rendre_table_des_matieres(
    dossier: DossierExplorable, *, etage: Optional[str] = None, sujet: Optional[str] = None,
    page: int = 1,
) -> dict[str, Any]:
    etage = (etage or "").strip().lower() or "toutes"
    if etage not in ("notes", "pieces", "toutes"):
        return {"erreur": f"étage inconnu : `{etage}` — attendu `notes`, `pieces`, ou rien (les deux)"}
    sujet_norm = (sujet or "").strip().lower() or None

    lignes: list[dict[str, Any]] = []
    if etage in ("notes", "toutes"):
        for n in dossier.notes:
            cible = f"{n.question_id} {n.framework_id} {n.verbatim or ''}".lower()
            if sujet_norm and sujet_norm not in cible:
                continue
            lignes.append({
                "type": "note", "question_id": n.question_id, "framework_id": n.framework_id,
                "statut": n.statut, "actualite": n.actualite,
            })
    if etage in ("pieces", "toutes"):
        # EN VIGUEUR seulement (spec §2) — une pièce remplacée s'ouvre par `ouvrir_piece`, elle ne
        # figure pas à la table des matières (elle n'y serait qu'un doublon de sa remplaçante).
        for p in sorted(dossier.pieces.values(), key=lambda p: p.numero):
            if p.superseded_by is not None:
                continue
            if sujet_norm and sujet_norm not in (p.titre or "").lower():
                continue
            lignes.append({
                "type": "piece", "numero": p.numero, "titre": _titre_court(p.titre),
                "date_du_fait": p.date_du_fait.isoformat() if p.date_du_fait else None,
                "type_source": p.type_source,
            })

    total = len(lignes)
    page = max(page, 1)
    debut = (page - 1) * _LIGNES_PAR_PAGE
    page_lignes = lignes[debut : debut + _LIGNES_PAR_PAGE]
    pages_totales = max(1, -(-total // _LIGNES_PAR_PAGE)) if total else 1
    return {
        "etage": etage, "lignes": page_lignes, "total": total, "page": page,
        "pages_totales": pages_totales,
    }


# ── `ouvrir_note` ───────────────────────────────────────────────────────────────────────────────

def rendre_note(dossier: DossierExplorable, question_id: str) -> dict[str, Any]:
    n = next((n for n in dossier.notes if n.question_id == question_id), None)
    if n is None:
        return {"erreur": f"question `{question_id}` absente du dossier"}
    return {
        "question_id": n.question_id, "framework_id": n.framework_id, "statut": n.statut,
        "verdict": n.verdict, "actualite": n.actualite, "motif_actualite": n.motif_actualite,
        "verbatim": n.verbatim, "fait_posterieur_effet": n.fait_posterieur_effet,
        "pieces": [
            {"numero": pid, "titre": _titre_court((dossier.pieces.get(pid) or PieceDossier(pid, None, "")).titre),
             "etat": etat_piece(pid, dossier)}
            for pid in sorted(n.pieces)
        ],
    }


# ── `ouvrir_piece` ──────────────────────────────────────────────────────────────────────────────

async def ouvrir_piece(
    dossier: DossierExplorable, numero: int, *, chercher: Optional[str] = None,
    select_relevant: Optional[Callable[..., Awaitable[dict]]] = None,
) -> tuple[dict[str, Any], Optional[str]]:
    """Rend `(objet_pour_le_modele, texte_rendu)` — `texte_rendu` est ce que le journal doit
    enregistrer (`JournalExploration.record_piece`), `None` si la pièce est inconnue.

    `select_relevant` est injectable (tests) ; par défaut `document_search.select_relevant`
    (détenteur unique de la sélection par pertinence, #134) — jamais une seconde implémentation."""
    p = dossier.pieces.get(numero)
    if p is None:
        return {"erreur": f"pièce #{numero} inconnue du dossier"}, None

    etat = etat_piece(numero, dossier)
    historique = p.superseded_by is not None
    contenu = p.contenu or ""
    if len(contenu) <= _CARACTERES_PIECE:
        texte, mode = contenu, "whole"
    else:
        if select_relevant is None:
            from app.knowledge.document_search import select_relevant as _sr
            select_relevant = _sr
        res = await select_relevant(contenu, None, max_chars=_CARACTERES_PIECE, focus=chercher)
        texte, mode = res["text"], res["mode"]

    out: dict[str, Any] = {
        "numero": numero, "titre": p.titre, "etat": etat, "historique": historique,
        "mode": mode, "texte": texte,
    }
    if historique:
        out["remplacee_par"] = p.superseded_by
    return out, texte


# ── `rechercher` ────────────────────────────────────────────────────────────────────────────────

def rendre_resultats_recherche(rows: list[dict[str, Any]], *, limite: int = _RESULTATS_RECHERCHE) -> dict[str, Any]:
    """Mappe les lignes de `knowledge.service.query_knowledge` (détenteur unique du vectoriel/texte,
    #22/#46 — jamais une seconde recherche ici) vers `titre + 300 caractères + état`. `query_knowledge`
    ne rend que les entrées COURANTES (`ENTRIES_COURANTES`) : l'état est donc toujours `en vigueur`."""
    out = []
    for r in rows[: max(1, min(limite, _RESULTATS_RECHERCHE))]:
        out.append({
            "numero": r.get("id") or r.get("entry_id"),
            "titre": _titre_court(r.get("title")),
            "extrait": (r.get("content") or "")[:300],
            "etat": "en vigueur",
        })
    return {"resultats": out}


def make_rechercher_executor(
    journal: JournalExploration, *, conn_factory: Callable[[], Any], ticker_id: Optional[str],
) -> ToolExecutor:
    """DÉTENTEUR UNIQUE de l'exécuteur `rechercher` (#46) — utilisé par `make_explorateur_tool_executors`
    (mode `explorateur`, appelé par le MODÈLE) et directement par `architecte._passage_deux_temps`
    (mode `deux_temps`, appelé par le CODE, sans modèle, pour chaque `besoin_d_information`)."""

    async def _rechercher(args: dict[str, Any]) -> Any:
        journal.record_call("rechercher")
        sujet = (args.get("sujet") or "").strip()
        if not sujet:
            return {"erreur": "rechercher : `sujet` requis"}
        try:
            limite = max(1, min(int(args.get("limite") or _RESULTATS_RECHERCHE), _RESULTATS_RECHERCHE))
        except (TypeError, ValueError):
            limite = _RESULTATS_RECHERCHE
        from app.knowledge.service import query_knowledge
        async with conn_factory() as conn:
            rows = await query_knowledge(conn, ticker_id=ticker_id, query=sujet, limit=limite)
        resultat = rendre_resultats_recherche(rows, limite=limite)
        # Le journal garde le texte COMPLET de la ligne (pas l'extrait de 300 caractères rendu au
        # modèle) : [S14]/[S15] de `structure.py` y cherchent un nom de programme qui peut dépasser
        # 300 caractères — tronquer ici ferait manquer des noms pourtant bien ouverts.
        par_id = {r.get("id"): (r.get("content") or "") for r in rows}
        for item in resultat["resultats"]:
            numero = item.get("numero")
            if numero is not None:
                journal.record_piece(numero, par_id.get(numero) or item.get("extrait") or "")
        return resultat

    return _rechercher


# ── Les exécuteurs (fermés sur le dossier/le journal/le ticker — jamais un argument du modèle) ──

def make_explorateur_tool_executors(
    dossier: DossierExplorable, journal: JournalExploration, *,
    conn_factory: Optional[Callable[[], Any]] = None, ticker_id: Optional[str] = None,
) -> dict[str, ToolExecutor]:
    """Table `nom d'outil → exécuteur`, même patron que `app.agents.v2.tools.build_tool_executors`.
    `conn_factory` (un context manager async, ex. `get_db_session`) n'est requis que pour
    `rechercher` — les trois autres outils opèrent sur le `dossier` déjà chargé en mémoire."""

    async def _table(args: dict[str, Any]) -> Any:
        journal.record_call("table_des_matieres")
        try:
            page = int(args.get("page") or 1)
        except (TypeError, ValueError):
            page = 1
        return rendre_table_des_matieres(dossier, etage=args.get("etage"), sujet=args.get("sujet"), page=page)

    async def _note(args: dict[str, Any]) -> Any:
        journal.record_call("ouvrir_note")
        qid = (args.get("question_id") or "").strip()
        if not qid:
            return {"erreur": "ouvrir_note : `question_id` requis"}
        return rendre_note(dossier, qid)

    async def _piece(args: dict[str, Any]) -> Any:
        journal.record_call("ouvrir_piece")
        try:
            numero = int(args.get("numero"))
        except (TypeError, ValueError):
            return {"erreur": "ouvrir_piece : `numero` requis (entier)"}
        chercher = (args.get("chercher") or "").strip()[:200] or None
        out, texte = await ouvrir_piece(dossier, numero, chercher=chercher)
        if texte is not None:
            journal.record_piece(numero, texte)
        return out

    if conn_factory is not None:
        _rechercher: ToolExecutor = make_rechercher_executor(
            journal, conn_factory=conn_factory, ticker_id=ticker_id)
    else:
        async def _rechercher(args: dict[str, Any]) -> Any:  # type: ignore[no-redef]
            journal.record_call("rechercher")
            return {"erreur": "rechercher : aucune base configurée pour ce passage"}

    return {
        "table_des_matieres": _table,
        "ouvrir_note": _note,
        "ouvrir_piece": _piece,
        "rechercher": _rechercher,
    }


# ── Les citations (spec §3) ─────────────────────────────────────────────────────────────────────

def pieces_citables_effectif(pieces_citables_matiere: frozenset[int], journal: JournalExploration) -> frozenset[int]:
    """`pieces_citables` de la matière (B4d §2) ∪ les numéros OUVERTS/rendus pendant le passage —
    DÉTENTEUR UNIQUE de cette union (#46). `[S6]` de `structure.py` n'en contrôle jamais une seconde :
    l'appelant (`architecte.py`) augmente `Matiere.pieces_citables` avec le résultat de cette fonction
    AVANT d'appeler `juger_architecture`."""
    return pieces_citables_matiere | frozenset(journal.pieces_ouvertes)


# ── La moitié qui lit (IO, non exercée par les checks — fictifs, sans base) ─────────────────────

async def charger_dossier_explorable(conn: Any, ticker_id: str) -> DossierExplorable:
    """La SEULE moitié qui lit. Assemble TOUTES les notes (une par question source, tenante ou la
    plus récente faute de mieux — même règle que `matiere._reponse_retenue`) et TOUTES les pièces du
    ticker (en vigueur ET historiques : une pièce remplacée doit rester ouvrable, marquée)."""
    from app.agents.v2.parcours import charger_etat_dossier, reponse_tient

    etat = await charger_etat_dossier(conn, ticker_id)

    rows = await conn.fetch(
        "SELECT id, title, content, entry_type, date_du_fait, source_date, superseded_by "
        "FROM knowledge_entries WHERE ticker_id = $1", ticker_id)
    pieces: dict[int, PieceDossier] = {
        r["id"]: PieceDossier(
            numero=r["id"], titre=r["title"], contenu=r["content"] or "",
            type_source=r["entry_type"], date_du_fait=r["date_du_fait"], source_date=r["source_date"],
            superseded_by=r["superseded_by"])
        for r in rows
    }

    par_question: dict[tuple[str, str], list] = {}
    for r in etat.reponses:
        par_question.setdefault((r.servie.framework_id, r.servie.question_id), []).append(r)

    notes: list[NoteDossier] = []
    for (fid, qid), reps in par_question.items():
        tenante = next((r for r in reps if reponse_tient(r)), None)
        if tenante is None:
            avec_date = [r for r in reps if r.cree_le is not None]
            tenante = max(avec_date, key=lambda r: r.cree_le) if avec_date else (reps[0] if reps else None)
        if tenante is None:
            continue
        servie = tenante.servie
        fondation = servie.fondation
        reponse = servie.reponse
        note_pieces: set[int] = set()
        effet: Optional[str] = None
        if fondation is not None:
            note_pieces |= set(fondation.cited_entry_ids)
        if reponse is not None:
            for fp in reponse.faits_posterieurs:
                note_pieces |= set(fp.cited_entry_ids)
            effets = [fp.effet for fp in reponse.faits_posterieurs]
            effet = " ; ".join(effets) if effets else None
        notes.append(NoteDossier(
            question_id=qid, framework_id=fid, statut=servie.statut,
            verdict=tenante.verdict, actualite=fondation.actualite if fondation else None,
            motif_actualite=fondation.motif_actualite if fondation else None,
            verbatim=reponse.verbatim if reponse is not None else None,
            pieces=frozenset(note_pieces), fait_posterieur_effet=effet,
        ))

    return DossierExplorable(ticker_id=ticker_id, notes=tuple(notes), pieces=pieces)
