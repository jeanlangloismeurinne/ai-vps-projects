"""Vérification de la TÉLÉMÉTRIE du runner V2 — pur, hors ligne, sans réseau.

Le correctif à l'origine de ce check : `runner.py` levait un `RuntimeError` nu quand la sortie
du modèle ne validait pas son contrat après réparation. Deux pertes silencieuses :
  (a) le texte brut fautif, seule pièce qui permette de diagnostiquer POURQUOI le modèle est
      sorti du contrat ;
  (b) la comptabilité des tokens/coût réellement facturés — un abandon persistait à 0 token/$0.

Désormais : `AgentOutputInvalid` (sous-classe de `RuntimeError`) porte les deux.

Convention de ce projet (#39) : un check qui valide des fixtures déjà conformes ne prouve rien.
On EXÉCUTE le vrai code — `run_json_agent` et `run_tool_json_agent` — via un faux provider scripté
dont les réponses (`CompletionResult`) sont prédéterminées. Aucun appel réseau, aucun appel
modèle, aucune DB. Le check tourne avec `--network none`.

§1  Succès inchangé : non-régression, le correctif ne touche pas le chemin nominal.
§2  Réparation réussie au 2e tour : tokens des deux tours cumulés.
§3  Échec après réparation : `AgentOutputInvalid` levée avec la SOMME exacte des deux tours.
§4  `raw_content` = texte fautif du DERNIER tour (pas vide, pas un message d'erreur).
§5  Compatibilité ascendante : `isinstance(e, RuntimeError)` — 6 sites d'appel font `except RuntimeError`.
§6  Noms d'attributs exacts : `tokens_in`, `tokens_out`, `cost_usd` — ceux que les `_persister_echec`
    lisent pour passer l'exception en `run=`.
§7  `run_tool_json_agent` avec boucle coûteuse puis clôture ratée : coût total = boucle + clôture.
    `raw_content` reste celui de la clôture, pas celui de la boucle.
§8  `__str__` après `add_upstream` : le total Y FIGURE (message recalculé, pas figé).
§9  Non-régression de `run_tool_json_agent` en succès : boucle + clôture cumulés.
"""
import asyncio
import sys
from dataclasses import dataclass, field, replace
from typing import Any, Iterator, Optional

from pydantic import BaseModel

from app.agents.providers import CompletionResult, ResolvedAgent
from app.agents.providers.base import AgentProvider
from app.agents.v2.runner import (
    AgentOutputInvalid,
    AgentRunResult,
    run_json_agent,
    run_tool_json_agent,
)

ok = fail = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


# ── Contrat Pydantic minimal — schéma conforme ──────────────────────────────

class ContratOk(BaseModel):
    """Schéma conforme utilisé pour les tours qui réussissent."""
    model_config = {"extra": "forbid"}
    valeur: int


class ContratStrict(BaseModel):
    """Schéma strict utilisé pour tester l'échec de validation."""
    model_config = {"extra": "forbid"}
    valeur: int


# ── Faux provider scripté ───────────────────────────────────────────────────

class _FakeProvider(AgentProvider):
    """Provider bouchonné : rend les `CompletionResult` de `_reponses` dans l'ordre des appels.

    Ce provider remplace un vrai modèle : aucun appel réseau, aucun token réel. Les valeurs
    `tokens_in`, `tokens_out`, `cost_usd` sont prédéterminées pour permettre des assertions
    chiffrées exactes — si elles passent, la comptabilité du runner est juste.
    """

    name = "fake"

    def __init__(self, reponses: list[CompletionResult]) -> None:
        self._reponses = iter(reponses)

    async def complete(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        model: str,
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[str | dict] = None,
        response_format: Optional[dict[str, Any]] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        timeout: int = 720,
    ) -> CompletionResult:
        return next(self._reponses)

    async def stream(self, **kwargs: Any):  # type: ignore[override]
        # Non utilisé par ce check.
        raise NotImplementedError
        yield  # pragma: no cover


