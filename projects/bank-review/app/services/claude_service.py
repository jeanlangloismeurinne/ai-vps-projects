import anthropic
import pandas as pd
import os

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

    message = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system="Tu analyses des relevés bancaires. Réponds en français, de façon structurée et claire.",
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text
