#!/usr/bin/env python3
"""
Интеграция с ML-сервисом для получения прогнозов
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class MLServiceIntegration:
    """Интеграция с ML-сервисом для получения прогнозов"""
    
    def __init__(self, ml_service_url: str = "http://ml-service:8000"):
        self.ml_service_url = ml_service_url
        self.session = None
    
    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход"""
        if self.session:
            await self.session.close()
    
    async def get_forecast(self, product_code: str, historical_data: List[float], 
                          forecast_days: int = 30) -> Dict[str, Any]:
        """Получает прогноз от ML-сервиса"""
        try:
            if not self.session:
                raise Exception("Сессия не инициализирована")
            
            # Подготавливаем данные для ML-сервиса
            features = self._prepare_features(product_code, historical_data)
            
            # Отправляем запрос к ML-сервису
            url = f"{self.ml_service_url}/forecast"
            payload = {
                "product_id": product_code,
                "features": features,
                "forecast_days": forecast_days
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return self._process_ml_response(result)
                else:
                    logger.warning(f"ML-сервис вернул статус {response.status}")
                    return self._get_fallback_forecast(historical_data)
                    
        except Exception as e:
            logger.error(f"Ошибка получения прогноза от ML-сервиса: {e}")
            return self._get_fallback_forecast(historical_data)
    
    async def get_batch_forecasts(self, products_data: Dict[str, List[float]], 
                                 forecast_days: int = 30) -> Dict[str, Dict[str, Any]]:
        """Получает прогнозы для нескольких товаров"""
        try:
            if not self.session:
                raise Exception("Сессия не инициализирована")
            
            # Подготавливаем данные для всех товаров
            batch_payload = {
                "forecasts": [
                    {
                        "product_id": product_code,
                        "features": self._prepare_features(product_code, historical_data),
                        "forecast_days": forecast_days
                    }
                    for product_code, historical_data in products_data.items()
                ]
            }
            
            # Отправляем запрос к ML-сервису
            url = f"{self.ml_service_url}/batch_forecast"
            
            async with self.session.post(url, json=batch_payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        product_code: self._process_ml_response(forecast_data)
                        for product_code, forecast_data in result.get("forecasts", {}).items()
                    }
                else:
                    logger.warning(f"ML-сервис вернул статус {response.status}")
                    return self._get_fallback_batch_forecasts(products_data)
                    
        except Exception as e:
            logger.error(f"Ошибка получения batch прогнозов от ML-сервиса: {e}")
            return self._get_fallback_batch_forecasts(products_data)
    
    def _prepare_features(self, product_code: str, historical_data: List[float]) -> Dict[str, Any]:
        """Подготавливает признаки для ML-модели"""
        if not historical_data:
            return {
                "historical_consumption": [],
                "days_count": 0,
                "avg_consumption": 1.0,
                "trend": "stable",
                "seasonality": 1.0
            }
        
        # Базовые статистики
        avg_consumption = sum(historical_data) / len(historical_data)
        
        # Анализ тренда
        if len(historical_data) >= 7:
            recent_avg = sum(historical_data[-7:]) / 7
            older_avg = sum(historical_data[-14:-7]) / 7 if len(historical_data) >= 14 else avg_consumption
            trend = "increasing" if recent_avg > older_avg * 1.1 else "decreasing" if recent_avg < older_avg * 0.9 else "stable"
        else:
            trend = "stable"
        
        # Сезонность (упрощенная)
        current_month = datetime.now().month
        if current_month in [12, 1, 2]:  # Зима
            seasonality = 0.9
        elif current_month in [6, 7, 8]:  # Лето
            seasonality = 1.1
        else:
            seasonality = 1.0
        
        return {
            "historical_consumption": historical_data,
            "days_count": len(historical_data),
            "avg_consumption": avg_consumption,
            "trend": trend,
            "seasonality": seasonality,
            "product_code": product_code,
            "current_date": datetime.now().isoformat()
        }
    
    def _process_ml_response(self, ml_response: Dict[str, Any]) -> Dict[str, Any]:
        """Обрабатывает ответ от ML-сервиса"""
        try:
            predictions = ml_response.get("predictions", [])
            confidence = ml_response.get("confidence", 0.5)
            model_type = ml_response.get("model_type", "fallback")
            
            if not predictions:
                return self._get_fallback_forecast([])
            
            # Рассчитываем средний прогноз
            avg_prediction = sum(predictions) / len(predictions)
            
            # Определяем тренд
            if len(predictions) >= 2:
                trend = "increasing" if predictions[-1] > predictions[0] * 1.05 else "decreasing" if predictions[-1] < predictions[0] * 0.95 else "stable"
            else:
                trend = "stable"
            
            # Рассчитываем сезонность
            seasonality_factor = ml_response.get("seasonality_factor", 1.0)
            
            return {
                "predicted_consumption": avg_prediction,
                "confidence": confidence,
                "trend": trend,
                "seasonality_factor": seasonality_factor,
                "next_month_forecast": avg_prediction * 30,
                "model_type": model_type,
                "predictions": predictions
            }
            
        except Exception as e:
            logger.error(f"Ошибка обработки ответа ML-сервиса: {e}")
            return self._get_fallback_forecast([])
    
    def _get_fallback_forecast(self, historical_data: List[float]) -> Dict[str, Any]:
        """Возвращает fallback прогноз при ошибке ML-сервиса"""
        if not historical_data:
            return {
                "predicted_consumption": 1.0,
                "confidence": 0.3,
                "trend": "stable",
                "seasonality_factor": 1.0,
                "next_month_forecast": 30.0,
                "model_type": "fallback",
                "predictions": [1.0] * 30
            }
        
        # Простой анализ
        avg_consumption = sum(historical_data) / len(historical_data)
        
        # Тренд
        if len(historical_data) >= 7:
            recent_avg = sum(historical_data[-7:]) / 7
            older_avg = sum(historical_data[-14:-7]) / 7 if len(historical_data) >= 14 else avg_consumption
            trend = "increasing" if recent_avg > older_avg * 1.1 else "decreasing" if recent_avg < older_avg * 0.9 else "stable"
        else:
            trend = "stable"
        
        # Сезонность
        current_month = datetime.now().month
        if current_month in [12, 1, 2]:
            seasonality_factor = 0.9
        elif current_month in [6, 7, 8]:
            seasonality_factor = 1.1
        else:
            seasonality_factor = 1.0
        
        return {
            "predicted_consumption": avg_consumption * seasonality_factor,
            "confidence": 0.5,
            "trend": trend,
            "seasonality_factor": seasonality_factor,
            "next_month_forecast": avg_consumption * 30 * seasonality_factor,
            "model_type": "fallback",
            "predictions": [avg_consumption * seasonality_factor] * 30
        }
    
    def _get_fallback_batch_forecasts(self, products_data: Dict[str, List[float]]) -> Dict[str, Dict[str, Any]]:
        """Возвращает fallback прогнозы для batch запроса"""
        return {
            product_code: self._get_fallback_forecast(historical_data)
            for product_code, historical_data in products_data.items()
        }
    
    async def check_ml_service_health(self) -> bool:
        """Проверяет доступность ML-сервиса"""
        try:
            if not self.session:
                return False
            
            url = f"{self.ml_service_url}/health"
            async with self.session.get(url) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Ошибка проверки здоровья ML-сервиса: {e}")
            return False
    
    async def get_model_performance(self, product_code: str) -> Dict[str, Any]:
        """Получает информацию о производительности модели"""
        try:
            if not self.session:
                return {"error": "Сессия не инициализирована"}
            
            url = f"{self.ml_service_url}/model_performance/{product_code}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"ML-сервис вернул статус {response.status}"}
                    
        except Exception as e:
            logger.error(f"Ошибка получения производительности модели: {e}")
            return {"error": str(e)}

# Пример использования
async def main():
    """Тестирование интеграции с ML-сервисом"""
    
    # Тестовые данные
    historical_data = {
        '30001': [1.2, 1.1, 1.3, 1.0, 1.2, 1.4, 1.1, 1.3, 1.2, 1.1, 1.3, 1.2, 1.4, 1.1],
        '30002': [0.8, 0.9, 1.0, 0.8, 0.9, 1.1, 0.8, 0.9, 1.0, 0.8, 0.9, 1.1, 0.8, 0.9],
    }
    
    async with MLServiceIntegration() as ml_service:
        # Проверяем здоровье сервиса
        health = await ml_service.check_ml_service_health()
        print(f"ML-сервис здоров: {health}")
        
        # Получаем прогноз для одного товара
        forecast = await ml_service.get_forecast('30001', historical_data['30001'])
        print(f"Прогноз для 30001: {forecast}")
        
        # Получаем batch прогнозы
        batch_forecasts = await ml_service.get_batch_forecasts(historical_data)
        print(f"Batch прогнозы: {batch_forecasts}")

if __name__ == "__main__":
    asyncio.run(main()) 