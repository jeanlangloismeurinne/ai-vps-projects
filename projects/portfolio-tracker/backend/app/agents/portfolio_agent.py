import json
import logging
from app.agents.dust_client import DustClient
from app.config import settings

logger = logging.getLogger(__name__)


# ── PRÉ-EVENT BRIEF (J-2) ────────────────────────────────────────────────────

async def run_pre_event_brief(ticker: str, company_name: str, hypotheses: list,
                               event_type: str, guidance_published: dict,
                               dust_client: DustClient) -> dict:
    prompt = f"""Demain : publication {event_type} pour {company_name} ({ticker}).

HYPOTHÈSES ACTIVES :
{json.dumps(hypotheses, indent=2)}

GUIDANCE PUBLIÉE (si dispo) :
{json.dumps(guidance_published, indent=2)}

Produis un brief de lecture JSON (3 items max dans reading_checklist) :
{{
  "event":"{event_type}","ticker":"{ticker}",
  "reading_checklist":[
    {{"hypothesis_code":"H1","what_to_look_for":"...",
      "confirmation_signal":"...","alert_signal":"..."}}
  ],
  "ignore_completely":["cours à l'ouverture","commentaires analystes premières heures"],
  "key_numbers_to_find":["..."]
}}
JSON uniquement."""

    result = await dust_client.run_agent(
        agent_id=settings.DUST_PORTFOLIO_AGENT_ID, message=prompt,
        model_override="gpt-4o-mini", temperature=0.1,
    )
    try:
        c = result["content"]
        return json.loads(c[c.find("{"):c.rfind("}") + 1])
    except Exception:
        return {"error": "parse_error"}


# ── RÉGIME 2 ─────────────────────────────────────────────────────────────────

async def run_regime_2(ticker: str, company_name: str, data_brief: dict,
                       dust_client: DustClient) -> dict:
    prompt = f"""Tu exécutes la revue trimestrielle de {company_name} ({ticker}).

## DATA BRIEF
```json
{json.dumps(data_brief, indent=2, default=str)}
```

## INSTRUCTIONS
Pour chaque hypothèse dans active_thesis.hypotheses :
- Statut : "confirmed" | "neutral" | "alert" | "invalidated"
- Justification en 1 phrase avec fait chiffré

Règles d'escalade :
- 1 hypothèse critique "invalidated" → flag = "REVIEW_REQUIRED"
- 2 hypothèses (quelle criticité) "alert" → flag = "REVIEW_REQUIRED"
- Sinon → flag = "RAS"

```json
{{
  "ticker":"{ticker}","review_date":"ISO","regime":2,
  "hypotheses_scores":[
    {{"code":"H1","status":"confirmed|neutral|alert|invalidated","evidence":"1 phrase"}}
  ],
  "kpis_observed":{{
    "organic_growth_cc_pct":null,"operating_margin_pct":null,
    "guidance_vs_consensus":"above|inline|below|maintained|raised|cut"
  }},
  "sector_context":"1 phrase sur les pairs",
  "flag":"RAS|REVIEW_REQUIRED","escalation_reason":null,
  "recommendation":"maintain|reinforce|reduce_25|reduce_50|exit",
  "alert_level":"green|orange|red"
}}
```"""

    result = await dust_client.run_agent(
        agent_id=settings.DUST_PORTFOLIO_AGENT_ID, message=prompt,
        model_override="gemini-2-5-flash-preview", temperature=0.1,
    )
    try:
        c = result["content"]
        j = c.find("```json")
        parsed = json.loads(c[j + 7:c.find("```", j + 7)].strip()) if j >= 0 \
            else json.loads(c[c.find("{"):c.rfind("}") + 1])
        parsed["dust_conversation_id"] = result.get("conversation_id")
        return parsed
    except json.JSONDecodeError:
        return {"error": "parse_error", "flag": "REVIEW_REQUIRED",
                "escalation_reason": "parse_error_requires_manual_review",
                "dust_conversation_id": result.get("conversation_id")}


# ── RÉGIME 3 ─────────────────────────────────────────────────────────────────

async def run_regime_3(ticker: str, company_name: str, data_brief: dict,
                       position_context: dict, deviation_trigger: dict,
                       dust_client: DustClient) -> dict:
    current_price = position_context.get("current_price", "?")
    prompt = f"""Tu es gestionnaire de portefeuille. Décision requise — {company_name} ({ticker}).

## CONTEXTE DE POSITION
```json
{json.dumps(position_context, indent=2, default=str)}
```

## DÉCLENCHEUR DE L'ESCALADE
```json
{json.dumps(deviation_trigger, indent=2)}
```

## DATA BRIEF COMPLET (avec M3 qualitatif)
```json
{json.dumps(data_brief, indent=2, default=str)}
```

## PROCESSUS EN 3 ÉTAPES OBLIGATOIRES

### ÉTAPE 1 — DIAGNOSTIC
Écart structurel (change la thèse) ou conjoncturel (bruit) ? 3-5 phrases avec faits.

### ÉTAPE 2 — RÉVISION DE LA THÈSE
Si positif : scénarios à réviser ? Cible à repousser ?
Si négatif : quelle hypothèse est compromise ? La thèse tient-elle encore ?

TEST DE MUNGER (OBLIGATOIRE) :
"En faisant abstraction de ma position, achèterais-je ce titre
aujourd'hui à {current_price} ?" → OUI ou NON + 2 phrases de justification.

### ÉTAPE 3 — DÉCISION
reinforce | maintain | reduce_25 | reduce_50 | exit — 3-4 phrases de justification.

```json
{{
  "ticker":"{ticker}","review_date":"ISO","regime":3,
  "deviation_type":"positive|negative",
  "diagnosis":{{"nature":"structural|cyclical","explanation":"..."}},
  "thesis_revision":{{
    "strength_change":"stronger|unchanged|weaker|invalidated",
    "revised_scenarios":null,"hypotheses_updated":[]
  }},
  "munger_test":{{"answer":"yes|no","rationale":"..."}},
  "decision":{{
    "recommendation":"reinforce|maintain|reduce_25|reduce_50|exit",
    "rationale":"...","urgency":"immediate|next_session|week"
  }},
  "updated_thresholds":{{"partial_exit_zone1":null,"partial_exit_zone2":null}},
  "alert_level":"green|orange|red"
}}
```"""

    result = await dust_client.run_agent(
        agent_id=settings.DUST_PORTFOLIO_AGENT_ID, message=prompt,
        model_override="claude-sonnet-4-5", temperature=0.2, timeout=180,
    )
    try:
        c = result["content"]
        j = c.find("```json")
        parsed = json.loads(c[j + 7:c.find("```", j + 7)].strip()) if j >= 0 \
            else json.loads(c[c.find("{"):c.rfind("}") + 1])
        parsed["dust_conversation_id"] = result.get("conversation_id")
        return parsed
    except json.JSONDecodeError as e:
        logger.error(f"Regime 3 parse error {ticker}: {e}")
        return {"error": "parse_error", "raw_content": result["content"][:1000],
                "dust_conversation_id": result.get("conversation_id")}
