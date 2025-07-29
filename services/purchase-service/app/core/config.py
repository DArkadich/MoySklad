"""
Конфигурация приложения
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения с учетом сроков доставки"""
    
    # MoySklad API
    moysklad_api_token: str = "your_token_here"
    moysklad_api_url: str = "https://api.moysklad.ru/api/remap/1.2"
    
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/horiens_purchase"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 0
    
    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    
    # Telegram Bot
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    # ML Service
    ml_service_url: str = "http://ml-service:8002"
    
    # Application
    app_name: str = "Horiens Purchase Agent"
    app_version: str = "1.0.0"
    debug: bool = False
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Caching
    cache_ttl: int = 300  # 5 minutes
    stock_cache_ttl: int = 60  # 1 minute for stock data
    
    # API
    api_prefix: str = "/api/v1"
    project_name: str = "Horiens Purchase Agent"
    
    # CORS
    cors_origins: list = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list = ["*"]
    cors_allow_headers: list = ["*"]
    
    # Rate Limiting
    rate_limit_per_minute: int = 100
    
    # Security
    secret_key: str = "your-secret-key-here"
    
    # Delivery Optimization
    delivery_optimization_enabled: bool = True
    combined_delivery_savings_percent: float = 20.0
    max_delivery_combination_days: int = 7
    
    # Manufacturing Times (days)
    manufacturing_time_solutions: int = 45  # 30-60 дней, берем среднее
    manufacturing_time_lenses: int = 45     # 30-60 дней, берем среднее
    
    # Delivery Times (days)
    delivery_time_solutions: int = 30       # 30-45 дней для растворов
    delivery_time_lenses: int = 10          # 10-15 дней для линз
    
    # Safety Stock (days)
    safety_stock_solutions: int = 30
    safety_stock_lenses: int = 15
    
    # Reorder Points (days before stockout)
    reorder_point_solutions: int = 45
    reorder_point_lenses: int = 20
    
    # Minimum Batch Sizes
    min_batch_solutions_360_500: int = 5000
    min_batch_solutions_120: int = 5000
    min_batch_monthly_lenses: int = 5000
    min_batch_daily_lenses: int = 3000
    
    # Multiplicity (packages per box)
    multiplicity_solutions_360_500: int = 24
    multiplicity_solutions_120: int = 48
    multiplicity_monthly_lenses: int = 50
    multiplicity_daily_lenses: int = 30
    
    # Delivery Partners
    delivery_partners_solutions: list = [
        "ТК Деловые Линии",
        "ТК ПЭК", 
        "ТК Байкал-Сервис"
    ]
    delivery_partners_lenses: list = [
        "DHL Express",
        "FedEx",
        "EMS"
    ]
    
    # Cost Configuration
    base_delivery_cost_solutions: float = 5000.0
    base_delivery_cost_lenses: float = 8000.0
    cost_per_kg: float = 100.0
    
    # Monitoring
    health_check_interval: int = 30  # seconds
    metrics_enabled: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Создание экземпляра настроек
settings = Settings() 