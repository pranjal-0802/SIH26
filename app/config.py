import os
from pathlib import Path
from dotenv import load_dotenv

# Explicitly load .env from project root if present
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

def _get_required_secret(var_name: str) -> str:
    val = os.getenv(var_name)
    if not val:
        raise KeyError(
            f"CRITICAL SECURITY CONFIGURATION ERROR: Environment variable '{var_name}' is missing. "
            "Prismarine enforces zero-fallback security posture. "
            "Please configure secrets in your environment or .env file before starting."
        )
    return val

class Settings:
    APP_NAME: str = "Prismarine: Defense Personnel Stress & Welfare Monitoring Platform"
    APP_CODE: str = "PRISMARINE"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment & Demo Mode
    APP_ENV: str = os.getenv("APP_ENV", "production").lower()
    DEMO_MODE: bool = os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")
    
    # Cryptographic Secrets — REQUIRED (Fail fast if missing, zero hardcoded fallback in repo)
    SECRET_KEY: str = _get_required_secret("SECRET_KEY")
    AES_MASTER_KEY_HEX: str = _get_required_secret("AES_MASTER_KEY_HEX")
    AUDIT_HMAC_KEY_HEX: str = _get_required_secret("AUDIT_HMAC_KEY_HEX")
    
    ALGORITHM: str = "HS256"
    
    # Token expiration by role (privilege hierarchy)
    TOKEN_EXPIRE_MINUTES_PERSONNEL: int = 60 * 24  # 24 hours
    TOKEN_EXPIRE_MINUTES_WELFARE: int = 60         # 1 hour
    TOKEN_EXPIRE_MINUTES_COMMANDER: int = 60       # 1 hour
    TOKEN_EXPIRE_MINUTES_ADMIN: int = 30           # 30 minutes
    
    # Database URL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./prismarine.db")
    
    # Explicit CORS Allowed Origins
    ALLOWED_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
        if origin.strip()
    ]
    
    # Privacy parameters
    K_ANONYMITY_THRESHOLD: int = int(os.getenv("K_ANONYMITY_THRESHOLD", "5"))
    DP_EPSILON: float = float(os.getenv("DP_EPSILON", "0.5"))
    DP_MAX_BUDGET_PER_DAY: float = float(os.getenv("DP_MAX_BUDGET_PER_DAY", "5.0"))
    # When True, queries are rejected with HTTP 429 when budget is exhausted. When False (default), graceful noise degradation is applied.
    DP_STRICT_ENFORCEMENT: bool = os.getenv("DP_STRICT_ENFORCEMENT", "false").lower() in ("true", "1", "yes")
    
    # Game-theoretic alert prioritization parameters
    OFFICER_WEEKLY_CAPACITY: int = int(os.getenv("OFFICER_WEEKLY_CAPACITY", "15"))
    STIGMA_PENALTY_WEIGHT: float = 1.8
    TRUE_POSITIVE_GAIN: float = 3.5

settings = Settings()