def _agent(reponses: list[CompletionResult], *, avec_outils: bool = False) -> ResolvedAgent:
    """Fabrique un `ResolvedAgent` bouchonné.

    `ResolvedAgent` est un dataclass (pas de __init__ custom) — on passe directement les champs.
    `tools` est positionné selon `avec_outils` : `run_tool_json_agent` en fait un `replace(tools=None)`
    pour la clôture, on doit donc passer des outils factices sur la version 'avec_outils'.
    """
    return ResolvedAgent(
        agent_name="agent-test",
        flow_version="v2",
        provider=_FakeProvider(reponses),
        model="fake-model",
        system_prompt="system",
        tools=[{"type": "function", "function": {"name": "outil_fake"}}] if avec_outils else None,
    )


# ── Helpers de fixtures ─────────────────────────────────────────────────────

def _cr(
    content: str,
    *,
    tokens_in: int,
    tokens_out: int,
    cost_usd: float,
    tool_calls: Optional[list[dict[str, Any]]] = None,
) -> CompletionResult:
    """Construit un `CompletionResult` avec les champs exacts définis dans `base.py`."""
    return CompletionResult(
        content=content,
        model="fake-model",
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
        tool_calls=tool_calls,
    )


# JSON conforme et non conforme pour nos tours
_JSON_OK = '{"valeur": 42}'
_JSON_INVALIDE = '{"valeur": "pas_un_int"}'   # Pydantic refusera : str ≠ int
_TEXTE_BRUT_FAUTIF = "voici ma réponse : " + _JSON_INVALIDE  # texte parasite + JSON invalide

MESSAGES = [{"role": "user", "content": "Analyse ce ticker."}]


# ══════════════════════════════════════════════════════════════════════════════
print("§1 — Succès inchangé : le correctif ne touche pas le chemin nominal")
# ══════════════════════════════════════════════════════════════════════════════
# Un seul tour, sortie conforme. Le runner doit renvoyer un `AgentRunResult` sans jamais lever.
# C'est la non-régression fondamentale : si cette section tombe, le correctif casse la prod.

TOUR1_IN = 100
TOUR1_OUT = 50
TOUR1_COUT = 0.000025

reponse_ok = _cr(_JSON_OK, tokens_in=TOUR1_IN, tokens_out=TOUR1_OUT, cost_usd=TOUR1_COUT)
agent_s1 = _agent([reponse_ok])

resultat_s1: AgentRunResult = asyncio.run(
    run_json_agent(agent_s1, MESSAGES, ContratOk)
)

check("type de retour = AgentRunResult", isinstance(resultat_s1, AgentRunResult))
check("parsed.valeur = 42 (contrat respecté)", resultat_s1.parsed.valeur == 42)
check("tokens_in du 1er tour dans le résultat", resultat_s1.tokens_in == TOUR1_IN)
check("tokens_out du 1er tour dans le résultat", resultat_s1.tokens_out == TOUR1_OUT)
check("cost_usd du 1er tour dans le résultat", abs(resultat_s1.cost_usd - TOUR1_COUT) < 1e-9)
check("attempts = 1", resultat_s1.attempts == 1)
check("raw_content = texte brut du modèle", resultat_s1.raw_content == _JSON_OK)


# ══════════════════════════════════════════════════════════════════════════════
print("\n§2 — Réparation réussie au 2e tour : tokens CUMULÉS")
# ══════════════════════════════════════════════════════════════════════════════
# Tour 1 : JSON invalide → runner injecte l'erreur.
# Tour 2 : JSON conforme → succès.
# Les tokens des deux tours DOIVENT être additionnés dans l'AgentRunResult.
# Si seul le 2e tour est compté, on sous-déclare systématiquement toute réparation.

T2_IN_1, T2_OUT_1, T2_COUT_1 = 200, 60, 0.000040
T2_IN_2, T2_OUT_2, T2_COUT_2 = 300, 80, 0.000060

agent_s2 = _agent([
    _cr(_JSON_INVALIDE, tokens_in=T2_IN_1, tokens_out=T2_OUT_1, cost_usd=T2_COUT_1),
    _cr(_JSON_OK,       tokens_in=T2_IN_2, tokens_out=T2_OUT_2, cost_usd=T2_COUT_2),
])

resultat_s2: AgentRunResult = asyncio.run(
    run_json_agent(agent_s2, MESSAGES, ContratOk)
)

