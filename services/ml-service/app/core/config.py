"""
Конфигурация ML сервиса
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки ML сервиса"""
    
    # Database
    DATABASE_URL: str = "postgresql://horiens:horiens_pass@postgres:5432/horiens_db"
    
    # Redis
    REDIS_URL: str = "redis://redis:6379"
    
    # RabbitMQ
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"
    
    # Application
    APP_NAME: str = "Horiens ML Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # ML Models
    MODELS_DIR: str = "/app/models"
    MODEL_CACHE_TTL: int = 3600  # 1 hour
    
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Horiens Purchase Agent"
    
    # CORS
    BACKEND_CORS_ORIGINS: list = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Создание экземпляра настроек
settings = Settings() 