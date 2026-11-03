from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    database_url: str = "sqlite:///./roster.db"
    secret_key: str = "development-only-change-me"
    cors_origins: str = "https://smart-roster.netlify.app,http://localhost:5173"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
settings = Settings()