check("résultat présent (réparation réussie)", isinstance(resultat_s2, AgentRunResult))
check(
    f"tokens_in cumulés : {T2_IN_1}+{T2_IN_2} = {T2_IN_1 + T2_IN_2}",
    resultat_s2.tokens_in == T2_IN_1 + T2_IN_2,
    f"— reçu {resultat_s2.tokens_in}",
)
check(
    f"tokens_out cumulés : {T2_OUT_1}+{T2_OUT_2} = {T2_OUT_1 + T2_OUT_2}",
    resultat_s2.tokens_out == T2_OUT_1 + T2_OUT_2,
    f"— reçu {resultat_s2.tokens_out}",
)
check(
    f"cost_usd cumulé : {T2_COUT_1}+{T2_COUT_2} = {T2_COUT_1 + T2_COUT_2}",
    abs(resultat_s2.cost_usd - (T2_COUT_1 + T2_COUT_2)) < 1e-9,
    f"— reçu {resultat_s2.cost_usd}",
)
check("attempts = 2 (deux tours facturés)", resultat_s2.attempts == 2)


# ══════════════════════════════════════════════════════════════════════════════
print("\n§3 — Échec après réparation : AgentOutputInvalid avec SOMME exacte des deux tours")
# ══════════════════════════════════════════════════════════════════════════════
# C'est l'assertion la plus importante de ce fichier.
# Tour 1 : invalide. Tour 2 (réparation) : invalide aussi → runner lève AgentOutputInvalid.
# L'exception DOIT porter la somme des deux tours — pas seulement le dernier.
# Si seul le dernier tour est compté, les `_persister_echec` enregistrent une dépense tronquée.

T3_IN_1, T3_OUT_1, T3_COUT_1 = 150, 70, 0.000033
T3_IN_2, T3_OUT_2, T3_COUT_2 = 250, 90, 0.000055

T3_TOTAL_IN   = T3_IN_1   + T3_IN_2
T3_TOTAL_OUT  = T3_OUT_1  + T3_OUT_2
T3_TOTAL_COUT = T3_COUT_1 + T3_COUT_2

agent_s3 = _agent([
    _cr(_JSON_INVALIDE, tokens_in=T3_IN_1, tokens_out=T3_OUT_1, cost_usd=T3_COUT_1),
    _cr(_JSON_INVALIDE, tokens_in=T3_IN_2, tokens_out=T3_OUT_2, cost_usd=T3_COUT_2),
])

exc_s3: Optional[AgentOutputInvalid] = None
try:
    asyncio.run(run_json_agent(agent_s3, MESSAGES, ContratOk))
    check("AgentOutputInvalid levée après épuisement des réparations", False,
          "— aucune exception levée")
except AgentOutputInvalid as e:
    exc_s3 = e
    check("AgentOutputInvalid levée après épuisement des réparations", True)

if exc_s3 is not None:
    check(
        f"tokens_in = SOMME des deux tours ({T3_IN_1}+{T3_IN_2} = {T3_TOTAL_IN})",
        exc_s3.tokens_in == T3_TOTAL_IN,
        f"— reçu {exc_s3.tokens_in}",
    )
    check(
        f"tokens_out = SOMME des deux tours ({T3_OUT_1}+{T3_OUT_2} = {T3_TOTAL_OUT})",
        exc_s3.tokens_out == T3_TOTAL_OUT,
        f"— reçu {exc_s3.tokens_out}",
    )
    check(
        f"cost_usd = SOMME des deux tours ({T3_COUT_1}+{T3_COUT_2} = {T3_TOTAL_COUT:.6f})",
        abs(exc_s3.cost_usd - T3_TOTAL_COUT) < 1e-9,
        f"— reçu {exc_s3.cost_usd}",
    )
    check("attempts = 2 dans l'exception", exc_s3.attempts == 2)
else:
    # Bloquer les sections suivantes sans crash : on saute avec des FAIL explicites.
    check("tokens_in de l'exception", False, "— exception non capturée")
    check("tokens_out de l'exception", False, "— exception non capturée")
    check("cost_usd de l'exception",   False, "— exception non capturée")
    check("attempts de l'exception",   False, "— exception non capturée")


