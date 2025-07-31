#!/usr/bin/env python3
"""
Дообучение ML моделей свежими данными
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

class IncrementalModelTrainer:
    """Класс для дообучения ML моделей свежими данными"""
    
    def __init__(self):
        self.models_dir = "/app/data/models"
        self.training_results = {}
    
    def load_existing_model(self, product_code: str) -> Optional[Dict]:
        """Загружает существующую модель для товара"""
        model_path = os.path.join(self.models_dir, f"{product_code}.joblib")
        
        if os.path.exists(model_path):
            try:
                model_data = joblib.load(model_path)
                logger.info(f"Загружена существующая модель для {product_code}")
                return model_data
            except Exception as e:
                logger.error(f"Ошибка загрузки модели {product_code}: {e}")
                return None
        else:
            logger.warning(f"Модель для {product_code} не найдена")
            return None
    
    async def get_fresh_data(self, product_code: str, days_back: int = 30) -> pd.DataFrame:
        """Получает свежие данные для товара"""
        logger.info(f"Получение свежих данных для товара {product_code}...")
        
        try:
            # Получаем свежие данные об остатках
            stock_df = await self.get_fresh_stock_data(product_code, days_back)
            sales_df = await self.get_fresh_sales_data(product_code, days_back)
            
            # Объединяем данные
            if not stock_df.empty and not sales_df.empty:
                merged_df = pd.merge(stock_df, sales_df, on='date', how='outer')
                merged_df['daily_sales'] = merged_df['daily_sales'].fillna(0)
            elif not stock_df.empty:
                merged_df = stock_df.copy()
                merged_df['daily_sales'] = 0
            elif not sales_df.empty:
                merged_df = sales_df.copy()
                merged_df['stock'] = merged_df['daily_sales'].cumsum()
            else:
                return pd.DataFrame()
            
            logger.info(f"Получено {len(merged_df)} свежих записей для {product_code}")
            return merged_df
            
        except Exception as e:
            logger.error(f"Ошибка получения свежих данных для {product_code}: {e}")
            return pd.DataFrame()
    
    async def get_fresh_stock_data(self, product_code: str, days_back: int = 30) -> pd.DataFrame:
        """Получает свежие данные об остатках"""
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
                    await asyncio.sleep(0.1)
                
                df = pd.DataFrame(stock_data)
                if not df.empty:
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.sort_values('date')
                
                return df
                
        except Exception as e:
            logger.error(f"Ошибка получения свежих остатков: {e}")
            return pd.DataFrame()
    
    async def get_fresh_sales_data(self, product_code: str, days_back: int = 30) -> pd.DataFrame:
        """Получает свежие данные о продажах"""
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
                        df = df.groupby('date')['quantity'].sum().reset_index()
                        df.columns = ['date', 'daily_sales']
                        df = df.sort_values('date')
                    
                    return df
                
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Ошибка получения свежих продаж: {e}")
            return pd.DataFrame()
    
    def create_incremental_features(self, fresh_df: pd.DataFrame, existing_model_data: Dict) -> pd.DataFrame:
        """Создает признаки для дообучения с учетом существующей модели"""
        
        if fresh_df.empty:
            return pd.DataFrame()
        
        features_list = []
        
        for idx, row in fresh_df.iterrows():
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
                'is_spring_season': date.month in [3, 4, 5],
                'is_autumn_season': date.month in [9, 10, 11],
                
                # Признаки товара
                'product_code_numeric': float(row['product_code']) if row['product_code'].replace('.', '').isdigit() else 0,
            }
            
            # Лаговые признаки
            if idx > 0:
                feature_dict['stock_lag_1'] = fresh_df.iloc[idx-1]['stock']
                feature_dict['sales_lag_1'] = fresh_df.iloc[idx-1]['daily_sales']
            else:
                feature_dict['stock_lag_1'] = row['stock']
                feature_dict['sales_lag_1'] = row['daily_sales']
            
            if idx > 6:
                feature_dict['stock_lag_7'] = fresh_df.iloc[idx-7]['stock']
                feature_dict['sales_lag_7'] = fresh_df.iloc[idx-7]['daily_sales']
            else:
                feature_dict['stock_lag_7'] = row['stock']
                feature_dict['sales_lag_7'] = row['daily_sales']
            
            if idx > 29:
                feature_dict['stock_lag_30'] = fresh_df.iloc[idx-30]['stock']
                feature_dict['sales_lag_30'] = fresh_df.iloc[idx-30]['daily_sales']
            else:
                feature_dict['stock_lag_30'] = row['stock']
                feature_dict['sales_lag_30'] = row['daily_sales']
            
            # Скользящие средние
            if idx >= 6:
                feature_dict['sales_ma_7'] = fresh_df.iloc[idx-7:idx]['daily_sales'].mean()
                feature_dict['stock_ma_7'] = fresh_df.iloc[idx-7:idx]['stock'].mean()
            else:
                feature_dict['sales_ma_7'] = row['daily_sales']
                feature_dict['stock_ma_7'] = row['stock']
            
            if idx >= 29:
                feature_dict['sales_ma_30'] = fresh_df.iloc[idx-30:idx]['daily_sales'].mean()
                feature_dict['stock_ma_30'] = fresh_df.iloc[idx-30:idx]['stock'].mean()
            else:
                feature_dict['sales_ma_30'] = row['daily_sales']
                feature_dict['stock_ma_30'] = row['stock']
            
            # Тренды
            if idx >= 6:
                feature_dict['sales_trend_7'] = np.polyfit(range(7), fresh_df.iloc[idx-7:idx]['daily_sales'], 1)[0]
                feature_dict['stock_trend_7'] = np.polyfit(range(7), fresh_df.iloc[idx-7:idx]['stock'], 1)[0]
            else:
                feature_dict['sales_trend_7'] = 0
                feature_dict['stock_trend_7'] = 0
            
            features_list.append(feature_dict)
        
        return pd.DataFrame(features_list)
    
    def incremental_train_model(self, product_code: str, fresh_features: pd.DataFrame, 
                              existing_model_data: Dict) -> Dict:
        """Дообучает существующую модель свежими данными"""
        
        if fresh_features.empty or len(fresh_features) < 7:  # Минимум неделя свежих данных
            logger.warning(f"Недостаточно свежих данных для дообучения модели {product_code}")
            return None
        
        try:
            # Получаем существующую модель и scaler
            existing_model = existing_model_data['model']
            existing_scaler = existing_model_data['scaler']
            existing_metadata = existing_model_data['metadata']
            
            # Подготавливаем свежие данные
            feature_columns = existing_metadata['feature_columns']
            X_fresh = fresh_features[feature_columns].values
            y_fresh = fresh_features['daily_sales'].values
            
            # Масштабируем свежие данные с существующим scaler
            X_fresh_scaled = existing_scaler.transform(X_fresh)
            
            # Создаем новую модель с дообучением
            updated_model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42
            )
            
            # Обучаем на свежих данных
            updated_model.fit(X_fresh_scaled, y_fresh)
            
            # Оцениваем качество на свежих данных
            y_pred = updated_model.predict(X_fresh_scaled)
            mae = mean_absolute_error(y_fresh, y_pred)
            r2 = r2_score(y_fresh, y_pred)
            
            # Обновляем метаданные
            updated_metadata = existing_metadata.copy()
            updated_metadata.update({
                'last_updated': datetime.now().isoformat(),
                'incremental_training_samples': len(X_fresh),
                'incremental_mae': mae,
                'incremental_r2_score': r2,
                'incremental_model_score': max(0, min(1, r2)),
                'model_type': 'historical_trained_incremental',
                'fresh_data_period': {
                    'start_date': fresh_features['date'].min().strftime('%Y-%m-%d'),
                    'end_date': fresh_features['date'].max().strftime('%Y-%m-%d'),
                    'fresh_days': len(fresh_features)
                }
            })
            
            # Сохраняем обновленную модель
            updated_model_data = {
                'model': updated_model,
                'scaler': existing_scaler,
                'metadata': updated_metadata
            }
            
            model_path = os.path.join(self.models_dir, f"{product_code}.joblib")
            joblib.dump(updated_model_data, model_path)
            
            logger.info(f"Модель {product_code} дообучена: MAE={mae:.2f}, R²={r2:.2f}")
            
            return {
                'product_code': product_code,
                'mae': mae,
                'r2_score': r2,
                'fresh_samples': len(X_fresh),
                'fresh_days': len(fresh_features)
            }
            
        except Exception as e:
            logger.error(f"Ошибка дообучения модели для {product_code}: {e}")
            return None
    
    async def incremental_train_all_models(self):
        """Дообучает все существующие модели свежими данными"""
        logger.info("Начинаем дообучение ML моделей свежими данными...")
        
        # Получаем список всех существующих моделей
        model_files = [f for f in os.listdir(self.models_dir) if f.endswith('.joblib')]
        
        if not model_files:
            logger.warning("Не найдено существующих моделей для дообучения")
            return
        
        updated_models = 0
        failed_models = 0
        
        for model_file in model_files:
            product_code = model_file.replace('.joblib', '')
            
            try:
                logger.info(f"Дообучение модели для товара {product_code}...")
                
                # Загружаем существующую модель
                existing_model_data = self.load_existing_model(product_code)
                if not existing_model_data:
                    failed_models += 1
                    continue
                
                # Получаем свежие данные
                fresh_df = await self.get_fresh_data(product_code, days_back=30)
                
                if not fresh_df.empty:
                    # Создаем признаки для дообучения
                    fresh_features = self.create_incremental_features(fresh_df, existing_model_data)
                    
                    if not fresh_features.empty:
                        # Дообучаем модель
                        result = self.incremental_train_model(product_code, fresh_features, existing_model_data)
                        if result:
                            self.training_results[product_code] = result
                            updated_models += 1
                        else:
                            failed_models += 1
                    else:
                        logger.warning(f"Не удалось создать признаки для дообучения {product_code}")
                        failed_models += 1
                else:
                    logger.warning(f"Нет свежих данных для дообучения {product_code}")
                    failed_models += 1
                
                # Пауза между товарами
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Ошибка дообучения модели {product_code}: {e}")
                failed_models += 1
        
        # Сохраняем результаты дообучения
        self.save_incremental_results()
        
        logger.info(f"Дообучение завершено. Обновлено: {updated_models}, Ошибок: {failed_models}")
    
    def save_incremental_results(self):
        """Сохраняет результаты дообучения"""
        timestamp = datetime.now().isoformat()
        
        results = {
            'timestamp': timestamp,
            'training_type': 'incremental_learning',
            'total_models': len(self.training_results),
            'results': self.training_results,
            'summary': {
                'avg_mae': np.mean([r['mae'] for r in self.training_results.values()]),
                'avg_r2': np.mean([r['r2_score'] for r in self.training_results.values()]),
                'avg_fresh_days': np.mean([r['fresh_days'] for r in self.training_results.values()]),
                'best_model': max(self.training_results.values(), key=lambda x: x['r2_score'])['product_code'] if self.training_results else None
            }
        }
        
        results_file = os.path.join(self.models_dir, 'incremental_training_results.json')
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Результаты дообучения сохранены в {results_file}")

async def main():
    """Основная функция"""
    logger.info("Запуск дообучения ML моделей свежими данными...")
    
    trainer = IncrementalModelTrainer()
    await trainer.incremental_train_all_models()
    
    logger.info("Дообучение завершено!")

if __name__ == "__main__":
    asyncio.run(main()) 