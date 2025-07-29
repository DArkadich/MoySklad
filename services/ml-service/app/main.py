"""
Horiens ML Service
Сервис машинного обучения для прогнозирования спроса
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pickle
import os

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from app.core.config import settings
from app.core.database import get_database
from app.core.redis_client import get_redis_client
from app.services.ml_models import MLModelService
from app.services.data_processor import DataProcessor
from app.services.feature_engineering import FeatureEngineer
from app.utils.logging_config import setup_logging

# Настройка логирования
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Horiens ML Service",
    description="Сервис машинного обучения для прогнозирования спроса",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация сервисов
ml_service = MLModelService()
data_processor = DataProcessor()
feature_engineer = FeatureEngineer()


class ForecastRequest(BaseModel):
    """Запрос на прогнозирование"""
    product_id: str = Field(..., description="ID продукта")
    forecast_days: int = Field(30, description="Количество дней для прогноза")
    model_type: Optional[str] = Field(None, description="Тип модели (linear/rf/sarima/ensemble)")


class ForecastResponse(BaseModel):
    """Ответ с прогнозом"""
    product_id: str = Field(..., description="ID продукта")
    daily_demand: float = Field(..., description="Средний дневной спрос")
    weekly_demand: float = Field(..., description="Средний недельный спрос")
    monthly_demand: float = Field(..., description="Средний месячный спрос")
    accuracy: float = Field(..., description="Точность прогноза (0-1)")
    confidence_interval: Dict[str, float] = Field(..., description="Доверительный интервал")
    seasonality_factor: Optional[float] = Field(None, description="Фактор сезонности")
    trend_factor: Optional[float] = Field(None, description="Фактор тренда")
    model_type: str = Field(..., description="Использованная модель")
    features_used: List[str] = Field(..., description="Использованные признаки")
    last_updated: datetime = Field(..., description="Время последнего обновления")


class ModelTrainingRequest(BaseModel):
    """Запрос на обучение модели"""
    product_id: str = Field(..., description="ID продукта")
    model_type: str = Field(..., description="Тип модели")
    force_retrain: bool = Field(False, description="Принудительное переобучение")


class ModelTrainingResponse(BaseModel):
    """Ответ на обучение модели"""
    product_id: str = Field(..., description="ID продукта")
    model_type: str = Field(..., description="Тип модели")
    accuracy: float = Field(..., description="Точность модели")
    training_time: float = Field(..., description="Время обучения в секундах")
    features_count: int = Field(..., description="Количество признаков")
    status: str = Field(..., description="Статус обучения")


class ModelPerformance(BaseModel):
    """Производительность модели"""
    product_id: str = Field(..., description="ID продукта")
    model_type: str = Field(..., description="Тип модели")
    accuracy: float = Field(..., description="Точность")
    mae: float = Field(..., description="Средняя абсолютная ошибка")
    rmse: float = Field(..., description="Среднеквадратичная ошибка")
    r2_score: float = Field(..., description="R² коэффициент")
    last_evaluation: datetime = Field(..., description="Время последней оценки")


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info("🚀 Запуск Horiens ML Service")
    
    # Проверка подключений
    try:
        db = get_database()
        await db.connect()
        logger.info("✅ База данных подключена")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к БД: {e}")
    
    try:
        redis_client = get_redis_client()
        await redis_client.ping()
        logger.info("✅ Redis подключен")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к Redis: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при остановке"""
    logger.info("🛑 Остановка Horiens ML Service")


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "service": "ml-service",
        "timestamp": datetime.now().isoformat(),
        "models_loaded": len(ml_service.loaded_models)
    }


