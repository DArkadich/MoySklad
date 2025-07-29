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


async def init_database():
    """Инициализация базы данных"""
    try:
        pool = await get_database()
        
        # Создание таблиц
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS purchase_logs (
                    id SERIAL PRIMARY KEY,
                    order_id VARCHAR(255) NOT NULL,
                    product_id VARCHAR(255) NOT NULL,
                    quantity INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'created'
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sales_data (
                    id SERIAL PRIMARY KEY,
                    product_id VARCHAR(255) NOT NULL,
                    date DATE NOT NULL,
                    quantity INTEGER NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ml_models (
                    id SERIAL PRIMARY KEY,
                    product_id VARCHAR(255) NOT NULL,
                    model_type VARCHAR(50) NOT NULL,
                    accuracy DECIMAL(5,4),
                    trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    model_path VARCHAR(500)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS forecasts (
                    id SERIAL PRIMARY KEY,
                    product_id VARCHAR(255) NOT NULL,
                    forecast_date DATE NOT NULL,
                    daily_demand DECIMAL(10,2) NOT NULL,
                    weekly_demand DECIMAL(10,2) NOT NULL,
                    monthly_demand DECIMAL(10,2) NOT NULL,
                    accuracy DECIMAL(5,4),
                    model_type VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Создание индексов
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_purchase_logs_product_id 
                ON purchase_logs(product_id)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sales_data_product_id_date 
                ON sales_data(product_id, date)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_forecasts_product_id_date 
                ON forecasts(product_id, forecast_date)
            """)
        
        logger.info("✅ База данных инициализирована")
        
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации базы данных: {e}")
        raise 