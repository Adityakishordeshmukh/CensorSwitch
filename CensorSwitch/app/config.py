import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    rate_limit_capacity: int = int(os.getenv("RATE_LIMIT_CAPACITY", "20"))
    rate_limit_refill_per_sec: float = float(os.getenv("RATE_LIMIT_REFILL_PER_SEC", "0.5"))

    cache_similarity_threshold: float = float(os.getenv("CACHE_SIMILARITY_THRESHOLD", "0.92"))

    log_db_path: str = os.getenv("LOG_DB_PATH", "agentgate.db")


settings = Settings()
