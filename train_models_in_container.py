#!/usr/bin/env python3
"""
Скрипт для обучения ML моделей только на реальных исторических данных.
Если данных нет — завершает работу с ошибкой.
"""

import os
import sys
import logging
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
    """Тренировщик моделей для работы только с реальными данными"""
    
    def __init__(self):
        self.models_dir = "/app/data/models"
        try:
            os.makedirs(self.models_dir, exist_ok=True)
        except PermissionError:
            self.models_dir = "/tmp/models"
            os.makedirs(self.models_dir, exist_ok=True)
            logger.info(f"📁 Модели будут сохранены в {self.models_dir}")

    def load_real_historical_data(self, data_dir):
        """Загружает реальные исторические данные"""
        logger.info("📊 Загрузка реальных исторических данных...")
        production_data_file = os.path.join(data_dir, 'production_stock_data.csv')
        if os.path.exists(production_data_file):
            try:
                data = pd.read_csv(production_data_file)
                logger.info(f"✅ Загружено {len(data)} записей из production_stock_data.csv")
                products = data['product_code'].unique() if 'product_code' in data.columns else []
                logger.info(f"📦 Найдено {len(products)} товаров")
                return data, products
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки production_stock_data.csv: {e}")
                return None, []
        else:
            logger.error("❌ Нет файла production_stock_data.csv! Обучение невозможно.")
            return None, []

    def prepare_features_from_real_data(self, real_data):
        logger.info("🔧 Подготовка признаков из реальных данных...")
        if 'date' in real_data.columns:
            real_data['date'] = pd.to_datetime(real_data['date'])
            real_data['year'] = real_data['date'].dt.year
            real_data['month'] = real_data['date'].dt.month
            real_data['day_of_week'] = real_data['date'].dt.dayofweek
            real_data['day_of_year'] = real_data['date'].dt.dayofyear
        if 'quantity' not in real_data.columns:
            logger.error('❌ Нет колонки quantity в данных!')
            raise ValueError('Нет колонки quantity в данных!')
        if 'stock' not in real_data.columns:
            logger.error('❌ Нет колонки stock в данных!')
            raise ValueError('Нет колонки stock в данных!')
        if 'product_code' in real_data.columns:
            for lag in [1, 7, 30]:
                real_data[f'quantity_lag_{lag}'] = real_data.groupby('product_code')['quantity'].shift(lag)
                real_data[f'stock_lag_{lag}'] = real_data.groupby('product_code')['stock'].shift(lag)
            for window in [7, 30]:
                real_data[f'quantity_ma_{window}'] = real_data.groupby('product_code')['quantity'].rolling(window).mean().reset_index(0, drop=True)
                real_data[f'stock_ma_{window}'] = real_data.groupby('product_code')['stock'].rolling(window).mean().reset_index(0, drop=True)
            real_data['quantity_std_30'] = real_data.groupby('product_code')['quantity'].rolling(30).std().reset_index(0, drop=True)
            real_data['stock_std_30'] = real_data.groupby('product_code')['stock'].rolling(30).std().reset_index(0, drop=True)
        real_data = real_data.dropna()
        logger.info(f"✅ Подготовлено {len(real_data)} записей с признаками")
        return real_data

    def train_model_for_product(self, product_data, product_code):
        logger.info(f"🎯 Обучение модели для товара {product_code}...")
        base_features = ['year', 'month', 'day_of_week', 'day_of_year']
        lag_features = []
        ma_features = []
        std_features = []
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
        y = product_data['quantity']
        model = RandomForestRegressor(n_estimators=200, random_state=42)
        model.fit(X, y)
        model_path = os.path.join(self.models_dir, f"{product_code}_model.joblib")
        joblib.dump(model, model_path)
        scaler = StandardScaler()
        scaler.fit(X)
        scaler_path = os.path.join(self.models_dir, f"{product_code}_scaler.joblib")
        joblib.dump(scaler, scaler_path)
        logger.info(f"✅ Модель для {product_code} сохранена")
        return model_path

    def train_all_models(self):
        logger.info("🚀 Начало обучения моделей...")
        data_dir = '/app/data'
        try:
            os.makedirs(data_dir, exist_ok=True)
        except PermissionError:
            data_dir = '/tmp/data'
            os.makedirs(data_dir, exist_ok=True)
            logger.info(f"📁 Данные будут искаться в {data_dir}")
        real_data, real_products = self.load_real_historical_data(data_dir)
        if real_data is None or len(real_products) == 0:
            logger.error("❌ Нет реальных исторических данных для обучения! Завершаем работу.")
            sys.exit(1)
        logger.info("🎯 Используем только реальные исторические данные")
        data = self.prepare_features_from_real_data(real_data)
        trained_models = []
        for product_code in real_products:
            product_data = data[data['product_code'] == product_code]
            if len(product_data) > 100:
                model_path = self.train_model_for_product(product_data, product_code)
                trained_models.append(model_path)
        logger.info(f"✅ Обучено {len(trained_models)} моделей на реальных данных")
        return trained_models

def main():
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