@app.post("/forecast", response_model=ForecastResponse)
async def get_forecast(request: ForecastRequest):
    """Получение прогноза спроса для продукта"""
    try:
        # Получение исторических данных
        historical_data = await data_processor.get_historical_data(
            request.product_id, 
            days_back=90
        )
        
        if not historical_data:
            raise HTTPException(
                status_code=404, 
                detail=f"Исторические данные для продукта {request.product_id} не найдены"
            )
        
        # Создание признаков
        features = await feature_engineer.create_features(historical_data)
        
        # Получение прогноза
        forecast = await ml_service.get_forecast(
            product_id=request.product_id,
            features=features,
            forecast_days=request.forecast_days,
            model_type=request.model_type
        )
        
        return ForecastResponse(
            product_id=request.product_id,
            daily_demand=forecast["daily_demand"],
            weekly_demand=forecast["weekly_demand"],
            monthly_demand=forecast["monthly_demand"],
            accuracy=forecast["accuracy"],
            confidence_interval=forecast["confidence_interval"],
            seasonality_factor=forecast.get("seasonality_factor"),
            trend_factor=forecast.get("trend_factor"),
            model_type=forecast["model_type"],
            features_used=forecast["features_used"],
            last_updated=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения прогноза для {request.product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/train", response_model=ModelTrainingResponse)
async def train_model(request: ModelTrainingRequest, background_tasks: BackgroundTasks):
    """Обучение модели для продукта"""
    try:
        # Получение данных для обучения
        training_data = await data_processor.get_training_data(
            request.product_id,
            days_back=180
        )
        
        if not training_data:
            raise HTTPException(
                status_code=404,
                detail=f"Данные для обучения модели {request.product_id} не найдены"
            )
        
        # Обучение модели
        training_result = await ml_service.train_model(
            product_id=request.product_id,
            training_data=training_data,
            model_type=request.model_type,
            force_retrain=request.force_retrain
        )
        
        return ModelTrainingResponse(
            product_id=request.product_id,
            model_type=request.model_type,
            accuracy=training_result["accuracy"],
            training_time=training_result["training_time"],
            features_count=training_result["features_count"],
            status="completed"
        )
        
    except Exception as e:
        logger.error(f"Ошибка обучения модели для {request.product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/retrain-all")
async def retrain_all_models(background_tasks: BackgroundTasks):
    """Переобучение всех моделей"""
    try:
        background_tasks.add_task(ml_service.retrain_all_models)
        return {
            "message": "Переобучение всех моделей запущено в фоне",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Ошибка запуска переобучения моделей: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models/{product_id}/performance", response_model=List[ModelPerformance])
async def get_model_performance(product_id: str):
    """Получение производительности моделей для продукта"""
    try:
        performance = await ml_service.get_model_performance(product_id)
        return performance
    except Exception as e:
        logger.error(f"Ошибка получения производительности моделей для {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models/status")
async def get_models_status():
    """Получение статуса всех моделей"""
    try:
        status = await ml_service.get_models_status()
        return status
    except Exception as e:
        logger.error(f"Ошибка получения статуса моделей: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/models/{product_id}/evaluate")
async def evaluate_model(product_id: str, model_type: str):
    """Оценка производительности модели"""
    try:
        evaluation = await ml_service.evaluate_model(product_id, model_type)
        return evaluation
    except Exception as e:
        logger.error(f"Ошибка оценки модели {model_type} для {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/seasonality/{product_id}")
async def get_seasonality_analysis(product_id: str):
    """Анализ сезонности для продукта"""
    try:
        seasonality = await ml_service.get_seasonality_analysis(product_id)
        return seasonality
    except Exception as e:
        logger.error(f"Ошибка анализа сезонности для {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/trends/{product_id}")
async def get_trend_analysis(product_id: str):
    """Анализ трендов для продукта"""
    try:
        trends = await ml_service.get_trend_analysis(product_id)
        return trends
    except Exception as e:
        logger.error(f"Ошибка анализа трендов для {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/data/update")
async def update_training_data(background_tasks: BackgroundTasks):
    """Обновление данных для обучения"""
    try:
        background_tasks.add_task(data_processor.update_all_data)
        return {
            "message": "Обновление данных запущено в фоне",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Ошибка обновления данных: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    ) 