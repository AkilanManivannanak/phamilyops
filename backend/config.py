from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ANTHROPIC_API_KEY: str
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    FRONTEND_URL: str = "*"
    ENVIRONMENT: str = "production"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
