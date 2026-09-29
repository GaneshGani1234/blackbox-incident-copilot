import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


class Settings:
    hindsight_base_url = os.getenv("HINDSIGHT_BASE_URL", "http://localhost:8888")
    hindsight_api_key = os.getenv("HINDSIGHT_API_KEY") or None
    bank_id = os.getenv("HINDSIGHT_BANK_ID", "checkout-team")
    memory_backend = os.getenv("MEMORY_BACKEND", "hindsight").lower()

    llm_api_key = os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY")
    llm_base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    llm_model = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
    llm_fallback_model = os.getenv("LLM_FALLBACK_MODEL", "qwen/qwen3-32b")
    llm_mode = os.getenv("LLM_MODE", "groq").lower()

    allow_reset = os.getenv("ALLOW_RESET", "true").lower() == "true"  # set false on the public demo

    data_dir = ROOT / "data"


settings = Settings()
