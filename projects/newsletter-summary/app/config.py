from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Base PostgreSQL partagée (shared-postgres) — postgresql+asyncpg://user:pass@shared-postgres:5432/db_newsletter_summary
    DATABASE_URL: str

    # COMMS-GATEWAY — l'envoi du digest passe par le gateway (le projet ne détient
    # plus de clé Resend ; seul le gateway possède les secrets des providers).
    GATEWAY_URL: str = "http://comms-gateway:8000"
    GATEWAY_TOKEN: str
    RECIPIENT_EMAIL: str = "jean.langlois-meurinne@mailbox.org"

    # LLM (DeepInfra, pattern réutilisé d'assistant-ia)
    DEEPINFRA_API_KEY: str = ""
    DEEPINFRA_API_BASE: str = "https://api.deepinfra.com/v1/openai"
    DEEPINFRA_MODEL: str = "deepseek-ai/DeepSeek-V4-Flash-0731"

    # Prompts (configurables en variable d'env)
    SUMMARIZATION_PROMPT: str = (
        "Résume l'email ci-dessous en français en suivant la STRUCTURE du mail d'origine : "
        "reprends les mêmes sections, titres et sous-titres, ainsi que leur ordre de présentation. "
        "Condense chaque section en ses points essentiels (1 à 3 phrases par section selon la densité) "
        "en conservant les données factuelles importantes : chiffres, noms propres, dates, statistiques, "
        "liens et appels à l'action. Ne rien inventer ni extrapoler ; si un passage est ambigu, reste au "
        "plus près du texte. Si le mail n'a pas de titres explicites, organise les paragraphes clés en "
        "points structurés sans en changer le sens. Produis un texte lisible, sans jargon superflu.\n\n"
        "EMAIL À RÉSUMER :\n{email}"
    )
    # Prompt du résumé en HTML (bloc autonome, styles inline) — sert au rendu de l'email.
    # C'est LE prompt actif que le digest envoie à DeepInfra, éditable via le Hub
    # (/newsletter/prompt). Les exigences « français » et « pas de pub » sont DOUBLÉES
    # côté code (message système dans summarizer.summarize_html) pour qu'elles restent
    # garanties même si ce texte est librement réédité.
    SUMMARIZE_HTML_PROMPT: str = (
        "Résume le CORPS d'une newsletter en HTML, destiné à être inséré dans une carte déjà "
        "mise en forme par le code (en-tête expéditeur/sujet et cadre fournis automatiquement).\n"
        "Rédige TOUT en français.\n"
        "CONSIGNES :\n"
        "- 600 MOTS MAXIMUM au total. Sois synthétique et hiérarchise : 3 à 6 sections courtes, "
        "puces brèves. Un résumé plus court est préférable à un résumé long ; ne cherche pas l'exhaustivité.\n"
        "- Suis la STRUCTURE du mail d'origine (mêmes sections et sous-titres, dans leur ordre), mais condense.\n"
        "- Produis UNIQUEMENT le corps : PAS de <div> d'encadrement/carte, PAS de fond ni de bordure de "
        "carte, et NE répète NI l'expéditeur NI le sujet. Commence directement par le contenu.\n"
        "- HTML valide avec styles INLINE (style=\"...\"). Sous-titres <h3>, listes <ul>/<li>, <strong>, liens <a>. "
        "AUCUNE balise <html>, <head>, <body>, <style> ni tableau complexe.\n"
        "- Échappe correctement les caractères HTML ; conserve chiffres, noms, dates, statistiques et liens importants.\n"
        "- EXCLUS toute publicité, bandeau promo, offre sponsorisée, encart commercial, lien de parrainage ou contenu promotionnel : "
        "ne garde que le contenu ÉDITORIAL.\n"
        "- Ne rien inventer ni extrapoler.\n"
        "- Rends UNIQUEMENT le HTML du corps (aucun texte avant/après, aucun bloc de code).\n\n"
        "EMAIL À RÉSUMER :\n{email}"
    )

    # Job matinal (Europe/Paris)
    SUMMARY_HOUR: int = 8
    SUMMARY_MINUTE: int = 0

    # Sécurité du webhook inbound : si défini, requis en ?token= sur POST /webhook/resend
    WEBHOOK_TOKEN: str = ""

    # Jeton partagé avec le Hub (app « homepage ») : le Hub appelle /api/* de ce service
    # sur le réseau Docker. Si défini, le header `X-Hub-Token` doit correspondre.
    HUB_API_TOKEN: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
