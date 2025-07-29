"""
Модуль для работы с Redis (API Gateway)
"""

import redis.asyncio as redis
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

# Глобальный клиент Redis
_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    """Получение клиента Redis"""
    global _redis_client
    
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("✅ Подключение к Redis установлено")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Redis: {e}")
            raise
    
    return _redis_client


async def close_redis():
    """Закрытие подключения к Redis"""
    global _redis_client
    
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("🔌 Подключение к Redis закрыто") 