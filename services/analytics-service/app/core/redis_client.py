"""
Модуль для работы с Redis
"""

import redis.asyncio as redis
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

# Глобальное подключение к Redis
_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    """Получение подключения к Redis"""
    global _redis_client
    
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.redis_url,
                db=settings.redis_db,
                decode_responses=True
            )
            # Проверка подключения
            await _redis_client.ping()
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


async def set_cache(key: str, value: str, ttl: int = 300):
    """Установка значения в кэш"""
    try:
        client = await get_redis_client()
        await client.set(key, value, ex=ttl)
        logger.debug(f"✅ Кэш установлен: {key}")
    except Exception as e:
        logger.error(f"❌ Ошибка установки кэша: {e}")


async def get_cache(key: str) -> Optional[str]:
    """Получение значения из кэша"""
    try:
        client = await get_redis_client()
        value = await client.get(key)
        if value:
            logger.debug(f"✅ Кэш получен: {key}")
        return value
    except Exception as e:
        logger.error(f"❌ Ошибка получения кэша: {e}")
        return None


async def delete_cache(key: str):
    """Удаление значения из кэша"""
    try:
        client = await get_redis_client()
        await client.delete(key)
        logger.debug(f"✅ Кэш удален: {key}")
    except Exception as e:
        logger.error(f"❌ Ошибка удаления кэша: {e}") 