from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Slack
    SLACK_BOT_TOKEN: str
    SLACK_SIGNING_SECRET: str           # requis pour HTTP Events API
    SLACK_APP_TOKEN: str = ""           # xapp-... requis pour Socket Mode (conservé pour rollback)

    # Bank review
    BANK_REVIEW_CHANNEL_ID: str = "C0AV2EJHR5H"        # #bank-review
    BANK_REVIEW_BASE_URL: str = "https://bank.jlmvpscode.duckdns.org"
    BANK_REVIEW_API_KEY: str
    BANK_REVIEW_FEEDBACK_CHANNEL_ID: str = "C0ATW9S0S7N"  # #features-bank-review

    ASSISTANT_BASE_URL: str = "https://assistant.jlmvpscode.duckdns.org"

    # Database
    DATABASE_URL: str  # postgresql://user:pass@shared-postgres:5432/db_assistant

    # Channels Slack par service (valeurs par défaut = IDs connus)
    JOURNAL_CHANNEL_ID: str = "C0B080X2ZBK"         # #journal
    TASKS_CHANNEL_ID: str = "C0AV5M6385T"            # #tasks (kanban)
    FEATURES_AI_CHANNEL_ID: str = "C0AUCE6NELT"      # #features-ai-assistant (déprécié)
    FEEDBACK_CHANNEL_ID: str = "C0AUCE6NELT"         # #feedback (canal unifié)

    # Agent conversationnel (channels privés — le bot doit y être invité)
    ASSISTANT_CHANNEL_ID: str = "C0ATLALRZL3"           # #assistant — conversation agent
    ASSISTANT_FEEDBACK_CHANNEL_ID: str = "C0BSB9S9HHS"  # #feedback-assistant — approbation des diffs

    # DeepInfra (nommage aligné sur portfolio-tracker)
    DEEPINFRA_API_KEY: str = ""
    DEEPINFRA_API_BASE: str = "https://api.deepinfra.com/v1/openai"
    # Classifieur KB journal. Llama 3.1 8B (-Turbo) a été abandonné après vérification contre
    # l'API : DeepInfra refuse `json_schema` pour ce modèle (HTTP 405), donc tout appel coûtait
    # 2 requêtes (405 puis fallback json_object) et le vocabulaire fermé n'était plus qu'une
    # consigne en prose — le modèle produisait `nature: ["vacances"]` (un tag libre) 1 fois sur 2
    # et ne renvoyait jamais la liste vide pourtant autorisée en 0..n.
    # DeepSeek-V4-Flash supporte `json_schema` : 1 seul appel, vocabulaire contraint par `enum`.
    DEEPINFRA_MODEL_CLASSIF: str = "deepseek-ai/DeepSeek-V4-Flash"
    DEEPINFRA_MODEL_CHAT: str = "deepseek-ai/DeepSeek-V4-Flash"
    DEEPINFRA_MODEL_SYSTEM: str = "deepseek-ai/DeepSeek-V4-Pro"

    # KB journal — vault Obsidian (bind-mount en écriture)
    JOURNAL_VAULT_PATH: str = "/storage/journal-vault"

    # Agent — bornes de sécurité du doc système (roadmap §5.4)
    AGENT_DOC_MAX_CHARS: int = 20000          # taille totale plafond du doc système
    AGENT_DOC_MAX_ADDED_CHARS: int = 4000     # ajout maximal en une seule proposition
    AGENT_HISTORY_TURNS: int = 20             # fenêtre d'historique renvoyée au modèle (10 échanges)
    # Slack user IDs autorisés à approuver un diff, séparés par des virgules.
    # Vide = personne : le channel privé ne suffit pas comme autorisation (#1787559677496).
    AGENT_APPROVERS: str = ""

    # Feature 1 — Journal
    SLACK_CHANNEL_JOURNAL: str = "#journal"

    # Feature 2 — Kanban
    SLACK_CHANNEL_TASKS: str = "#tasks"

    # Sécurité webhook deploy
    DEPLOY_WEBHOOK_SECRET: str = ""  # si vide, pas d'auth sur /webhook/deploy-complete

    # Clé API interne pour les endpoints feedback d'assistant-ia
    ASSISTANT_INTERNAL_API_KEY: str = ""

    # Web auth
    WEB_USERNAME: str
    WEB_PASSWORD: str
    SESSION_SECRET: str  # partagé avec homepage pour le cookie hub_session

    class Config:
        env_file = ".env"


settings = Settings()
