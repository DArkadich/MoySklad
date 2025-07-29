"""
Сервис инженерии признаков для машинного обучения
"""

import logging
from typing import List, Dict, Any
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """Сервис инженерии признаков"""
    
    def __init__(self):
        self.feature_columns = [
            'quantity', 'price', 'day_of_week', 'month', 'is_weekend', 'is_holiday',
            'lag_1', 'lag_7', 'lag_30', 'rolling_mean_7', 'rolling_mean_30', 
            'rolling_std_7', 'trend', 'trend_squared', 'day_of_week_sin', 
            'day_of_week_cos', 'month_sin', 'month_cos', 'price_change', 'price_ma_7'
        ]

    async def create_features(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Создание признаков для прогнозирования"""
        try:
            if not historical_data:
                return {}
            
            # Создание DataFrame
            df = pd.DataFrame(historical_data)
            df = df.sort_values('date')
            
            # Создание признаков
            features = await self._create_time_features(df)
            features = await self._create_lag_features(features)
            features = await self._create_rolling_features(features)
            features = await self._create_trend_features(features)
            features = await self._create_seasonal_features(features)
            features = await self._create_price_features(features)
            
            # Удаление NaN значений
            features = features.dropna()
            
            # Преобразование в словарь
            feature_dict = {
                'features': features[self.feature_columns].to_dict('records'),
                'target': features['quantity'].tolist(),
                'dates': features['date'].tolist(),
                'feature_names': self.feature_columns
            }
            
            logger.info(f"Создано {len(feature_dict['features'])} записей с {len(self.feature_columns)} признаками")
            return feature_dict
            
        except Exception as e:
            logger.error(f"Ошибка создания признаков: {e}")
            return {}

    async def _create_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Создание временных признаков"""
        try:
            # Базовые временные признаки
            df['day_of_week'] = df['date'].dt.weekday
            df['month'] = df['date'].dt.month
            df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
            df['is_holiday'] = 0  # Будет добавлено позже
            
            return df
            
        except Exception as e:
            logger.error(f"Ошибка создания временных признаков: {e}")
            return df

    async def _create_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Создание лаговых признаков"""
        try:
            # Лаговые признаки
            df['lag_1'] = df['quantity'].shift(1)
            df['lag_7'] = df['quantity'].shift(7)
            df['lag_30'] = df['quantity'].shift(30)
            
            return df
            
        except Exception as e:
            logger.error(f"Ошибка создания лаговых признаков: {e}")
            return df

    async def _create_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Создание скользящих признаков"""
        try:
            # Скользящие средние и стандартные отклонения
            df['rolling_mean_7'] = df['quantity'].rolling(window=7).mean()
            df['rolling_mean_30'] = df['quantity'].rolling(window=30).mean()
            df['rolling_std_7'] = df['quantity'].rolling(window=7).std()
            
            return df
            
        except Exception as e:
            logger.error(f"Ошибка создания скользящих признаков: {e}")
            return df

    async def _create_trend_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Создание трендовых признаков"""
        try:
            # Трендовые признаки
            df['trend'] = np.arange(len(df))
            df['trend_squared'] = df['trend'] ** 2
            
            return df
            
        except Exception as e:
            logger.error(f"Ошибка создания трендовых признаков: {e}")
            return df

    async def _create_seasonal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Создание сезонных признаков"""
        try:
            # Сезонные признаки (синус и косинус)
            df['day_of_week_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
            df['day_of_week_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
            df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
            df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
            
            return df
            
        except Exception as e:
            logger.error(f"Ошибка создания сезонных признаков: {e}")
            return df

    async def _create_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Создание признаков цены"""
        try:
            # Признаки цены
            df['price_change'] = df['price'].pct_change()
            df['price_ma_7'] = df['price'].rolling(window=7).mean()
            
            return df
            
        except Exception as e:
            logger.error(f"Ошибка создания признаков цены: {e}")
            return df

    async def create_forecast_features(
        self, 
        last_data: List[Dict[str, Any]], 
        forecast_days: int
    ) -> List[Dict[str, Any]]:
        """Создание признаков для прогноза"""
        try:
            if not last_data:
                return []
            
            # Создание DataFrame из последних данных
            df = pd.DataFrame(last_data)
            df = df.sort_values('date')
            
            # Создание признаков
            features = await self._create_time_features(df)
            features = await self._create_lag_features(features)
            features = await self._create_rolling_features(features)
            features = await self._create_trend_features(features)
            features = await self._create_seasonal_features(features)
            features = await self._create_price_features(features)
            
            # Создание признаков для прогноза
            forecast_features = []
            last_date = features['date'].max()
            
            for i in range(forecast_days):
                forecast_date = last_date + timedelta(days=i+1)
                
                # Создание базовых признаков для прогноза
                feature_row = {
                    'date': forecast_date,
                    'day_of_week': forecast_date.weekday(),
                    'month': forecast_date.month,
                    'is_weekend': int(forecast_date.weekday() >= 5),
                    'is_holiday': 0,
                    'trend': len(features) + i,
                    'trend_squared': (len(features) + i) ** 2,
                    'day_of_week_sin': np.sin(2 * np.pi * forecast_date.weekday() / 7),
                    'day_of_week_cos': np.cos(2 * np.pi * forecast_date.weekday() / 7),
                    'month_sin': np.sin(2 * np.pi * forecast_date.month / 12),
                    'month_cos': np.cos(2 * np.pi * forecast_date.month / 12)
                }
                
                # Добавление лаговых признаков (используем последние известные значения)
                if len(features) > 0:
                    feature_row['lag_1'] = features['quantity'].iloc[-1]
                    feature_row['lag_7'] = features['quantity'].iloc[-7] if len(features) >= 7 else features['quantity'].iloc[-1]
                    feature_row['lag_30'] = features['quantity'].iloc[-30] if len(features) >= 30 else features['quantity'].iloc[-1]
                    feature_row['rolling_mean_7'] = features['rolling_mean_7'].iloc[-1]
                    feature_row['rolling_mean_30'] = features['rolling_mean_30'].iloc[-1]
                    feature_row['rolling_std_7'] = features['rolling_std_7'].iloc[-1]
                    feature_row['price'] = features['price'].iloc[-1]
                    feature_row['price_change'] = 0
                    feature_row['price_ma_7'] = features['price_ma_7'].iloc[-1]
                else:
                    # Значения по умолчанию
                    feature_row.update({
                        'lag_1': 0, 'lag_7': 0, 'lag_30': 0,
                        'rolling_mean_7': 0, 'rolling_mean_30': 0, 'rolling_std_7': 0,
                        'price': 0, 'price_change': 0, 'price_ma_7': 0
                    })
                
                forecast_features.append(feature_row)
            
            return forecast_features
            
        except Exception as e:
            logger.error(f"Ошибка создания признаков для прогноза: {e}")
            return []

    async def get_feature_importance(self, model, feature_names: List[str]) -> Dict[str, float]:
        """Получение важности признаков"""
        try:
            if hasattr(model, 'feature_importances_'):
                # Для Random Forest
                importance_dict = dict(zip(feature_names, model.feature_importances_))
            elif hasattr(model, 'coef_'):
                # Для Linear Regression
                importance_dict = dict(zip(feature_names, np.abs(model.coef_)))
            else:
                importance_dict = {name: 0.0 for name in feature_names}
            
            # Сортировка по важности
            sorted_importance = dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
            
            return sorted_importance
            
        except Exception as e:
            logger.error(f"Ошибка получения важности признаков: {e}")
            return {name: 0.0 for name in feature_names} 