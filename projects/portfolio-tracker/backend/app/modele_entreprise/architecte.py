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
from typing import Annotated, Any, Optional

from pydantic import Field, ValidationError

from app.agents.providers import ResolvedAgent, get_agent_provider
from app.agents.v2.runner import AgentOutputInvalid, AgentRunResult, run_json_agent, run_tool_json_agent
from app.contracts.analysis_v2_schemas import Strict
from app.contracts.modele_entreprise_schema import (
    ARCHITECTURE_SCHEMA_VERSION, Architecture, AxeUsage, BlocPropose, CelluleAttendue,
    InventaireProgramme, ManqueDuDossier, PassageAgrege, VariablePropre,
)
from app.knowledge.explorateur import (
    EXPLORATEUR_TOOLS, JournalExploration, charger_dossier_explorable, make_explorateur_tool_executors,
    make_rechercher_executor, pieces_citables_effectif,
)
from app.modele_entreprise.faits_publies import poser_maille
from app.modele_entreprise.matiere import Matiere, MatiereRefusee, charger_matiere, rendre_matiere
from app.modele_entreprise.porte import Porte, porte_de_l_architecte
from app.modele_entreprise.referentiel import (
    ArchitectureRefusee as PontRefuse, ReferentielModele, load_referentiel, valider_pont_architecture,
)
from app.modele_entreprise.registre import prochaine_version, proposer_architecture
from app.modele_entreprise.structure import ArchitectureRefusee as StructureRefusee, valider_structure

