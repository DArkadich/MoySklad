#!/usr/bin/env python3
"""
Обучение универсальных ML-моделей на всех товарах
Создает модели, которые работают для любого товара
"""

import pandas as pd
import numpy as np
import pickle
import logging
import os
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_and_prepare_data():
    """Загружает и подготавливает данные для всех товаров"""
    logger.info("Загрузка данных о потреблении...")
    
    try:
        # Определяем путь к данным
        data_file = os.path.join(os.getcwd(), 'data', 'accurate_consumption_results.csv')
        
        # Загружаем данные
        df = pd.read_csv(data_file)
        logger.info(f"Загружено {len(df)} записей")
        
        # Фильтруем валидные записи
        valid_data = df.dropna()
        logger.info(f"Валидных записей: {len(valid_data)}")
        
        # Анализируем количество товаров
        unique_products = valid_data['product_code'].nunique()
        logger.info(f"Уникальных товаров: {unique_products}")
        
        # Показываем распределение по товарам
        product_counts = valid_data['product_code'].value_counts()
        logger.info("Топ-10 товаров по количеству записей:")
        for i, (product, count) in enumerate(product_counts.head(10).items(), 1):
            logger.info(f"  {i}. Товар {product}: {count} записей")
        
        return valid_data
        
    except Exception as e:
        logger.error(f"Ошибка загрузки данных: {e}")
        return None

def create_universal_features(df):
    """Создает универсальные признаки для всех товаров"""
    logger.info("Создание универсальных признаков...")
    
    # Базовые признаки
    features = [
        'year', 'quarter', 'month', 'total_days', 
        'days_with_stock_above_3', 'days_for_consumption',
        'total_sales', 'days_with_sales', 'max_stock', 
        'min_stock', 'sales_per_day', 'stock_availability_ratio',
        'sales_frequency', 'stock_range', 'avg_stock'
    ]
    
    # Добавляем признаки товара
    df['product_code_numeric'] = pd.to_numeric(df['product_code'], errors='coerce')
    
    # Создаем признаки категоризации товаров
    df['product_category'] = df['product_code_numeric'] % 1000  # Категория товара
    df['product_group'] = df['product_code_numeric'] // 1000   # Группа товара
    
    # Добавляем статистики по товарам
    product_stats = df.groupby('product_code').agg({
        'total_sales': ['mean', 'std'],
        'max_stock': ['mean', 'std'],
        'sales_per_day': ['mean', 'std']
    }).fillna(0)
    
    product_stats.columns = ['_'.join(col).strip() for col in product_stats.columns]
    product_stats = product_stats.reset_index()
    
    # Объединяем с основными данными
    df = df.merge(product_stats, on='product_code', how='left')
    
    # Заполняем пропуски
    df = df.fillna(0)
    
    # Финальный список признаков
    final_features = features + [
        'product_code_numeric', 'product_category', 'product_group',
        'total_sales_mean', 'total_sales_std',
        'max_stock_mean', 'max_stock_std',
        'sales_per_day_mean', 'sales_per_day_std'
    ]
    
    logger.info(f"Создано {len(final_features)} признаков")
    logger.info(f"Признаки: {final_features}")
    
    return df, final_features

def train_universal_models(df, features):
    """Обучает универсальные модели на всех товарах"""
    logger.info("Обучение универсальных ML-моделей...")
    
    # Подготавливаем данные
    X = df[features]
    y = df['consumption_per_day']
    
    # Разделяем на обучающую и тестовую выборки
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Нормализация признаков
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    models = {}
    results = {}
    
    # 1. Линейная регрессия
    logger.info("Обучение линейной регрессии...")
    lr = LinearRegression()
    lr.fit(X_train_scaled, y_train)
    
    y_pred_lr = lr.predict(X_test_scaled)
    mae_lr = mean_absolute_error(y_test, y_pred_lr)
    r2_lr = r2_score(y_test, y_pred_lr)
    
    models['linear_regression'] = lr
    results['linear_regression'] = {
        'mae': mae_lr,
        'r2': r2_lr,
        'scaler': scaler
    }
    
    logger.info(f"Линейная регрессия - MAE: {mae_lr:.4f}, R²: {r2_lr:.4f}")
    
    # 2. Случайный лес
    logger.info("Обучение случайного леса...")
    rf = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    rf.fit(X_train, y_train)
    
    y_pred_rf = rf.predict(X_test)
    mae_rf = mean_absolute_error(y_test, y_pred_rf)
    r2_rf = r2_score(y_test, y_pred_rf)
    
    models['random_forest'] = rf
    results['random_forest'] = {
        'mae': mae_rf,
        'r2': r2_rf,
        'feature_importance': dict(zip(features, rf.feature_importances_))
    }
    
    logger.info(f"Случайный лес - MAE: {mae_rf:.4f}, R²: {r2_rf:.4f}")
    
    return models, results, features

