import asyncpg
from typing import Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Глобальная переменная для пула соединений
_pool: Optional[asyncpg.Pool] = None

async def get_database() -> asyncpg.Pool:
    """Получить пул соединений с базой данных"""
    global _pool
    
    if _pool is None:
        try:
            _pool = await asyncpg.create_pool(
                settings.database_url,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            logger.info("Подключение к базе данных установлено")
        except Exception as e:
            logger.error(f"Ошибка подключения к базе данных: {e}")
            raise
    
    return _pool

async def close_database():
    """Закрыть соединение с базой данных"""
    global _pool
    
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Соединение с базой данных закрыто")

async def init_database():
    """Инициализация базы данных"""
    pool = await get_database()
    
    async with pool.acquire() as conn:
        # Создание таблиц для хранения данных МойСклад
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS moysklad_products (
                id UUID PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                code VARCHAR(100),
                description TEXT,
                price DECIMAL(10,2),
                quantity DECIMAL(10,2) DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS moysklad_sales (
                id UUID PRIMARY KEY,
                product_id UUID REFERENCES moysklad_products(id),
                quantity DECIMAL(10,2) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                sale_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS moysklad_orders (
                id UUID PRIMARY KEY,
                order_number VARCHAR(100) UNIQUE NOT NULL,
                supplier_id UUID,
                total_amount DECIMAL(10,2) NOT NULL,
                status VARCHAR(50) DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Создание индексов
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_products_name ON moysklad_products(name);
            CREATE INDEX IF NOT EXISTS idx_sales_date ON moysklad_sales(sale_date);
            CREATE INDEX IF NOT EXISTS idx_sales_product ON moysklad_sales(product_id);
            CREATE INDEX IF NOT EXISTS idx_orders_status ON moysklad_orders(status);
        """)
        
        logger.info("База данных MoySklad Service инициализирована") 