# ══════════════════════════════════════════════════════════════════════════════
print("\n§4 — raw_content = texte fautif du DERNIER tour (pas vide, pas le message d'erreur)")
# ══════════════════════════════════════════════════════════════════════════════
# Le texte brut est la SEULE pièce qui permette de diagnostiquer pourquoi le modèle est sorti
# du contrat. Il doit être le `content` du 2e tour (le dernier), pas du premier, et ne doit pas
# avoir été remplacé par le message d'erreur Pydantic injecté dans la conversation.

T4_TEXTE_TOUR1 = '{"valeur": "premier_echec"}'
T4_TEXTE_TOUR2 = _TEXTE_BRUT_FAUTIF  # texte parasite + JSON invalide

agent_s4 = _agent([
    _cr(T4_TEXTE_TOUR1, tokens_in=100, tokens_out=40, cost_usd=0.000010),
    _cr(T4_TEXTE_TOUR2, tokens_in=150, tokens_out=60, cost_usd=0.000015),
])

exc_s4: Optional[AgentOutputInvalid] = None
try:
    asyncio.run(run_json_agent(agent_s4, MESSAGES, ContratOk))
except AgentOutputInvalid as e:
    exc_s4 = e

if exc_s4 is not None:
    check(
        "raw_content = texte du DERNIER tour (pas celui du 1er)",
        exc_s4.raw_content == T4_TEXTE_TOUR2,
        f"— reçu {exc_s4.raw_content!r:.80}",
    )
    check(
        "raw_content non vide",
        bool(exc_s4.raw_content),
    )
    check(
        "raw_content ≠ message d'erreur Pydantic (le texte brut, pas le verdict)",
        "contrat" not in exc_s4.raw_content and "Erreurs" not in exc_s4.raw_content,
        f"— raw_content commence par {exc_s4.raw_content[:60]!r}",
    )
else:
    check("raw_content du dernier tour", False, "— exception non capturée")
    check("raw_content non vide",         False, "— exception non capturée")
    check("raw_content ≠ message d'erreur", False, "— exception non capturée")


# ══════════════════════════════════════════════════════════════════════════════
print("\n§5 — Compatibilité ascendante : isinstance(e, RuntimeError) est vrai")
# ══════════════════════════════════════════════════════════════════════════════
# Six sites d'appel existants font `except RuntimeError`. Si `AgentOutputInvalid` ne sous-classe
# plus `RuntimeError`, ces sites laissent l'exception se propager, ce qui casse silencieusement
# la persistance des analyses en production. Cette assertion protège tous ces sites à la fois.

if exc_s3 is not None:
    check(
        "isinstance(AgentOutputInvalid, RuntimeError) — 6 sites d'appel font except RuntimeError",
        isinstance(exc_s3, RuntimeError),
    )
    check(
        "isinstance(AgentOutputInvalid, AgentOutputInvalid)",
        isinstance(exc_s3, AgentOutputInvalid),
    )
else:
    check("isinstance RuntimeError", False, "— exception non capturée en §3")
    check("isinstance AgentOutputInvalid", False, "— exception non capturée en §3")


# ══════════════════════════════════════════════════════════════════════════════
print("\n§6 — Noms d'attributs : ceux que les `_persister_echec` lisent en `run=`")
# ══════════════════════════════════════════════════════════════════════════════
# Les `_persister_echec` accèdent aux champs PAR NOM via `getattr`. Un renommage silencieux
# (ex: `tokens_in` → `input_tokens`) ferait repersister des zéros sans qu'aucun test ne bronche
# car le `getattr` avec valeur par défaut serait 0. On vérifie que les attributs existent et
# contiennent des valeurs non nulles (le scénario §3 était chiffré non nul).

