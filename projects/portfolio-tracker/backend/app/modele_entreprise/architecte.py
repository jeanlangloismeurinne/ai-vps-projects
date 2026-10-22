"""L'AGENT ARCHITECTE — lot M3, roadmap V3 `12-lot-M3-architecte.md` §4.

Dessine l'architecture du classeur d'UNE entreprise à partir de sa matière (`matiere.py`) : les blocs,
les variables qu'il retient par bloc, la règle de passage au format agrégé, et les cellules à remplir.
Patron de l'agent : `app/agents/v2/traducteur.py` (le prompt vit dans le code, le modèle ne produit que
les LIGNES, le code pose l'EN-TÊTE, un renvoi UNE fois sur refus).
"""
from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from typing import Any, Optional

from pydantic import Field

from app.agents.providers import ResolvedAgent, get_agent_provider
from app.agents.v2.runner import AgentRunResult, run_json_agent
from app.contracts.analysis_v2_schemas import Strict
from app.contracts.modele_entreprise_schema import (
    ARCHITECTURE_SCHEMA_VERSION, Architecture, Bloc, CelluleAttendue, PassageAgrege, VariablePropre,
)
from app.modele_entreprise.matiere import Matiere, MatiereRefusee, charger_matiere, rendre_matiere
from app.modele_entreprise.porte import Porte, porte_de_l_architecte
from app.modele_entreprise.referentiel import (
    ArchitectureRefusee as PontRefuse, ReferentielModele, load_referentiel, valider_pont_architecture,
)
from app.modele_entreprise.registre import prochaine_version, proposer_architecture
from app.modele_entreprise.structure import ArchitectureRefusee as StructureRefusee, valider_structure

__all__ = [
    "PorteFermee", "ArchitectureRefusee", "ArchitecteSortie", "ResultatArchitecte",
    "juger_architecture", "proposer_architecture_du_titre",
]


class PorteFermee(Exception):
    """La porte de l'architecte est fermée — levée AVANT toute dépense (#40/#63)."""

    def __init__(self, porte: Porte) -> None:
        self.porte = porte
        fermees = [f"{q.question_id} : {q.raison}" for q in porte.questions if not q.ouvre]
        super().__init__(
            f"porte fermée pour `{porte.archetype}`"
            + (f" — {len(fermees)} question(s) ferment : " + " ; ".join(fermees) if fermees
               else f" — {porte.raison}"))


class ArchitectureRefusee(RuntimeError):
    """L'architecture proposée par le modèle ne tient pas, même après un renvoi — AVEC la
    télémétrie cumulée des deux appels (même geste que `AgentOutputInvalid`)."""

    def __init__(self, *, motifs: str, tokens_in: int, tokens_out: int, cost_usd: float,
                attempts: int) -> None:
        super().__init__(motifs)
        self.motifs = motifs
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.cost_usd = cost_usd
        self.attempts = attempts


class ArchitecteSortie(Strict):
    """Ce que le MODÈLE produit — rien que les blocs/variables/formules/cellules. L'en-tête
    (ticker_id, version, archetype, famille, version_referentiel, schema_version) est posé par le
    code (§4.1 point 4) : `Strict` refuse un `ticker_id` venu du modèle."""
    blocs: list[Bloc] = Field(min_length=1)
    variables_propres: list[VariablePropre] = Field(default_factory=list)
    passage_a_l_agrege: list[PassageAgrege] = Field(min_length=1)
    cellules_attendues: list[CelluleAttendue] = Field(min_length=1)


@dataclass(frozen=True)
class ResultatArchitecte:
    porte: Porte
    architecture: Optional[Architecture]
    signaux: tuple[str, ...]
    run: Optional[AgentRunResult]
    ecrite_sous_id: Optional[int] = None


# ── Le prompt (§4.2) ──────────────────────────────────────────────────────────────────────────────

