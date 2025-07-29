"""
Сервис ML моделей для прогнозирования спроса
"""

import logging
import pickle
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.seasonal import seasonal_decompose
import warnings
warnings.filterwarnings('ignore')

from app.core.config import settings
from app.core.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class MLModelService:
    """Сервис машинного обучения для прогнозирования спроса"""
    
    def __init__(self):
        self.models_dir = "/app/models"
        self.loaded_models = {}
        self.scalers = {}
        self.redis_client = None
        
        # Создание директории для моделей
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Загрузка существующих моделей
        self._load_existing_models()

    def _load_existing_models(self):
        """Загрузка существующих моделей из файлов"""
        try:
            for filename in os.listdir(self.models_dir):
                if filename.endswith('.pkl'):
                    model_path = os.path.join(self.models_dir, filename)
                    with open(model_path, 'rb') as f:
                        model_data = pickle.load(f)
                        
                    product_id = model_data['product_id']
                    model_type = model_data['model_type']
                    key = f"{product_id}_{model_type}"
                    
                    self.loaded_models[key] = model_data
                    logger.info(f"Загружена модель: {key}")
                    
        except Exception as e:
            logger.error(f"Ошибка загрузки моделей: {e}")

    async def get_forecast(
        self, 
        product_id: str, 
        features: Dict[str, Any],
        forecast_days: int = 30,
        model_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Получение прогноза спроса"""
        try:
            # Определение лучшей модели
            if not model_type:
                model_type = await self._get_best_model_type(product_id)
            
            # Получение модели
            model_key = f"{product_id}_{model_type}"
            model_data = self.loaded_models.get(model_key)
            
            if not model_data:
                # Fallback на простую модель
                return await self._get_simple_forecast(features, forecast_days)
            
            # Подготовка данных для прогноза
            X_forecast = await self._prepare_forecast_features(features, forecast_days)
            
            # Получение прогноза
            if model_type == "linear":
                forecast = await self._linear_forecast(model_data, X_forecast)
            elif model_type == "rf":
                forecast = await self._random_forest_forecast(model_data, X_forecast)
            elif model_type == "sarima":
                forecast = await self._sarima_forecast(model_data, features)
            elif model_type == "ensemble":
                forecast = await self._ensemble_forecast(product_id, X_forecast)
            else:
                forecast = await self._get_simple_forecast(features, forecast_days)
            
            # Добавление метаданных
            forecast.update({
                "model_type": model_type,
                "features_used": list(features.keys()),
                "accuracy": model_data.get("accuracy", 0.8),
                "confidence_interval": await self._calculate_confidence_interval(forecast["predictions"])
            })
            
            return forecast
            
        except Exception as e:
            logger.error(f"Ошибка получения прогноза для {product_id}: {e}")
            return await self._get_simple_forecast(features, forecast_days)

    async def train_model(
        self, 
        product_id: str, 
        training_data: List[Dict[str, Any]],
        model_type: str = "ensemble",
        force_retrain: bool = False
    ) -> Dict[str, Any]:
        """Обучение модели"""
        try:
            start_time = datetime.now()
            
            # Подготовка данных
            X, y = await self._prepare_training_data(training_data)
            
            if len(X) < 30:  # Минимальное количество данных
                raise ValueError("Недостаточно данных для обучения модели")
            
            # Обучение модели
            if model_type == "linear":
                model, scaler = await self._train_linear_model(X, y)
            elif model_type == "rf":
                model, scaler = await self._train_random_forest_model(X, y)
            elif model_type == "sarima":
                model, scaler = await self._train_sarima_model(training_data)
            elif model_type == "ensemble":
                model, scaler = await self._train_ensemble_model(X, y)
            else:
                raise ValueError(f"Неизвестный тип модели: {model_type}")
            
            # Оценка модели
            accuracy = await self._evaluate_model(model, X, y, model_type)
            
            # Сохранение модели
            model_data = {
                "product_id": product_id,
                "model_type": model_type,
                "model": model,
                "scaler": scaler,
                "accuracy": accuracy,
                "training_time": (datetime.now() - start_time).total_seconds(),
                "features_count": X.shape[1] if hasattr(X, 'shape') else len(X[0]),
                "trained_at": datetime.now().isoformat()
            }
            
            await self._save_model(model_data)
            
            # Обновление загруженных моделей
            key = f"{product_id}_{model_type}"
            self.loaded_models[key] = model_data
            
            logger.info(f"Модель {model_type} для {product_id} обучена с точностью {accuracy:.4f}")
            
            return {
                "accuracy": accuracy,
                "training_time": model_data["training_time"],
                "features_count": model_data["features_count"]
            }
            
        except Exception as e:
            logger.error(f"Ошибка обучения модели {model_type} для {product_id}: {e}")
            raise

    async def _train_linear_model(self, X: np.ndarray, y: np.ndarray) -> Tuple[LinearRegression, StandardScaler]:
        """Обучение линейной модели"""
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        model = LinearRegression()
        model.fit(X_scaled, y)
        
        return model, scaler

    async def _train_random_forest_model(self, X: np.ndarray, y: np.ndarray) -> Tuple[RandomForestRegressor, StandardScaler]:
        """Обучение модели случайного леса"""
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        model.fit(X_scaled, y)
        
        return model, scaler

    async def _train_sarima_model(self, training_data: List[Dict[str, Any]]) -> Tuple[SARIMAX, None]:
        """Обучение SARIMA модели"""
        # Подготовка временного ряда
        df = pd.DataFrame(training_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
        
        # SARIMA модель
        model = SARIMAX(
            df['quantity'],
            order=(1, 1, 1),
            seasonal_order=(1, 1, 1, 7),  # Недельная сезонность
            enforce_stationarity=False,
            enforce_invertibility=False
        )
        
        fitted_model = model.fit(disp=False)
        return fitted_model, None

    async def _train_ensemble_model(self, X: np.ndarray, y: np.ndarray) -> Tuple[Dict, StandardScaler]:
        """Обучение ансамблевой модели"""
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Обучение нескольких моделей
        models = {
            "linear": LinearRegression(),
            "rf": RandomForestRegressor(n_estimators=100, random_state=42)
        }
        
        for name, model in models.items():
            model.fit(X_scaled, y)
        
        return models, scaler

    async def _evaluate_model(self, model, X: np.ndarray, y: np.ndarray, model_type: str) -> float:
        """Оценка производительности модели"""
        if model_type == "sarima":
            # Для SARIMA используем последние данные
            predictions = model.forecast(steps=len(y))
            accuracy = r2_score(y, predictions)
        else:
            predictions = model.predict(X)
            accuracy = r2_score(y, predictions)
        
        return max(0, accuracy)  # Ограничиваем снизу нулем

    async def _prepare_training_data(self, training_data: List[Dict[str, Any]]) -> Tuple[np.ndarray, np.ndarray]:
        """Подготовка данных для обучения"""
        features = []
        targets = []
        
        for data_point in training_data:
            feature_vector = [
                data_point.get('quantity', 0),
                data_point.get('price', 0),
                data_point.get('day_of_week', 0),
                data_point.get('month', 0),
                data_point.get('is_weekend', 0),
                data_point.get('is_holiday', 0),
                data_point.get('lag_1', 0),
                data_point.get('lag_7', 0),
                data_point.get('rolling_mean_7', 0),
                data_point.get('rolling_std_7', 0)
            ]
            features.append(feature_vector)
            targets.append(data_point.get('quantity', 0))
        
        return np.array(features), np.array(targets)

    async def _prepare_forecast_features(self, features: Dict[str, Any], forecast_days: int) -> np.ndarray:
        """Подготовка признаков для прогноза"""
        forecast_features = []
        
        for day in range(forecast_days):
            feature_vector = [
                features.get('current_quantity', 0),
                features.get('current_price', 0),
                (datetime.now() + timedelta(days=day)).weekday(),
                (datetime.now() + timedelta(days=day)).month,
                int((datetime.now() + timedelta(days=day)).weekday() >= 5),
                0,  # is_holiday
                features.get('lag_1', 0),
                features.get('lag_7', 0),
                features.get('rolling_mean_7', 0),
                features.get('rolling_std_7', 0)
            ]
            forecast_features.append(feature_vector)
        
        return np.array(forecast_features)

    async def _linear_forecast(self, model_data: Dict, X_forecast: np.ndarray) -> Dict[str, Any]:
        """Прогноз с помощью линейной модели"""
        model = model_data['model']
        scaler = model_data['scaler']
        
        X_scaled = scaler.transform(X_forecast)
        predictions = model.predict(X_scaled)
        
        return {
            "predictions": predictions.tolist(),
            "daily_demand": float(np.mean(predictions)),
            "weekly_demand": float(np.mean(predictions) * 7),
            "monthly_demand": float(np.mean(predictions) * 30)
        }

    async def _random_forest_forecast(self, model_data: Dict, X_forecast: np.ndarray) -> Dict[str, Any]:
        """Прогноз с помощью случайного леса"""
        model = model_data['model']
        scaler = model_data['scaler']
        
        X_scaled = scaler.transform(X_forecast)
        predictions = model.predict(X_scaled)
        
        return {
            "predictions": predictions.tolist(),
            "daily_demand": float(np.mean(predictions)),
            "weekly_demand": float(np.mean(predictions) * 7),
            "monthly_demand": float(np.mean(predictions) * 30)
        }

    async def _sarima_forecast(self, model_data: Dict, features: Dict[str, Any]) -> Dict[str, Any]:
        """Прогноз с помощью SARIMA"""
        model = model_data['model']
        
        # Прогноз на 30 дней
        forecast = model.forecast(steps=30)
        
        return {
            "predictions": forecast.tolist(),
            "daily_demand": float(np.mean(forecast)),
            "weekly_demand": float(np.mean(forecast) * 7),
            "monthly_demand": float(np.mean(forecast) * 30),
            "seasonality_factor": await self._calculate_seasonality_factor(forecast),
            "trend_factor": await self._calculate_trend_factor(forecast)
        }

    async def _ensemble_forecast(self, product_id: str, X_forecast: np.ndarray) -> Dict[str, Any]:
        """Ансамблевый прогноз"""
        predictions = []
        
        # Получение прогнозов от всех моделей
        for model_type in ["linear", "rf"]:
            model_key = f"{product_id}_{model_type}"
            model_data = self.loaded_models.get(model_key)
            
            if model_data:
                if model_type == "linear":
                    pred = await self._linear_forecast(model_data, X_forecast)
                elif model_type == "rf":
                    pred = await self._random_forest_forecast(model_data, X_forecast)
                
                predictions.append(pred["predictions"])
        
        if predictions:
            # Усреднение прогнозов
            ensemble_predictions = np.mean(predictions, axis=0)
            
            return {
                "predictions": ensemble_predictions.tolist(),
                "daily_demand": float(np.mean(ensemble_predictions)),
                "weekly_demand": float(np.mean(ensemble_predictions) * 7),
                "monthly_demand": float(np.mean(ensemble_predictions) * 30)
            }
        else:
            return await self._get_simple_forecast({}, 30)

    async def _get_simple_forecast(self, features: Dict[str, Any], forecast_days: int) -> Dict[str, Any]:
        """Простой прогноз на основе исторических данных"""
        # Простое среднее значение
        base_demand = features.get('rolling_mean_7', 10)
        
        predictions = [base_demand] * forecast_days
        
        return {
            "predictions": predictions,
            "daily_demand": float(base_demand),
            "weekly_demand": float(base_demand * 7),
            "monthly_demand": float(base_demand * 30),
            "model_type": "simple",
            "accuracy": 0.5
        }

    async def _get_best_model_type(self, product_id: str) -> str:
        """Определение лучшей модели для продукта"""
        best_model = "ensemble"
        best_accuracy = 0
        
        for model_type in ["linear", "rf", "ensemble"]:
            model_key = f"{product_id}_{model_type}"
            model_data = self.loaded_models.get(model_key)
            
            if model_data and model_data.get("accuracy", 0) > best_accuracy:
                best_accuracy = model_data["accuracy"]
                best_model = model_type
        
        return best_model

    async def _calculate_confidence_interval(self, predictions: List[float]) -> Dict[str, float]:
        """Расчет доверительного интервала"""
        if not predictions:
            return {"lower": 0, "upper": 0}
        
        mean_pred = np.mean(predictions)
        std_pred = np.std(predictions)
        
        return {
            "lower": float(mean_pred - 1.96 * std_pred),
            "upper": float(mean_pred + 1.96 * std_pred)
        }

    async def _calculate_seasonality_factor(self, predictions: np.ndarray) -> float:
        """Расчет фактора сезонности"""
        if len(predictions) < 7:
            return 1.0
        
        # Простой анализ сезонности
        weekly_pattern = []
        for i in range(7):
            week_values = predictions[i::7]
            weekly_pattern.append(np.mean(week_values))
        
        return float(np.std(weekly_pattern) / np.mean(weekly_pattern))

    async def _calculate_trend_factor(self, predictions: np.ndarray) -> float:
        """Расчет фактора тренда"""
        if len(predictions) < 2:
            return 0.0
        
        # Простой анализ тренда
        x = np.arange(len(predictions))
        slope = np.polyfit(x, predictions, 1)[0]
        
        return float(slope / np.mean(predictions))

    async def _save_model(self, model_data: Dict[str, Any]):
        """Сохранение модели в файл"""
        try:
            filename = f"{model_data['product_id']}_{model_data['model_type']}.pkl"
            filepath = os.path.join(self.models_dir, filename)
            
            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"Модель сохранена: {filepath}")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения модели: {e}")

    async def retrain_all_models(self):
        """Переобучение всех моделей"""
        # Этот метод будет реализован позже
        logger.info("Переобучение всех моделей")

    async def get_model_performance(self, product_id: str) -> List[Dict[str, Any]]:
        """Получение производительности моделей"""
        performance = []
        
        for model_type in ["linear", "rf", "ensemble"]:
            model_key = f"{product_id}_{model_type}"
            model_data = self.loaded_models.get(model_key)
            
            if model_data:
                performance.append({
                    "product_id": product_id,
                    "model_type": model_type,
                    "accuracy": model_data.get("accuracy", 0),
                    "mae": 0,  # Будет рассчитано при оценке
                    "rmse": 0,  # Будет рассчитано при оценке
                    "r2_score": model_data.get("accuracy", 0),
                    "last_evaluation": model_data.get("trained_at", datetime.now().isoformat())
                })
        
        return performance

    async def get_models_status(self) -> Dict[str, Any]:
        """Получение статуса всех моделей"""
        status = {
            "total_models": len(self.loaded_models),
            "models_by_type": {},
            "average_accuracy": 0
        }
        
        accuracies = []
        for key, model_data in self.loaded_models.items():
            model_type = model_data["model_type"]
            accuracy = model_data.get("accuracy", 0)
            
            if model_type not in status["models_by_type"]:
                status["models_by_type"][model_type] = 0
            status["models_by_type"][model_type] += 1
            
            accuracies.append(accuracy)
        
        if accuracies:
            status["average_accuracy"] = float(np.mean(accuracies))
        
        return status

    async def evaluate_model(self, product_id: str, model_type: str) -> Dict[str, Any]:
        """Оценка производительности модели"""
        # Этот метод будет реализован позже
        return {"status": "evaluation_not_implemented"}

    async def get_seasonality_analysis(self, product_id: str) -> Dict[str, Any]:
        """Анализ сезонности"""
        # Этот метод будет реализован позже
        return {"status": "seasonality_analysis_not_implemented"}

    async def get_trend_analysis(self, product_id: str) -> Dict[str, Any]:
        """Анализ трендов"""
        # Этот метод будет реализован позже
        return {"status": "trend_analysis_not_implemented"} 