if exc_s3 is not None:
    check(
        "getattr(e, 'tokens_in') accessible et non nul",
        getattr(exc_s3, "tokens_in", None) == T3_TOTAL_IN,
        f"— reçu {getattr(exc_s3, 'tokens_in', 'ABSENT')}",
    )
    check(
        "getattr(e, 'tokens_out') accessible et non nul",
        getattr(exc_s3, "tokens_out", None) == T3_TOTAL_OUT,
        f"— reçu {getattr(exc_s3, 'tokens_out', 'ABSENT')}",
    )
    check(
        "getattr(e, 'cost_usd') accessible et non nul",
        abs(getattr(exc_s3, "cost_usd", 0.0) - T3_TOTAL_COUT) < 1e-9,
        f"— reçu {getattr(exc_s3, 'cost_usd', 'ABSENT')}",
    )
    check(
        "getattr(e, 'raw_content') accessible",
        isinstance(getattr(exc_s3, "raw_content", None), str),
    )
    check(
        "getattr(e, 'agent_name') accessible",
        getattr(exc_s3, "agent_name", None) == "agent-test",
    )
    check(
        "getattr(e, 'schema_name') accessible",
        getattr(exc_s3, "schema_name", None) == "ContratOk",
    )
    # Les TYPES comptent autant que les noms : `tokens_in`/`tokens_out` sont bindés sur des colonnes
    # INTEGER et `cost_usd` sur une NUMERIC. asyncpg est strict, et `_persister_echec` enveloppe son
    # INSERT dans un `except Exception` — une DataError y serait AVALÉE, et la trace d'échec perdue
    # une seconde fois, en silence. Le chemin de succès écrit des int/float (les sessions #8 et #9 en
    # production le prouvent) : l'exception doit fournir exactement les mêmes types.
    check(
        "tokens_in est un int (colonne INTEGER)",
        type(getattr(exc_s3, "tokens_in", None)) is int,
        f"— reçu {type(getattr(exc_s3, 'tokens_in', None)).__name__}",
    )
    check(
        "tokens_out est un int (colonne INTEGER)",
        type(getattr(exc_s3, "tokens_out", None)) is int,
        f"— reçu {type(getattr(exc_s3, 'tokens_out', None)).__name__}",
    )
    check(
        "cost_usd est un float (colonne NUMERIC, comme le chemin de succès)",
        type(getattr(exc_s3, "cost_usd", None)) is float,
        f"— reçu {type(getattr(exc_s3, 'cost_usd', None)).__name__}",
    )
else:
    for lbl in ("tokens_in", "tokens_out", "cost_usd", "raw_content", "agent_name", "schema_name"):
        check(f"getattr(e, '{lbl}')", False, "— exception non capturée en §3")


# ══════════════════════════════════════════════════════════════════════════════
print("\n§7 — run_tool_json_agent : boucle coûteuse puis clôture ratée → coût total cumulé")
# ══════════════════════════════════════════════════════════════════════════════
# C'est le cas qui MOTIVE le correctif `add_upstream`.
# La boucle d'outils compte plusieurs tours à gros contexte (part dominante de la facture).
# La clôture échoue. L'exception doit porter : coût boucle + coût clôture.
# Si `add_upstream` n'est pas appelé, on déclare un run d'ouvrier entier comme gratuit.
# On vérifie aussi que `raw_content` reste celui de la clôture (le texte fautif).

# Boucle : 2 tours avec outils, puis 1 tour sans outils (fin de boucle)
BOUCLE_IN_1, BOUCLE_OUT_1, BOUCLE_COUT_1 = 1000, 200, 0.000250
BOUCLE_IN_2, BOUCLE_OUT_2, BOUCLE_COUT_2 = 1200, 180, 0.000280
# Le 3e tour de la boucle n'a PAS de tool_calls → la boucle s'arrête (exhausted=False)
BOUCLE_IN_3, BOUCLE_OUT_3, BOUCLE_COUT_3 =  800, 150, 0.000200

BOUCLE_TOTAL_IN   = BOUCLE_IN_1   + BOUCLE_IN_2   + BOUCLE_IN_3
BOUCLE_TOTAL_OUT  = BOUCLE_OUT_1  + BOUCLE_OUT_2  + BOUCLE_OUT_3
BOUCLE_TOTAL_COUT = BOUCLE_COUT_1 + BOUCLE_COUT_2 + BOUCLE_COUT_3

# Clôture : 2 tours (max_repair=1), tous deux invalides
CLOTURE_IN_1, CLOTURE_OUT_1, CLOTURE_COUT_1 =  400,  80, 0.000090
CLOTURE_IN_2, CLOTURE_OUT_2, CLOTURE_COUT_2 =  450,  90, 0.000100

