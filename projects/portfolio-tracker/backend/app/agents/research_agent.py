import json
import logging
from app.agents.dust_client import DustClient
from app.config import settings

logger = logging.getLogger(__name__)

RESEARCH_PROMPT = """Tu es un expert en investissement long terme (horizon 3-15 ans).
Construis une thèse d'investissement complète pour {company_name} ({ticker}).

## DONNÉES

### Data Brief :
```json
{data_brief}
```

### Schéma sectoriel :
```json
{sector_schema}
```

## PROCESSUS EN 8 ÉTAPES OBLIGATOIRES

### ÉTAPE 1 — PRÉ-QUALIFICATION
Si moins de 3 critères sur 5, retourner uniquement {{"prequalification":"failed","reasons":[]}}.
Critères : 1/ PER NTM < 20x OU FCF Yield > 5% ; 2/ Leader sectoriel ou position défendable ;
3/ Catalyseur identifiable à 6-18 mois ; 4/ FCF positif 2 derniers exercices ; 5/ Dette nette < 4x EBITDA.

### ÉTAPE 2 — ANALYSE FONDAMENTALE
Trajectoire CA 3 ans, marges, bilan, track record management, politique retour actionnaires.

### ÉTAPE 3 — ANALYSE CONCURRENTIELLE
Positionnement vs. 4-6 peers, écarts de valorisation, dynamiques sectorielles, moat.

### ÉTAPE 4 — EQUITY PITCH M&A (si acquisition centrale à la thèse)
Terms, logique stratégique, accrétion EPS, synergies réalistes, risques intégration.

### ÉTAPE 5 — SCÉNARIOS ET RENDEMENTS (Bear / Central / Bull, horizon 5 ans)
Pour chaque scénario : EPS CAGR, multiple de sortie, prix cible, dividendes cumulés, CAGR total.
Comparer avec CAC40/S&P500 long terme (~9%/an).

### ÉTAPE 6 — HYPOTHÈSES FONDATRICES (H1 à H7 maximum)
Pour chaque hypothèse : code, label court, description, criticité (critical/important/secondary),
horizon de vérification, KPI à surveiller, seuil de confirmation, seuil d'alerte.

### ÉTAPE 7 — TRACK RECORD ANALYSTES
Recommandations actuelles, évolution récente 12 mois, timing (laggard / en avance),
pondération recommandée (high/medium/low).

### ÉTAPE 8 — AVOCAT DU DIABLE (OBLIGATOIRE — ne pas adoucir)
Les 3 risques structurels les plus sérieux avec les MÊMES données.
Ne pas équilibrer, ne pas atténuer. Conclure avec prix baissier chiffré sur 5 ans.

## FORMAT DE SORTIE — JSON ENTRE ```json et ``` UNIQUEMENT

```json
{{
  "ticker": "...", "company_name": "...", "prequalification": "passed",
  "thesis_one_liner": "...",
  "fundamental_analysis": {{}},
  "competitive_analysis": {{}},
  "ma_equity_pitch": {{}},
  "scenarios": {{
    "bear":    {{"eps_cagr_pct":0,"exit_pe":0,"price_target_5y":0,"dividends_cumulated":0,"cagr_pct":0}},
    "central": {{"eps_cagr_pct":0,"exit_pe":0,"price_target_5y":0,"dividends_cumulated":0,"cagr_pct":0}},
    "bull":    {{"eps_cagr_pct":0,"exit_pe":0,"price_target_5y":0,"dividends_cumulated":0,"cagr_pct":0}}
  }},
  "hypotheses": [
    {{"code":"H1","label":"...","description":"...",
     "criticality":"critical|important|secondary",
     "verification_horizon":"...","kpi_to_watch":"...",
     "confirmation_threshold":"...","alert_threshold":"..."}}
  ],
  "price_thresholds": {{
    "reinforce_below":0, "alert_below":0,
    "partial_exit_zone1":{{"from":0,"to":0,"pct_to_sell":25}},
    "partial_exit_zone2":{{"from":0,"to":0,"pct_to_sell":50}}
  }},
  "analyst_track_record": [
    {{"firm":"...","current_reco":"...","current_target":0,
     "timing_quality":"high|medium|low","credibility_weight":"high|medium|low"}}
  ],
  "bear_steel_man": {{
    "risk_1":{{"title":"...","argument":"...","evidence":"..."}},
    "risk_2":{{"title":"...","argument":"...","evidence":"..."}},
    "risk_3":{{"title":"...","argument":"...","evidence":"..."}},
    "downside_scenario":"Si ces 3 risques se matérialisent : [X€] dans [Y] ans"
  }}
}}
```"""


async def run_regime_1(ticker: str, company_name: str, data_brief: dict,
                       sector_schema: dict, dust_client: DustClient) -> dict:
    prompt = RESEARCH_PROMPT.format(
        ticker=ticker, company_name=company_name,
        data_brief=json.dumps(data_brief, indent=2, default=str),
        sector_schema=json.dumps(sector_schema, indent=2),
    )
    result = await dust_client.run_agent(
        agent_id=settings.DUST_RESEARCH_AGENT_ID,
        message=prompt, model_override="claude-sonnet-4-5",
        temperature=0.2, timeout=180,
    )
    try:
        c = result["content"]
        j = c.find("```json")
        thesis = json.loads(c[j + 7:c.find("```", j + 7)].strip()) if j >= 0 \
            else json.loads(c[c.find("{"):c.rfind("}") + 1])
        thesis["dust_cost_usd"] = result.get("cost_usd")
        return thesis
    except json.JSONDecodeError as e:
        logger.error(f"Regime 1 parse error {ticker}: {e}")
        return {"error": "parse_error", "raw_content": result["content"][:2000]}
