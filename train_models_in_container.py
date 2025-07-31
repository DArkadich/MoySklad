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
        try:
            os.makedirs(self.models_dir, exist_ok=True)
        except PermissionError:
            # Если нет прав, создаем в временной папке
            self.models_dir = "/tmp/models"
            os.makedirs(self.models_dir, exist_ok=True)
            logger.info(f"📁 Модели будут сохранены в {self.models_dir}")
        
    def create_test_data(self, data_dir):
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
        
        stock_file = os.path.join(data_dir, 'stock_history.csv')
        sales_file = os.path.join(data_dir, 'sales_history.csv')
        
        stock_df.to_csv(stock_file, index=False)
        sales_df.to_csv(sales_file, index=False)
        
        logger.info(f"✅ Создано {len(stock_data)} записей для {len(products)} товаров")
        return products
    
    def load_real_historical_data(self, data_dir):
        """Загружает реальные исторические данные"""
        logger.info("📊 Загрузка реальных исторических данных...")
        
        # Проверяем наличие реальных данных
        production_data_file = os.path.join(data_dir, 'production_stock_data.csv')
        
        if os.path.exists(production_data_file):
            try:
                # Загружаем реальные данные
                data = pd.read_csv(production_data_file)
                logger.info(f"✅ Загружено {len(data)} записей из реальных данных")
                
                # Извлекаем уникальные товары
                products = data['product_code'].unique() if 'product_code' in data.columns else []
                logger.info(f"📦 Найдено {len(products)} товаров")
                
                return data, products
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки реальных данных: {e}")
                return None, []
        else:
            logger.warning("⚠️ Реальные данные не найдены, используем тестовые")
            return None, []
    
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
    
    def prepare_features_from_real_data(self, real_data):
        """Подготавливает признаки из реальных данных"""
        logger.info("🔧 Подготовка признаков из реальных данных...")
        
        # Конвертируем даты если есть
        if 'date' in real_data.columns:
            real_data['date'] = pd.to_datetime(real_data['date'])
        
        # Создаем базовые признаки
        if 'date' in real_data.columns:
            real_data['year'] = real_data['date'].dt.year
            real_data['month'] = real_data['date'].dt.month
            real_data['day_of_week'] = real_data['date'].dt.dayofweek
            real_data['day_of_year'] = real_data['date'].dt.dayofyear
        
        # Добавляем числовые признаки если их нет
        if 'quantity' not in real_data.columns:
            real_data['quantity'] = 1  # По умолчанию
        
        if 'stock' not in real_data.columns:
            real_data['stock'] = 100  # По умолчанию
        
        # Группируем по товару и дате для агрегации
        if 'product_code' in real_data.columns:
            # Создаем лаги и скользящие средние
            for lag in [1, 7, 30]:
                real_data[f'quantity_lag_{lag}'] = real_data.groupby('product_code')['quantity'].shift(lag)
                real_data[f'stock_lag_{lag}'] = real_data.groupby('product_code')['stock'].shift(lag)
            
            for window in [7, 30]:
                real_data[f'quantity_ma_{window}'] = real_data.groupby('product_code')['quantity'].rolling(window).mean().reset_index(0, drop=True)
                real_data[f'stock_ma_{window}'] = real_data.groupby('product_code')['stock'].rolling(window).mean().reset_index(0, drop=True)
            
            # Статистики
            real_data['quantity_std_30'] = real_data.groupby('product_code')['quantity'].rolling(30).std().reset_index(0, drop=True)
            real_data['stock_std_30'] = real_data.groupby('product_code')['stock'].rolling(30).std().reset_index(0, drop=True)
        
        # Удаляем NaN
        real_data = real_data.dropna()
        
        logger.info(f"✅ Подготовлено {len(real_data)} записей с признаками")
        return real_data
    
    def train_model_for_product(self, product_data, product_code):
        """Обучает модель для конкретного товара"""
        logger.info(f"🎯 Обучение модели для товара {product_code}...")
        
        # Признаки для обучения (адаптивные)
        base_features = ['year', 'month', 'day_of_week', 'day_of_year']
        lag_features = []
        ma_features = []
        std_features = []
        
        # Добавляем доступные признаки
        for lag in [1, 7, 30]:
            if f'stock_lag_{lag}' in product_data.columns:
                lag_features.append(f'stock_lag_{lag}')
            if f'quantity_lag_{lag}' in product_data.columns:
                lag_features.append(f'quantity_lag_{lag}')
        
        for window in [7, 30]:
            if f'stock_ma_{window}' in product_data.columns:
                ma_features.append(f'stock_ma_{window}')
            if f'quantity_ma_{window}' in product_data.columns:
                ma_features.append(f'quantity_ma_{window}')
        
        if 'stock_std_30' in product_data.columns:
            std_features.append('stock_std_30')
        if 'quantity_std_30' in product_data.columns:
            std_features.append('quantity_std_30')
        
        feature_columns = base_features + lag_features + ma_features + std_features
        
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
            # Создаем папку data если её нет
            data_dir = '/app/data'
            try:
                os.makedirs(data_dir, exist_ok=True)
            except PermissionError:
                data_dir = '/tmp/data'
                os.makedirs(data_dir, exist_ok=True)
                logger.info(f"📁 Данные будут сохранены в {data_dir}")
            
            # Пытаемся загрузить реальные исторические данные
            real_data, real_products = self.load_real_historical_data(data_dir)
            
            if real_data is not None and len(real_products) > 0:
                # Используем реальные данные
                logger.info("🎯 Используем реальные исторические данные")
                
                # Подготавливаем признаки из реальных данных
                data = self.prepare_features_from_real_data(real_data)
                
                # Обучаем модели для каждого товара
                trained_models = []
                for product_code in real_products[:10]:  # Ограничиваем первыми 10 товарами
                    product_data = data[data['product_code'] == product_code]
                    if len(product_data) > 100:  # Минимум данных для обучения
                        model_path = self.train_model_for_product(product_data, product_code)
                        trained_models.append(model_path)
                
                logger.info(f"✅ Обучено {len(trained_models)} моделей на реальных данных")
                return trained_models
            else:
                # Используем тестовые данные
                logger.info("🧪 Используем тестовые данные")
                
                # Создаем тестовые данные если их нет
                stock_file = os.path.join(data_dir, 'stock_history.csv')
                sales_file = os.path.join(data_dir, 'sales_history.csv')
                
                if not os.path.exists(stock_file):
                    products = self.create_test_data(data_dir)
                else:
                    # Загружаем существующие данные
                    stock_data = pd.read_csv(stock_file)
                    sales_data = pd.read_csv(sales_file)
                    products = stock_data['product_code'].unique()
                
                # Загружаем данные
                stock_data = pd.read_csv(stock_file)
                sales_data = pd.read_csv(sales_file)
            
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