#!/usr/bin/env python3
"""
Скрипт для обучения ML моделей с учетом ограничений API MoySklad
"""

import asyncio
import httpx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import logging
import time
import random
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import pickle
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RateLimitedMoySkladCollector:
    """Класс для сбора данных из MoySklad API с учетом ограничений"""
    
    def __init__(self):
        self.api_token = os.getenv('MOYSKLAD_API_TOKEN')
        self.api_url = os.getenv('MOYSKLAD_API_URL', 'https://api.moysklad.ru/api/remap/1.2')
        
        if not self.api_token:
            raise ValueError("MOYSKLAD_API_TOKEN не найден в переменных окружения")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        # Ограничения API
        self.requests_per_minute = 30  # Лимит запросов в минуту
        self.delay_between_requests = 2.0  # Задержка между запросами в секундах
        self.last_request_time = 0
        
    async def _rate_limit(self):
        """Ограничение частоты запросов"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.delay_between_requests:
            sleep_time = self.delay_between_requests - time_since_last
            logger.info(f"⏳ Ожидание {sleep_time:.1f} секунд для соблюдения лимитов API...")
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    async def _make_request(self, method: str, url: str, **kwargs) -> Optional[Dict]:
        """Выполнение запроса с ограничениями"""
        await self._rate_limit()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(method, url, headers=self.headers, **kwargs)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Too Many Requests
                    logger.warning("⚠️ Превышен лимит запросов. Ожидание 60 секунд...")
                    await asyncio.sleep(60)
                    return None
                elif response.status_code == 403:  # Forbidden
                    logger.error("❌ API заблокирован. Проверьте токен и права доступа.")
                    return None
                else:
                    logger.error(f"❌ Ошибка API: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Ошибка запроса: {e}")
            return None
    
    async def get_all_products(self) -> List[Dict]:
        """Получение всех товаров из MoySklad с ограничениями"""
        logger.info("📦 Получение списка товаров из MoySklad...")
        
        data = await self._make_request("GET", f"{self.api_url}/entity/product")
        
        if data:
            products = data.get("rows", [])
            logger.info(f"✅ Получено {len(products)} товаров из MoySklad")
            return products
        else:
            logger.error("❌ Не удалось получить товары из MoySklad")
            return []
    
    async def get_sales_data(self, product_id: str, days_back: int = 90) -> List[Dict]:
        """Получение данных о продажах товара с ограничениями"""
        logger.info(f"📊 Получение данных о продажах для товара {product_id}...")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # Формат дат без микросекунд для совместимости с API
        moment_from = start_date.replace(microsecond=0).strftime('%Y-%m-%dT00:00:00')
        moment_to = end_date.replace(microsecond=0).strftime('%Y-%m-%dT23:59:59')

        # Получаем документы продаж с ограничениями (используем momentFrom/momentTo)
        data = await self._make_request(
            "GET",
            f"{self.api_url}/entity/demand",
            params={
                "momentFrom": moment_from,
                "momentTo": moment_to,
                "limit": 100  # Уменьшаем лимит
            }
        )
        
        if not data:
            return []
        
        sales_data = []
        
        for demand in data.get("rows", []):
            # Получаем позиции документа с задержкой
            positions_data = await self._make_request(
                "GET",
                f"{self.api_url}/entity/demand/{demand['id']}/positions",
                params={"expand": "assortment"}
            )
            
            if positions_data:
                for position in positions_data.get("rows", []):
                    assortment = position.get("assortment", {})
                    assortment_id = None

                    if isinstance(assortment, dict):
                        # Прямой id, если expand сработал
                        assortment_id = assortment.get("id")
                        if not assortment_id:
                            # Пробуем извлечь из meta.href
                            href = (assortment.get("meta", {}) or {}).get("href", "")
                            if href:
                                assortment_id = href.rstrip("/").split("/")[-1]

                    if assortment_id == product_id:
                        sales_data.append({
                            "date": demand.get("moment"),
                            "quantity": position.get("quantity", 0),
                            "price": (position.get("price", 0) or 0) / 100,
                            "sum": (position.get("sum", 0) or 0) / 100
                        })
        
        logger.info(f"✅ Получено {len(sales_data)} записей продаж для товара {product_id}")
        return sales_data
    
    async def get_stock_data(self, product_id: str, days_back: int = 30) -> List[Dict]:
        """Получение данных об остатках товара с ограничениями"""
        logger.info(f"📦 Получение данных об остатках для товара {product_id}...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        data = await self._make_request(
            "GET", 
            f"{self.api_url}/report/stock/all",
            params={
                "filter": f"assortmentId={product_id}",
                "momentFrom": start_date.isoformat(),
                "momentTo": end_date.isoformat()
            }
        )
        
        if not data:
            return []
        
        stock_data = []
        for row in data.get("rows", []):
            stock_data.append({
                "date": row.get("moment", datetime.now().isoformat()),
                "quantity": row.get("quantity", 0),
                "reserve": row.get("reserve", 0),
                "inTransit": row.get("inTransit", 0)
            })
        
        logger.info(f"✅ Получено {len(stock_data)} записей остатков для товара {product_id}")
        return stock_data

class MLModelTrainer:
    """Класс для обучения ML моделей"""
    
    def __init__(self):
        self.models_dir = "data/real_models"
        os.makedirs(self.models_dir, exist_ok=True)
    
    def prepare_features(self, sales_data: List[Dict], stock_data: List[Dict]) -> pd.DataFrame:
        """Подготовка признаков для обучения"""
        if not sales_data:
            return pd.DataFrame()
        
        # Создаем DataFrame из данных о продажах
        df = pd.DataFrame(sales_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
        
        # Группируем по дням
        daily_sales = df.groupby(df.index.date).agg({
            'quantity': 'sum',
            'price': 'mean',
            'sum': 'sum'
        }).reset_index()
        daily_sales['date'] = pd.to_datetime(daily_sales['date'])
        daily_sales = daily_sales.set_index('date')
        
        # Добавляем временные признаки
        daily_sales['year'] = daily_sales.index.year
        daily_sales['month'] = daily_sales.index.month
        daily_sales['day'] = daily_sales.index.day
        daily_sales['day_of_year'] = daily_sales.index.dayofyear
        daily_sales['day_of_week'] = daily_sales.index.dayofweek
        daily_sales['is_month_start'] = daily_sales.index.day == 1
        daily_sales['is_quarter_start'] = (daily_sales.index.day == 1) & (daily_sales.index.month.isin([1, 4, 7, 10]))
        daily_sales['is_weekend'] = daily_sales.index.dayofweek >= 5
        
        # Сезонные признаки
        daily_sales['is_holiday_season'] = daily_sales.index.month.isin([12, 1, 2])
        daily_sales['is_summer_season'] = daily_sales.index.month.isin([6, 7, 8])
        
        # Лаговые признаки
        daily_sales['quantity_lag_1'] = daily_sales['quantity'].shift(1)
        daily_sales['quantity_lag_7'] = daily_sales['quantity'].shift(7)
        daily_sales['quantity_lag_30'] = daily_sales['quantity'].shift(30)
        
        # Скользящие средние
        daily_sales['quantity_ma_7'] = daily_sales['quantity'].rolling(7).mean()
        daily_sales['quantity_ma_30'] = daily_sales['quantity'].rolling(30).mean()
        
        # Удаляем NaN значения
        daily_sales = daily_sales.dropna()
        
        return daily_sales
    
    def train_models(self, product_id: str, features_df: pd.DataFrame) -> Dict:
        """Обучение моделей"""
        if len(features_df) < 20:  # Уменьшаем минимальное количество данных
            logger.warning(f"⚠️ Недостаточно данных для товара {product_id}: {len(features_df)} записей")
            return {}
        
        # Подготовка данных
        feature_columns = [col for col in features_df.columns if col not in ['quantity', 'price', 'sum']]
        X = features_df[feature_columns].values
        y = features_df['quantity'].values
        
        # Разделение на обучающую и тестовую выборки
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        # Нормализация
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Обучение моделей
        models = {}
        
        # Линейная регрессия
        lr_model = LinearRegression()
        lr_model.fit(X_train_scaled, y_train)
        lr_score = lr_model.score(X_test_scaled, y_test)
        models['linear_regression'] = {
            'model': lr_model,
            'scaler': scaler,
            'accuracy': lr_score,
            'feature_columns': feature_columns
        }
        
        # Случайный лес
        rf_model = RandomForestRegressor(n_estimators=50, random_state=42)  # Уменьшаем количество деревьев
        rf_model.fit(X_train_scaled, y_train)
        rf_score = rf_model.score(X_test_scaled, y_test)
        models['random_forest'] = {
            'model': rf_model,
            'scaler': scaler,
            'accuracy': rf_score,
            'feature_columns': feature_columns
        }
        
        logger.info(f"✅ Модели для товара {product_id} обучены:")
        logger.info(f"  Linear Regression: {lr_score:.4f}")
        logger.info(f"  Random Forest: {rf_score:.4f}")
        
        return models
    
    def save_models(self, product_id: str, models: Dict):
        """Сохранение моделей"""
        model_data = {
            'product_id': product_id,
            'models': {},
            'results': {},
            'features': [],
            'training_date': datetime.now().isoformat(),
            'model_type': 'real_data'
        }
        
        for model_name, model_info in models.items():
            # Сохраняем модель
            model_path = os.path.join(self.models_dir, f"{product_id}_{model_name}.pkl")
            with open(model_path, 'wb') as f:
                pickle.dump(model_info['model'], f)
            
            # Сохраняем scaler
            scaler_path = os.path.join(self.models_dir, f"{product_id}_{model_name}_scaler.pkl")
            with open(scaler_path, 'wb') as f:
                pickle.dump(model_info['scaler'], f)
            
            model_data['models'][model_name] = model_path
            model_data['results'][model_name] = {
                'accuracy': model_info['accuracy'],
                'feature_columns': model_info['feature_columns']
            }
        
        # Сохраняем метаданные
        metadata_path = os.path.join(self.models_dir, f"{product_id}_metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(model_data, f, indent=2)
        
        logger.info(f"💾 Модели для товара {product_id} сохранены в {self.models_dir}")

async def main():
    """Основная функция"""
    logger.info("🚀 Начинаем обучение моделей с учетом ограничений API MoySklad")
    
    # Инициализация
    data_collector = RateLimitedMoySkladCollector()
    model_trainer = MLModelTrainer()
    
    # Получение всех товаров
    products = await data_collector.get_all_products()
    
    if not products:
        logger.error("❌ Не удалось получить товары из MoySklad")
        logger.info("💡 Возможные причины:")
        logger.info("   - API заблокирован из-за превышения лимитов")
        logger.info("   - Неправильный токен API")
        logger.info("   - Нет прав доступа")
        return
    
    logger.info(f"📦 Найдено {len(products)} товаров для обучения")
    
    # Ограничиваем количество товаров для тестирования
    test_products = products[:3]  # Уменьшаем до 3 товаров
    
    successful_models = 0
    
    for i, product in enumerate(test_products, 1):
        product_id = product['id']
        product_name = product.get('name', 'Неизвестный товар')
        product_code = product.get('code', '')
        
        logger.info(f"📦 [{i}/{len(test_products)}] Обрабатываем товар: {product_name}")
        logger.info(f"   ID: {product_id}, Код: {product_code}")
        
        try:
            # Получение данных о продажах
            sales_data = await data_collector.get_sales_data(product_id, days_back=90)
            
            if not sales_data:
                logger.warning(f"⚠️ Нет данных о продажах для товара {product_name}")
                continue
            
            # Получение данных об остатках
            stock_data = await data_collector.get_stock_data(product_id, days_back=30)
            
            # Подготовка признаков
            features_df = model_trainer.prepare_features(sales_data, stock_data)
            
            if features_df.empty:
                logger.warning(f"⚠️ Не удалось подготовить признаки для товара {product_name}")
                continue
            
            # Обучение моделей
            models = model_trainer.train_models(product_id, features_df)
            
            if models:
                # Сохранение моделей
                model_trainer.save_models(product_id, models)
                logger.info(f"✅ Модели для товара {product_name} успешно обучены и сохранены")
                successful_models += 1
            else:
                logger.warning(f"⚠️ Не удалось обучить модели для товара {product_name}")
        
        except Exception as e:
            logger.error(f"❌ Ошибка обработки товара {product_name}: {e}")
            continue
        
        # Пауза между товарами
        if i < len(test_products):
            logger.info("⏳ Пауза между товарами для соблюдения лимитов API...")
            await asyncio.sleep(5)
    
    logger.info(f"🎉 Обучение завершено! Успешно обучено моделей: {successful_models}/{len(test_products)}")
    
    if successful_models > 0:
        logger.info("✅ Система готова к работе с реальными моделями!")
    else:
        logger.warning("⚠️ Не удалось обучить ни одной модели. Проверьте API токен и лимиты.")

if __name__ == "__main__":
    asyncio.run(main()) 