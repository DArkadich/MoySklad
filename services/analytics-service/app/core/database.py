"""
Модуль для работы с базой данных
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
                settings.database_url,
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


async def init_database():
    """Инициализация базы данных"""
    try:
        pool = await get_database()
        
        # Создание таблиц для аналитики
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS analytics_reports (
                    id SERIAL PRIMARY KEY,
                    report_type VARCHAR(100) NOT NULL,
                    report_data JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sales_analytics (
                    id SERIAL PRIMARY KEY,
                    product_id VARCHAR(255) NOT NULL,
                    date DATE NOT NULL,
                    quantity INTEGER NOT NULL,
                    revenue DECIMAL(10,2) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id SERIAL PRIMARY KEY,
                    metric_name VARCHAR(100) NOT NULL,
                    metric_value DECIMAL(10,4) NOT NULL,
                    metric_date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Создание индексов
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_analytics_reports_type 
                ON analytics_reports(report_type)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sales_analytics_product_date 
                ON sales_analytics(product_id, date)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_performance_metrics_name_date 
                ON performance_metrics(metric_name, metric_date)
            """)
            
        logger.info("✅ База данных аналитики инициализирована")
        
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации базы данных: {e}")
        raise 