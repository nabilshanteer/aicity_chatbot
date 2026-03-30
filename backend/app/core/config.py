from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    ANTHROPIC_API_KEY: str = ""
    XAI_API_KEY: str = ""
    SECRET_KEY: str = ""
    NEXTAUTH_SECRET: str = ""
    CORS_ORIGINS: str = "http://localhost:3000"
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    class Config:
        env_file = ".env"

settings = Settings()

