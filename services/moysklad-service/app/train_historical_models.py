#!/usr/bin/env python3
"""
Обучение ML моделей на исторических данных за 4 года
"""

import asyncio
import pandas as pd
import numpy as np
import logging
import json
import os
import joblib
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import httpx
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Настройки API МойСклад
MOYSKLAD_API_URL = "https://api.moysklad.ru/api/remap/1.2"
MOYSKLAD_API_TOKEN = os.getenv('MOYSKLAD_API_TOKEN')

HEADERS = {
    "Authorization": f"Bearer {MOYSKLAD_API_TOKEN}",
    "Content-Type": "application/json"
}

class HistoricalModelTrainer:
    """Класс для обучения ML моделей на исторических данных"""
    
    def __init__(self):
        self.models_dir = "/app/data/models"
        self.data_dir = "/app/data"
        os.makedirs(self.models_dir, exist_ok=True)
        self.training_results = {}
    
    def load_historical_data(self) -> Dict[str, pd.DataFrame]:
        """Загружает исторические данные из папки data"""
        logger.info("Загрузка исторических данных...")
        
        historical_data = {}
        
        try:
            # Загружаем CSV файлы с историческими данными
            csv_files = [f for f in os.listdir(self.data_dir) if f.endswith('.csv')]
            
            for file in csv_files:
                file_path = os.path.join(self.data_dir, file)
                df = pd.read_csv(file_path)
                
                # Определяем тип данных по имени файла
                if 'stock' in file.lower():
                    logger.info(f"Загружены данные об остатках: {len(df)} записей")
                    historical_data['stock'] = df
                elif 'sales' in file.lower() or 'demand' in file.lower():
                    logger.info(f"Загружены данные о продажах: {len(df)} записей")
                    historical_data['sales'] = df
                elif 'production' in file.lower():
                    logger.info(f"Загружены производственные данные: {len(df)} записей")
                    historical_data['production'] = df
                else:
                    logger.info(f"Загружены данные из {file}: {len(df)} записей")
                    historical_data[file.replace('.csv', '')] = df
            
            logger.info(f"Загружено {len(historical_data)} типов данных")
            return historical_data
            
        except Exception as e:
            logger.error(f"Ошибка загрузки исторических данных: {e}")
            return {}
    
    def get_all_products_from_data(self, historical_data: Dict[str, pd.DataFrame]) -> List[str]:
        """Получает список всех товаров из исторических данных"""
        product_codes = set()
        
        for data_type, df in historical_data.items():
            if 'product_code' in df.columns:
                product_codes.update(df['product_code'].unique())
            elif 'code' in df.columns:
                product_codes.update(df['code'].unique())
        
        product_list = list(product_codes)
        logger.info(f"Найдено {len(product_list)} уникальных товаров в исторических данных")
        return product_list
    
    def prepare_historical_features(self, product_code: str, historical_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Подготавливает признаки из исторических данных для товара"""
        
        features_list = []
        
        # Обрабатываем данные об остатках
        if 'stock' in historical_data:
            stock_df = historical_data['stock']
            if 'product_code' in stock_df.columns:
                product_stock = stock_df[stock_df['product_code'] == product_code].copy()
            elif 'code' in stock_df.columns:
                product_stock = stock_df[stock_df['code'] == product_code].copy()
            else:
                product_stock = pd.DataFrame()
            
            if not product_stock.empty:
                # Стандартизируем колонки
                if 'date' in product_stock.columns:
                    product_stock['date'] = pd.to_datetime(product_stock['date'])
                elif 'moment' in product_stock.columns:
                    product_stock['date'] = pd.to_datetime(product_stock['moment'])
                
                # Переименовываем колонки
                if 'quantity' in product_stock.columns:
                    product_stock['stock'] = product_stock['quantity']
                elif 'available' in product_stock.columns:
                    product_stock['stock'] = product_stock['available']
                
                product_stock = product_stock.sort_values('date')
        
        # Обрабатываем данные о продажах
        if 'sales' in historical_data:
            sales_df = historical_data['sales']
            if 'product_code' in sales_df.columns:
                product_sales = sales_df[sales_df['product_code'] == product_code].copy()
            elif 'code' in sales_df.columns:
                product_sales = sales_df[sales_df['code'] == product_code].copy()
            else:
                product_sales = pd.DataFrame()
            
            if not product_sales.empty:
                # Стандартизируем колонки
                if 'date' in product_sales.columns:
                    product_sales['date'] = pd.to_datetime(product_sales['date'])
                elif 'moment' in product_sales.columns:
                    product_sales['date'] = pd.to_datetime(product_sales['moment'])
                
                # Переименовываем колонки
                if 'quantity' in product_sales.columns:
                    product_sales['daily_sales'] = product_sales['quantity']
                elif 'sales' in product_sales.columns:
                    product_sales['daily_sales'] = product_sales['sales']
                
                # Группируем по дням
                product_sales = product_sales.groupby('date')['daily_sales'].sum().reset_index()
                product_sales = product_sales.sort_values('date')
        
        # Объединяем данные
        if 'product_stock' in locals() and not product_stock.empty and 'product_sales' in locals() and not product_sales.empty:
            # Объединяем остатки и продажи
            merged_df = pd.merge(product_stock[['date', 'stock']], product_sales, on='date', how='outer')
            merged_df['daily_sales'] = merged_df['daily_sales'].fillna(0)
        elif 'product_stock' in locals() and not product_stock.empty:
            merged_df = product_stock[['date', 'stock']].copy()
            merged_df['daily_sales'] = 0
        elif 'product_sales' in locals() and not product_sales.empty:
            merged_df = product_sales.copy()
            merged_df['stock'] = merged_df['daily_sales'].cumsum()  # Приблизительные остатки
        else:
            logger.warning(f"Недостаточно данных для товара {product_code}")
            return pd.DataFrame()
        
        # Создаем признаки
        for idx, row in merged_df.iterrows():
            date = row['date']
            
            feature_dict = {
                'date': date,
                'product_code': product_code,
                'stock': row['stock'],
                'daily_sales': row['daily_sales'],
                
                # Временные признаки
                'year': date.year,
                'month': date.month,
                'day': date.day,
                'day_of_year': date.timetuple().tm_yday,
                'day_of_week': date.weekday(),
                'is_month_start': date.day == 1,
                'is_quarter_start': date.day == 1 and date.month in [1, 4, 7, 10],
                'is_weekend': date.weekday() >= 5,
                
                # Сезонные признаки
                'is_holiday_season': date.month in [12, 1, 2],
                'is_summer_season': date.month in [6, 7, 8],
                'is_spring_season': date.month in [3, 4, 5],
                'is_autumn_season': date.month in [9, 10, 11],
                
                # Признаки товара
                'product_code_numeric': float(product_code) if product_code.replace('.', '').isdigit() else 0,
            }
            
            # Лаговые признаки
            if idx > 0:
                feature_dict['stock_lag_1'] = merged_df.iloc[idx-1]['stock']
                feature_dict['sales_lag_1'] = merged_df.iloc[idx-1]['daily_sales']
            else:
                feature_dict['stock_lag_1'] = row['stock']
                feature_dict['sales_lag_1'] = row['daily_sales']
            
            if idx > 6:
                feature_dict['stock_lag_7'] = merged_df.iloc[idx-7]['stock']
                feature_dict['sales_lag_7'] = merged_df.iloc[idx-7]['daily_sales']
            else:
                feature_dict['stock_lag_7'] = row['stock']
                feature_dict['sales_lag_7'] = row['daily_sales']
            
            if idx > 29:
                feature_dict['stock_lag_30'] = merged_df.iloc[idx-30]['stock']
                feature_dict['sales_lag_30'] = merged_df.iloc[idx-30]['daily_sales']
            else:
                feature_dict['stock_lag_30'] = row['stock']
                feature_dict['sales_lag_30'] = row['daily_sales']
            
            # Скользящие средние
            if idx >= 6:
                feature_dict['sales_ma_7'] = merged_df.iloc[idx-7:idx]['daily_sales'].mean()
                feature_dict['stock_ma_7'] = merged_df.iloc[idx-7:idx]['stock'].mean()
            else:
                feature_dict['sales_ma_7'] = row['daily_sales']
                feature_dict['stock_ma_7'] = row['stock']
            
            if idx >= 29:
                feature_dict['sales_ma_30'] = merged_df.iloc[idx-30:idx]['daily_sales'].mean()
                feature_dict['stock_ma_30'] = merged_df.iloc[idx-30:idx]['stock'].mean()
            else:
                feature_dict['sales_ma_30'] = row['daily_sales']
                feature_dict['stock_ma_30'] = row['stock']
            
            # Тренды
            if idx >= 6:
                feature_dict['sales_trend_7'] = np.polyfit(range(7), merged_df.iloc[idx-7:idx]['daily_sales'], 1)[0]
                feature_dict['stock_trend_7'] = np.polyfit(range(7), merged_df.iloc[idx-7:idx]['stock'], 1)[0]
            else:
                feature_dict['sales_trend_7'] = 0
                feature_dict['stock_trend_7'] = 0
            
            features_list.append(feature_dict)
        
        return pd.DataFrame(features_list)
    
    def train_model_for_product(self, product_code: str, features_df: pd.DataFrame) -> Dict:
        """Обучает ML модель для конкретного товара на исторических данных"""
        
        if features_df.empty or len(features_df) < 30:  # Минимум 30 дней данных
            logger.warning(f"Недостаточно исторических данных для обучения модели {product_code}")
            return None
        
        try:
            # Подготавливаем данные
            feature_columns = [col for col in features_df.columns 
                             if col not in ['date', 'product_code', 'daily_sales']]
            
            X = features_df[feature_columns].values
            y = features_df['daily_sales'].values
            
            # Разделяем на обучающую и тестовую выборки (80/20)
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Масштабируем признаки
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Обучаем модель с большим количеством деревьев для исторических данных
            model = RandomForestRegressor(
                n_estimators=200,  # Больше деревьев для лучшего качества
                max_depth=15,       # Ограничиваем глубину
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42
            )
            model.fit(X_train_scaled, y_train)
            
            # Оцениваем качество
            y_pred = model.predict(X_test_scaled)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            # Сохраняем модель
            model_data = {
                'model': model,
                'scaler': scaler,
                'metadata': {
                    'product_code': product_code,
                    'trained_at': datetime.now().isoformat(),
                    'training_samples': len(X_train),
                    'test_samples': len(X_test),
                    'mae': mae,
                    'r2_score': r2,
                    'model_score': max(0, min(1, r2)),
                    'feature_columns': feature_columns,
                    'data_period': {
                        'start_date': features_df['date'].min().strftime('%Y-%m-%d'),
                        'end_date': features_df['date'].max().strftime('%Y-%m-%d'),
                        'total_days': len(features_df)
                    },
                    'model_type': 'historical_trained'
                }
            }
            
            model_path = os.path.join(self.models_dir, f"{product_code}.joblib")
            joblib.dump(model_data, model_path)
            
            logger.info(f"Историческая модель для {product_code} обучена: MAE={mae:.2f}, R²={r2:.2f}")
            
            return {
                'product_code': product_code,
                'mae': mae,
                'r2_score': r2,
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'data_period_days': len(features_df)
            }
            
        except Exception as e:
            logger.error(f"Ошибка обучения исторической модели для {product_code}: {e}")
            return None
    
    async def train_models_on_historical_data(self):
        """Обучает модели на исторических данных за 4 года"""
        logger.info("Начинаем обучение ML моделей на исторических данных...")
        
        # Загружаем исторические данные
        historical_data = self.load_historical_data()
        if not historical_data:
            logger.error("Не удалось загрузить исторические данные")
            return
        
        # Получаем список товаров
        product_codes = self.get_all_products_from_data(historical_data)
        if not product_codes:
            logger.error("Не найдено товаров в исторических данных")
            return
        
        trained_models = 0
        failed_models = 0
        
        for product_code in product_codes[:50]:  # Ограничиваем для тестирования
            try:
                logger.info(f"Обработка товара {product_code}...")
                
                # Подготавливаем признаки из исторических данных
                features_df = self.prepare_historical_features(product_code, historical_data)
                
                if not features_df.empty:
                    # Обучаем модель
                    result = self.train_model_for_product(product_code, features_df)
                    if result:
                        self.training_results[product_code] = result
                        trained_models += 1
                    else:
                        failed_models += 1
                else:
                    logger.warning(f"Недостаточно исторических данных для товара {product_code}")
                    failed_models += 1
                
            except Exception as e:
                logger.error(f"Ошибка обработки товара {product_code}: {e}")
                failed_models += 1
        
        # Сохраняем результаты обучения
        self.save_training_results()
        
        logger.info(f"Обучение на исторических данных завершено. Успешно: {trained_models}, Ошибок: {failed_models}")
    
    def save_training_results(self):
        """Сохраняет результаты обучения"""
        timestamp = datetime.now().isoformat()
        
        results = {
            'timestamp': timestamp,
            'training_type': 'historical_data',
            'total_models': len(self.training_results),
            'results': self.training_results,
            'summary': {
                'avg_mae': np.mean([r['mae'] for r in self.training_results.values()]),
                'avg_r2': np.mean([r['r2_score'] for r in self.training_results.values()]),
                'avg_data_period': np.mean([r['data_period_days'] for r in self.training_results.values()]),
                'best_model': max(self.training_results.values(), key=lambda x: x['r2_score'])['product_code'] if self.training_results else None
            }
        }
        
        results_file = os.path.join(self.models_dir, 'historical_training_results.json')
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Результаты исторического обучения сохранены в {results_file}")

async def main():
    """Основная функция"""
    logger.info("Запуск обучения ML моделей на исторических данных...")
    
    trainer = HistoricalModelTrainer()
    await trainer.train_models_on_historical_data()
    
    logger.info("Обучение на исторических данных завершено!")

if __name__ == "__main__":
    asyncio.run(main()) 