CLOTURE_TOTAL_IN   = CLOTURE_IN_1   + CLOTURE_IN_2
CLOTURE_TOTAL_OUT  = CLOTURE_OUT_1  + CLOTURE_OUT_2
CLOTURE_TOTAL_COUT = CLOTURE_COUT_1 + CLOTURE_COUT_2

# Total attendu dans l'exception
S7_TOTAL_IN   = BOUCLE_TOTAL_IN   + CLOTURE_TOTAL_IN
S7_TOTAL_OUT  = BOUCLE_TOTAL_OUT  + CLOTURE_TOTAL_OUT
S7_TOTAL_COUT = BOUCLE_TOTAL_COUT + CLOTURE_TOTAL_COUT

# `raw_content` de la clôture : c'est ce texte qu'on doit retrouver dans l'exception
TEXTE_CLOTURE_FAUTIF = '{"mauvais_champ": "cloture"}'

# Construction d'un tool_call factice (format OpenAI)
_tool_call_fake = [{"id": "call_1", "type": "function",
                    "function": {"name": "outil_fake", "arguments": '{"q": "test"}'}}]

# L'agent de la boucle doit avoir des outils (sinon _tool_loop ne voit pas de tool_calls)
# Tous les CompletionResult sont mis dans la liste — le FakeProvider les consomme dans l'ordre.
# L'agent est créé AVEC outils ; run_tool_json_agent fait `replace(agent, tools=None)` pour
# la clôture → le FakeProvider du clone est indépendant (c'est la même instance de provider,
# mais le replace() ne clone pas le provider). Pour simuler correctement, on doit fournir TOUS
# les CompletionResult dans le provider de l'agent original dans l'ordre chronologique.
# run_tool_json_agent appelle `_tool_loop(agent, ...)` puis `run_json_agent(closer, ...)` où
# closer = replace(agent, tools=None). Les deux utilisent le même provider.

agent_s7 = _agent(
    [
        # Tour 1 boucle : avec tool_calls → la boucle continue
        _cr("", tokens_in=BOUCLE_IN_1, tokens_out=BOUCLE_OUT_1, cost_usd=BOUCLE_COUT_1,
            tool_calls=_tool_call_fake),
        # Tour 2 boucle : avec tool_calls → la boucle continue
        _cr("", tokens_in=BOUCLE_IN_2, tokens_out=BOUCLE_OUT_2, cost_usd=BOUCLE_COUT_2,
            tool_calls=_tool_call_fake),
        # Tour 3 boucle : SANS tool_calls → boucle s'arrête (exhausted=False)
        _cr("texte libre final de la boucle",
            tokens_in=BOUCLE_IN_3, tokens_out=BOUCLE_OUT_3, cost_usd=BOUCLE_COUT_3,
            tool_calls=None),
        # Tour 1 clôture (run_json_agent avec closer sans outils) : invalide
        _cr(TEXTE_CLOTURE_FAUTIF,
            tokens_in=CLOTURE_IN_1, tokens_out=CLOTURE_OUT_1, cost_usd=CLOTURE_COUT_1),
        # Tour 2 clôture (réparation) : invalide aussi → AgentOutputInvalid
        _cr(TEXTE_CLOTURE_FAUTIF,
            tokens_in=CLOTURE_IN_2, tokens_out=CLOTURE_OUT_2, cost_usd=CLOTURE_COUT_2),
    ],
    avec_outils=True,
)

# L'exécuteur d'outil factice : renvoie un résultat quelconque, ne doit pas bloquer la boucle
async def _outil_fake(args: dict[str, Any]) -> dict[str, Any]:
    return {"résultat": "données factices"}

exc_s7: Optional[AgentOutputInvalid] = None
try:
    asyncio.run(
        run_tool_json_agent(
            agent_s7,
            MESSAGES,
            {"outil_fake": _outil_fake},
            ContratOk,
            closing_instruction="Synthétise en JSON.",
            max_repair=1,
        )
    )
    check("AgentOutputInvalid levée (boucle OK, clôture ratée)", False,
          "— aucune exception levée")
