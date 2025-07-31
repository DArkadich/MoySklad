#!/usr/bin/env python3
"""
ML-модель прогнозирования спроса на основе точных данных о потреблении
Использует результаты accurate_consumption_results.csv для обучения моделей
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import pickle

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_consumption_data(filename: str) -> pd.DataFrame:
    """Загружает данные о потреблении"""
    logger.info(f"Загрузка данных о потреблении из {filename}")
    
    try:
        df = pd.read_csv(filename)
        logger.info(f"Загружено {len(df)} записей о потреблении")
        
        # Конвертируем даты
        df['start_date'] = pd.to_datetime(df['start_date'])
        df['end_date'] = pd.to_datetime(df['end_date'])
        
        # Добавляем признаки времени
        df['year'] = df['start_date'].dt.year
        df['quarter'] = df['start_date'].apply(get_quarter)
        df['month'] = df['start_date'].dt.month
        
        # Фильтруем валидные записи
        valid_data = df[
            (df['avg_consumption'] > 0) & 
            (df['days_for_consumption'] > 0) &
            (df['total_sales'] > 0)
        ]
        
        logger.info(f"Валидных записей: {len(valid_data)}")
        return valid_data
        
    except Exception as e:
        logger.error(f"Ошибка загрузки данных: {e}")
        return pd.DataFrame()

def prepare_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """Подготавливает признаки для ML-модели"""
    logger.info("Подготовка признаков для ML-модели...")
    
    # Базовые признаки
    features = [
        'year', 'quarter', 'month',
        'total_days', 'days_with_stock_above_3', 'days_for_consumption',
        'total_sales', 'days_with_sales', 'max_stock', 'min_stock'
    ]
    
    # Создаем признаки
    X = df[features].copy()
    
    # Добавляем производные признаки
    X['sales_per_day'] = df['total_sales'] / df['total_days']
    X['stock_availability_ratio'] = df['days_with_stock_above_3'] / df['total_days']
    X['sales_frequency'] = df['days_with_sales'] / df['total_days']
    X['stock_range'] = df['max_stock'] - df['min_stock']
    X['avg_stock'] = (df['max_stock'] + df['min_stock']) / 2
    
    # Целевая переменная
    y = df['avg_consumption']
    
    logger.info(f"Признаки: {list(X.columns)}")
    logger.info(f"Размер данных: {X.shape}")
    
    return X, y

def train_models(X: pd.DataFrame, y: pd.Series) -> Dict:
    """Обучает ML-модели"""
    logger.info("Обучение ML-моделей...")
    
    # Разделяем данные
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    models = {}
    results = {}
    
    # 1. Линейная регрессия
    logger.info("Обучение линейной регрессии...")
    lr_model = LinearRegression()
    lr_model.fit(X_train, y_train)
    
    lr_pred = lr_model.predict(X_test)
    lr_mae = mean_absolute_error(y_test, lr_pred)
    lr_r2 = r2_score(y_test, lr_pred)
    
    models['linear_regression'] = lr_model
    results['linear_regression'] = {
        'mae': lr_mae,
        'r2': lr_r2,
        'predictions': lr_pred
    }
    
    logger.info(f"Линейная регрессия - MAE: {lr_mae:.4f}, R²: {lr_r2:.4f}")
    
    # 2. Случайный лес
    logger.info("Обучение случайного леса...")
    rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
    rf_model.fit(X_train, y_train)
    
    rf_pred = rf_model.predict(X_test)
    rf_mae = mean_absolute_error(y_test, rf_pred)
    rf_r2 = r2_score(y_test, rf_pred)
    
    models['random_forest'] = rf_model
    results['random_forest'] = {
        'mae': rf_mae,
        'r2': rf_r2,
        'predictions': rf_pred,
        'feature_importance': dict(zip(X.columns, rf_model.feature_importances_))
    }
    
    logger.info(f"Случайный лес - MAE: {rf_mae:.4f}, R²: {rf_r2:.4f}")
    
    return models, results, X_test, y_test

def save_models(models: Dict, results: Dict, filename: str):
    """Сохраняет обученные модели"""
    logger.info(f"Сохранение моделей в {filename}")
    
    model_data = {
        'models': models,
        'results': results,
        'timestamp': datetime.now().isoformat()
    }
    
    with open(filename, 'wb') as f:
        pickle.dump(model_data, f)
    
    logger.info("Модели сохранены!")

def get_quarter(date: datetime) -> int:
    """Возвращает номер квартала для даты"""
    return (date.month - 1) // 3 + 1

def create_forecast_features(product_code: str, current_date: datetime) -> pd.DataFrame:
    """Создает признаки для прогнозирования"""
    logger.info(f"Создание признаков для прогноза товара {product_code} на {current_date}")
    
    # Базовые признаки времени
    features = {
        'year': current_date.year,
        'quarter': get_quarter(current_date),
        'month': current_date.month,
        'total_days': 90,  # Квартал
        'days_with_stock_above_3': 60,  # Предполагаем 2/3 дней с остатками
        'days_for_consumption': 30,  # 1/3 дней без остатков
        'total_sales': 0,  # Будет предсказано
        'days_with_sales': 15,  # Предполагаем продажи в половине дней
        'max_stock': 50,  # Типичный максимум
        'min_stock': 5,   # Типичный минимум
    }
    
    # Производные признаки
    features['sales_per_day'] = features['total_sales'] / features['total_days']
    features['stock_availability_ratio'] = features['days_with_stock_above_3'] / features['total_days']
    features['sales_frequency'] = features['days_with_sales'] / features['total_days']
    features['stock_range'] = features['max_stock'] - features['min_stock']
    features['avg_stock'] = (features['max_stock'] + features['min_stock']) / 2
    
    return pd.DataFrame([features])

def predict_consumption(models: Dict, features: pd.DataFrame) -> Dict:
    """Делает прогноз потребления"""
    logger.info("Прогнозирование потребления...")
    
    predictions = {}
    
    for model_name, model in models.items():
        try:
            pred = model.predict(features)[0]
            predictions[model_name] = max(0, pred)  # Потребление не может быть отрицательным
        except Exception as e:
            logger.error(f"Ошибка прогноза для {model_name}: {e}")
            predictions[model_name] = 0
    
    return predictions

def main():
    """Основная функция"""
    logger.info("Запуск ML-модели прогнозирования спроса...")
    
    # Загружаем данные
    consumption_df = load_consumption_data('/app/data/accurate_consumption_results.csv')
    
    if consumption_df.empty:
        logger.error("Не удалось загрузить данные о потреблении")
        return
    
    # Подготавливаем признаки
    X, y = prepare_features(consumption_df)
    
    if len(X) < 10:
        logger.warning(f"Мало данных для обучения: {len(X)} записей")
        return
    
    # Обучаем модели
    models, results, X_test, y_test = train_models(X, y)
    
    # Сохраняем модели
    save_models(models, results, '/app/data/forecast_models.pkl')
    
    # Тестируем прогноз
    logger.info("Тестирование прогноза...")
    
    # Берем первый товар для примера
    sample_product = consumption_df['product_code'].iloc[0]
    current_date = datetime.now()
    
    # Создаем признаки для прогноза
    forecast_features = create_forecast_features(sample_product, current_date)
    
    # Делаем прогноз
    predictions = predict_consumption(models, forecast_features)
    
    logger.info(f"Прогноз для товара {sample_product}:")
    for model_name, pred in predictions.items():
        logger.info(f"  {model_name}: {pred:.4f} единиц/день")
    
    # Сохраняем результаты
    results_df = pd.DataFrame({
        'model': list(results.keys()),
        'mae': [results[model]['mae'] for model in results.keys()],
        'r2': [results[model]['r2'] for model in results.keys()]
    })
    
    results_df.to_csv('/app/data/model_performance.csv', index=False)
    logger.info("Результаты сохранены в /app/data/model_performance.csv")
    
    # Выводим важность признаков для случайного леса
    if 'random_forest' in results:
        importance = results['random_forest']['feature_importance']
        logger.info("Важность признаков (случайный лес):")
        for feature, importance_score in sorted(importance.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {feature}: {importance_score:.4f}")
    
    logger.info("Обучение ML-моделей завершено!")

if __name__ == "__main__":
    main() 