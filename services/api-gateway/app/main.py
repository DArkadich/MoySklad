"""
Horiens API Gateway
Единая точка входа для всех API запросов
"""

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import uvicorn

from app.core.config import settings
from app.core.redis_client import get_redis_client
from app.utils.logging_config import setup_logging

# Настройка логирования
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Horiens API Gateway",
    description="API Gateway для системы автоматизации закупок",
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

# HTTP клиент
http_client = httpx.AsyncClient(timeout=30.0)


class HealthCheck(BaseModel):
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.now)
    services: Dict[str, str] = {
        "purchase_service": "connected",
        "ml_service": "connected",
        "moysklad_service": "connected",
        "notification_service": "connected",
        "analytics_service": "connected"
    }


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info("🚀 Запуск Horiens API Gateway")


@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при остановке"""
    logger.info("🛑 Остановка Horiens API Gateway")
    await http_client.aclose()


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Проверка здоровья API Gateway"""
    return HealthCheck()


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "Horiens Purchase Agent API Gateway",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "purchase": "/api/v1/purchase",
            "ml": "/api/v1/ml",
            "analytics": "/api/v1/analytics",
            "docs": "/docs"
        }
    }


# Проксирование запросов к сервисам
@app.api_route("/api/v1/purchase/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def purchase_proxy(request: Request, path: str):
    """Проксирование запросов к сервису закупок"""
    try:
        # Получение тела запроса
        body = None
        if request.method in ["POST", "PUT"]:
            body = await request.body()
        
        # Формирование URL
        url = f"http://purchase-service:8001/{path}"
        
        # Выполнение запроса
        response = await http_client.request(
            method=request.method,
            url=url,
            params=request.query_params,
            headers=dict(request.headers),
            content=body
        )
        
        return JSONResponse(
            content=response.json(),
            status_code=response.status_code,
            headers=dict(response.headers)
        )
        
    except Exception as e:
        logger.error(f"Ошибка проксирования к purchase service: {e}")
        raise HTTPException(status_code=500, detail="Service unavailable")


@app.api_route("/api/v1/ml/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def ml_proxy(request: Request, path: str):
    """Проксирование запросов к ML сервису"""
    try:
        # Получение тела запроса
        body = None
        if request.method in ["POST", "PUT"]:
            body = await request.body()
        
        # Формирование URL
        url = f"http://ml-service:8002/{path}"
        
        # Выполнение запроса
        response = await http_client.request(
            method=request.method,
            url=url,
            params=request.query_params,
            headers=dict(request.headers),
            content=body
        )
        
        return JSONResponse(
            content=response.json(),
            status_code=response.status_code,
            headers=dict(response.headers)
        )
        
    except Exception as e:
        logger.error(f"Ошибка проксирования к ml service: {e}")
        raise HTTPException(status_code=500, detail="Service unavailable")


@app.api_route("/api/v1/analytics/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def analytics_proxy(request: Request, path: str):
    """Проксирование запросов к сервису аналитики"""
    try:
        # Получение тела запроса
        body = None
        if request.method in ["POST", "PUT"]:
            body = await request.body()
        
        # Формирование URL
        url = f"http://analytics-service:8003/{path}"
        
        # Выполнение запроса
        response = await http_client.request(
            method=request.method,
            url=url,
            params=request.query_params,
            headers=dict(request.headers),
            content=body
        )
        
        return JSONResponse(
            content=response.json(),
            status_code=response.status_code,
            headers=dict(response.headers)
        )
        
    except Exception as e:
        logger.error(f"Ошибка проксирования к analytics service: {e}")
        raise HTTPException(status_code=500, detail="Service unavailable")


# Упрощенные эндпоинты для основных операций
@app.get("/api/v1/products")
async def get_products():
    """Получение списка продуктов"""
    try:
        response = await http_client.get("http://purchase-service:8001/products")
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка получения продуктов: {e}")
        raise HTTPException(status_code=500, detail="Service unavailable")


@app.get("/api/v1/inventory/status")
async def get_inventory_status():
    """Получение статуса остатков"""
    try:
        response = await http_client.get("http://purchase-service:8001/inventory/status")
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка получения статуса остатков: {e}")
        raise HTTPException(status_code=500, detail="Service unavailable")


@app.post("/api/v1/purchase/recommendations")
async def get_purchase_recommendations():
    """Получение рекомендаций по закупкам"""
    try:
        response = await http_client.post("http://purchase-service:8001/purchase/recommendations")
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка получения рекомендаций: {e}")
        raise HTTPException(status_code=500, detail="Service unavailable")


@app.get("/api/v1/forecast/{product_id}")
async def get_product_forecast(product_id: str):
    """Получение прогноза для продукта"""
    try:
        response = await http_client.get(f"http://ml-service:8002/forecast/{product_id}")
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка получения прогноза: {e}")
        raise HTTPException(status_code=500, detail="Service unavailable")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 