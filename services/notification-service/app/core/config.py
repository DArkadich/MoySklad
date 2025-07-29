from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str = "your_telegram_bot_token"
    telegram_chat_id: str = "your_telegram_chat_id"
    
    # Email
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = "your_email@gmail.com"
    smtp_password: str = "your_app_password"
    sender_email: str = "your_email@gmail.com"
    sender_name: str = "Horiens Purchase Agent"
    admin_email: str = "admin@example.com"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 0
    
    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    
    # Application
    app_name: str = "Notification Service"
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