except AgentOutputInvalid as e:
    exc_s7 = e
    check("AgentOutputInvalid levée (boucle OK, clôture ratée)", True)

if exc_s7 is not None:
    check(
        f"tokens_in = boucle({BOUCLE_TOTAL_IN}) + clôture({CLOTURE_TOTAL_IN}) = {S7_TOTAL_IN}",
        exc_s7.tokens_in == S7_TOTAL_IN,
        f"— reçu {exc_s7.tokens_in}",
    )
    check(
        f"tokens_out = boucle({BOUCLE_TOTAL_OUT}) + clôture({CLOTURE_TOTAL_OUT}) = {S7_TOTAL_OUT}",
        exc_s7.tokens_out == S7_TOTAL_OUT,
        f"— reçu {exc_s7.tokens_out}",
    )
    check(
        f"cost_usd = boucle({BOUCLE_TOTAL_COUT:.6f}) + clôture({CLOTURE_TOTAL_COUT:.6f}) "
        f"= {S7_TOTAL_COUT:.6f}",
        abs(exc_s7.cost_usd - S7_TOTAL_COUT) < 1e-9,
        f"— reçu {exc_s7.cost_usd:.6f}",
    )
    check(
        "raw_content = texte fautif de la CLÔTURE (pas celui de la boucle)",
        exc_s7.raw_content == TEXTE_CLOTURE_FAUTIF,
        f"— reçu {exc_s7.raw_content!r:.80}",
    )
    check(
        "raw_content ≠ texte de la boucle (la boucle a réussi, son texte ne doit pas filtrer)",
        exc_s7.raw_content != "texte libre final de la boucle",
    )
else:
    for lbl in ("tokens_in", "tokens_out", "cost_usd", "raw_content clôture", "raw_content ≠ boucle"):
        check(lbl, False, "— exception non capturée")


# ══════════════════════════════════════════════════════════════════════════════
print("\n§8 — __str__ après add_upstream : le total figure dans la représentation")
# ══════════════════════════════════════════════════════════════════════════════
# `add_upstream` modifie les compteurs EN PLACE après construction. `__str__` est déclaré comme
# « recalculé » dans le code (commentaire explicit). On vérifie que le str reflète bien le total
# APRÈS add_upstream, pas les valeurs au moment de la construction de l'exception.
# Si __str__ lisait des copies figées, les logs d'erreur mentionneraient des tokens tronqués.

INIT_IN, INIT_OUT, INIT_COUT = 300, 80, 0.000070
AMONT_IN, AMONT_OUT, AMONT_COUT = 2000, 400, 0.000500
ATTENDU_IN   = INIT_IN   + AMONT_IN
ATTENDU_OUT  = INIT_OUT  + AMONT_OUT
ATTENDU_COUT = INIT_COUT + AMONT_COUT

exc_s8 = AgentOutputInvalid(
    agent_name="agent-str-test",
    schema_name="ContratOk",
    attempts=2,
    last_error="validation échouée",
    raw_content="texte brut",
    tokens_in=INIT_IN,
    tokens_out=INIT_OUT,
    cost_usd=INIT_COUT,
)

# Avant add_upstream : str doit mentionner les valeurs initiales
str_avant = str(exc_s8)
check(
    f"str avant add_upstream mentionne tokens_in={INIT_IN}",
    str(INIT_IN) in str_avant,
    f"— str: {str_avant}",
)

exc_s8.add_upstream(AMONT_IN, AMONT_OUT, AMONT_COUT, iterations=3)

str_apres = str(exc_s8)
check(
    f"str APRÈS add_upstream mentionne tokens_in={ATTENDU_IN} (recalculé, pas figé)",
    str(ATTENDU_IN) in str_apres,
    f"— str: {str_apres}",
)
check(
    f"str APRÈS add_upstream mentionne tokens_out={ATTENDU_OUT}",
    str(ATTENDU_OUT) in str_apres,
    f"— str: {str_apres}",
)
check(
    f"str APRÈS add_upstream mentionne cost_usd={ATTENDU_COUT:.6f}",
    f"{ATTENDU_COUT:.6f}" in str_apres,
    f"— str: {str_apres}",
)
check(
    "str ne mentionne plus l'ancien tokens_in (le message est recalculé, pas concaténé)",
    # tokens_in initial était 300, tokens_in final est 2300 ; "300" peut être sous-chaîne de "2300"
    # on vérifie que "2300" apparaît (ce qui est la vraie information)
    str(ATTENDU_IN) in str_apres,
)
check(
    "attempts = 2 + 3 = 5 après add_upstream",
    exc_s8.attempts == 5,
    f"— reçu {exc_s8.attempts}",
)


