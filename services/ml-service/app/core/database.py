"""
Модуль для работы с базой данных (ML Service)
"""

import asyncpg
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

# Глобальное подключение к БД
_db_pool: Optional[asyncpg.Pool] = None


async def get_database() -> asyncpg.Pool:
    """Получение подключения к базе данных"""
    global _db_pool
    
    if _db_pool is None:
        try:
            _db_pool = await asyncpg.create_pool(
                settings.DATABASE_URL,
                min_size=5,
                max_size=20
            )
            logger.info("✅ Подключение к базе данных установлено")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к базе данных: {e}")
            raise
    
    return _db_pool


async def close_database():
    """Закрытие подключения к базе данных"""
    global _db_pool
    
    if _db_pool:
        await _db_pool.close()
        _db_pool = None
        logger.info("🔌 Подключение к базе данных закрыто") 