_EXEMPLE_ARCHITECTURE: dict[str, Any] = {
    "blocs": [
        {
            "id": "produit_a", "libelle": "Produit A", "role": "activite",
            "statut": "metier_actuel", "maille": "publie",
            "rattachement": {"type": "publie", "axe": "activites", "membre": "fictif:ProduitAMember"},
            "variables": ["chiffre_affaires_du_bloc"],
            "motif": "Segment publié du 10-K, premier niveau de l'axe `activites`.",
        },
        {
            "id": "produit_b", "libelle": "Produit B", "role": "activite",
            "statut": "metier_actuel", "maille": "publie",
            "rattachement": {"type": "publie", "axe": "activites", "membre": "fictif:ProduitBMember"},
            "variables": ["chiffre_affaires_du_bloc"],
            "motif": "Segment publié du 10-K, premier niveau de l'axe `activites`.",
        },
        {
            "id": "produit_a_sous_segment", "libelle": "Produit A — composant estimé",
            "role": "activite", "statut": "metier_actuel", "maille": "estime",
            "rattachement": {"type": "parent", "bloc": "produit_a"},
            "variables": ["chiffre_affaires_du_bloc"],
            "motif": "Découpage plus fin que la publication, hypothèse maison documentée en pièce.",
            "pieces": [101],
        },
        {
            "id": "extension_capsules", "libelle": "Extension annoncée — capsules",
            "role": "activite", "statut": "extension_annoncee", "maille": "estime",
            "rattachement": {"type": "agrege", "ligne": "recherche_developpement"},
            "variables": ["taille_du_marche"],
            "motif": "Activité seulement annoncée par la direction — n'entre dans aucune formule.",
            "pieces": [102],
        },
        {
            "id": "commun", "libelle": "Frais communs non affectés", "role": "commun",
            "statut": "metier_actuel", "maille": "estime",
            "rattachement": {"type": "agrege", "ligne": "autres_charges_exploitation"},
            "variables": ["couts_communs"],
            "motif": "Charges de structure non rattachées à un bloc d'activité pris isolément.",
            "pieces": [101],
        },
    ],
    "variables_propres": [],
    "passage_a_l_agrege": [
        {"ligne": "chiffre_affaires",
         "formule": "produit_a__chiffre_affaires_du_bloc + produit_b__chiffre_affaires_du_bloc"},
    ],
    "cellules_attendues": [
        {"bloc": "produit_a", "variable": "chiffre_affaires_du_bloc", "periodes": ["FY2026", "FY2027"],
         "auteur": {"type": "demande_ciblee"}},
        {"bloc": "produit_b", "variable": "chiffre_affaires_du_bloc", "periodes": ["FY2026", "FY2027"],
         "auteur": {"type": "demande_ciblee"}},
    ],
}


