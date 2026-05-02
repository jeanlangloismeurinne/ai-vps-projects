import json
import logging

logger = logging.getLogger(__name__)

QUERY_TEMPLATES = {
    "post_earnings": [
        "{company} Q{quarter} {year} results revenue organic growth",
        "{company} {year} guidance outlook management CEO comments",
        "{company} analyst rating target price {month} {year}",
        "{company} {peer1} IT services sector comparison {quarter} {year}",
    ],
    "post_cmd": [
        "{company} capital markets day {year} targets guidance",
        "{company} medium term plan {year} organic growth margin",
    ],
    "ma_announcement": [
        "{company} acquisition {target} strategic rationale {year}",
        "{company} {target} synergies integration timeline",
    ],
}

M3_PROMPT = """Tu es un extracteur de données financières.
Pour chaque requête, effectue la recherche web et extrait UNIQUEMENT
les faits chiffrés et citations directes. Ne synthétise pas.

Format JSON UNIQUEMENT :
{"results": [{"query":"...","source_url":"...","publication_date":"YYYY-MM-DD",
"extracted_facts":[{"type":"number|quote|guidance","content":"...","context":"..."}]}]}"""


async def collect_m3(ticker: str, company_name: str, event_type: str,
                     context: dict, dust_client) -> dict:
    template = QUERY_TEMPLATES.get(event_type, QUERY_TEMPLATES["post_earnings"])
    queries = []
    for q in template:
        try:
            queries.append(q.format(company=company_name, ticker=ticker, **context))
        except KeyError as e:
            queries.append(q.replace("{" + str(e).strip("'") + "}", ""))

    from app.config import settings
    result = await dust_client.run_agent(
        agent_id=settings.DUST_PORTFOLIO_AGENT_ID,
        message=f"Société : {company_name} ({ticker})\nÉvénement : {event_type}\n\n"
                f"Requêtes :\n" + "\n".join(f"- {q}" for q in queries) + f"\n\n{M3_PROMPT}",
        model_override="gemini-2-5-flash-preview",
        temperature=0.1,
    )
    try:
        return json.loads(result["content"])
    except json.JSONDecodeError:
        return {"results": [], "error": "parse_error"}
