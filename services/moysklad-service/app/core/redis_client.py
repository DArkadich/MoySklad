import redis.asyncio as redis
import json
import logging
from typing import Optional, Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# Глобальная переменная для Redis клиента
_redis_client: Optional[redis.Redis] = None

async def get_redis_client() -> redis.Redis:
    """Получить Redis клиент"""
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
            logger.info("Подключение к Redis установлено")
        except Exception as e:
            logger.error(f"Ошибка подключения к Redis: {e}")
            raise
    
    return _redis_client

async def close_redis():
    """Закрыть соединение с Redis"""
    global _redis_client
    
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Соединение с Redis закрыто")

async def cache_get(key: str) -> Optional[Any]:
    """Получить данные из кэша"""
    try:
        client = await get_redis_client()
        data = await client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.error(f"Ошибка получения из кэша: {e}")
        return None

async def cache_set(key: str, value: Any, ttl: int = None) -> bool:
    """Сохранить данные в кэш"""
    try:
        client = await get_redis_client()
        if ttl is None:
            ttl = settings.cache_ttl
        
        await client.setex(
            key,
            ttl,
            json.dumps(value, ensure_ascii=False)
        )
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения в кэш: {e}")
        return False

async def cache_delete(key: str) -> bool:
    """Удалить данные из кэша"""
    try:
        client = await get_redis_client()
        await client.delete(key)
        return True
    except Exception as e:
        logger.error(f"Ошибка удаления из кэша: {e}")
        return False

async def cache_exists(key: str) -> bool:
    """Проверить существование ключа в кэше"""
    try:
        client = await get_redis_client()
        return await client.exists(key) > 0
    except Exception as e:
        logger.error(f"Ошибка проверки кэша: {e}")
        return False

async def cache_ttl(key: str) -> int:
    """Получить TTL ключа в кэше"""
    try:
        client = await get_redis_client()
        return await client.ttl(key)
    except Exception as e:
        logger.error(f"Ошибка получения TTL: {e}")
        return -1 