_ARCHITECTE_SYSTEM_PROMPT = (
    "Tu es l'ARCHITECTE DU CLASSEUR d'un fonds d'investissement. On te confie le dossier complet "
    "d'UNE entreprise (son identité, l'horloge, son classement, les périodes du classeur, le "
    "catalogue de fiches maison, le patron de départ de son archétype, ses comptes reconstitués, sa "
    "ventilation publiée, les réponses de ses questions sources, ses notes flash récentes). Ta "
    "tâche : dessiner l'architecture de SON classeur — les blocs d'activité, les variables que "
    "chaque bloc retient, la règle de passage du détail à l'agrégé, et les cellules à remplir.\n\n"
    "PRINCIPES :\n"
    "  · tu dessines CETTE entreprise, à partir du dossier fourni — le patron de départ est une "
    "SUGGESTION, pas une cage : compose ce qui convient réellement ;\n"
    "  · une variable propre (hors catalogue) n'est déclarée que si AUCUNE fiche du catalogue ne "
    "convient, avec sa fiche complète (comme une fiche du catalogue) et son motif d'ajout ;\n"
    "  · un bloc PUBLIÉ cite une adresse RECOPIÉE TELLE QUELLE de la ventilation (`axe`, `membre` — "
    "jamais inventée) ; au premier niveau, un seul axe ; jamais un bloc et son propre sous-membre "
    "côte à côte au même niveau (double compte) ; ce qu'aucun bloc publié ne couvre va dans un bloc "
    "ESTIMÉ « reste », rattaché (agrege) à la ligne des comptes que vise le chiffre d'affaires des "
    "blocs ;\n"
    "  · un bloc plus fin que la publication est ESTIMÉ, rattaché (parent) à son bloc parent, avec "
    "motif et au moins une pièce du dossier ;\n"
    "  · une activité seulement ANNONCÉE (pas encore vendue) est `extension_annoncee` : elle n'entre "
    "dans AUCUNE formule de passage (elle ira dans les scénarios, plus tard) ; un programme EN "
    "DÉVELOPPEMENT est `en_developpement` et PEUT entrer dans une formule (pondéré) ;\n"
    "  · si la publication a CHANGÉ de découpage (un redécoupage récent), choisis-en UN, dis LEQUEL "
    "et POURQUOI dans le motif des blocs concernés ;\n"
    "  · chaque CELLULE ATTENDUE : si une question source de la variable instruit déjà cette cellule, "
    "son auteur est cette question (`{\"type\": \"question\", \"question_id\": \"...\"}`) ; sinon "
    "`{\"type\": \"demande_ciblee\"}` ; les périodes sont prises dans la liste fournie (jamais "
    "inventées) ; les variables lues par une formule de passage doivent couvrir TOUTES les périodes "
    "PROJETÉES ;\n"
    "  · tout bloc ESTIMÉ, ou de statut autre que `metier_actuel`, cite AU MOINS une pièce du "
    "dossier qui le fonde (`pieces`, des ids cités dans le dossier) ;\n"
    "  · les identifiants (`id` d'un bloc, d'une variable propre) : minuscules, chiffres, `_`, "
    "jamais `__` (réservé au séparateur `bloc__variable` d'une formule de passage).\n\n"
    "Sortie : UNIQUEMENT l'objet JSON ci-après (aucun ticker, aucun id de version, aucun archétype — "
    "le système les pose lui-même), commençant par `{` et finissant par `}`, sans aucun texte "
    "autour. Exemple de forme — une société FICTIVE, à deux activités publiées, un découpage estimé, "
    "une extension annoncée, un bloc commun :\n"
    f"{json.dumps(_EXEMPLE_ARCHITECTURE, ensure_ascii=False, indent=2)}"
)


def _message_architecte(matiere_rendue: str) -> str:
    return (
        "[mode: architecture]\n\nLe dossier de l'entreprise :\n"
        f"{matiere_rendue}\n\n"
        "Produis l'objet JSON de l'architecture (blocs, variables_propres, passage_a_l_agrege, "
        "cellules_attendues) — rien d'autre."
    )


async def _resolve_architecte_agent() -> ResolvedAgent:
    """Même provider que l'ingestion-agent (config en DB), prompt système de l'architecte — même
    montage que `traducteur._resolve_traducteur_agent` (#19/#39 au câblage runtime)."""
    base = await get_agent_provider("ingestion-agent", "v2")
    return ResolvedAgent(
        agent_name="ingestion-agent", flow_version="v2", provider=base.provider, model=base.model,
        system_prompt=_ARCHITECTE_SYSTEM_PROMPT)


def _poser_entete(sortie: ArchitecteSortie, *, ticker_id: str, version: int, archetype: str,
                  famille: str, version_referentiel: str) -> Architecture:
    return Architecture(
        schema_version=ARCHITECTURE_SCHEMA_VERSION, ticker_id=ticker_id, version=version,
        archetype=archetype, famille=famille, version_referentiel=version_referentiel,
        blocs=sortie.blocs, variables_propres=sortie.variables_propres,
        passage_a_l_agrege=sortie.passage_a_l_agrege, cellules_attendues=sortie.cellules_attendues)


