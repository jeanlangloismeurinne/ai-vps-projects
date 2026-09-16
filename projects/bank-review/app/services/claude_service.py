import anthropic
import pandas as pd
import os
import logging

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"


def df_to_text(df: pd.DataFrame, max_rows: int = 200) -> str:
    """Convert dataframe to a compact text representation for Claude."""
    sample = df.head(max_rows)
    return sample.to_csv(index=False)


async def analyze_transactions(df: pd.DataFrame, question: str | None = None) -> str:
    """Send banking data to Claude and return analysis."""
    data_text = df_to_text(df)
    total = len(df)
    shown = min(total, 200)

    prompt = f"""Tu es un expert en analyse financière. Voici des données d'activité bancaire ({shown} lignes sur {total} au total).

```csv
{data_text}
```

{"Question spécifique : " + question if question else "Fais une analyse complète : résumé des flux, catégories de dépenses, tendances notables, anomalies éventuelles."}
"""

    system = "Tu analyses des relevés bancaires. Réponds en français, de façon structurée et claire."
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception as e:
        # Claude indisponible → repli DeepInfra.
        logger.warning("Claude indisponible (%s) — analyse via DeepInfra", e)
        from app.services.llm import deepinfra_complete
        return await deepinfra_complete(system=system, user=prompt, max_tokens=2048)
