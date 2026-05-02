import json
import logging
from app.agents.dust_client import DustClient
from app.config import settings

logger = logging.getLogger(__name__)


async def run_sector_pulse(peer_ticker: str, peer_company: str,
                            main_position_ticker: str, peer_m2_data: dict,
                            main_hypotheses: list, dust_client: DustClient) -> dict:
    prompt = f"""Le pair {peer_company} ({peer_ticker}) vient de publier.
Impact sur la thèse de {main_position_ticker} ?

## RÉSULTATS DU PAIR
```json
{json.dumps(peer_m2_data, indent=2, default=str)}
```

## HYPOTHÈSES DE {main_position_ticker}
```json
{json.dumps(main_hypotheses, indent=2)}
```

Règles :
- Réponds UNIQUEMENT sur les hypothèses listées ci-dessus
- Pour chaque hypothèse impactée : direction + 1 phrase de justification
- Score : -5 (très négatif) à +5 (très positif)
- action = "store" si score entre -2 et +2
- action = "escalate_to_regime3" si score ≤ -3

```json
{{
  "peer_ticker":"{peer_ticker}",
  "main_position_ticker":"{main_position_ticker}",
  "peer_result_summary":"1 phrase avec chiffres clés",
  "hypothesis_impacts":{{
    "H2":{{"direction":"positive|negative|neutral","rationale":"..."}}
  }},
  "pulse_score":0,
  "action":"store|escalate_to_regime3",
  "escalation_reason":null
}}
```"""

    result = await dust_client.run_agent(
        agent_id=settings.DUST_PORTFOLIO_AGENT_ID, message=prompt,
        model_override="gemini-2-5-flash-preview", temperature=0.1,
    )
    try:
        c = result["content"]
        j = c.find("```json")
        pulse = json.loads(c[j + 7:c.find("```", j + 7)].strip()) if j >= 0 \
            else json.loads(c[c.find("{"):c.rfind("}") + 1])
        pulse["dust_cost_usd"] = result.get("cost_usd")
        return pulse
    except json.JSONDecodeError:
        return {"peer_ticker": peer_ticker, "action": "store", "pulse_score": 0, "error": "parse_error"}
