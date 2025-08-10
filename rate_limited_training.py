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
from collections import deque
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
        # Настройка лимитов: целимся ниже 200 req/min для запаса
        self.requests_per_minute = int(os.getenv('MSK_REQ_PER_MIN', '180'))
        self.min_delay_between_requests = float(os.getenv('MSK_MIN_DELAY_SEC', '0.30'))
        self.last_request_time = 0.0
        self.request_timestamps = deque()  # моменты времени последних запросов (секунды)
        
    async def _rate_limit(self):
        """Скользящее окно: не более N запросов за последние 60 секунд + минимальная задержка с джиттером."""
        now = time.time()
        # Минимальная задержка между запросами
        since_last = now - self.last_request_time
        if since_last < self.min_delay_between_requests:
            sleep_time = self.min_delay_between_requests - since_last + random.uniform(0.02, 0.12)
            await asyncio.sleep(sleep_time)
            now = time.time()

        # Чистим окно старше 60 секунд
        while self.request_timestamps and now - self.request_timestamps[0] > 60.0:
            self.request_timestamps.popleft()

        # Если достигли лимита, ждём до освобождения окна
        if len(self.request_timestamps) >= self.requests_per_minute:
            sleep_needed = 60.0 - (now - self.request_timestamps[0]) + random.uniform(0.05, 0.15)
            logger.info(f"⏳ Достигнут лимит {self.requests_per_minute}/мин. Ожидание {sleep_needed:.1f} c...")
            await asyncio.sleep(max(0.0, sleep_needed))

        # Фиксируем текущий запрос
        self.last_request_time = time.time()
        self.request_timestamps.append(self.last_request_time)
    
    async def _make_request(self, method: str, url: str, **kwargs) -> Optional[Dict]:
        """Выполнение запроса с ограничениями"""
        await self._rate_limit()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(method, url, headers=self.headers, **kwargs)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code in (429, 412):  # Rate-limit / anti-bot
                    logger.warning(f"⚠️ Ограничение API ({response.status_code}). Ожидание 60 секунд...")
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
        """Получение ассортимента (с кодами) из MoySklad с ограничениями"""
        logger.info("📦 Получение ассортимента из MoySklad...")
        all_rows: List[Dict] = []
        offset = 0
        page_size = 100
        while True:
            data = await self._make_request(
                "GET",
                f"{self.api_url}/entity/assortment",
                params={"limit": page_size, "offset": offset},
            )
            if not data:
                break
            rows = data.get("rows", [])
            if not rows:
                break
            all_rows.extend(rows)
            if len(rows) < page_size:
                break
            offset += page_size
        logger.info(f"✅ Получено {len(all_rows)} позиций ассортимента из MoySklad")
        return all_rows
    
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
    
    async def get_stock_data(self, product_code: str, days_back: int = 120) -> List[Dict]:
        """Получение данных об остатках товара: day-by-day по report/stock/all с фильтром по коду."""
        logger.info(f"📦 Получение данных об остатках для кода {product_code}...")

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)

        stock_data: List[Dict] = []
        current = start_date
        while current <= end_date:
            params = {
                "moment": f"{current.isoformat()}T00:00:00",
                "limit": 1000,
            }

            data = await self._make_request(
                "GET",
                f"{self.api_url}/report/stock/all",
                params=params,
            )
            if data:
                for row in data.get("rows", []):
                    row_code = row.get("code")
                    if product_code and row_code and row_code != product_code:
                        continue
                    if product_code and not row_code:
                        # Если у строки нет кода, пропускаем (мы работаем только с товарами с кодом)
                        continue
                    stock_data.append({
                        "date": current.isoformat(),
                        "quantity": row.get("quantity", 0),
                        "reserve": row.get("reserve", 0),
                        "inTransit": row.get("inTransit", 0),
                        "product_code": row_code or product_code,
                    })
            # Пауза между днями для снижения нагрузки
            await asyncio.sleep(0.2)
            current += timedelta(days=1)

        logger.info(f"✅ Получено {len(stock_data)} дневных записей остатков для кода {product_code}")
        return stock_data