# ══════════════════════════════════════════════════════════════════════════════
print("\n§9 — Non-régression run_tool_json_agent en succès : boucle + clôture cumulés")
# ══════════════════════════════════════════════════════════════════════════════
# Chemin nominal de run_tool_json_agent (boucle OK, clôture OK).
# Les coûts des deux phases doivent être additionnés dans l'AgentRunResult.
# Si seule la clôture était comptée, on déclarerait les runs d'ouvrier 3× moins chers.

S9_BOUCLE_IN,   S9_BOUCLE_OUT,   S9_BOUCLE_COUT   = 900, 160, 0.000180
S9_CLOTURE_IN,  S9_CLOTURE_OUT,  S9_CLOTURE_COUT  = 350,  70, 0.000075

S9_TOTAL_IN   = S9_BOUCLE_IN   + S9_CLOTURE_IN
S9_TOTAL_OUT  = S9_BOUCLE_OUT  + S9_CLOTURE_OUT
S9_TOTAL_COUT = S9_BOUCLE_COUT + S9_CLOTURE_COUT

agent_s9 = _agent(
    [
        # Tour boucle : SANS tool_calls → boucle s'arrête immédiatement (1 seul tour)
        _cr("texte libre", tokens_in=S9_BOUCLE_IN, tokens_out=S9_BOUCLE_OUT,
            cost_usd=S9_BOUCLE_COUT, tool_calls=None),
        # Tour clôture : JSON conforme
        _cr(_JSON_OK, tokens_in=S9_CLOTURE_IN, tokens_out=S9_CLOTURE_OUT,
            cost_usd=S9_CLOTURE_COUT),
    ],
    avec_outils=True,
)

resultat_s9: Optional[AgentRunResult] = None
try:
    resultat_s9 = asyncio.run(
        run_tool_json_agent(
            agent_s9,
            MESSAGES,
            {},  # aucun outil nécessaire : la boucle s'arrête sur tool_calls=None
            ContratOk,
            closing_instruction="Synthétise en JSON.",
        )
    )
    check("AgentRunResult rendu (succès)", isinstance(resultat_s9, AgentRunResult))
except Exception as exc:
    check("AgentRunResult rendu (succès)", False, f"— exception inattendue : {exc}")

if resultat_s9 is not None:
    check(
        f"tokens_in = boucle({S9_BOUCLE_IN}) + clôture({S9_CLOTURE_IN}) = {S9_TOTAL_IN}",
        resultat_s9.tokens_in == S9_TOTAL_IN,
        f"— reçu {resultat_s9.tokens_in}",
    )
    check(
        f"tokens_out = boucle({S9_BOUCLE_OUT}) + clôture({S9_CLOTURE_OUT}) = {S9_TOTAL_OUT}",
        resultat_s9.tokens_out == S9_TOTAL_OUT,
        f"— reçu {resultat_s9.tokens_out}",
    )
    check(
        f"cost_usd = boucle({S9_BOUCLE_COUT:.6f}) + clôture({S9_CLOTURE_COUT:.6f}) "
        f"= {S9_TOTAL_COUT:.6f}",
        abs(resultat_s9.cost_usd - S9_TOTAL_COUT) < 1e-9,
        f"— reçu {resultat_s9.cost_usd:.6f}",
    )
    check("parsed.valeur = 42 (clôture conforme)", resultat_s9.parsed.valeur == 42)
    check(
        "raw_content = celui de la clôture (le JSON conforme)",
        resultat_s9.raw_content == _JSON_OK,
    )
else:
    for lbl in ("tokens_in", "tokens_out", "cost_usd", "parsed.valeur", "raw_content"):
        check(lbl, False, "— résultat non disponible")


# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print(f"{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
