"""
Сервис обработки данных для машинного обучения
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

from app.core.database import get_database
from app.services.moysklad_integration import MoySkladService

logger = logging.getLogger(__name__)


class DataProcessor:
    """Сервис обработки данных для ML"""
    
    def __init__(self):
        self.moysklad_service = MoySkladService()

    async def get_historical_data(
        self, 
        product_id: str, 
        days_back: int = 90
    ) -> List[Dict[str, Any]]:
        """Получение исторических данных для продукта"""
        try:
            # Получение данных из базы
            db = get_database()
            
            # Получение данных о продажах
            sales_query = """
                SELECT date, quantity, price 
                FROM sales_data 
                WHERE product_id = $1 
                AND date >= $2 
                ORDER BY date
            """
            
            start_date = datetime.now() - timedelta(days=days_back)
            
            async with db.acquire() as conn:
                sales_rows = await conn.fetch(sales_query, product_id, start_date.date())
            
            # Преобразование в список словарей
            historical_data = []
            for row in sales_rows:
                historical_data.append({
                    "date": row["date"],
                    "quantity": row["quantity"],
                    "price": float(row["price"]),
                    "day_of_week": row["date"].weekday(),
                    "month": row["date"].month,
                    "is_weekend": int(row["date"].weekday() >= 5),
                    "is_holiday": 0  # Будет добавлено позже
                })
            
            # Если данных нет в БД, попробуем получить из МойСклад
            if not historical_data:
                historical_data = await self._get_data_from_moysklad(product_id, days_back)
            
            logger.info(f"Получено {len(historical_data)} записей для {product_id}")
            return historical_data
            
        except Exception as e:
            logger.error(f"Ошибка получения исторических данных для {product_id}: {e}")
            return []

    async def get_training_data(
        self, 
        product_id: str, 
        days_back: int = 180
    ) -> List[Dict[str, Any]]:
        """Получение данных для обучения модели"""
        try:
            # Получение исторических данных
            historical_data = await self.get_historical_data(product_id, days_back)
            
            if not historical_data:
                return []
            
            # Создание признаков для обучения
            training_data = await self._create_training_features(historical_data)
            
            logger.info(f"Создано {len(training_data)} записей для обучения {product_id}")
            return training_data
            
        except Exception as e:
            logger.error(f"Ошибка создания данных для обучения {product_id}: {e}")
            return []

    async def _get_data_from_moysklad(
        self, 
        product_id: str, 
        days_back: int
    ) -> List[Dict[str, Any]]:
        """Получение данных из МойСклад"""
        try:
            # Получение данных о продажах из МойСклад
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            sales_data = await self.moysklad_service.get_sales_data(
                product_id, start_date, end_date
            )
            
            # Преобразование данных
            historical_data = []
            for sale in sales_data:
                sale_date = datetime.fromisoformat(sale["date"].replace("Z", "+00:00"))
                historical_data.append({
                    "date": sale_date.date(),
                    "quantity": sale["quantity"],
                    "price": sale["price"],
                    "day_of_week": sale_date.weekday(),
                    "month": sale_date.month,
                    "is_weekend": int(sale_date.weekday() >= 5),
                    "is_holiday": 0
                })
            
            # Сохранение в базу данных
            await self._save_sales_data(product_id, historical_data)
            
            return historical_data
            
        except Exception as e:
            logger.error(f"Ошибка получения данных из МойСклад для {product_id}: {e}")
            return []

    async def _create_training_features(
        self, 
        historical_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Создание признаков для обучения"""
        try:
            if not historical_data:
                return []
            
            # Создание DataFrame
            df = pd.DataFrame(historical_data)
            df = df.sort_values('date')
            
            # Создание лаговых признаков
            df['lag_1'] = df['quantity'].shift(1)
            df['lag_7'] = df['quantity'].shift(7)
            df['lag_30'] = df['quantity'].shift(30)
            
            # Скользящие средние
            df['rolling_mean_7'] = df['quantity'].rolling(window=7).mean()
            df['rolling_mean_30'] = df['quantity'].rolling(window=30).mean()
            df['rolling_std_7'] = df['quantity'].rolling(window=7).std()
            
            # Трендовые признаки
            df['trend'] = np.arange(len(df))
            df['trend_squared'] = df['trend'] ** 2
            
            # Сезонные признаки
            df['day_of_week_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
            df['day_of_week_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
            df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
            df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
            
            # Признаки цены
            df['price_change'] = df['price'].pct_change()
            df['price_ma_7'] = df['price'].rolling(window=7).mean()
            
            # Удаление NaN значений
            df = df.dropna()
            
            # Преобразование обратно в список словарей
            training_data = df.to_dict('records')
            
            return training_data
            
        except Exception as e:
            logger.error(f"Ошибка создания признаков: {e}")
            return []

    async def _save_sales_data(
        self, 
        product_id: str, 
        sales_data: List[Dict[str, Any]]
    ):
        """Сохранение данных о продажах в базу"""
        try:
            db = get_database()
            
            async with db.acquire() as conn:
                for sale in sales_data:
                    await conn.execute("""
                        INSERT INTO sales_data (product_id, date, quantity, price)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (product_id, date) DO UPDATE SET
                        quantity = EXCLUDED.quantity,
                        price = EXCLUDED.price
                    """, product_id, sale["date"], sale["quantity"], sale["price"])
            
            logger.info(f"Сохранено {len(sales_data)} записей о продажах для {product_id}")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения данных о продажах: {e}")

    async def update_all_data(self):
        """Обновление всех данных"""
        try:
            # Список продуктов для обновления
            products = [
                "solution_360", "solution_500", "solution_120",
                "monthly_3", "monthly_6", "daily"
            ]
            
            for product_id in products:
                try:
                    # Получение свежих данных
                    historical_data = await self._get_data_from_moysklad(product_id, 90)
                    
                    if historical_data:
                        # Создание признаков
                        training_data = await self._create_training_features(historical_data)
                        
                        # Сохранение в базу
                        await self._save_sales_data(product_id, historical_data)
                        
                        logger.info(f"Данные для {product_id} обновлены")
                    
                except Exception as e:
                    logger.error(f"Ошибка обновления данных для {product_id}: {e}")
            
            logger.info("Обновление всех данных завершено")
            
        except Exception as e:
            logger.error(f"Ошибка обновления всех данных: {e}")

    async def get_data_statistics(self, product_id: str) -> Dict[str, Any]:
        """Получение статистики данных"""
        try:
            historical_data = await self.get_historical_data(product_id, 365)
            
            if not historical_data:
                return {}
            
            df = pd.DataFrame(historical_data)
            
            stats = {
                "total_records": len(df),
                "date_range": {
                    "start": df["date"].min().isoformat(),
                    "end": df["date"].max().isoformat()
                },
                "quantity_stats": {
                    "mean": float(df["quantity"].mean()),
                    "std": float(df["quantity"].std()),
                    "min": int(df["quantity"].min()),
                    "max": int(df["quantity"].max()),
                    "median": float(df["quantity"].median())
                },
                "price_stats": {
                    "mean": float(df["price"].mean()),
                    "std": float(df["price"].std()),
                    "min": float(df["price"].min()),
                    "max": float(df["price"].max())
                },
                "seasonality": {
                    "weekly_pattern": df.groupby("day_of_week")["quantity"].mean().to_dict(),
                    "monthly_pattern": df.groupby("month")["quantity"].mean().to_dict()
                }
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики для {product_id}: {e}")
            return {} 