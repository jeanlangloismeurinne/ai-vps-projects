"""
Schéma Pydantic versionné du `readiness_report_json` (curator, §7) — DÉRIVÉ des cartes de provenance.

5ᵉ et dernier contrat majeur du chemin critique. C'est le **GO/NO-GO** du flux (ex-screening) :
il gate l'appel Opus. Sa particularité d'auditabilité : il est presque entièrement **DÉRIVÉ**
(recompute déterministe depuis l'*existence* d'entries), donc vérifiable **sans token LLM** — c'est
la projection des cartes de provenance du `research_memo` sur (dimension MVDD → champs factual →
tier plancher). Voir readiness_derivation.md (matrice de dérivation) et §7 de 01-spec-v2-unifiee.md.

Garde-fous encodés :
  G1  extra='forbid' + schema_version figé -> aucun champ hors contrat ; l'un des 3 points de synchro.
  G2  le verdict est CONTRAINT par la coverage (compute_verdict), il n'est jamais libre : un dossier
      structuré-complet mais mince en qualitatif sort `thin_qualitative`, JAMAIS `ready` (anti-faux-complet).
  A3  trois indicateurs séparés, jamais fusionnés — au stade readiness (pré-analyse) seul `qualite_info`
      est formé ; `conviction`/`marge_securite` restent None (produits par l'analyse aval).
  B   bijection stricte champs_non_fondables <-> gaps (au grain CHAMP) : aucun manque comblable ne
      reste silencieux, aucun gap ne cible un champ déjà fondable. Pareto se module par priorite/
      arret_pareto_recommande, jamais en retirant un gap. `too_hard` exempté (blocage = décision A10).
  Économie (constitution §3) : coverage/verdict/gaps/entries_par_tier sont tous des `derived`
      déterministes (aucun token) — la readiness est bon marché par construction.

Stockage : knowledge_curator_reports(report_type='readiness', report_json, verdict,
coverage_structuree, coverage_qualitative, context_pack_entry_id) — migration 024, déjà appliquée.

Cible : pydantic v2 (container backend 2.13.4). Le python hôte a v1 → tester en container.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "v2.0.0"  # aligné sur analysis_v2_schemas.py (même famille de contrats V2)

ReadinessVerdict = Literal["not_ready", "researching", "thin_qualitative", "ready", "too_hard"]
Tier = Literal["A", "A-", "B+", "B", "B-", "C+", "C"]

# POURQUOI la cause est un AXE SÉPARÉ et non un verdict composé (`not_ready_peremption`).
# La roadmap 02 §4 demande que le verdict global distingue « not_ready (péremption) » de
# « not_ready (lacune) ». Le faire en allongeant `ReadinessVerdict` recombinerait deux propriétés
# orthogonales — *est-ce livrable ?* et *pourquoi ne l'est-ce pas ?* — dans un scalaire unique,
# c'est-à-dire exactement le défaut que toute cette révision corrige (#50 : jamais de composite).
# Le GO/NO-GO garde donc son vocabulaire fermé, et la cause se lit à côté.
CauseNonReady = Literal["peremption", "lacune", "mixte"]

# blocs de couverture (§7, DÉCISION #1 : jamais fusionnés)
_DIMS_STRUCTUREE = {"business_model", "financials", "valorisation"}
_DIMS_QUALITATIVE = {"produits", "positionnement", "marche", "management_allocation", "risques"}


class Strict(BaseModel):
    """Base commune : aucun champ hors contrat (G1)."""
    model_config = ConfigDict(extra="forbid")


# ─────────────────────────── couverture (derived) ───────────────────────────
class FieldGrounding(Strict):
    """Option C (2026-08-26) : le LLM PROPOSE, pour un champ factual requis qu'il juge fondé, les
    `entry_ids` qui le fondent. Le backend DISPOSE : il vérifie en Python que ≥1 de ces entries existe
    au tier réel ≥ plancher du champ (le LLM ne peut plus faire passer un champ sous-doté — même
    patron que #24/#28 : proposé par le modèle, vérifié par le code)."""
    champ: str
    entry_ids: list[int] = Field(min_length=1)


class DimensionCoverage(Strict):
    """Une dimension MVDD. `ok` est DÉRIVÉ : ∃ entry couvrant chaque champ factual requis au
    tier ≥ plancher ⇔ `champs_non_fondables` est vide. Recompute déterministe (aucun LLM).

    TROIS ÉTATS PAR CHAMP, jamais deux confondus (capacité 4 de la roadmap 02) :

      couvert         → le champ figure dans `fondations`, avec les entries qui le fondent VRAIMENT ;
      couvert_perime  → le champ figure dans `champs_perimes` : il a des entries, mais aucune ne
                        tient l'actualité qu'il exige (`FIELD_PROFILES[...]["actualite_bloquante"]`).
                        Remède = **rafraîchir**, pas collecter ;
      non_couvert     → `champs_non_fondables` PRIVÉ de `champs_perimes` : aucune entry au plancher.
                        Remède = **collecter**.

    `champs_non_fondables` reste l'UNION des deux causes, et c'est délibéré : c'est lui qui porte la
    bijection avec les gaps (option B) et la dérivation de `ok`. Un champ périmé est un manque —
    il ne fonde plus. Ce qui ne doit jamais se perdre, c'est la CAUSE, donc le remède : elle vit
    dans `champs_perimes` et dans `GapItem.remede`. Confondre les deux ferait payer une recherche
    complète là où un rafraîchissement suffisait.
    """
    dimension: str
    tier_plancher: Tier
    champs_requis: list[str] = Field(min_length=1)
    fondations: list[FieldGrounding] = Field(default_factory=list)   # option C : mapping champ→entry_ids
    champs_non_fondables: list[str] = Field(default_factory=list)
    champs_perimes: list[str] = Field(default_factory=list)          # sous-ensemble : cause = péremption
    tier_atteint: Optional[Tier] = None            # meilleur tier couvrant (None si non couvert)
    ok: bool

    @model_validator(mode="after")
    def _ok_est_derive(self):
        # G2 : `ok` n'est pas déclaratif, c'est une projection de l'existence de fondations
        attendu = len(self.champs_non_fondables) == 0
        if self.ok != attendu:
            raise ValueError(
                f"{self.dimension}: ok={self.ok} incohérent — "
                f"{len(self.champs_non_fondables)} champ(s) non fondable(s)"
            )
        # cohérence référentielle : les non-fondables sont un sous-ensemble des requis
        inconnus = set(self.champs_non_fondables) - set(self.champs_requis)
        if inconnus:
            raise ValueError(f"{self.dimension}: champs non fondables hors requis: {sorted(inconnus)}")
        # les fondations ne portent que sur des champs requis
        f_inconnus = {g.champ for g in self.fondations} - set(self.champs_requis)
        if f_inconnus:
            raise ValueError(f"{self.dimension}: fondations hors champs requis: {sorted(f_inconnus)}")
        # un champ périmé est un champ NON FONDÉ dont on connaît la cause : hors de l'union, il
        # serait un état orphelin — compté nulle part, donc silencieux.
        hors_union = set(self.champs_perimes) - set(self.champs_non_fondables)
        if hors_union:
            raise ValueError(
                f"{self.dimension}: champs périmés hors des non-fondables: {sorted(hors_union)} — "
                "un champ périmé ne fonde plus, il appartient à l'union"
            )
        # et il ne peut pas être fondé en même temps : les trois états sont EXCLUSIFS
        double = {g.champ for g in self.fondations} & set(self.champs_perimes)
        if double:
            raise ValueError(
                f"{self.dimension}: champ(s) à la fois fondé(s) et périmé(s): {sorted(double)}"
            )
        return self


class BlocCoverage(Strict):
    dimensions: list[DimensionCoverage] = Field(min_length=1)
    bloc_ok: bool                                  # derived: ∧ dimensions.ok

    @model_validator(mode="after")
    def _bloc_ok_est_derive(self):
        attendu = all(d.ok for d in self.dimensions)
        if self.bloc_ok != attendu:
            raise ValueError(f"bloc_ok={self.bloc_ok} incohérent avec les dimensions")
        return self


class Coverage(Strict):
    structuree: BlocCoverage
    qualitative_marche: BlocCoverage

    @model_validator(mode="after")
    def _blocs_attendus(self):
        # verrou : chaque bloc couvre exactement ses dimensions MVDD (§7)
        for bloc, attendu, nom in (
            (self.structuree, _DIMS_STRUCTUREE, "structuree"),
            (self.qualitative_marche, _DIMS_QUALITATIVE, "qualitative_marche"),
        ):
            noms = {d.dimension for d in bloc.dimensions}
            if noms != attendu:
                raise ValueError(f"bloc {nom}: dimensions {sorted(noms)} != attendu {sorted(attendu)}")
        return self


# ─────────────────── comptes & indicateurs (derived, A3) ────────────────────
class EntriesParTier(Strict):
    """DÉRIVÉ : comptes recalculés depuis la KB (même logique que sources_summary du groundedness)."""
    tier_A: int = Field(ge=0)
    tier_B: int = Field(ge=0)
    tier_C_llm_memory: int = Field(ge=0)
    total: int = Field(ge=0)

    @model_validator(mode="after")
    def _somme(self):
        if self.tier_A + self.tier_B + self.tier_C_llm_memory != self.total:
            raise ValueError("total incohérent avec les comptes par tier")
        return self


class IndicateursReadiness(Strict):
    """A3 : trois axes distincts, jamais fusionnés en un score global. Au stade readiness
    (pré-analyse) seul `qualite_info` est formé ; les deux autres sont produits par l'analyse aval."""
    qualite_info: float = Field(ge=0, le=1)        # derived (couverture × tiers)
    conviction: Optional[float] = None             # pending — pas de conviction avant analyse
    marge_securite: Optional[float] = None         # pending — pas de MS avant valorisation


# ─────────────────────────── gaps & incertitudes ────────────────────────────
class GapItem(Strict):
    """DÉRIVÉ : émis pour chaque champ factual non fondable (colonne « Gap si non-fondable » des
    cartes). §7 : 2 sources (curator | gap-intake NL) convergent dans UN pipeline de même schéma.
    `champs_cibles` porte l'option B : le grain champ des manques que ce gap comble (jamais vide)."""
    dimension: str
    champs_cibles: list[str] = Field(min_length=1)   # option B : les champs non fondables visés
    manque: str
    queries_suggerees: list[str] = Field(default_factory=list)
    priorite: Literal["haute", "moyenne", "basse"]
    coverage_actuelle: str
    origine: Literal["curator", "gap_intake"] = "curator"
    # Les DEUX remèdes de la capacité 4, jamais confondus : un champ périmé se RAFRAÎCHIT (il a des
    # entries, il leur manque une date postérieure à l'événement), un champ vide se COLLECTE. Les
    # fusionner ferait payer une recherche complète là où un rafraîchissement suffisait — et
    # inversement, un rafraîchissement lancé sur un champ vide ne rapporterait rien.
    # Défaut `collecte` : un gap venu de `gap_intake` (langage naturel) décrit un manque, pas une
    # péremption — le sens sûr est de collecter, jamais de supposer qu'une entry existe déjà.
    remede: Literal["collecte", "rafraichissement"] = "collecte"


class IncertitudeBloquante(Strict):
    question: str
    impact_si_non_resolu: str
    statut: Literal["resolue", "en_cours", "non_resolvable"]


class IncertitudeInvestissable(Strict):
    question: str
    fourchette: str


# ═══════════════════════════ readiness_report_json ═══════════════════════════
class ReadinessReport(Strict):
    schema_version: Literal["v2.0.0"] = "v2.0.0"
    verdict: ReadinessVerdict                      # SEUL GO/NO-GO — contraint par la coverage (G2)
    coverage: Coverage
    entries_par_tier: EntriesParTier
    indicateurs: IndicateursReadiness
    incertitudes_bloquantes: list[IncertitudeBloquante] = Field(default_factory=list)
    incertitudes_investissables: list[IncertitudeInvestissable] = Field(default_factory=list)
    gaps: list[GapItem] = Field(default_factory=list)
    arret_pareto_recommande: bool = False          # judgment : recommandation curator (impact marginal faible)
    context_pack_entry_id: Optional[int] = None    # entry 'agent_synthesis' réutilisable si ready (§7)
    cause_non_ready: Optional[CauseNonReady] = None  # derived : POURQUOI ce n'est pas livrable
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def _verdict_contraint(self):
        # G2 : `too_hard` (décision, A10) et `researching` (état transitoire de la boucle) ne sont
        # pas des fonctions de la coverage ; les trois autres SONT la projection déterministe (§7).
        if self.verdict not in ("too_hard", "researching"):
            attendu = compute_verdict(self.coverage)
            if self.verdict != attendu:
                raise ValueError(
                    f"verdict={self.verdict} incohérent avec la coverage (attendu {attendu}) — "
                    "un dossier struct-complet mais mince en qualitatif sort thin_qualitative, jamais ready"
                )
        # gate : un verdict non-livrable doit être EXPLIQUÉ (gaps ou incertitude bloquante non résolue)
        non_livrable = self.verdict in ("not_ready", "researching", "thin_qualitative")
        incert_ouverte = any(u.statut != "resolue" for u in self.incertitudes_bloquantes)
        if non_livrable and not self.gaps and not incert_ouverte:
            raise ValueError("verdict non-ready sans gaps[] ni incertitude bloquante non résolue")
        # context_pack front-loadé exigé quand ready (réutilisation research/bull/bear, §7)
        if self.verdict == "ready" and self.context_pack_entry_id is None:
            raise ValueError("verdict=ready exige un context_pack_entry_id (base front-loadée aval)")
        # La cause est DÉRIVÉE de la coverage, comme le verdict : elle n'est jamais déclarée. Un
        # rapport qui pourrait annoncer « lacune » sur un corpus périmé enverrait un mandat de
        # collecte là où un rafraîchissement suffisait — le remède se trompe de cible en silence.
        attendue = compute_cause_non_ready(self.coverage)
        if self.cause_non_ready != attendue:
            raise ValueError(
                f"cause_non_ready={self.cause_non_ready} incohérente avec la coverage "
                f"(attendu {attendue}) — la cause est dérivée, pas déclarée"
            )
        return self

    @model_validator(mode="after")
    def _gaps_couvrent_les_manques(self):
        # Option B : bijection stricte champs_non_fondables <-> gaps (au grain CHAMP). Aucun manque
        # comblable ne reste silencieux ; aucun gap ne cible un champ déjà fondable (travail fantôme).
        # L'arrêt de Pareto se module par `priorite`/`arret_pareto_recommande`, jamais en retirant un gap.
        dims = {d.dimension: d for bloc in (self.coverage.structuree, self.coverage.qualitative_marche)
                for d in bloc.dimensions}
        cibles_par_dim: dict[str, set[str]] = {}
        for g in self.gaps:
            if g.dimension not in dims:
                raise ValueError(f"gap sur dimension inconnue: {g.dimension}")
            orphelins = set(g.champs_cibles) - set(dims[g.dimension].champs_non_fondables)
            if orphelins:
                raise ValueError(
                    f"gap {g.dimension}: champs_cibles hors des non-fondables (travail fantôme): "
                    f"{sorted(orphelins)}"
                )
            cibles_par_dim.setdefault(g.dimension, set()).update(g.champs_cibles)
        # too_hard exempté : le blocage y est une décision (A10), pas un manque comblable par recherche
        # -> il s'exprime en incertitudes_bloquantes[non_resolvable], pas en gap actionnable.
        if self.verdict != "too_hard":
            for nom, d in dims.items():
                non_couverts = set(d.champs_non_fondables) - cibles_par_dim.get(nom, set())
                if non_couverts:
                    raise ValueError(
                        f"champ(s) non fondable(s) sans gap ({nom}): {sorted(non_couverts)} — "
                        "option B : tout manque comblable doit être actionnable"
                    )
        return self


def compute_verdict(coverage: Coverage) -> ReadinessVerdict:
    """Règle de verdict §7 / readiness_derivation.md — recompute déterministe (aucun token LLM).

        ready            ⇔ structuree_ok ∧ qualitative_ok
        thin_qualitative ⇔ structuree_ok ∧ ¬qualitative_ok
        not_ready        ⇔ ¬structuree_ok
    """
    if coverage.structuree.bloc_ok and coverage.qualitative_marche.bloc_ok:
        return "ready"
    if coverage.structuree.bloc_ok:
        return "thin_qualitative"
    return "not_ready"


def _champs(d: Any, clef: str) -> list[str]:
    """Lecture d'une liste de champs, que la dimension soit un modèle validé ou le dict en cours de
    recompute. La cause doit être calculable AVANT validation (le curator la pose sur un dict) ET
    APRÈS (le validateur la revérifie sur le modèle) : deux lectures d'un même état, une seule
    règle — un jumeau côté curator la ferait diverger au premier correctif (#46)."""
    return list(d.get(clef) or []) if isinstance(d, dict) else list(getattr(d, clef) or [])


def compute_cause_non_ready(coverage: Any) -> Optional[CauseNonReady]:
    """Pourquoi le dossier n'est pas livrable — recompute déterministe, aucun token (capacité 4).

        None        ⇔ rien ne manque (le dossier est complet : il n'y a pas de cause à donner)
        peremption  ⇔ tout ce qui manque a des entries, elles sont seulement trop anciennes
        lacune      ⇔ tout ce qui manque n'a aucune entry au plancher
        mixte       ⇔ les deux à la fois — et les DEUX remèdes doivent alors partir

    `mixte` est un état à part entière, pas un fourre-tout : c'est le cas de RVMD (9 lacunes de
    collecte ET des champs périmés). Le replier sur l'une des deux causes ferait disparaître l'autre
    moitié du travail à faire.

    Accepte un `Coverage` validé ou le dict équivalent (cf. `_champs`).
    """
    if isinstance(coverage, dict):
        blocs = [coverage.get("structuree") or {}, coverage.get("qualitative_marche") or {}]
        dims = [d for b in blocs for d in (b.get("dimensions") or []) if isinstance(d, dict)]
    else:
        dims = [d for b in (coverage.structuree, coverage.qualitative_marche) for d in b.dimensions]

    perimes = manques = 0
    for d in dims:
        p = _champs(d, "champs_perimes")
        perimes += len(p)
        manques += len(set(_champs(d, "champs_non_fondables")) - set(p))
    if not perimes and not manques:
        return None
    if perimes and manques:
        return "mixte"
    return "peremption" if perimes else "lacune"