__all__ = [
    "PorteFermee", "ArchitectureRefusee", "DemandeDeRecherche", "ArchitecteSortie",
    "ResultatArchitecte", "juger_architecture", "proposer_architecture_du_titre",
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
    télémétrie cumulée des deux appels (même geste que `AgentOutputInvalid`).

    `sorties` : `(sortie_brute_du_modele, motif)` de CHAQUE tentative refusée (une ou deux, dans
    l'ordre) — §3 de la spec `15-lot-M3ter-architecte.md` : « que tout refus se lise ». Avant ce
    lot, cette télémétrie n'existait pas et `tools/architecte.py --sortie` n'écrivait qu'en cas de
    succès (diagnostic impossible, §0 de la spec)."""

    def __init__(self, *, motifs: str, tokens_in: int, tokens_out: int, cost_usd: float,
                attempts: int, sorties: tuple[tuple[str, str], ...] = ()) -> None:
        super().__init__(motifs)
        self.motifs = motifs
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.cost_usd = cost_usd
        self.attempts = attempts
        self.sorties = sorties
        # B4f : posé par `proposer_architecture_du_titre` quand le refus suit une exploration —
        # un refus doit dire ce qui a été ouvert, sinon « information ou consigne ? » est indécidable.
        self.exploration: Optional[JournalExploration] = None


class DemandeDeRecherche(Strict):
    """Lot B4f (spec `16-lot-B4f-explorateur.md` §4, « B′ ») — ce que le DOSSIER NE CONTIENT PAS et
    dont le classeur a besoin. À blanc : rendue, pour que le comité la voie. À l'écriture (hors
    périmètre de ce lot) : chacune devient une demande au collecteur par le mécanisme EXISTANT des
    demandes de recherche (`FrameworkMandate`/`persist_mandate`, `app/agents/v2/manager_persist.py`
    — détenteur identifié à l'étape 0, PAS un second mécanisme, #46)."""
    sujet: Annotated[str, Field(min_length=20)]
    pourquoi: Annotated[str, Field(min_length=20)]
    blocs: list[str] = Field(default_factory=list)


class ArchitecteSortie(Strict):
    """Ce que le MODÈLE produit — rien que les blocs/variables/formules/cellules. L'en-tête
    (ticker_id, version, archetype, famille, version_referentiel, schema_version) est posé par le
    code (§4.1 point 4) : `Strict` refuse un `ticker_id` venu du modèle. `blocs: list[BlocPropose]`
    (lot M3 bis, cause ①) — SANS `maille` : le code la pose (`faits_publies.poser_maille`), en même
    temps que l'en-tête."""
    blocs: list[BlocPropose] = Field(min_length=1)
    variables_propres: list[VariablePropre] = Field(default_factory=list)
    passage_a_l_agrege: list[PassageAgrege] = Field(min_length=1)
    cellules_attendues: list[CelluleAttendue] = Field(min_length=1)
    # 1.2.0 (cause ①, §2) — place pour le second découpage publié, hors de l'arbre ([S10]).
    autres_axes: list[AxeUsage] = Field(default_factory=list)
    # 1.2.0 (cause ③, §4.4) — ce que le dossier ne permet pas de découper.
    manques_du_dossier: list[ManqueDuDossier] = Field(default_factory=list)
    # 1.3.0 (lot M3 ter, §4) — pour CHAQUE programme nommé par `me_7`, ce que l'architecte en fait.
    inventaire_des_programmes: list[InventaireProgramme] = Field(default_factory=list)
    # Lot B4f (spec §4, « B′ ») — ce que le dossier ne permet PAS de construire et qu'il faudrait
    # aller chercher. Rendu dans les TROIS modes (`acces_au_dossier`) ; vide si rien ne manque.
    demandes_de_recherche: list[DemandeDeRecherche] = Field(default_factory=list)
    # Lot B4f (spec §5) — n'est AGI par le code qu'en mode `deux_temps` : des sujets (≥ 10
    # caractères) que le premier appel (SANS outil) voudrait voir cherchés avant de conclure. Dans
    # les modes `aucun`/`explorateur`, un champ renseigné est simplement IGNORÉ (ordre 0 inchangé ;
    # `explorateur` a déjà ses outils).
    besoins_d_information: list[Annotated[str, Field(min_length=10)]] = Field(default_factory=list)


def _refus_hors_contrat(e: AgentOutputInvalid, precedentes: tuple[tuple[str, str], ...]) -> ArchitectureRefusee:
    """Une sortie que le contrat refuse même après les réparations du runner : refus NOMMÉ
    `[CONTRAT]`, télémétrie cumulée, sortie brute gardée (§3 de `15-lot-M3ter-architecte.md`)."""
    motif = f"[CONTRAT] la sortie ne respecte pas le contrat de l'architecture : {e.last_error}"
    return ArchitectureRefusee(motifs=motif, tokens_in=e.tokens_in, tokens_out=e.tokens_out,
                               cost_usd=e.cost_usd, attempts=e.attempts,
                               sorties=precedentes + ((e.raw_content, motif),))


@dataclass(frozen=True)
class ResultatArchitecte:
    porte: Porte
    architecture: Optional[Architecture]
    signaux: tuple[str, ...]
    run: Optional[AgentRunResult]
    ecrite_sous_id: Optional[int] = None
    # B4f : ce que les outils ont RÉELLEMENT ouvert pendant le passage (`None` en mode `aucun`) —
    # rendu par `tools/architecte.py` à côté des `demandes_de_recherche` de `run.parsed`.
    exploration: Optional[JournalExploration] = None


# ── Le prompt (§4.2) ──────────────────────────────────────────────────────────────────────────────

_EXEMPLE_ARCHITECTURE: dict[str, Any] = {
    "blocs": [
        {
            "id": "produit_a", "libelle": "Produit A", "role": "activite",
            "statut": "metier_actuel", "origine": "interne",
            "rattachement": {"type": "publie", "axe": "activites", "membres": ["fictif:ProduitAMember"]},
            "variables": ["chiffre_affaires_du_bloc"],
            "motif": "Segment publié du 10-K, premier niveau de l'axe `activites`.",
        },
        {
            "id": "produit_b", "libelle": "Produit B", "role": "activite",
            "statut": "metier_actuel", "origine": "interne",
            "rattachement": {"type": "publie", "axe": "activites", "membres": ["fictif:ProduitBMember"]},
            "variables": ["chiffre_affaires_du_bloc"],
            "motif": "Segment publié du 10-K, premier niveau de l'axe `activites`.",
        },
        {
            "id": "produit_a_sous_segment", "libelle": "Produit A — composant estimé",
            "role": "activite", "statut": "metier_actuel", "origine": "interne",
            "rattachement": {"type": "parent", "bloc": "produit_a"},
            "variables": ["chiffre_affaires_du_bloc"],
            "motif": "Découpage plus fin que la publication, hypothèse maison documentée en pièce.",
            "pieces": [101],
        },
        {
            "id": "extension_capsules", "libelle": "Extension annoncée — capsules",
            "role": "activite", "statut": "extension_annoncee", "origine": "interne",
            "rattachement": {"type": "agrege", "ligne": "recherche_developpement"},
            "variables": ["taille_du_marche"],
            "motif": "Activité seulement annoncée par la direction — n'entre dans aucune formule.",
            "pieces": [102],
        },
        {
            "id": "programme_x", "libelle": "Programme X en développement", "role": "programme",
            "statut": "en_developpement", "origine": "licence",
            "jalon": {"franchi": "preuve de concept de laboratoire", "franchi_le": "2026-03-01",
                      "prochain": "autorisation d'essai clinique", "attendu_vers": "2027-06-01"},
            "rattachement": {"type": "agrege", "ligne": "recherche_developpement"},
            "variables": ["probabilite_de_succes", "cout_restant_de_developpement"],
            # UNE ligne par programme NOMMÉ individuellement par le dossier (`programmes`, un SEUL
            # nom pour un bloc non plateforme, [S13]) — recopié TEL QUE `me_7` l'écrit.
            "programmes": ["Programme X"],
            "motif": "Programme en développement sous licence, décrit par `me_7` — jalon suivant daté.",
            "pieces": [103],
        },
        {
            "id": "programmes_amont", "libelle": "Recherche amont (programmes non nommés)",
            "role": "programme", "statut": "en_developpement", "origine": "interne",
            "jalon": {"franchi": "validation de la plateforme", "franchi_le": "2026-01-10",
                      "prochain": "sélection d'un candidat", "attendu_vers": "2027-09-01"},
            "rattachement": {"type": "agrege", "ligne": "recherche_developpement"},
            "variables": ["cout_restant_de_developpement"],
            # Bloc PLATEFORME : regroupe des programmes que le dossier NE NOMME PAS individuellement
            # — `programmes` reste vide, `nombre_de_programmes_non_nommes` les compte.
            "plateforme": True, "nombre_de_programmes_non_nommes": 3,
            "motif": "Recherche amont non nommée individuellement par `me_7` — regroupée en plateforme.",
            "pieces": [103],
        },
        {
            "id": "commun", "libelle": "Frais communs non affectés", "role": "commun",
            "statut": "metier_actuel", "origine": "interne",
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
        {"ligne": "recherche_developpement", "formule": "commun__couts_communs"},
    ],
    "cellules_attendues": [
        {"bloc": "produit_a", "variable": "chiffre_affaires_du_bloc", "periodes": ["FY2026", "FY2027"],
         "auteur": {"type": "demande_ciblee"}},
        {"bloc": "produit_b", "variable": "chiffre_affaires_du_bloc", "periodes": ["FY2026", "FY2027"],
         "auteur": {"type": "demande_ciblee"}},
        {"bloc": "programme_x", "variable": "probabilite_de_succes", "periodes": ["sans_periode"],
         "auteur": {"type": "question", "question_id": "me_7"}},
        {"bloc": "programme_x", "variable": "cout_restant_de_developpement", "periodes": ["sans_periode"],
         "auteur": {"type": "question", "question_id": "me_7"}},
        {"bloc": "commun", "variable": "couts_communs", "periodes": ["FY2026", "FY2027"],
         "auteur": {"type": "demande_ciblee"}},
    ],
    # 1.2.0 — pour CHAQUE axe de la ventilation sans bloc publié, ce que l'architecte en fait.
    "autres_axes": [
        {"axe": "geographie", "usage": "Information de concentration géographique, hors de l'arbre "
                                       "(raccord des marges par zone)."},
    ],
    "manques_du_dossier": [
        {"sujet": "Dépense de R&D affectée par programme, non publiée séparément par l'émetteur.",
         "blocs": ["programme_x"],
         "consequence": "`depense_de_developpement_du_bloc` du programme X reste une demande ciblée, "
                        "non une réponse de `me_7`."},
    ],
    # 1.3.0 — pour CHAQUE programme que `me_7` NOMME individuellement, ce que l'architecte en fait.
    # Un programme de la plateforme (non nommé) n'a PAS d'entrée ici — par construction.
    "inventaire_des_programmes": [
        {"programme": "Programme X", "traitement": "bloc", "bloc": "programme_x",
         "motif": "Nommé individuellement par `me_7`, réussite incertaine : sa propre ligne."},
    ],
    # Lot B4f — ce que le dossier ne permet pas de construire (rendu dans les TROIS modes).
    "demandes_de_recherche": [
        {"sujet": "Taille et concurrence du marché visé par le Programme X, non publiées par l'émetteur.",
         "pourquoi": "`taille_du_marche`/`part_de_marche` du bloc ne peuvent pas s'estimer sans elles.",
         "blocs": ["programme_x"]},
    ],
    # Lot B4f — n'est agi par le code qu'en mode `deux_temps` (ignoré dans les deux autres modes).
    "besoins_d_information": [
        "Part du chiffre d'affaires du Produit B réalisée hors du marché domestique, non détaillée au dossier.",
    ],
}


_ARCHITECTE_SYSTEM_PROMPT = (
    "Tu es l'ARCHITECTE DU CLASSEUR d'un fonds d'investissement. On te confie le dossier complet "
    "d'UNE entreprise (son identité, l'horloge, son classement, les périodes du classeur, le "
    "catalogue de fiches maison, le patron de départ de son archétype, ses comptes reconstitués, sa "
    "ventilation publiée, les réponses de ses questions sources — dont « que prépare l'entreprise "
    "pour ses années futures » — ses notes flash récentes). Ta tâche : dessiner l'architecture de "
    "SON classeur — les blocs d'activité, les variables que chaque bloc retient, la règle de "
    "passage du détail à l'agrégé, et les cellules à remplir. Tu ne déclares JAMAIS la maille d'un "
    "bloc ni son emboîtement avec un autre bloc PUBLIÉ : le système les établit lui-même depuis la "
    "ventilation que tu cites.\n\n"
    "PRINCIPES :\n"
    "  · tu dessines CETTE entreprise, à partir du dossier fourni — le patron de départ est une "
    "SUGGESTION, pas une cage : compose ce qui convient réellement ;\n"
    "  · une variable propre (hors catalogue) n'est déclarée que si AUCUNE fiche du catalogue ne "
    "convient, avec sa fiche complète (comme une fiche du catalogue) et son motif d'ajout ;\n"
    "  · un bloc PUBLIÉ cite une adresse RECOPIÉE TELLE QUELLE de la ventilation (`axe`, `membres` — "
    "jamais inventée) ; `membres` porte PLUSIEURS qnames SEULEMENT pour un REGROUPEMENT (membres du "
    "même axe, du même parent — ex. les membres sous le seuil de matérialité réunis en un bloc) ; "
    "AU PREMIER NIVEAU, un seul axe ; le système dérive lui-même l'emboîtement entre deux blocs "
    "publiés (jamais à toi de le déclarer) ; ce qu'aucun bloc publié ne couvre va dans un bloc "
    "ESTIMÉ « reste », rattaché (agrege) à la ligne des comptes que vise le chiffre d'affaires des "
    "blocs ;\n"
    "  · UN SEUL axe peut porter des blocs publiés de premier niveau — pour CHAQUE AUTRE axe de la "
    "ventilation (le second découpage publié, marchés, pays, clients…), écris dans `autres_axes` ce "
    "que tu en fais (`usage`, au moins 20 caractères : raccord des marges, contrôle de "
    "concentration, information pour un bloc…) — NE LE FORCE PAS dans l'arbre en le déclarant "
    "`estime` : un membre réellement publié reste `publie`, ou va dans `autres_axes`, jamais les "
    "deux à la fois ;\n"
    "  · un bloc plus fin que la publication (sous-détail que tu composes toi-même) est ESTIMÉ, "
    "rattaché (parent) à son bloc parent, avec motif et au moins une pièce du dossier ;\n"
    "  · `origine` (interne, acquisition, licence, partenariat) est DISTINCTE de `statut` (maturité) "
    ": une ACQUISITION est `metier_actuel` (conclue) ou `extension_annoncee` (annoncée, non "
    "conclue), JAMAIS `en_developpement` (qui désigne un programme de recherche) ;\n"
    "  · une activité seulement ANNONCÉE (pas encore vendue, ni acquise) est `extension_annoncee` : "
    "elle n'entre dans AUCUNE formule de passage (elle ira dans les scénarios, plus tard) ; un "
    "programme EN DÉVELOPPEMENT est `en_developpement`, PORTE un `jalon` (dernier franchi et sa "
    "date, prochain et sa date attendue) et PEUT entrer dans une formule (pondéré) ;\n"
    "  · chaque axe de la ventilation est rendu dans son découpage le PLUS RÉCENT, qui fait foi ; son "
    "historique y est publié par l'émetteur ou reconstitué par « addition vérifiée » (somme exacte "
    "d'anciens membres publiés) ; quand le contenu des membres a changé sans passage vérifiable, "
    "l'historique n'est PAS reconstitué (« non comparable ») — ne le comble jamais toi-même ; le "
    "découpage ANTÉRIEUR est montré à part, tel que publié : tu peux le suivre si tu as une raison "
    "(dis-la dans le motif des blocs ; le comité verra le signal), mais ne mêle JAMAIS les deux "
    "découpages dans les blocs d'un même axe ;\n"
    "  · quand le dossier ne permet PAS de découper (programmes non nommés individuellement, "
    "dépense de R&D non affectée par programme…), écris-le dans `manques_du_dossier` (sujet, blocs "
    "concernés, conséquence) PLUTÔT que de regrouper en silence ;\n"
    "  · UNE LIGNE PAR PROGRAMME que l'émetteur NOMME individuellement ET dont la réussite est "
    "incertaine (essai clinique, autorisation, technologie non prouvée) : `programmes` porte ce "
    "nom unique recopié TEL QUE le dossier l'écrit — un passage CONTINU du texte de la réponse qui "
    "nomme les programmes, mot pour mot, sans rien y ajouter (ni marque entre parenthèses, ni "
    "précision) ni en retirer (ni article) — (un seul bloc = un seul programme nommé) ; SEULS "
    "les programmes NON nommés individuellement (recherche amont, plateforme) se regroupent dans un "
    "bloc `plateforme: true` (`programmes` vide, `nombre_de_programmes_non_nommes` ≥ 1) — et quand "
    "le dossier COMPTE plus de programmes qu'il n'en nomme, l'écart va dans une plateforme, jamais "
    "sous un nom inventé ;\n"
    "  · LIGNE PROPRE OU RATTACHÉE (#143) — le SEUL critère : faudra-t-il aller chercher des données "
    "de marché et de concurrence PROPRES (taille du marché visé, concurrents, part, probabilité de "
    "succès) pour l'estimer ? OUI → sa ligne, même s'il porte la marque ou la molécule d'un produit "
    "déjà vendu : une EXTENSION D'INDICATION (nouvelle maladie, nouvelle ligne de traitement) est un "
    "NOUVEAU MARCHÉ, donc un bloc à elle (`en_developpement`, son jalon) ; un produit déjà vendu sur "
    "un marché où l'activité n'était pas est un bloc ESTIMÉ à lui, enfant de l'activité qui le vend, "
    "`metier_actuel`, avec ses variables de marché. NON → rattaché à l'activité dont il prolonge le "
    "marché (`metier_actuel`) : la génération suivante d'un produit vendu (mêmes clients, mêmes "
    "concurrents), un nouveau segment de clients ou une nouvelle zone pour les produits déjà vendus. "
    "Jamais le nom ni la marque ne décident ;\n"
    "  · `inventaire_des_programmes` : pour CHAQUE élément que `me_7` NOMME (même ceux qu'une autre "
    "règle t'a fait omettre de l'arbre, même ceux que tu rattaches) — ni plus, ni moins : le système "
    "compare ton décompte aux chiffres clés `nombre_de_programmes` et `nombre_de_programmes_non_nommes` "
    "de `me_7` —, dis ce que tu en fais — `bloc` (sa "
    "ligne propre, `bloc` = cet id), `rattache` (s'estime avec les hypothèses de marché d'une "
    "activité vendue — `bloc` = cette activité, ou le bloc estimé à lui qui en est l'enfant, de statut "
    "`metier_actuel` — JAMAIS un bloc `en_developpement` ni une plateforme, motif ≥ 20 caractères), `extension` (devient une activité "
    "annoncée, `bloc` = ce bloc `extension_annoncee`), `hors_modele` (abandonné, immatériel — motif "
    "≥ 20 caractères, AUCUN `bloc`) ;\n"
    "  · chaque CELLULE ATTENDUE : si une question source de la variable instruit déjà cette cellule, "
    "son auteur est cette question (`{\"type\": \"question\", \"question_id\": \"...\"}`) ; sinon "
    "`{\"type\": \"demande_ciblee\"}` ; les périodes sont prises dans la liste fournie (jamais "
    "inventées) ; les variables lues par une formule de passage doivent couvrir TOUTES les périodes "
    "PROJETÉES ;\n"
    "  · une formule de passage est HOMOGÈNE : chaque ligne du business plan est un montant en M$ ; "
    "on n'ajoute jamais des M$ à un pourcentage, ni un STOCK (montant sans période, à un instant) à "
    "un flux de l'exercice ; un produit change d'unité (volume × prix moyen donne des $, à ramener "
    "en M$ par `/ 1000000` ; M$ × % se ramène par `/ 100`) ; un coefficient s'écrit en décimal "
    "(`* 0.9`), jamais sous forme de rapport d'échelles (`* 90 / 100`) ;\n"
    "  · tout bloc ESTIMÉ, ou de statut autre que `metier_actuel`, cite AU MOINS une pièce du "
    "dossier qui le fonde (`pieces`) — et cite UNIQUEMENT des numéros de la section « Pièces que tu "
    "peux citer » du dossier (jamais un numéro de RÉPONSE, qui s'écrit `réponse R-...` dans le "
    "dossier, jamais `#...`) ;\n"
    "  · les identifiants (`id` d'un bloc, d'une variable propre) : minuscules, chiffres, `_`, "
    "jamais `__` (réservé au séparateur `bloc__variable` d'une formule de passage) ;\n"
    "  · `demandes_de_recherche` : ce que le DOSSIER NE CONTIENT PAS et dont le classeur aurait "
    "besoin (sujet ≥ 20 caractères, pourquoi ≥ 20 caractères, blocs concernés) — vide si rien ne "
    "manque ; ce n'est jamais un prétexte pour laisser une cellule vide que le dossier permettrait "
    "de remplir ;\n"
    "  · si on te donne des OUTILS pour explorer le dossier (table des matières, ouvrir une note, "
    "ouvrir une pièce, rechercher), utilise-les : une note peut être écrite avant un fait plus "
    "récent (péremption, lu dans son état), une pièce remplacée reste consultable comme historique "
    "(jamais citable comme fondant un bloc), et un programme nommé dans une pièce que tu OUVRES "
    "mais absent du verbatim de `me_7` entre quand même dans `inventaire_des_programmes` — le "
    "système le signalera « absent de `me_7` » au comité, ce n'est pas une erreur de ta part ; "
    "cite UNIQUEMENT des numéros de pièces EN VIGUEUR ou que tu as toi-même ouverts/vus pendant ce "
    "passage, jamais un numéro simplement mentionné sans avoir été ouvert ; si on ne te donne AUCUN "
    "outil, remplis plutôt `besoins_d_information` (sujets ≥ 10 caractères) — le code cherchera pour "
    "toi avant un second appel ; ce champ est ignoré si des outils te sont donnés.\n\n"
    "Sortie : UNIQUEMENT l'objet JSON ci-après (aucun ticker, aucun id de version, aucun archétype, "
    "aucune `maille` — le système les pose lui-même), commençant par `{` et finissant par `}`, sans "
    "aucun texte autour. Exemple de forme — une société FICTIVE, à deux activités publiées, un "
    "découpage estimé, une extension annoncée, un programme en développement nommé (sous licence) "
    "et une plateforme de recherche amont non nommée, un axe secondaire déclaré en `autres_axes`, "
    "un manque du dossier, un bloc commun. Les numéros de pièces (101, 102, 103) sont FICTIFS, à "
    "remplacer par ceux de la section « Pièces que tu peux citer » du dossier réel :\n"
    f"{json.dumps(_EXEMPLE_ARCHITECTURE, ensure_ascii=False, indent=2)}"
)


def _message_architecte(matiere_rendue: str) -> str:
    return (
        "[mode: architecture]\n\nLe dossier de l'entreprise :\n"
        f"{matiere_rendue}\n\n"
        "Produis l'objet JSON de l'architecture (blocs, variables_propres, passage_a_l_agrege, "
        "cellules_attendues) — rien d'autre."
    )


# Le modèle de l'architecte vit ICI, avec son prompt (un seul détenteur) — pas celui de l'ingestion-agent.
# Mesuré le 2026-10-23 (`roadmap/V3/mesures/2026-10-23/banc-modeles/`), même matière, mêmes contrôles,
# noms réels ET anonymisés : V4-Pro rattache la génération suivante à son activité et donne une ligne
# par molécule à chaque passage, y compris sans pouvoir reconnaître l'entreprise ; V4-Flash jamais.
# Coût ≈ 0,07 $ par architecture (contre ≈ 0,01 $).
MODELE_ARCHITECTE = "deepseek-ai/DeepSeek-V4-Pro-0813"


async def _resolve_architecte_agent() -> ResolvedAgent:
    """Même provider que l'ingestion-agent (config en DB), prompt système ET modèle de l'architecte —
    même montage que `traducteur._resolve_traducteur_agent` (#19/#39 au câblage runtime)."""
    base = await get_agent_provider("ingestion-agent", "v2")
    return ResolvedAgent(
        agent_name="ingestion-agent", flow_version="v2", provider=base.provider, model=MODELE_ARCHITECTE,
        system_prompt=_ARCHITECTE_SYSTEM_PROMPT)


def _poser_entete(sortie: ArchitecteSortie, *, ticker_id: str, version: int, archetype: str,
                  famille: str, version_referentiel: str) -> Architecture:
    # 1.2.0 (cause ①, §2) — la MAILLE est posée par le code, jamais déclarée par le modèle
    # (`sortie.blocs: list[BlocPropose]`, sans `maille`) : `faits_publies.poser_maille`, détenteur
    # unique de cette dérivation, en même temps que le reste de l'en-tête.
    blocs = poser_maille(sortie.blocs)
    return Architecture(
        schema_version=ARCHITECTURE_SCHEMA_VERSION, ticker_id=ticker_id, version=version,
        archetype=archetype, famille=famille, version_referentiel=version_referentiel,
        blocs=blocs, variables_propres=sortie.variables_propres,
        passage_a_l_agrege=sortie.passage_a_l_agrege, cellules_attendues=sortie.cellules_attendues,
        autres_axes=sortie.autres_axes, manques_du_dossier=sortie.manques_du_dossier,
        inventaire_des_programmes=sortie.inventaire_des_programmes)


def juger_architecture(arch: Architecture, ref: ReferentielModele, matiere: Matiere) -> tuple[bool, str, tuple[str, ...]]:
    """`(tient, motif, signaux)`."""
    try:
        valider_pont_architecture(arch, ref, matiere.periodes_projetees)
    except PontRefuse as e:
        return False, str(e), ()
    try:
        signaux = tuple(valider_structure(arch, ref, matiere))
    except StructureRefusee as e:
        return False, str(e), ()
    return True, "", signaux


# ── L'interrupteur à trois positions, `acces_au_dossier` (lot B4f, spec §5) ──────────────────────
# `aucun` (ordre 0) reste le chemin direct de `proposer_architecture_du_titre` : un seul appel, pas
# de fonction à part, sortie strictement identique à avant ce lot. `deux_temps`/`explorateur` sont
# chacun une fonction qui rend `(run, matiere)` — `matiere` peut revenir AUGMENTÉE (`pieces_citables`
# ∪ pièces ouvertes, `pieces_ouvertes_texte`, §3 de la spec), jamais autre chose : le reste de
# `proposer_architecture_du_titre` (construction de l'en-tête, jugement, renvoi UNE fois) est
# strictement le MÊME dans les trois modes.

_CLOTURE_EXPLORATEUR = (
    "Clos l'exploration : produis maintenant l'objet JSON COMPLET de l'architecture (blocs, "
    "variables_propres, passage_a_l_agrege, cellules_attendues, autres_axes, manques_du_dossier, "
    "inventaire_des_programmes, demandes_de_recherche) — rien d'autre. Si le budget d'ouvertures a "
    "été atteint avant d'avoir fini d'explorer ce qu'il fallait, dis-le dans un `manque_du_dossier`."
)


async def _passage_deux_temps(
    agent: ResolvedAgent, messages: list[dict[str, Any]], matiere: Matiere, *,
    ticker_id: str, max_besoins: int,
) -> tuple[AgentRunResult, Matiere, Optional[JournalExploration]]:
    """Garde-fou F (spec §5) : un premier appel SANS outil qui rend sa proposition ET
    `besoins_d_information` ; le CODE exécute `rechercher` pour chacun (SANS modèle, borné à
    `max_besoins` — le même paramètre du référentiel que la boucle d'outils, §2), ajoute les
    résultats à la matière, puis un second appel conclut. Coût et durée bornés, besoins visibles."""
    from app.db.database import get_db_session

    premier = await run_json_agent(agent, messages, ArchitecteSortie, json_object=False)
    besoins = (premier.parsed.besoins_d_information if premier.parsed else [])[:max_besoins]
    if not besoins:
        return premier, matiere, None

    journal = JournalExploration()
    executeur_rechercher = make_rechercher_executor(
        journal, conn_factory=get_db_session, ticker_id=ticker_id)
    lignes: list[str] = []
    for sujet in besoins:
        resultat = await executeur_rechercher({"sujet": sujet})
        pieces = resultat.get("resultats") or []
        lignes.append(
            f"- {sujet} : " + (", ".join(f"#{p['numero']} ({p['titre']})" for p in pieces)
                               if pieces else "aucun résultat"))

    if not journal.pieces_ouvertes:
        return premier, matiere, journal

    matiere_enrichie = dataclasses.replace(
        matiere, pieces_citables=pieces_citables_effectif(matiere.pieces_citables, journal),
        pieces_ouvertes_texte={**matiere.pieces_ouvertes_texte, **journal.pieces_ouvertes})

    messages2 = messages + [
        {"role": "assistant", "content": premier.raw_content},
        {"role": "user", "content": (
            "Résultats de `rechercher` pour vos besoins d'information (exécuté par le CODE, SANS "
            "modèle) :\n" + "\n".join(lignes) + "\n\nProduis l'architecture JSON COMPLÈTE finale "
            "(même format), en tenant compte de ces résultats s'ils sont pertinents.")}]
    second = await run_json_agent(agent, messages2, ArchitecteSortie, json_object=False)
    run = dataclasses.replace(
        second, tokens_in=premier.tokens_in + second.tokens_in,
        tokens_out=premier.tokens_out + second.tokens_out,
        cost_usd=premier.cost_usd + second.cost_usd, attempts=premier.attempts + second.attempts)
    return run, matiere_enrichie, journal


async def _passage_explorateur(
    agent: ResolvedAgent, messages: list[dict[str, Any]], matiere: Matiere, *,
    ticker_id: str, max_iterations: int,
) -> tuple[AgentRunResult, Matiere, Optional[JournalExploration]]:
    """La boucle d'outils §2 de la spec (`table_des_matieres`/`ouvrir_note`/`ouvrir_piece`/
    `rechercher`), puis la clôture en JSON strict (`run_tool_json_agent`, détenteur unique de la
    boucle — #46, même mécanique que le search-worker)."""
    from app.db.database import get_db_session

    dossier = None
    async with get_db_session() as conn:
        dossier = await charger_dossier_explorable(conn, ticker_id)

    journal = JournalExploration()
    executeurs = make_explorateur_tool_executors(
        dossier, journal, conn_factory=get_db_session, ticker_id=ticker_id)
    agent_avec_outils = dataclasses.replace(agent, tools=EXPLORATEUR_TOOLS)
    run = await run_tool_json_agent(
        agent_avec_outils, messages, executeurs, ArchitecteSortie,
        closing_instruction=_CLOTURE_EXPLORATEUR, max_iterations=max_iterations)

    matiere_enrichie = dataclasses.replace(
        matiere, pieces_citables=pieces_citables_effectif(matiere.pieces_citables, journal),
        pieces_ouvertes_texte={**matiere.pieces_ouvertes_texte, **journal.pieces_ouvertes})
    return run, matiere_enrichie, journal


async def proposer_architecture_du_titre(
    ticker_id: str, *, agent: Optional[ResolvedAgent] = None, ecrire: bool = False,
    hors_porte: bool = False, acces_au_dossier: Optional[str] = None,
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
    if acces_au_dossier is not None and ecrire:
        raise ValueError("`acces_au_dossier` forcé n'est admis qu'à blanc : à l'écriture, le référentiel décide")
    mode = acces_au_dossier or ref.acces_au_dossier
    exploration: Optional[JournalExploration] = None
    try:
        if mode == "aucun":
            # Ordre 0 (principe fondateur n° 3) — chemin INCHANGÉ depuis avant ce lot.
            run = await run_json_agent(agent, messages, ArchitecteSortie, json_object=False)
        elif mode == "deux_temps":
            run, matiere, exploration = await _passage_deux_temps(
                agent, messages, matiere, ticker_id=ticker_id,
                max_besoins=ref.max_iterations_explorateur)
        elif mode == "explorateur":
            run, matiere, exploration = await _passage_explorateur(
                agent, messages, matiere, ticker_id=ticker_id,
                max_iterations=ref.max_iterations_explorateur)
        else:  # défensif — le `Literal` du contrat du référentiel l'interdit déjà
            raise ValueError(f"`acces_au_dossier` inconnu : {mode!r}")
    except AgentOutputInvalid as e:
        # §3 (jamais de plantage) : une sortie hors contrat (ex. [S13], invariant d'un seul objet,
        # levé au DÉCODAGE) a déjà eu ses renvois dans le runner, erreurs Pydantic à l'appui — elle
        # devient un refus NOMMÉ, sortie brute gardée, comme un refus [P]/[S].
        raise _refus_hors_contrat(e, ()) from e

    def _architecture(sortie: ArchitecteSortie) -> Architecture:
        return _poser_entete(sortie, ticker_id=ticker_id, version=version, archetype=matiere.archetype,
                            famille=matiere.famille, version_referentiel=ref.version)

    def _construire_et_juger(sortie: ArchitecteSortie) -> tuple[bool, str, tuple[str, ...], Optional[Architecture]]:
        """§3 de la spec (jamais de plantage) : toute erreur de contrat levée À L'ASSEMBLAGE
        (`_poser_entete` → `faits_publies.poser_maille`, ou la validation de `Architecture` elle-
        même — ex. [S12]/[S13] côté `Bloc`, un bloc estimé sans pièce, un cycle de rattachement…)
        devient un refus NOMMÉ qui suit le MÊME chemin de renvoi que [P]/[S] — jamais un plantage.
        Seule une panne d'infrastructure (réseau, base) reste une exception non rattrapée ici."""
        try:
            arch = _architecture(sortie)
        except ValidationError as e:
            return False, f"[ASSEMBLAGE] l'architecture posée (en-tête + maille) ne tient pas : {e}", (), None
        tient, motif, signaux = juger_architecture(arch, ref, matiere)
        return tient, motif, signaux, arch

    tient, motif, signaux, arch = _construire_et_juger(run.parsed)
    sorties_refusees: list[tuple[str, str]] = []
    if not tient:
        sorties_refusees.append((run.raw_content, motif))
        messages = messages + [
            {"role": "assistant", "content": run.raw_content},
            {"role": "user", "content": (
                f"Architecture refusée — {motif}\nRends l'architecture COMPLÈTE corrigée (même "
                "format), en levant TOUS les motifs ci-dessus.")}]
        try:
            second = await run_json_agent(agent, messages, ArchitecteSortie, json_object=False)
        except AgentOutputInvalid as e:
            refus = _refus_hors_contrat(e.add_upstream(run.tokens_in, run.tokens_out, run.cost_usd,
                                                     run.attempts), tuple(sorties_refusees))
            refus.exploration = exploration
            raise refus from e
        run = dataclasses.replace(
            second, tokens_in=run.tokens_in + second.tokens_in, tokens_out=run.tokens_out + second.tokens_out,
            cost_usd=run.cost_usd + second.cost_usd, attempts=run.attempts + second.attempts)
        tient, motif, signaux, arch = _construire_et_juger(run.parsed)
        if not tient:
            sorties_refusees.append((run.raw_content, motif))
            refus = ArchitectureRefusee(
                motifs=motif, tokens_in=run.tokens_in, tokens_out=run.tokens_out,
                cost_usd=run.cost_usd, attempts=run.attempts, sorties=tuple(sorties_refusees))
            refus.exploration = exploration
            raise refus

    ecrite_sous_id = None
    if ecrire:
        async with get_db_session() as conn:
            ecrite_sous_id = await proposer_architecture(
                conn, arch, ref, auteur=f"architecte ({agent.model})")

    return ResultatArchitecte(porte=porte, architecture=arch, signaux=signaux, run=run,
                              ecrite_sous_id=ecrite_sous_id, exploration=exploration)
