import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    LOG_LEVEL: str = "INFO"
    
    # Database
    database_url: str = "postgresql://moysklad:moysklad123@postgres:5432/moysklad"
    
    # Redis
    redis_url: str = "redis://redis:6379"
    redis_db: int = 0
    
    # MoySklad API
    moysklad_api_token: str = "your_token_here"
    moysklad_api_url: str = "https://api.moysklad.ru/api/remap/1.2"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings() 