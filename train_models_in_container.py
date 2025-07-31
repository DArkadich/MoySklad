#!/usr/bin/env python3
"""
Скрипт для обучения ML моделей прямо в контейнере
Запускается внутри Docker контейнера: docker exec -it forecast-api python3 train_models_in_container.py
"""

import os
import sys
import logging
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ContainerModelTrainer:
    """Тренировщик моделей для работы в контейнере"""
    
    def __init__(self):
        self.models_dir = "/app/data/models"
        os.makedirs(self.models_dir, exist_ok=True)
        
    def create_test_data(self):
        """Создает тестовые данные если исторических нет"""
        logger.info("📊 Создание тестовых данных...")
        
        # Создаем тестовые данные за 4 года
        dates = pd.date_range(start='2020-01-01', end='2024-01-01', freq='D')
        
        # Создаем несколько товаров
        products = ['PROD001', 'PROD002', 'PROD003']
        
        stock_data = []
        sales_data = []
        
        for product in products:
            # Базовые значения для каждого товара
            base_stock = np.random.randint(50, 200)
            base_sales = np.random.randint(0, 10)
            
            for date in dates:
                # Добавляем сезонность и тренд
                seasonal_factor = 1 + 0.3 * np.sin(2 * np.pi * date.dayofyear / 365)
                trend_factor = 1 + 0.1 * (date - dates[0]).days / 365
                
                # Генерируем данные
                stock = max(0, int(base_stock * seasonal_factor * trend_factor + np.random.normal(0, 10)))
                sales = max(0, int(base_sales * seasonal_factor * trend_factor + np.random.normal(0, 2)))
                
                stock_data.append({
                    'date': date,
                    'product_code': product,
                    'stock': stock,
                    'product_name': f'Товар {product}'
                })
                
                sales_data.append({
                    'date': date,
                    'product_code': product,
                    'quantity': sales,
                    'product_name': f'Товар {product}'
                })
        
        # Сохраняем данные
        stock_df = pd.DataFrame(stock_data)
        sales_df = pd.DataFrame(sales_data)
        
        stock_df.to_csv('/app/data/stock_history.csv', index=False)
        sales_df.to_csv('/app/data/sales_history.csv', index=False)
        
        logger.info(f"✅ Создано {len(stock_data)} записей для {len(products)} товаров")
        return products
    
    def prepare_features(self, stock_data, sales_data):
        """Подготавливает признаки для ML"""
        logger.info("🔧 Подготовка признаков...")
        
        # Объединяем данные
        data = pd.merge(stock_data, sales_data, on=['date', 'product_code'], how='outer')
        data = data.fillna(0)
        
        # Создаем признаки
        data['year'] = data['date'].dt.year
        data['month'] = data['date'].dt.month
        data['day_of_week'] = data['date'].dt.dayofweek
        data['day_of_year'] = data['date'].dt.dayofyear
        
        # Лаги
        for lag in [1, 7, 30]:
            data[f'stock_lag_{lag}'] = data.groupby('product_code')['stock'].shift(lag)
            data[f'sales_lag_{lag}'] = data.groupby('product_code')['quantity'].shift(lag)
        
        # Скользящие средние
        for window in [7, 30]:
            data[f'stock_ma_{window}'] = data.groupby('product_code')['stock'].rolling(window).mean().reset_index(0, drop=True)
            data[f'sales_ma_{window}'] = data.groupby('product_code')['quantity'].rolling(window).mean().reset_index(0, drop=True)
        
        # Статистики
        data['stock_std_30'] = data.groupby('product_code')['stock'].rolling(30).std().reset_index(0, drop=True)
        data['sales_std_30'] = data.groupby('product_code')['quantity'].rolling(30).std().reset_index(0, drop=True)
        
        # Удаляем NaN
        data = data.dropna()
        
        return data
    
    def train_model_for_product(self, product_data, product_code):
        """Обучает модель для конкретного товара"""
        logger.info(f"🎯 Обучение модели для товара {product_code}...")
        
        # Признаки для обучения
        feature_columns = [
            'year', 'month', 'day_of_week', 'day_of_year',
            'stock_lag_1', 'stock_lag_7', 'stock_lag_30',
            'sales_lag_1', 'sales_lag_7', 'sales_lag_30',
            'stock_ma_7', 'stock_ma_30', 'sales_ma_7', 'sales_ma_30',
            'stock_std_30', 'sales_std_30'
        ]
        
        X = product_data[feature_columns]
        y = product_data['quantity']  # Прогнозируем продажи
        
        # Обучаем модель
        model = RandomForestRegressor(n_estimators=200, random_state=42)
        model.fit(X, y)
        
        # Сохраняем модель
        model_path = os.path.join(self.models_dir, f"{product_code}_model.joblib")
        joblib.dump(model, model_path)
        
        # Сохраняем скейлер
        scaler = StandardScaler()
        scaler.fit(X)
        scaler_path = os.path.join(self.models_dir, f"{product_code}_scaler.joblib")
        joblib.dump(scaler, scaler_path)
        
        logger.info(f"✅ Модель для {product_code} сохранена")
        return model_path
    
    def train_all_models(self):
        """Обучает модели для всех товаров"""
        logger.info("🚀 Начало обучения моделей...")
        
        try:
            # Создаем тестовые данные если их нет
            if not os.path.exists('/app/data/stock_history.csv'):
                products = self.create_test_data()
            else:
                # Загружаем существующие данные
                stock_data = pd.read_csv('/app/data/stock_history.csv')
                sales_data = pd.read_csv('/app/data/sales_history.csv')
                products = stock_data['product_code'].unique()
            
            # Загружаем данные
            stock_data = pd.read_csv('/app/data/stock_history.csv')
            sales_data = pd.read_csv('/app/data/sales_history.csv')
            
            # Конвертируем даты
            stock_data['date'] = pd.to_datetime(stock_data['date'])
            sales_data['date'] = pd.to_datetime(sales_data['date'])
            
            # Подготавливаем признаки
            data = self.prepare_features(stock_data, sales_data)
            
            # Обучаем модели для каждого товара
            trained_models = []
            for product_code in products:
                product_data = data[data['product_code'] == product_code]
                if len(product_data) > 100:  # Минимум данных для обучения
                    model_path = self.train_model_for_product(product_data, product_code)
                    trained_models.append(model_path)
            
            logger.info(f"✅ Обучено {len(trained_models)} моделей")
            return trained_models
            
        except Exception as e:
            logger.error(f"❌ Ошибка обучения: {e}")
            raise

def main():
    """Основная функция"""
    logger.info("🎯 Запуск обучения ML моделей в контейнере...")
    
    try:
        trainer = ContainerModelTrainer()
        trained_models = trainer.train_all_models()
        
        logger.info("🎉 Обучение завершено успешно!")
        logger.info(f"📊 Обучено моделей: {len(trained_models)}")
        logger.info("🔄 Система готова к использованию")
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 