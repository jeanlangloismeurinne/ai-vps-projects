"""Maillon 1 du découpage — RELEVER ce que le dossier nomme pour l'avenir, une fiche par élément × marché.

Plan « découpage » B4g, arbitrage de l'utilisateur du 2026-10-24 : l'inventaire est une TÂCHE SÉPARÉE
de `me_7` (la réponse en texte garde son rôle dans la note), lue sur les MÊMES pièces (le dossier
`modele_economique` de l'analyste, `app/agents/v2/dossier.py`), sur DeepSeek-V4.1-Flash. Elle relève
des FAITS ; elle ne CLASSE pas (maillon 2) et ne CONSTRUIT pas (maillon 3, du code).

Le modèle propose, le CODE vérifie chaque fiche contre les pièces (`verifier_inventaire`, pur) : pièces
du dossier, nom, marché visé et extrait recopiés LITTÉRALEMENT dans une pièce citée ; doublons
(nom × marché) fusionnés. Une fiche qui ne tient pas est ÉCARTÉE avec son motif, jamais corrigée.

Une lecture ou trois ? L'utilisateur estime qu'une suffit : à MESURER (3 passages à dossier identique,
`tools/inventaire.sh`) avant d'écrire le vote — `feedback_decision_figee_a_remesurer`.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from app.agents.providers import ResolvedAgent, get_agent_provider
from app.agents.v2.runner import AgentRunResult, run_json_agent
from app.contracts.inventaire_schema import FicheElement, InventaireSortie
from app.modele_entreprise.structure import _forme_comparable

__all__ = ["MODELE_INVENTAIRE", "FRAMEWORK_DU_DOSSIER", "FicheEcartee", "Inventaire", "rendre_pieces",
           "verifier_inventaire", "relever_inventaire"]

# Arbitrage de l'utilisateur du 2026-10-24 : « le dernier modèle V4.1 Flash » — version FIGÉE (`-1017`),
# jamais l'alias mouvant, pour qu'une mesure se rejoue sur le même modèle.
MODELE_INVENTAIRE = "deepseek-ai/DeepSeek-V4.1-Flash-1017"
# Les mêmes pièces que `me_7` : le dossier du framework qui porte la question.
FRAMEWORK_DU_DOSSIER = "modele_economique"

_EXEMPLE = {
    "fiches": [
        {"nom": "Produit Z", "marche_vise": "maladie Y en première ligne",
         "extrait": "Produit Z est en phase 3 dans la maladie Y en première ligne, résultats attendus au T2 2027.",
         "stade": "phase 3", "dernier_jalon": {"libelle": "début de la phase 3", "date": "2025-12"},
         "prochain_jalon": {"libelle": "résultats de phase 3", "date": "T2 2027"},
         "origine": "interne", "pieces": [101]},
        {"nom": "Produit Z", "marche_vise": "maladie Y après échec d'un premier traitement",
         "extrait": "Produit Z est autorisé depuis mars 2026 dans la maladie Y après échec d'un premier traitement.",
         "stade": "autorisé", "dernier_jalon": {"libelle": "autorisation", "date": "2026-03"},
         "prochain_jalon": None, "origine": "interne", "pieces": [101]},
        {"nom": "acquisition de la société W", "marche_vise": None,
         "extrait": "L'accord d'acquisition de la société W a été signé ; la clôture est attendue au S1 2027.",
         "stade": "accord signé, non conclu", "dernier_jalon": {"libelle": "accord signé", "date": "2026-09-02"},
         "prochain_jalon": {"libelle": "clôture", "date": "S1 2027"}, "origine": "acquisition", "pieces": [102]},
    ],
    "non_nommes": {"nombre": 3, "extrait": "Trois autres programmes de recherche amont ne sont pas encore divulgués.",
                   "pieces": [103]},
}

_INVENTAIRE_SYSTEM_PROMPT = (
    "Tu es analyste dans un fonds d'investissement. On te remet les pièces du dossier d'UNE entreprise. "
    "Ta tâche : RELEVER, sans rien juger, tout ce que l'entreprise prépare pour ses années futures — "
    "produits et générations annoncés ou récemment lancés, programmes en développement (y compris les "
    "plus précoces), nouvelles indications d'un produit existant, nouvelles catégories de produits, "
    "initiatives vers un type de clients ou une zone, capacités en construction, acquisitions, licences "
    "et partenariats en cours.\n\n"
    "UNITÉ — une fiche par ÉLÉMENT × MARCHÉ :\n"
    "  · un élément est ce que l'entreprise vendra ou développe et présente comme une offre ou un "
    "programme DISTINCT (une molécule, une famille de produits ou sa génération, une plateforme "
    "technique, une acquisition, un accord, une initiative) ; ne sont PAS des éléments : un ESSAI "
    "CLINIQUE (il sert une molécule dans une indication — la fiche est celle de la molécule dans cette "
    "indication), les configurations ou déclinaisons d'un même produit (tailles, versions d'un même "
    "système : une seule fiche, au nom de la famille), un PARTENAIRE (une collaboration se dit dans la "
    "fiche de la molécule ou du produit concerné, `origine` partenariat ou licence), un bail ou un "
    "bâtiment administratif, un segment déjà publié, une tendance générale de la demande ;\n"
    "  · un même élément visant PLUSIEURS marchés (une molécule dans plusieurs indications, un produit "
    "vers plusieurs types d'acheteurs) donne une fiche PAR marché, sous le MÊME `nom` ; y compris le "
    "marché où il est DÉJÀ vendu, s'il est aussi développé ailleurs ;\n"
    "  · le marché est ce que le dossier écrit : en santé la maladie et la ligne de traitement, ailleurs "
    "les acheteurs, le type de clients ou la zone visés.\n\n"
    "RECOPIE, ne reformule pas, NE TRADUIS PAS : `nom` (le nom seul — « Hugging Face », pas "
    "« acquisition de Hugging Face »), `marche_vise` (`null` si le dossier n'en nomme aucun) et "
    "`extrait` (un passage CONTINU qui parle de l'élément, au moins une phrase) sont recopiés MOT POUR "
    "MOT d'une pièce que tu cites dans `pieces`, DANS LA LANGUE DE CETTE PIÈCE (une pièce en anglais se "
    "recopie en anglais) — sans les marques de mise en forme (gras, guillemets) ; le système le vérifie "
    "et écarte une fiche qui ne s'y trouve pas. `marche_vise` est un passage de la pièce, jamais une "
    "description que tu composes. `stade`, `dernier_jalon`, `prochain_jalon` (libellé et date telle que "
    "le dossier l'écrit, `null` si non datée) et `origine` (interne, acquisition, licence, partenariat, "
    "non_dit) disent ce que le dossier en dit, rien de plus. Ce que le dossier COMPTE sans le nommer "
    "individuellement va dans `non_nommes` (le nombre, l'extrait, la pièce), jamais sous un nom inventé.\n\n"
    "N'oublie rien : parcours TOUTES les pièces, un élément cité dans une seule pièce compte autant qu'un "
    "élément cité partout. Ne classe pas (ni « déjà vendu », ni « même marché ») : c'est l'étape suivante.\n\n"
    "Sortie : UNIQUEMENT l'objet JSON ci-après, commençant par `{` et finissant par `}`, sans texte "
    "autour. Exemple de FORME — une société FICTIVE, numéros de pièces fictifs :\n"
    f"{json.dumps(_EXEMPLE, ensure_ascii=False, indent=2)}"
)


def rendre_pieces(entries: dict[int, dict[str, Any]]) -> str:
    """Les pièces telles que le modèle les lit — numéro, titre, date du document, contenu. Pur."""
    blocs = []
    for i in sorted(entries):
        e = entries[i]
        date = e.get("date_du_document") or e.get("source_date")
        blocs.append(f"=== Pièce #{i} — {e.get('title') or '(sans titre)'}"
                     f"{f' ({date})' if date else ''}\n{e.get('content') or ''}")
    return "\n\n".join(blocs)


@dataclass(frozen=True)
class FicheEcartee:
    fiche: FicheElement
    motif: str


@dataclass
class Inventaire:
    """Les fiches ADMISES (vérifiées, dédoublonnées), les fiches ÉCARTÉES et leur motif, les SIGNAUX (une
    fiche admise dont un champ a été retiré, et pourquoi), le relevé non nommé."""
    ticker_id: str
    fiches: list[FicheElement] = field(default_factory=list)
    ecartees: list[FicheEcartee] = field(default_factory=list)
    signaux: list[str] = field(default_factory=list)
    non_nommes: Optional[Any] = None
    run: Optional[AgentRunResult] = None


# Les marques de mise en forme des pièces (gras `**…**`, code `` `…` ``, guillemets « ») ne font pas partie
# du texte qu'on recopie : mesuré le 2026-10-24 (`inventaire-lectures/` 1ʳᵉ mesure), « le processeur
# **Vera CPU** — premier CPU » faisait écarter l'extrait recopié « Vera CPU — premier CPU ».
_MISE_EN_FORME = re.compile(r"\*\*|`|«|»|\u201c|\u201d|\"")


def _forme_lisible(texte: str) -> str:
    """`_forme_comparable` (détenteur unique : casse, espaces, apostrophes) après retrait de la mise en forme."""
    return _forme_comparable(_MISE_EN_FORME.sub(" ", texte))


def _texte_piece(e: dict[str, Any]) -> str:
    return _forme_lisible(f"{e.get('title') or ''} {e.get('content') or ''}")


_PARENTHESE = re.compile(r"\([^)]*\)")


def cle_de_fiche(f: FicheElement) -> tuple[str, str]:
    """L'identité d'une fiche : nom × marché, à la casse, aux espaces, à la mise en forme et aux
    parenthèses près — mesuré le 2026-10-24 (`inventaire-lectures-2/`) : « zoldonrasib » et « zoldonrasib
    (RMC-9805) » relevés comme deux éléments d'une lecture à l'autre."""
    return (_forme_lisible(_PARENTHESE.sub(" ", f.nom)),
            _forme_lisible(_PARENTHESE.sub(" ", f.marche_vise or "")))


def verifier_inventaire(sortie: InventaireSortie, entries: dict[int, dict[str, Any]],
                        ticker_id: str) -> Inventaire:
    """Pur. Chaque fiche : pièces du dossier, `nom` / `marche_vise` / `extrait` LITTÉRAUX dans une pièce
    citée ; une fiche déjà vue (même nom × marché) est fusionnée (pièces réunies), jamais dupliquée."""
    inv = Inventaire(ticker_id=ticker_id)
    par_cle: dict[tuple[str, str], int] = {}
    for f in sortie.fiches:
        hors = [p for p in f.pieces if p not in entries]
        if hors:
            inv.ecartees.append(FicheEcartee(f, f"pièces {hors} hors du dossier"))
            continue
        textes = [_texte_piece(entries[p]) for p in f.pieces]
        dans = lambda val: any(_forme_lisible(val) in t for t in textes)  # noqa: E731
        # L'EXTRAIT fonde la fiche : sans lui, rien n'atteste l'élément — écartée.
        if not dans(f.extrait):
            inv.ecartees.append(FicheEcartee(f, f"['extrait'] absent LITTÉRALEMENT des pièces citées {f.pieces}"))
            continue
        # Le NOM : dans une pièce citée, ou — un même élément sous deux noms d'une pièce à l'autre (RASONQUE /
        # daraxonrasib) — ailleurs dans le dossier ; jamais inventé.
        if not dans(f.nom):
            if not any(_forme_lisible(f.nom) in _texte_piece(e) for e in entries.values()):
                inv.ecartees.append(FicheEcartee(f, f"['nom'] absent LITTÉRALEMENT du dossier"))
                continue
            inv.signaux.append(f"« {f.nom} » : nom absent des pièces citées {f.pieces}, présent ailleurs au dossier")
        # Le MARCHÉ composé au lieu d'être recopié ne fait pas tomber l'élément (mesuré : Vera Rubin écarté
        # aux trois lectures pour « data center, charges de travail IA agentique… ») : il est RETIRÉ, dit.
        if f.marche_vise and not dans(f.marche_vise):
            inv.signaux.append(f"« {f.nom} » : marché « {f.marche_vise} » non recopié des pièces {f.pieces} — retiré")
            f = f.model_copy(update={"marche_vise": None})
        cle = cle_de_fiche(f)
        if cle in par_cle:
            deja = inv.fiches[par_cle[cle]]
            inv.fiches[par_cle[cle]] = deja.model_copy(
                update={"pieces": sorted(set(deja.pieces) | set(f.pieces))})
            continue
        par_cle[cle] = len(inv.fiches)
        inv.fiches.append(f)
    nn = sortie.non_nommes
    if nn is not None:
        hors = [p for p in nn.pieces if p not in entries]
        if hors or not any(_forme_lisible(nn.extrait) in _texte_piece(entries[p]) for p in nn.pieces if p in entries):
            inv.ecartees.append(FicheEcartee(
                FicheElement(nom="(non nommés)", extrait=nn.extrait, origine="non_dit", pieces=nn.pieces),
                f"relevé des non nommés : pièces hors du dossier {hors} ou extrait absent des pièces citées"))
        else:
            inv.non_nommes = nn
    return inv


async def _resolve_inventaire_agent() -> ResolvedAgent:
    """Même provider que l'architecte (config en DB), prompt ET modèle de l'inventaire — un détenteur."""
    base = await get_agent_provider("ingestion-agent", "v2")
    return ResolvedAgent(agent_name="ingestion-agent", flow_version="v2", provider=base.provider,
                         model=MODELE_INVENTAIRE, system_prompt=_INVENTAIRE_SYSTEM_PROMPT)


def _message_inventaire(raison_sociale: str, pieces: str) -> str:
    return (f"[mode: inventaire]\n\nEntreprise : {raison_sociale}.\n\nLes pièces du dossier :\n\n{pieces}\n\n"
            "Produis l'objet JSON de l'inventaire (fiches, non_nommes) — rien d'autre.")


async def relever_inventaire(ticker_id: str, raison_sociale: str, entries: dict[int, dict[str, Any]],
                             *, agent: Optional[ResolvedAgent] = None) -> Inventaire:
    """UNE lecture du modèle, puis la vérification par le code. N'écrit rien."""
    agent = agent or await _resolve_inventaire_agent()
    messages = [{"role": "user", "content": _message_inventaire(raison_sociale, rendre_pieces(entries))}]
    # json_object=False : même prudence que tous les agents DeepSeek de la chaîne (cf. run_json_agent).
    run = await run_json_agent(agent, messages, InventaireSortie, json_object=False, temperature=0.0)
    inv = verifier_inventaire(run.parsed, entries, ticker_id)
    inv.run = run
    return inv