def save_models_and_results(models, results, features):
    """Сохраняет модели и результаты"""
    logger.info("Сохранение универсальных моделей...")
    
    # Создаем папку data если её нет
    data_dir = os.path.join(os.getcwd(), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # Сохраняем модели
    model_data = {
        'models': models,
        'results': results,
        'features': features,
        'training_date': datetime.now().isoformat(),
        'model_type': 'universal'
    }
    
    model_file = os.path.join(data_dir, 'universal_forecast_models.pkl')
    with open(model_file, 'wb') as f:
        pickle.dump(model_data, f)
    
    logger.info(f"Модели сохранены в {model_file}")
    
    # Сохраняем результаты
    results_df = pd.DataFrame([
        {
            'model': model_name,
            'mae': result['mae'],
            'r2': result['r2']
        }
        for model_name, result in results.items()
    ])
    
    results_file = os.path.join(data_dir, 'universal_model_performance.csv')
    results_df.to_csv(results_file, index=False)
    logger.info(f"Результаты сохранены в {results_file}")

def test_universal_forecast(models, results, features):
    """Тестирует универсальные модели на разных товарах"""
    logger.info("Тестирование универсальных моделей...")
    
    # Загружаем данные для тестирования
    data_file = os.path.join(os.getcwd(), 'data', 'accurate_consumption_results.csv')
    df = pd.read_csv(data_file)
    df = df.dropna()
    
    # Выбираем несколько разных товаров для тестирования
    test_products = df['product_code'].unique()[:5]
    
    for product_code in test_products:
        logger.info(f"Тестирование товара {product_code}...")
        
        # Получаем данные товара
        product_data = df[df['product_code'] == product_code].iloc[-1:].copy()
        
        if len(product_data) == 0:
            continue
            
        # Создаем признаки
        product_data, _ = create_universal_features(product_data)
        
        # Подготавливаем признаки
        X_test = product_data[features].iloc[0:1]
        
        # Делаем прогнозы
        predictions = {}
        
        # Линейная регрессия
        lr_model = models['linear_regression']
        lr_scaler = results['linear_regression']['scaler']
        X_test_scaled = lr_scaler.transform(X_test)
        predictions['linear_regression'] = lr_model.predict(X_test_scaled)[0]
        
        # Случайный лес
        rf_model = models['random_forest']
        predictions['random_forest'] = rf_model.predict(X_test)[0]
        
        # Выводим результаты
        logger.info(f"Прогноз для товара {product_code}:")
        for model_name, pred in predictions.items():
            logger.info(f"  {model_name}: {pred:.4f} единиц/день")

def analyze_feature_importance(results):
    """Анализирует важность признаков"""
    logger.info("Анализ важности признаков (случайный лес):")
    
    rf_importance = results['random_forest']['feature_importance']
    sorted_features = sorted(rf_importance.items(), key=lambda x: x[1], reverse=True)
    
    for feature, importance in sorted_features[:10]:
        logger.info(f"  {feature}: {importance:.4f}")

def main():
    """Основная функция"""
    logger.info("Запуск обучения универсальных ML-моделей...")
    
    # 1. Загружаем данные
    df = load_and_prepare_data()
    if df is None:
        logger.error("Не удалось загрузить данные")
        return
    
    # 2. Создаем универсальные признаки
    df, features = create_universal_features(df)
    
    # 3. Обучаем модели
    models, results, features = train_universal_models(df, features)
    
    # 4. Сохраняем модели и результаты
    save_models_and_results(models, results, features)
    
    # 5. Тестируем на разных товарах
    test_universal_forecast(models, results, features)
    
    # 6. Анализируем важность признаков
    analyze_feature_importance(results)
    
    logger.info("Обучение универсальных ML-моделей завершено!")

if __name__ == "__main__":
    main() 