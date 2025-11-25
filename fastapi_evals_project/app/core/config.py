from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "")
    max_workers: int = int(os.getenv("MAX_WORKERS", "4"))
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "60"))
    mongo_uri: str = os.getenv("MONGO_URI", "")
    mongo_db_name: str = os.getenv("MONGO_DB_NAME", "")
    mongo_input_collection: str = os.getenv("MONGO_INPUT_COLLECTION", "")
    mongo_output_collection: str = os.getenv("MONGO_OUTPUT_COLLECTION", "")
    transcript_analyzer_url: str = os.getenv("TRANSCRIPT_ANALYZER_URL", "")
    class Config:
        env_file = ".env"

settings = Settings()