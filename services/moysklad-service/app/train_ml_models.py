#!/usr/bin/env python3
"""
Улучшенный модуль обучения ML моделей с реальными данными
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

class MLModelTrainer:
    """Класс для обучения ML моделей на реальных данных"""
    
    def __init__(self):
        self.models_dir = "/app/data/models"
        os.makedirs(self.models_dir, exist_ok=True)
        self.training_results = {}
    
    async def get_all_products(self) -> List[Dict]:
        """Получает список всех товаров из МойСклад"""
        logger.info("Получение списка всех товаров...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                params = {"limit": 1000}
                resp = await client.get(f"{MOYSKLAD_API_URL}/entity/assortment", 
                                      headers=HEADERS, params=params)
                
                if resp.status_code == 200:
                    data = resp.json()
                    products = data.get('rows', [])
                    logger.info(f"Найдено товаров: {len(products)}")
                    return products
                else:
                    logger.error(f"Ошибка получения товаров: {resp.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Ошибка получения товаров: {e}")
            return []
    
    async def get_real_stock_history(self, product_code: str, days_back: int = 90) -> pd.DataFrame:
        """Получает реальную историю остатков из МойСклад"""
        logger.info(f"Получение истории остатков для товара {product_code}...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days_back)
                
                stock_data = []
                current_date = start_date
                
                while current_date <= end_date:
                    params = {
                        "moment": current_date.strftime("%Y-%m-%dT00:00:00"),
                        "limit": 1000
                    }
                    
                    resp = await client.get(f"{MOYSKLAD_API_URL}/report/stock/all", 
                                          headers=HEADERS, params=params)
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        stock_items = data.get('rows', [])
                        
                        for item in stock_items:
                            if item.get('code') == product_code:
                                stock_data.append({
                                    'date': current_date.strftime('%Y-%m-%d'),
                                    'product_code': product_code,
                                    'stock': item.get('quantity', 0),
                                    'product_name': item.get('name', '')
                                })
                                break
                    
                    current_date += timedelta(days=1)
                    await asyncio.sleep(0.1)  # Пауза между запросами
                
                df = pd.DataFrame(stock_data)
                if not df.empty:
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.sort_values('date')
                    logger.info(f"Получено {len(df)} записей остатков для {product_code}")
                
                return df
                
        except Exception as e:
            logger.error(f"Ошибка получения истории остатков: {e}")
            return pd.DataFrame()
    
    async def get_real_sales_history(self, product_code: str, days_back: int = 90) -> pd.DataFrame:
        """Получает реальную историю продаж из МойСклад"""
        logger.info(f"Получение истории продаж для товара {product_code}...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days_back)
                
                params = {
                    "momentFrom": start_date.strftime('%Y-%m-%d') + "T00:00:00",
                    "momentTo": end_date.strftime('%Y-%m-%d') + "T23:59:59",
                    "limit": 1000
                }
                
                resp = await client.get(f"{MOYSKLAD_API_URL}/entity/demand", 
                                      headers=HEADERS, params=params)
                
                if resp.status_code == 200:
                    data = resp.json()
                    demands = data.get('rows', [])
                    
                    sales_data = []
                    
                    for demand in demands:
                        demand_id = demand.get('id')
                        demand_date = demand.get('moment', '')[:10]
                        
                        # Получаем позиции для документа
                        pos_resp = await client.get(f"{MOYSKLAD_API_URL}/entity/demand/{demand_id}/positions",
                                                  headers=HEADERS, params={"expand": "assortment"})
                        
                        if pos_resp.status_code == 200:
                            pos_data = pos_resp.json()
                            positions = pos_data.get('rows', [])
                            
                            for position in positions:
                                assortment = position.get('assortment', {})
                                if isinstance(assortment, dict) and assortment.get('code') == product_code:
                                    sales_data.append({
                                        'date': demand_date,
                                        'product_code': product_code,
                                        'quantity': position.get('quantity', 0),
                                        'product_name': assortment.get('name', '')
                                    })
                    
                    df = pd.DataFrame(sales_data)
                    if not df.empty:
                        df['date'] = pd.to_datetime(df['date'])
                        df = df.sort_values('date')
                        logger.info(f"Получено {len(df)} записей продаж для {product_code}")
                    
                    return df
                
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Ошибка получения истории продаж: {e}")
            return pd.DataFrame()
    
    def create_ml_features(self, stock_df: pd.DataFrame, sales_df: pd.DataFrame) -> pd.DataFrame:
        """Создает признаки для ML модели"""
        
        if stock_df.empty and sales_df.empty:
            return pd.DataFrame()
        
        # Объединяем данные по датам
        if not stock_df.empty and not sales_df.empty:
            # Группируем продажи по дням
            daily_sales = sales_df.groupby('date')['quantity'].sum().reset_index()
            daily_sales.columns = ['date', 'daily_sales']
            
            # Объединяем с остатками
            merged_df = pd.merge(stock_df, daily_sales, on='date', how='left')
            merged_df['daily_sales'] = merged_df['daily_sales'].fillna(0)
        elif not stock_df.empty:
            merged_df = stock_df.copy()
            merged_df['daily_sales'] = 0
        else:
            return pd.DataFrame()
        
        # Создаем признаки
        features = []
        
        for idx, row in merged_df.iterrows():
            date = row['date']
            
            feature_dict = {
                'date': date,
                'product_code': row['product_code'],
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
                
                # Признаки товара
                'product_code_numeric': float(row['product_code']) if row['product_code'].replace('.', '').isdigit() else 0,
            }
            
            # Лаговые признаки (если есть история)
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
            
            # Скользящие средние
            if idx >= 6:
                feature_dict['sales_ma_7'] = merged_df.iloc[idx-7:idx]['daily_sales'].mean()
                feature_dict['stock_ma_7'] = merged_df.iloc[idx-7:idx]['stock'].mean()
            else:
                feature_dict['sales_ma_7'] = row['daily_sales']
                feature_dict['stock_ma_7'] = row['stock']
            
            features.append(feature_dict)
        
        return pd.DataFrame(features)
    
    def train_model_for_product(self, product_code: str, features_df: pd.DataFrame) -> Dict:
        """Обучает ML модель для конкретного товара"""
        
        if features_df.empty or len(features_df) < 10:
            logger.warning(f"Недостаточно данных для обучения модели {product_code}")
            return None
        
        try:
            # Подготавливаем данные
            feature_columns = [col for col in features_df.columns 
                             if col not in ['date', 'product_code', 'daily_sales']]
            
            X = features_df[feature_columns].values
            y = features_df['daily_sales'].values
            
            # Разделяем на обучающую и тестовую выборки
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Масштабируем признаки
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Обучаем модель
            model = RandomForestRegressor(n_estimators=100, random_state=42)
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
                    'model_score': max(0, min(1, r2)),  # Нормализуем R² к [0,1]
                    'feature_columns': feature_columns
                }
            }
            
            model_path = os.path.join(self.models_dir, f"{product_code}.joblib")
            joblib.dump(model_data, model_path)
            
            logger.info(f"Модель для {product_code} обучена: MAE={mae:.2f}, R²={r2:.2f}")
            
            return {
                'product_code': product_code,
                'mae': mae,
                'r2_score': r2,
                'training_samples': len(X_train),
                'test_samples': len(X_test)
            }
            
        except Exception as e:
            logger.error(f"Ошибка обучения модели для {product_code}: {e}")
            return None
    
    async def train_models_for_all_products(self):
        """Обучает модели для всех товаров"""
        logger.info("Начинаем обучение ML моделей для всех товаров...")
        
        # Получаем список товаров
        products = await self.get_all_products()
        if not products:
            logger.error("Не удалось получить список товаров")
            return
        
        trained_models = 0
        failed_models = 0
        
        for product in products[:20]:  # Ограничиваем для тестирования
            product_code = product.get('code')
            if not product_code:
                continue
            
            try:
                logger.info(f"Обработка товара {product_code}...")
                
                # Получаем реальные данные
                stock_df = await self.get_real_stock_history(product_code, days_back=90)
                sales_df = await self.get_real_sales_history(product_code, days_back=90)
                
                # Создаем признаки
                features_df = self.create_ml_features(stock_df, sales_df)
                
                if not features_df.empty:
                    # Обучаем модель
                    result = self.train_model_for_product(product_code, features_df)
                    if result:
                        self.training_results[product_code] = result
                        trained_models += 1
                    else:
                        failed_models += 1
                else:
                    logger.warning(f"Недостаточно данных для товара {product_code}")
                    failed_models += 1
                
                # Пауза между товарами
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Ошибка обработки товара {product_code}: {e}")
                failed_models += 1
        
        # Сохраняем результаты обучения
        self.save_training_results()
        
        logger.info(f"Обучение завершено. Успешно: {trained_models}, Ошибок: {failed_models}")
    
    def save_training_results(self):
        """Сохраняет результаты обучения"""
        timestamp = datetime.now().isoformat()
        
        results = {
            'timestamp': timestamp,
            'total_models': len(self.training_results),
            'results': self.training_results,
            'summary': {
                'avg_mae': np.mean([r['mae'] for r in self.training_results.values()]),
                'avg_r2': np.mean([r['r2_score'] for r in self.training_results.values()]),
                'best_model': max(self.training_results.values(), key=lambda x: x['r2_score'])['product_code'] if self.training_results else None
            }
        }
        
        results_file = os.path.join(self.models_dir, 'training_results.json')
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Результаты обучения сохранены в {results_file}")

async def main():
    """Основная функция"""
    logger.info("Запуск обучения ML моделей на реальных данных...")
    
    trainer = MLModelTrainer()
    await trainer.train_models_for_all_products()
    
    logger.info("Обучение ML моделей завершено!")

if __name__ == "__main__":
    asyncio.run(main()) 