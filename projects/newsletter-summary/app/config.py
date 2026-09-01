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
    SUMMARIZE_HTML_PROMPT: str = (
        "Génère le contenu HTML d'un bloc de résumé de newsletter destiné à un email. "
        "Produis UN SEUL bloc HTML autonome (qui commence par <div>) présentant la newsletter : "
        "un en-tête avec l'expéditeur et le sujet, puis un résumé structuré qui repose sur la STRUCTURE "
        "du mail d'origine (mêmes sections et sous-titres, dans leur ordre).\n"
        "CONSIGNES :\n"
        "- HTML valide avec styles INLINE (style=\"...\") sur chaque élément.\n"
        "- AUCUNE balise <html>, <head>, <body>, <style> ni tableau complexe.\n"
        "- Privilégie la lisibilité : sous-titres <h3>, listes <ul>/<li>, passages <strong>, liens <a>.\n"
        "- Carte sobre : fond léger (#f6f8fa), bordure arrondie, marges internes confortables.\n"
        "- Échappe correctement les caractères HTML ; conserve chiffres, noms, dates, statistiques et liens importants.\n"
        "- Ne rien inventer ni extrapoler.\n"
        "- Rends UNIQUEMENT le HTML du bloc (aucun texte avant/après, aucun bloc de code).\n\n"
        "EMAIL À RÉSUMER :\n{email}"
    )

    # Job matinal (Europe/Paris)
    SUMMARY_HOUR: int = 8
    SUMMARY_MINUTE: int = 0

    # Sécurité du webhook inbound : si défini, requis en ?token= sur POST /webhook/resend
    WEBHOOK_TOKEN: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
