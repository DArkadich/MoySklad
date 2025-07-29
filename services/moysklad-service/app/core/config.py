from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # MoySklad API
    moysklad_api_token: str = "your_moysklad_token"
    moysklad_api_url: str = "https://api.moysklad.ru/api/remap/1.2"
    
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/moysklad_db"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 0
    
    # Application
    app_name: str = "MoySklad Service"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # API
    api_prefix: str = "/api/v1"
    project_name: str = "Horiens Purchase Agent"
    
    # CORS
    cors_origins: list = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list = ["*"]
    cors_allow_headers: list = ["*"]
    
    # Rate limiting
    rate_limit_per_minute: int = 100
    
    # Cache
    cache_ttl: int = 300  # 5 minutes
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings() 