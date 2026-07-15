import os 
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Ransomware-Resilient Backup Orchestrator"
    API_V1_STR: str = "/api"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "SUPER_SECURE_DEV_SECRET_KEY_997126315")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Database
    DATABASE_URL: str = "sqlite:///./database/backup.db"
    
    # VM Agent Endpoints
    PRODUCTION_AGENT_URL: str = os.getenv("PRODUCTION_AGENT_URL", "http://127.0.0.1:8001")
    DETECTION_AGENT_URL: str = os.getenv("DETECTION_AGENT_URL", "http://127.0.0.1:8002")
    BACKUP_AGENT_URL: str = os.getenv("BACKUP_AGENT_URL", "http://127.0.0.1:8003")
    QUARANTINE_AGENT_URL: str = os.getenv("QUARANTINE_AGENT_URL", "http://127.0.0.1:8004")

    class Config:
        env_file = ".env"

settings = Settings()