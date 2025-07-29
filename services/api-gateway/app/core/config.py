"""
Конфигурация API Gateway
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки API Gateway"""
    
    # Redis
    REDIS_URL: str = "redis://redis:6379"
    
    # RabbitMQ
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"
    
    # Application
    APP_NAME: str = "Horiens API Gateway"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Horiens Purchase Agent"
    
    # CORS
    BACKEND_CORS_ORIGINS: list = ["*"]
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Создание экземпляра настроек
settings = Settings() 