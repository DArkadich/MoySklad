"""
Модуль для работы с Redis
"""

import redis.asyncio as redis
import logging
from typing import Optional, Any
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


async def cache_get(key: str) -> Optional[str]:
    """Получение значения из кэша"""
    try:
        client = await get_redis_client()
        return await client.get(key)
    except Exception as e:
        logger.error(f"Ошибка получения из кэша: {e}")
        return None


async def cache_set(key: str, value: str, ttl: int = None) -> bool:
    """Установка значения в кэш"""
    try:
        client = await get_redis_client()
        if ttl:
            await client.setex(key, ttl, value)
        else:
            await client.set(key, value)
        return True
    except Exception as e:
        logger.error(f"Ошибка установки в кэш: {e}")
        return False


async def cache_delete(key: str) -> bool:
    """Удаление значения из кэша"""
    try:
        client = await get_redis_client()
        await client.delete(key)
        return True
    except Exception as e:
        logger.error(f"Ошибка удаления из кэша: {e}")
        return False


async def cache_exists(key: str) -> bool:
    """Проверка существования ключа в кэше"""
    try:
        client = await get_redis_client()
        return await client.exists(key) > 0
    except Exception as e:
        logger.error(f"Ошибка проверки кэша: {e}")
        return False


async def cache_ttl(key: str) -> int:
    """Получение TTL ключа"""
    try:
        client = await get_redis_client()
        return await client.ttl(key)
    except Exception as e:
        logger.error(f"Ошибка получения TTL: {e}")
        return -1 