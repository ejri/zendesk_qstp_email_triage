import os
from dotenv import load_dotenv

load_dotenv()

ZENDESK_SUBDOMAIN = os.getenv("ZENDESK_SUBDOMAIN")
ZENDESK_ACCESS_TOKEN = os.getenv("ZENDESK_ACCESS_TOKEN")
ZENDESK_WEBHOOK_SECRET = os.getenv("ZENDESK_WEBHOOK_SECRET")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-4")

OPENAI_COMPAT_BASE_URL = os.getenv("OPENAI_COMPAT_BASE_URL")
OPENAI_COMPAT_API_KEY = os.getenv("OPENAI_COMPAT_API_KEY")
OPENAI_COMPAT_MODEL = os.getenv("OPENAI_COMPAT_MODEL", "gemma-4")

REDIS_URL = os.getenv("REDIS_URL")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///triage.db")

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")
MAX_EMAIL_CHARS = int(os.getenv("MAX_EMAIL_CHARS", "12000"))
CONFIDENCE_HUMAN_REVIEW_THRESHOLD = int(
    os.getenv("CONFIDENCE_HUMAN_REVIEW_THRESHOLD", "70")
)

ZENDESK_BASE_URL = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2"