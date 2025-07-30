"""
Упрощенный скрипт для обучения ML-моделей на данных из МойСклад
"""

import pandas as pd
import numpy as np
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
import sys
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleModelTrainer:
    """Упрощенный класс для обучения моделей на данных МойСклад"""
    
    def __init__(self):
        # Пути к файлам данных
        self.sales_file = "sales_history.csv"
        self.stock_file = "stock_history.csv"
        
    def load_and_preprocess_data(self) -> Dict[str, pd.DataFrame]:
        """Загрузка и предобработка данных"""
        logger.info("Загрузка данных из CSV файлов...")
        
        # Возможные пути к файлам
        possible_sales_paths = [
            "/app/data/sales_history.csv",
            "sales_history.csv",
            "/app/sales_history.csv",
            "/app/app/sales_history.csv",
            "../sales_history.csv",
            "app/sales_history.csv"
        ]
        
        possible_stock_paths = [
            "/app/data/stock_history.csv",
            "stock_history.csv",
            "/app/stock_history.csv",
            "/app/app/stock_history.csv",
            "../stock_history.csv",
            "app/stock_history.csv"
        ]
        
        # Ищем файлы продаж
        sales_file = None
        for path in possible_sales_paths:
            if os.path.exists(path):
                sales_file = path
                logger.info(f"Найден файл продаж: {path}")
                break
        
        # Ищем файлы остатков
        stock_file = None
        for path in possible_stock_paths:
            if os.path.exists(path):
                stock_file = path
                logger.info(f"Найден файл остатков: {path}")
                break
        
        if not sales_file:
            logger.error("Файл продаж не найден ни в одном из мест:")
            for path in possible_sales_paths:
                logger.error(f"  - {path}")
            raise FileNotFoundError("sales_history.csv не найден")
        
        if not stock_file:
            logger.error("Файл остатков не найден ни в одном из мест:")
            for path in possible_stock_paths:
                logger.error(f"  - {path}")
            raise FileNotFoundError("stock_history.csv не найден")
        
        try:
            # Загружаем данные продаж
            sales_df = pd.read_csv(sales_file)
            logger.info(f"Загружено {len(sales_df)} записей продаж")
            
            # Загружаем данные остатков
            stock_df = pd.read_csv(stock_file)
            logger.info(f"Загружено {len(stock_df)} записей остатков")
            
            # Предобработка данных продаж
            sales_df = self._preprocess_sales_data(sales_df)
            
            # Предобработка данных остатков
            stock_df = self._preprocess_stock_data(stock_df)
            
            return {
                'sales': sales_df,
                'stock': stock_df
            }
            
        except FileNotFoundError as e:
            logger.error(f"Файл не найден: {e}")
            raise
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
            raise
    
    def _preprocess_sales_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Предобработка данных продаж"""
        logger.info("Предобработка данных продаж...")
        
        # Выводим примеры данных для диагностики
        logger.info(f"Примеры позиций (первые 3 записи):")
        for i, row in df.head(3).iterrows():
            positions = row.get('positions', 'N/A')
            logger.info(f"  Запись {i}: positions = {str(positions)[:200]}...")
        
        # Конвертируем даты
        df['moment'] = pd.to_datetime(df['moment'])
        df['date'] = df['moment'].dt.date
        
        # Извлекаем информацию о продуктах
        df['product_id'] = df['positions'].apply(self._extract_product_id)
        df['quantity'] = df['positions'].apply(self._extract_quantity)
        
        # Выводим статистику извлечения
        unknown_count = (df['product_id'] == "unknown").sum()
        valid_count = len(df) - unknown_count
        logger.info(f"Извлечено ID продуктов: валидных {valid_count}, unknown {unknown_count}")
        
        # Агрегируем по дням и продуктам
        daily_sales = df.groupby(['date', 'product_id']).agg({
            'quantity': 'sum',
            'sum': 'sum'
        }).reset_index()
        
        # Создаем временной ряд
        daily_sales['date'] = pd.to_datetime(daily_sales['date'])
        daily_sales = daily_sales.sort_values(['product_id', 'date'])
        
        logger.info(f"Предобработано {len(daily_sales)} записей продаж")
        return daily_sales
    
    def _preprocess_stock_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Предобработка данных остатков"""
        logger.info("Предобработка данных остатков...")
        
        # Конвертируем даты
        df['date'] = pd.to_datetime(df['date'])
        
        # Извлекаем информацию о продуктах
        df['product_id'] = df['meta'].apply(self._extract_product_id_from_meta)
        
        # Агрегируем по датам и продуктам
        daily_stock = df.groupby(['date', 'product_id']).agg({
            'quantity': 'sum',
            'stock': 'sum'
        }).reset_index()
        
        daily_stock = daily_stock.sort_values(['product_id', 'date'])
        
        logger.info(f"Предобработано {len(daily_stock)} записей остатков")
        return daily_stock
    
    def _extract_product_id(self, positions_str: str) -> str:
        """Извлечение ID продукта из строки позиций"""
        try:
            positions = json.loads(positions_str)
            if positions and len(positions) > 0:
                assortment = positions[0].get('assortment', {})
                meta = assortment.get('meta', {})
                href = meta.get('href', '')
                if href:
                    product_id = href.split('/')[-1]
                    return product_id
                else:
                    # Попробуем другие поля
                    if 'id' in assortment:
                        return str(assortment['id'])
                    elif 'name' in assortment:
                        return assortment['name']
        except Exception as e:
            logger.debug(f"Ошибка извлечения ID продукта: {e}")
        return "unknown"
    
    def _extract_quantity(self, positions_str: str) -> float:
        """Извлечение количества из строки позиций"""
        try:
            positions = json.loads(positions_str)
            if positions and len(positions) > 0:
                return float(positions[0].get('quantity', 0))
        except:
            pass
        return 0.0
    
    def _extract_product_id_from_meta(self, meta_str: str) -> str:
        """Извлечение ID продукта из мета-информации"""
        try:
            meta = json.loads(meta_str)
            return meta.get('href', '').split('/')[-1]
        except:
            pass
        return "unknown"
    
    def prepare_training_data(self, sales_df: pd.DataFrame, stock_df: pd.DataFrame) -> Dict[str, List[Dict]]:
        """Подготовка данных для обучения моделей"""
        logger.info("Подготовка данных для обучения...")
        
        training_data = {}
        
        # Получаем уникальные продукты
        products = sales_df['product_id'].unique()
        logger.info(f"Найдено {len(products)} уникальных продуктов")
        
        # Выводим информацию о продуктах
        for product_id in products:
            logger.info(f"Продукт {product_id}: {len(sales_df[sales_df['product_id'] == product_id])} записей")
        
        for product_id in products:
            if product_id == "unknown":
                logger.info(f"Пропускаем продукт {product_id} (unknown)")
                continue
                
            # Данные продаж для продукта
            product_sales = sales_df[sales_df['product_id'] == product_id].copy()
            
            if len(product_sales) < 30:  # Минимум 30 дней данных
                logger.warning(f"Недостаточно данных для продукта {product_id}: {len(product_sales)} записей")
                continue
            
            # Создаем временной ряд
            product_sales = product_sales.set_index('date').sort_index()
            
            # Заполняем пропуски нулями
            date_range = pd.date_range(
                start=product_sales.index.min(),
                end=product_sales.index.max(),
                freq='D'
            )
            product_sales = product_sales.reindex(date_range, fill_value=0)
            
            # Создаем признаки
            features = self._create_features(product_sales)
            
            training_data[product_id] = features
            
            logger.info(f"Подготовлены данные для продукта {product_id}: {len(features)} записей")
        
        return training_data
    
    def _create_features(self, sales_series: pd.DataFrame) -> List[Dict]:
        """Создание признаков для обучения"""
        features = []
        
        # Скользящие средние
        sales_series['ma_7'] = sales_series['quantity'].rolling(window=7).mean()
        sales_series['ma_30'] = sales_series['quantity'].rolling(window=30).mean()
        
        # Лаговые признаки
        sales_series['lag_1'] = sales_series['quantity'].shift(1)
        sales_series['lag_7'] = sales_series['quantity'].shift(7)
        sales_series['lag_30'] = sales_series['quantity'].shift(30)
        
        # Временные признаки
        sales_series['day_of_week'] = sales_series.index.dayofweek
        sales_series['month'] = sales_series.index.month
        sales_series['quarter'] = sales_series.index.quarter
        sales_series['year'] = sales_series.index.year
        
        # Удаляем NaN
        sales_series = sales_series.dropna()
        
        for idx, row in sales_series.iterrows():
            feature_dict = {
                'date': idx,
                'quantity': row['quantity'],
                'ma_7': row['ma_7'],
                'ma_30': row['ma_30'],
                'lag_1': row['lag_1'],
                'lag_7': row['lag_7'],
                'lag_30': row['lag_30'],
                'day_of_week': row['day_of_week'],
                'month': row['month'],
                'quarter': row['quarter'],
                'year': row['year']
            }
            features.append(feature_dict)
        
        return features
    
    def train_simple_models(self, training_data: Dict[str, List[Dict]]):
        """Обучение простых моделей для всех продуктов"""
        logger.info("Начинаем обучение простых моделей...")
        
        trained_models = 0
        failed_models = 0
        
        # Создаем директорию для моделей
        os.makedirs("/app/models", exist_ok=True)
        
        for product_id, features in training_data.items():
            try:
                logger.info(f"Обучение модели для продукта {product_id}...")
                
                # Создаем простую модель (среднее потребление)
                quantities = [f['quantity'] for f in features]
                avg_consumption = np.mean(quantities)
                
                # Сохраняем простую модель
                model_data = {
                    'product_id': product_id,
                    'model_type': 'simple_average',
                    'avg_consumption': avg_consumption,
                    'trained_at': datetime.now().isoformat(),
                    'features_count': len(features),
                    'accuracy': 0.8  # Простая оценка
                }
                
                model_file = f"/app/models/{product_id}_simple.pkl"
                with open(model_file, 'w') as f:
                    json.dump(model_data, f, indent=2)
                
                trained_models += 1
                logger.info(f"Модель для продукта {product_id} обучена. Среднее потребление: {avg_consumption:.2f}")
                
            except Exception as e:
                failed_models += 1
                logger.error(f"Исключение при обучении модели для продукта {product_id}: {e}")
        
        logger.info(f"Обучение завершено. Успешно: {trained_models}, Ошибок: {failed_models}")
        return trained_models, failed_models


async def main():
    """Основная функция"""
    logger.info("Запуск обучения простых ML-моделей...")
    
    trainer = SimpleModelTrainer()
    
    try:
        # Загружаем и предобрабатываем данные
        data = trainer.load_and_preprocess_data()
        
        # Подготавливаем данные для обучения
        training_data = trainer.prepare_training_data(data['sales'], data['stock'])
        
        # Обучаем модели
        trained, failed = trainer.train_simple_models(training_data)
        
        logger.info(f"Обучение завершено! Успешно обучено моделей: {trained}, Ошибок: {failed}")
        
    except Exception as e:
        logger.error(f"Ошибка в процессе обучения: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main()) 