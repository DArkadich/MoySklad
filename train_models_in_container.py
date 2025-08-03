#!/usr/bin/env python3
"""
Скрипт для обучения ML моделей на реальных данных из MoySklad внутри Docker контейнера
"""

import asyncio
import httpx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import logging
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

class MoySkladDataCollector:
    """Класс для сбора данных из MoySklad API"""
    
    def __init__(self):
        self.api_token = os.getenv('MOYSKLAD_API_TOKEN')
        self.api_url = os.getenv('MOYSKLAD_API_URL', 'https://api.moysklad.ru/api/remap/1.2')
        
        if not self.api_token:
            raise ValueError("MOYSKLAD_API_TOKEN не найден в переменных окружения")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
    
    async def get_all_products(self) -> List[Dict]:
        """Получение всех товаров из MoySklad"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/entity/product",
                    headers=self.headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    products = data.get("rows", [])
                    logger.info(f"Получено {len(products)} товаров из MoySklad")
                    return products
                else:
                    logger.error(f"Ошибка API MoySklad: {response.status_code} - {response.text}")
                    return []
                    
        except Exception as e:
            logger.error(f"Ошибка получения товаров: {e}")
            return []
    
    async def get_sales_data(self, product_id: str, days_back: int = 180) -> List[Dict]:
        """Получение данных о продажах товара"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            async with httpx.AsyncClient() as client:
                # Получаем документы продаж
                response = await client.get(
                    f"{self.api_url}/entity/demand",
                    headers=self.headers,
                    params={
                        "filter": f"moment>={start_date.isoformat()},moment<={end_date.isoformat()}",
                        "limit": 1000
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    logger.error(f"Ошибка получения продаж: {response.status_code}")
                    return []
                
                data = response.json()
                sales_data = []
                
                for demand in data.get("rows", []):
                    # Получаем позиции документа
                    positions_response = await client.get(
                        f"{self.api_url}/entity/demand/{demand['id']}/positions",
                        headers=self.headers,
                        timeout=30.0
                    )
                    
                    if positions_response.status_code == 200:
                        positions_data = positions_response.json()
                        
                        for position in positions_data.get("rows", []):
                            if position["assortment"]["id"] == product_id:
                                sales_data.append({
                                    "date": demand["moment"],
                                    "quantity": position["quantity"],
                                    "price": position["price"] / 100,  # Цена из копеек
                                    "sum": position["sum"] / 100
                                })
                
                logger.info(f"Получено {len(sales_data)} записей продаж для товара {product_id}")
                return sales_data
                
        except Exception as e:
            logger.error(f"Ошибка получения данных о продажах для {product_id}: {e}")
            return []
    
    async def get_stock_data(self, product_id: str, days_back: int = 30) -> List[Dict]:
        """Получение данных об остатках товара"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            async with httpx.AsyncClient() as client:
                # Получаем отчет об остатках
                response = await client.get(
                    f"{self.api_url}/report/stock/all",
                    headers=self.headers,
                    params={
                        "filter": f"assortmentId={product_id}",
                        "momentFrom": start_date.isoformat(),
                        "momentTo": end_date.isoformat()
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    logger.error(f"Ошибка получения остатков: {response.status_code}")
                    return []
                
                data = response.json()
                stock_data = []
                
                for row in data.get("rows", []):
                    stock_data.append({
                        "date": row.get("moment", datetime.now().isoformat()),
                        "quantity": row.get("quantity", 0),
                        "reserve": row.get("reserve", 0),
                        "inTransit": row.get("inTransit", 0)
                    })
                
                logger.info(f"Получено {len(stock_data)} записей остатков для товара {product_id}")
                return stock_data
                
        except Exception as e:
            logger.error(f"Ошибка получения данных об остатках для {product_id}: {e}")
            return []

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
        if len(features_df) < 30:
            logger.warning(f"Недостаточно данных для товара {product_id}: {len(features_df)} записей")
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
        rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
        rf_model.fit(X_train_scaled, y_train)
        rf_score = rf_model.score(X_test_scaled, y_test)
        models['random_forest'] = {
            'model': rf_model,
            'scaler': scaler,
            'accuracy': rf_score,
            'feature_columns': feature_columns
        }
        
        logger.info(f"Модели для товара {product_id} обучены:")
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
        
        logger.info(f"Модели для товара {product_id} сохранены в {self.models_dir}")

async def main():
    """Основная функция"""
    logger.info("🚀 Начинаем обучение моделей на реальных данных из MoySklad (в контейнере)")
    
    # Инициализация
    data_collector = MoySkladDataCollector()
    model_trainer = MLModelTrainer()
    
    # Получение всех товаров
    products = await data_collector.get_all_products()
    
    if not products:
        logger.error("Не удалось получить товары из MoySklad")
        return
    
    logger.info(f"Найдено {len(products)} товаров для обучения")
    
    # Ограничиваем количество товаров для тестирования
    test_products = products[:5]  # Первые 5 товаров
    
    for product in test_products:
        product_id = product['id']
        product_name = product.get('name', 'Неизвестный товар')
        product_code = product.get('code', '')
        
        logger.info(f"📦 Обрабатываем товар: {product_name} (ID: {product_id}, Код: {product_code})")
        
        try:
            # Получение данных о продажах
            sales_data = await data_collector.get_sales_data(product_id, days_back=180)
            
            if not sales_data:
                logger.warning(f"Нет данных о продажах для товара {product_name}")
                continue
            
            # Получение данных об остатках
            stock_data = await data_collector.get_stock_data(product_id, days_back=30)
            
            # Подготовка признаков
            features_df = model_trainer.prepare_features(sales_data, stock_data)
            
            if features_df.empty:
                logger.warning(f"Не удалось подготовить признаки для товара {product_name}")
                continue
            
            # Обучение моделей
            models = model_trainer.train_models(product_id, features_df)
            
            if models:
                # Сохранение моделей
                model_trainer.save_models(product_id, models)
                logger.info(f"✅ Модели для товара {product_name} успешно обучены и сохранены")
            else:
                logger.warning(f"Не удалось обучить модели для товара {product_name}")
        
        except Exception as e:
            logger.error(f"Ошибка обработки товара {product_name}: {e}")
            continue
    
    logger.info("🎉 Обучение моделей завершено!")

if __name__ == "__main__":
    asyncio.run(main()) 