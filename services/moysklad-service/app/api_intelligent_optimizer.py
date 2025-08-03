#!/usr/bin/env python3
"""
API для интеллектуального оптимизатора заказов с ML-интеграцией
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import json

from intelligent_order_optimizer import IntelligentOrderOptimizer
from ml_integration import MLServiceIntegration

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# FastAPI приложение
app = FastAPI(
    title="Intelligent Order Optimizer API", 
    description="API для интеллектуальной оптимизации заказов с ML-прогнозированием"
)

# Модели данных
class SKUData(BaseModel):
    """Данные SKU для анализа"""
    code: str = Field(..., description="Код товара")
    stock: float = Field(..., description="Текущий остаток")
    consumption: float = Field(..., description="Дневное потребление")
    diopter: Optional[float] = Field(None, description="Диоптрия")
    price: Optional[float] = Field(None, description="Цена товара")
    category: Optional[str] = Field(None, description="Категория товара")

class HistoricalData(BaseModel):
    """Исторические данные для ML-прогнозирования"""
    product_code: str = Field(..., description="Код товара")
    consumption_history: List[float] = Field(..., description="История потребления")
    dates: Optional[List[str]] = Field(None, description="Даты измерений")

class IntelligentOrderRequest(BaseModel):
    """Запрос на интеллектуальную оптимизацию заказа"""
    sku_data: List[SKUData] = Field(..., description="Данные SKU для анализа")
    historical_data: Optional[List[HistoricalData]] = Field(None, description="Исторические данные для ML")
    min_order_volume: Optional[int] = Field(None, description="Минимальный объем заказа")
    delivery_optimization: bool = Field(True, description="Включить оптимизацию доставки")
    ml_forecasting: bool = Field(True, description="Включить ML-прогнозирование")
    forecast_days: int = Field(30, description="Количество дней для прогноза")

class SKUOrder(BaseModel):
    """Заказ для конкретного SKU"""
    product_code: str
    diopter: Optional[float]
    volume: int
    days_until_oos: int
    new_oos_date: int
    criticality: str
    coverage_days: float
    ml_forecast: Optional[Dict[str, Any]]

class DeliveryOptimization(BaseModel):
    """Оптимизация доставки"""
    can_combine: bool
    savings_days: int
    combined_products: List[str]
    separate_products: List[str]

class MLInsights(BaseModel):
    """ML-инсайты"""
    trends: Dict[str, List[str]]
    seasonality_impact: Dict[str, List[str]]
    confidence_levels: Dict[str, List[str]]
    recommendations: List[str]

class IntelligentOrderResponse(BaseModel):
    """Ответ с результатами интеллектуальной оптимизации"""
    order_needed: bool
    total_volume: int
    min_order: int
    utilization: float
    sku_orders: List[SKUOrder]
    order_date: str
    delivery_date: str
    delivery_optimization: Optional[DeliveryOptimization]
    ml_insights: Optional[MLInsights]
    processing_time: float
    model_version: str = "2.0.0"

# Глобальные переменные
optimizer = None
ml_service = None

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    global optimizer, ml_service
    
    logger.info("🚀 Запуск Intelligent Order Optimizer API")
    
    # Инициализируем оптимизатор
    optimizer = IntelligentOrderOptimizer()
    
    # Проверяем доступность ML-сервиса
    try:
        async with MLServiceIntegration() as ml:
            health = await ml.check_ml_service_health()
            logger.info(f"ML-сервис доступен: {health}")
    except Exception as e:
        logger.warning(f"ML-сервис недоступен: {e}")

@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "service": "Intelligent Order Optimizer API",
        "version": "2.0.0",
        "description": "API для интеллектуальной оптимизации заказов с ML-прогнозированием",
        "endpoints": {
            "/optimize": "POST - Интеллектуальная оптимизация заказа",
            "/health": "GET - Проверка здоровья сервиса",
            "/ml-status": "GET - Статус ML-сервиса",
            "/batch-optimize": "POST - Batch оптимизация заказов"
        }
    }

@app.post("/optimize", response_model=IntelligentOrderResponse)
async def optimize_order(request: IntelligentOrderRequest):
    """Интеллектуальная оптимизация заказа"""
    start_time = datetime.now()
    
    try:
        logger.info(f"📊 Запрос на оптимизацию заказа для {len(request.sku_data)} SKU")
        
        # Подготавливаем данные
        sku_data = [sku.dict() for sku in request.sku_data]
        
        # Подготавливаем исторические данные
        historical_data = None
        if request.historical_data and request.ml_forecasting:
            historical_data = {
                hist.product_code: hist.consumption_history 
                for hist in request.historical_data
            }
        
        # Выполняем оптимизацию
        result = await optimizer.analyze_intelligent_order(sku_data, historical_data)
        
        # Добавляем время обработки
        processing_time = (datetime.now() - start_time).total_seconds()
        result['processing_time'] = processing_time
        
        logger.info(f"✅ Оптимизация завершена за {processing_time:.2f} сек")
        
        return IntelligentOrderResponse(**result)
        
    except Exception as e:
        logger.error(f"❌ Ошибка оптимизации: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка оптимизации: {str(e)}")

@app.post("/batch-optimize")
async def batch_optimize_orders(requests: List[IntelligentOrderRequest]):
    """Batch оптимизация заказов для нескольких категорий"""
    start_time = datetime.now()
    
    try:
        logger.info(f"📊 Batch оптимизация для {len(requests)} запросов")
        
        results = []
        for i, request in enumerate(requests):
            logger.info(f"Обработка запроса {i+1}/{len(requests)}")
            
            # Подготавливаем данные
            sku_data = [sku.dict() for sku in request.sku_data]
            
            # Подготавливаем исторические данные
            historical_data = None
            if request.historical_data and request.ml_forecasting:
                historical_data = {
                    hist.product_code: hist.consumption_history 
                    for hist in request.historical_data
                }
            
            # Выполняем оптимизацию
            result = await optimizer.analyze_intelligent_order(sku_data, historical_data)
            results.append(result)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "results": results,
            "total_requests": len(requests),
            "processing_time": processing_time,
            "average_time": processing_time / len(requests)
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка batch оптимизации: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка batch оптимизации: {str(e)}")

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    try:
        # Проверяем ML-сервис
        ml_health = False
        try:
            async with MLServiceIntegration() as ml:
                ml_health = await ml.check_ml_service_health()
        except Exception as e:
            logger.warning(f"ML-сервис недоступен: {e}")
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "ml_service": "healthy" if ml_health else "unavailable",
            "optimizer": "ready"
        }
    except Exception as e:
        logger.error(f"Ошибка проверки здоровья: {e}")
        raise HTTPException(status_code=500, detail="Service unhealthy")

@app.get("/ml-status")
async def ml_status():
    """Статус ML-сервиса"""
    try:
        async with MLServiceIntegration() as ml:
            health = await ml.check_ml_service_health()
            
            # Получаем информацию о производительности моделей
            model_performance = {}
            if health:
                # Здесь можно добавить получение информации о моделях
                pass
            
            return {
                "ml_service_available": health,
                "model_performance": model_performance,
                "last_check": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Ошибка проверки ML-статуса: {e}")
        return {
            "ml_service_available": False,
            "error": str(e),
            "last_check": datetime.now().isoformat()
        }

@app.get("/optimizer/features")
async def get_optimizer_features():
    """Получение информации о возможностях оптимизатора"""
    return {
        "features": [
            "ML-прогнозирование спроса",
            "Анализ сезонности",
            "Оптимизация доставки",
            "Динамическое формирование заказов",
            "Приоритизация по критичности",
            "Учет кратности заказов",
            "Анализ трендов",
            "Генерация ML-инсайтов"
        ],
        "supported_product_types": [
            "daily_lenses",
            "monthly_lenses_6", 
            "monthly_lenses_3",
            "solution_360",
            "solution_500",
            "solution_120"
        ],
        "ml_models": [
            "linear_regression",
            "random_forest", 
            "sarima",
            "ensemble"
        ]
    }

@app.post("/optimizer/test")
async def test_optimizer():
    """Тестирование оптимизатора с тестовыми данными"""
    try:
        # Тестовые данные
        test_data = [
            SKUData(code='30001', stock=385, consumption=1, diopter=-0.5),
            SKUData(code='30002', stock=154, consumption=1, diopter=-0.75),
            SKUData(code='30003', stock=103, consumption=1, diopter=-1.00),
            SKUData(code='30004', stock=80, consumption=1, diopter=-1.25),
            SKUData(code='30005', stock=5, consumption=1, diopter=-1.50),
        ]
        
        # Исторические данные
        historical_data = [
            HistoricalData(
                product_code='30001',
                consumption_history=[1.2, 1.1, 1.3, 1.0, 1.2, 1.4, 1.1, 1.3, 1.2, 1.1, 1.3, 1.2, 1.4, 1.1]
            ),
            HistoricalData(
                product_code='30002', 
                consumption_history=[0.8, 0.9, 1.0, 0.8, 0.9, 1.1, 0.8, 0.9, 1.0, 0.8, 0.9, 1.1, 0.8, 0.9]
            ),
            HistoricalData(
                product_code='30003',
                consumption_history=[1.0, 1.1, 1.0, 1.2, 1.0, 1.1, 1.0, 1.2, 1.0, 1.1, 1.0, 1.2, 1.0, 1.1]
            ),
            HistoricalData(
                product_code='30004',
                consumption_history=[0.7, 0.8, 0.7, 0.9, 0.7, 0.8, 0.7, 0.9, 0.7, 0.8, 0.7, 0.9, 0.7, 0.8]
            ),
            HistoricalData(
                product_code='30005',
                consumption_history=[0.5, 0.6, 0.5, 0.7, 0.5, 0.6, 0.5, 0.7, 0.5, 0.6, 0.5, 0.7, 0.5, 0.6]
            ),
        ]
        
        request = IntelligentOrderRequest(
            sku_data=test_data,
            historical_data=historical_data,
            ml_forecasting=True,
            delivery_optimization=True
        )
        
        # Выполняем оптимизацию
        result = await optimize_order(request)
        
        return {
            "test_result": result,
            "message": "Тест оптимизатора выполнен успешно"
        }
        
    except Exception as e:
        logger.error(f"Ошибка тестирования: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка тестирования: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 