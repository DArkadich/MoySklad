"""
Horiens Purchase Service
Основной сервис управления закупками
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from app.core.config import settings
from app.core.database import get_database, close_database
from app.core.redis_client import get_redis_client, close_redis
from app.core.rabbitmq_client import get_rabbitmq_client, close_rabbitmq, publish_message
from app.utils.logging_config import setup_logging, get_logger
from app.services.purchase_logic import PurchaseLogicService
from app.services.moysklad_integration import MoySkladService
from app.services.delivery_optimizer import DeliveryOptimizer
from app.models.purchase_models import (
    PurchaseRequest, PurchaseResponse, PurchaseRecommendation,
    InventoryStatus, ProductInfo, DeliveryOptimization
)

# Настройка логирования
setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="Purchase Service",
    description="Сервис управления закупками с учетом сроков доставки",
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
purchase_logic = PurchaseLogicService()
moysklad_service = MoySkladService()
delivery_optimizer = DeliveryOptimizer()

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info("Запуск Purchase Service...")
    await get_database()
    await get_redis_client()
    await get_rabbitmq_client()

@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при завершении"""
    logger.info("Остановка Purchase Service...")
    await close_database()
    await close_redis()
    await close_rabbitmq()

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "service": "purchase-service",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/products")
async def get_products():
    """Получить информацию о продуктах с учетом сроков доставки"""
    try:
        products = await purchase_logic.get_products_info()
        return {
            "status": "success",
            "data": products,
            "count": len(products)
        }
    except Exception as e:
        logger.error(f"Ошибка получения продуктов: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/inventory/status")
async def get_inventory_status(product_id: Optional[str] = None):
    """Получить статус склада с учетом прогнозов и сроков доставки"""
    try:
        inventory_status = await purchase_logic.get_inventory_status(product_id)
        return {
            "status": "success",
            "data": inventory_status,
            "count": len(inventory_status)
        }
    except Exception as e:
        logger.error(f"Ошибка получения статуса склада: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/purchase/recommendations")
async def get_purchase_recommendations():
    """Получить рекомендации по закупкам с учетом сроков доставки"""
    try:
        recommendations = await purchase_logic.generate_purchase_recommendations()
        return {
            "status": "success",
            "data": recommendations,
            "count": len(recommendations)
        }
    except Exception as e:
        logger.error(f"Ошибка получения рекомендаций: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/purchase/execute")
async def execute_purchase(request: PurchaseRequest, background_tasks: BackgroundTasks):
    """Выполнить закупку с учетом сроков доставки"""
    try:
        # Выполнение закупки
        response = await purchase_logic.execute_purchase(request)
        
        if response.success:
            # Отправка уведомления в фоне
            background_tasks.add_task(
                publish_message,
                "notifications",
                {
                    "type": "purchase_created",
                    "message": f"Создан заказ {response.order_id} на {request.quantity} шт",
                    "data": {
                        "order_id": response.order_id,
                        "product_id": request.product_id,
                        "quantity": request.quantity,
                        "estimated_delivery": response.estimated_delivery_date,
                        "manufacturing_time": response.manufacturing_time_days,
                        "delivery_time": response.delivery_time_days
                    }
                }
            )
        
        return response
    except Exception as e:
        logger.error(f"Ошибка выполнения закупки: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/delivery/optimize")
async def optimize_delivery(orders: List[Dict]):
    """Оптимизировать доставку с учетом возможности одновременной доставки"""
    try:
        # Оптимизация расписания доставки
        schedules = await delivery_optimizer.optimize_delivery_schedule(orders)
        
        # Расчет стоимости доставки
        cost_analysis = await delivery_optimizer.calculate_delivery_cost(schedules)
        
        # Генерация отчета
        delivery_report = await delivery_optimizer.generate_delivery_report(schedules)
        
        return {
            "status": "success",
            "data": {
                "schedules": schedules,
                "cost_analysis": cost_analysis,
                "delivery_report": delivery_report
            }
        }
    except Exception as e:
        logger.error(f"Ошибка оптимизации доставки: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/delivery/cost")