class MLModelTrainer:
    """Класс для обучения ML моделей"""
    
    def __init__(self):
        self.models_dir = "data/real_models"
        os.makedirs(self.models_dir, exist_ok=True)
    
    def prepare_features(self, sales_data: List[Dict], stock_data: List[Dict]) -> pd.DataFrame:
        """Подготовка признаков: продажи вычисляются как убывание остатков (stock delta)."""
        # Формируем DataFrame остатков
        if not stock_data:
            return pd.DataFrame()

        sdf = pd.DataFrame(stock_data)
        if sdf.empty:
            return pd.DataFrame()
        sdf['date'] = pd.to_datetime(sdf['date'])
        sdf = sdf.sort_values('date').reset_index(drop=True)

        # Нормализуем столбцы
        for col in ['quantity', 'reserve', 'inTransit']:
            if col not in sdf.columns:
                sdf[col] = 0

        # Вычисляем дневные продажи как убывание остатков (без учета пополнений)
        sdf['prev_stock'] = sdf['quantity'].shift(1).fillna(sdf['quantity'])
        raw_delta = sdf['prev_stock'] - sdf['quantity']
        sdf['daily_sales'] = raw_delta.clip(lower=0)

        # Подготовка итогового DataFrame с признаками
        sdf['year'] = sdf['date'].dt.year
        sdf['month'] = sdf['date'].dt.month
        sdf['day'] = sdf['date'].dt.day
        sdf['day_of_year'] = sdf['date'].dt.dayofyear
        sdf['day_of_week'] = sdf['date'].dt.dayofweek
        sdf['is_month_start'] = sdf['day'] == 1
        sdf['is_quarter_start'] = (sdf['day'] == 1) & (sdf['month'].isin([1, 4, 7, 10]))
        sdf['is_weekend'] = sdf['day_of_week'] >= 5
        sdf['is_holiday_season'] = sdf['month'].isin([12, 1, 2])
        sdf['is_summer_season'] = sdf['month'].isin([6, 7, 8])

        # Лаги и скользящие средние
        sdf['stock_lag_1'] = sdf['quantity'].shift(1).fillna(sdf['quantity'])
        sdf['sales_lag_1'] = sdf['daily_sales'].shift(1).fillna(0)
        sdf['sales_lag_7'] = sdf['daily_sales'].shift(7).fillna(0)
        sdf['sales_lag_30'] = sdf['daily_sales'].shift(30).fillna(0)
        sdf['sales_ma_7'] = sdf['daily_sales'].rolling(7, min_periods=1).mean()
        sdf['stock_ma_7'] = sdf['quantity'].rolling(7, min_periods=1).mean()

        # Чистим от NaN (после lag/rolling останутся первые значения, но мы их уже заполнили)
        sdf = sdf.fillna(0)

        # Унификация набора колонок
        feature_df = sdf.rename(columns={'quantity': 'stock'})
        return feature_df
    
    def train_models(self, product_id: str, features_df: pd.DataFrame) -> Dict:
        """Обучение моделей"""
        if len(features_df) < 20:  # Уменьшаем минимальное количество данных
            logger.warning(f"⚠️ Недостаточно данных для товара {product_id}: {len(features_df)} записей")
            return {}
        
        # Подготовка данных
        feature_columns = [col for col in features_df.columns if col not in ['daily_sales', 'date']]
        X = features_df[feature_columns].values
        y = features_df['daily_sales'].values
        
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

    def build_universal_models_file(self) -> int:
        """Собирает единый файл /app/data/universal_forecast_models.pkl из сохраненных real_models."""
        models_root = self.models_dir
        universal = {'models': {}, 'results': {}, 'features': [], 'training_date': datetime.now().isoformat(), 'model_type': 'real_data'}
        try:
            for name in os.listdir(models_root):
                if not name.endswith('_metadata.json'):
                    continue
                meta_path = os.path.join(models_root, name)
                with open(meta_path, 'r') as f:
                    meta = json.load(f)
                pid = meta.get('product_id')
                results = meta.get('results', {})
                models = meta.get('models', {})
                if not pid or not results or not models:
                    continue
                # выбираем модель с лучшей accuracy
                best = max(results.keys(), key=lambda k: results[k].get('accuracy', 0))
                model_path = models.get(best)
                if not model_path or not os.path.exists(model_path):
                    continue
                with open(model_path, 'rb') as f:
                    model_obj = pickle.load(f)
                # пытаемся загрузить scaler рядом
                scaler_path = model_path.replace('.pkl', '_scaler.pkl')
                scaler_obj = None
                if os.path.exists(scaler_path):
                    with open(scaler_path, 'rb') as f:
                        scaler_obj = pickle.load(f)
                universal['models'][pid] = model_obj
                universal['results'][pid] = {'metadata': {'chosen_model': best, **results[best]}, 'scaler': scaler_obj}
            out_path = '/app/data/universal_forecast_models.pkl'
            with open(out_path, 'wb') as f:
                pickle.dump(universal, f)
            return len(universal['models'])
        except Exception as e:
            logger.error(f"Ошибка сборки универсального файла моделей: {e}")
            return 0
    
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
            # Получение данных об остатках
            stock_data = await data_collector.get_stock_data(product_id, days_back=120)

            # Подготовка признаков (продажи = убывание остатков)
            features_df = model_trainer.prepare_features([], stock_data)
            
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
        # Сборка универсального файла моделей
        built = model_trainer.build_universal_models_file()
        logger.info(f"✅ Система готова. Универсальный файл моделей собран, моделей: {built}")
    else:
        logger.warning("⚠️ Не удалось обучить ни одной модели. Проверьте API токен и лимиты.")

if __name__ == "__main__":
    asyncio.run(main()) 