def juger_architecture(arch: Architecture, ref: ReferentielModele, matiere: Matiere) -> tuple[bool, str, tuple[str, ...]]:
    """`(tient, motif, signaux)`."""
    try:
        valider_pont_architecture(arch, ref)
    except PontRefuse as e:
        return False, str(e), ()
    try:
        signaux = tuple(valider_structure(arch, ref, matiere))
    except StructureRefusee as e:
        return False, str(e), ()
    return True, "", signaux


async def proposer_architecture_du_titre(
    ticker_id: str, *, agent: Optional[ResolvedAgent] = None, ecrire: bool = False,
    hors_porte: bool = False,
) -> ResultatArchitecte:
    """Ordre d'exécution — §4.1. Lève `PorteFermee` AVANT toute dépense (sauf `hors_porte=True`, à
    blanc uniquement) ; `ArchitectureRefusee` (ce module) après un renvoi resté sans effet."""
    if ecrire and hors_porte:
        raise ValueError("`--ecrire` et `--hors-porte` ensemble sont refusés : `hors_porte` n'est "
                         "admis qu'à blanc")

    from app.agents.v2.parcours import charger_etat_dossier
    from app.db.database import get_db_session

    ref = load_referentiel()
    async with get_db_session() as conn:
        etat = await charger_etat_dossier(conn, ticker_id)
        porte = porte_de_l_architecte(etat, ref)
        if not porte.ouverte and not hors_porte:
            raise PorteFermee(porte)

        try:
            matiere = await charger_matiere(conn, ticker_id, publier=ecrire)
        except MatiereRefusee as e:
            raise PorteFermee(porte) from e  # refus nommé avant dépense, même mode de panne

        version = await prochaine_version(conn, ticker_id)

    matiere_rendue = rendre_matiere(matiere)
    agent = agent or await _resolve_architecte_agent()
    messages = [{"role": "user", "content": _message_architecte(matiere_rendue)}]
    run = await run_json_agent(agent, messages, ArchitecteSortie, json_object=False)

    def _architecture(sortie: ArchitecteSortie) -> Architecture:
        return _poser_entete(sortie, ticker_id=ticker_id, version=version, archetype=matiere.archetype,
                            famille=matiere.famille, version_referentiel=ref.version)

    arch = _architecture(run.parsed)
    tient, motif, signaux = juger_architecture(arch, ref, matiere)
    if not tient:
        messages = messages + [
            {"role": "assistant", "content": run.raw_content},
            {"role": "user", "content": (
                f"Architecture refusée — {motif}\nRends l'architecture COMPLÈTE corrigée (même "
                "format), en levant TOUS les motifs ci-dessus.")}]
        second = await run_json_agent(agent, messages, ArchitecteSortie, json_object=False)
        run = dataclasses.replace(
            second, tokens_in=run.tokens_in + second.tokens_in, tokens_out=run.tokens_out + second.tokens_out,
            cost_usd=run.cost_usd + second.cost_usd, attempts=run.attempts + second.attempts)
        arch = _architecture(run.parsed)
        tient, motif, signaux = juger_architecture(arch, ref, matiere)
        if not tient:
            raise ArchitectureRefusee(
                motifs=motif, tokens_in=run.tokens_in, tokens_out=run.tokens_out,
                cost_usd=run.cost_usd, attempts=run.attempts)

    ecrite_sous_id = None
    if ecrire:
        async with get_db_session() as conn:
            ecrite_sous_id = await proposer_architecture(
                conn, arch, ref, auteur=f"architecte ({agent.model})")

    return ResultatArchitecte(porte=porte, architecture=arch, signaux=signaux, run=run,
                              ecrite_sous_id=ecrite_sous_id)