async def calculate_delivery_cost(product_type: str, quantity: int):
    """Рассчитать стоимость доставки для конкретного продукта"""
    try:
        # Создание тестового расписания
        test_order = {
            "product_id": "test",
            "product_name": f"Тестовый {product_type}",
            "quantity": quantity
        }
        
        schedules = await delivery_optimizer.optimize_delivery_schedule([test_order])
        cost_analysis = await delivery_optimizer.calculate_delivery_cost(schedules)
        
        return {
            "status": "success",
            "data": cost_analysis
        }
    except Exception as e:
        logger.error(f"Ошибка расчета стоимости доставки: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/delivery/optimal-date")
async def get_optimal_delivery_date(product_type: str, quantity: int):
    """Получить оптимальную дату доставки"""
    try:
        optimal_date = await delivery_optimizer.get_optimal_delivery_date(product_type, quantity)
        
        return {
            "status": "success",
            "data": {
                "product_type": product_type,
                "quantity": quantity,
                "optimal_delivery_date": optimal_date.isoformat(),
                "days_from_now": (optimal_date - datetime.now()).days
            }
        }
    except Exception as e:
        logger.error(f"Ошибка получения оптимальной даты доставки: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/moysklad/health")
async def check_moysklad_health():
    """Проверить здоровье интеграции с МойСклад"""
    try:
        health_status = await moysklad_service.health_check()
        return {
            "status": "success",
            "data": health_status
        }
    except Exception as e:
        logger.error(f"Ошибка проверки здоровья МойСклад: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/moysklad/products")
async def get_moysklad_products():
    """Получить продукты из МойСклад"""
    try:
        products = await moysklad_service.get_all_products()
        return {
            "status": "success",
            "data": products,
            "count": len(products.get("rows", []))
        }
    except Exception as e:
        logger.error(f"Ошибка получения продуктов из МойСклад: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/moysklad/stock")
async def get_moysklad_stock():
    """Получить остатки из МойСклад"""
    try:
        stock = await moysklad_service.get_stock_info()
        return {
            "status": "success",
            "data": stock,
            "count": len(stock.get("rows", []))
        }
    except Exception as e:
        logger.error(f"Ошибка получения остатков из МойСклад: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/purchase/bulk")
async def execute_bulk_purchase(requests: List[PurchaseRequest], background_tasks: BackgroundTasks):
    """Выполнить массовую закупку с оптимизацией доставки"""
    try:
        results = []
        successful_orders = []
        
        # Выполнение закупок
        for request in requests:
            try:
                response = await purchase_logic.execute_purchase(request)
                results.append(response)
                
                if response.success:
                    successful_orders.append({
                        "product_id": request.product_id,
                        "product_name": "Product",  # Можно получить из МойСклад
                        "quantity": request.quantity
                    })
            except Exception as e:
                logger.error(f"Ошибка закупки {request.product_id}: {e}")
                results.append(PurchaseResponse(
                    success=False,
                    message=str(e),
                    order_id=None,
                    estimated_delivery_date=None
                ))
        
        # Оптимизация доставки для успешных заказов
        delivery_optimization = None
        if successful_orders:
            try:
                schedules = await delivery_optimizer.optimize_delivery_schedule(successful_orders)
                cost_analysis = await delivery_optimizer.calculate_delivery_cost(schedules)
                
                delivery_optimization = {
                    "schedules": schedules,
                    "cost_analysis": cost_analysis
                }
            except Exception as e:
                logger.error(f"Ошибка оптимизации доставки: {e}")
        
        # Отправка уведомления о массовой закупке
        background_tasks.add_task(
            publish_message,
            "notifications",
            {
                "type": "bulk_purchase_completed",
                "message": f"Завершена массовая закупка: {len(successful_orders)} успешных заказов",
                "data": {
                    "total_orders": len(requests),
                    "successful_orders": len(successful_orders),
                    "delivery_optimization": delivery_optimization
                }
            }
        )
        
        return {
            "status": "success",
            "data": {
                "results": results,
                "delivery_optimization": delivery_optimization
            },
            "summary": {
                "total_orders": len(requests),
                "successful_orders": len(successful_orders),
                "failed_orders": len(requests) - len(successful_orders)
            }
        }
    except Exception as e:
        logger.error(f"Ошибка массовой закупки: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    ) 