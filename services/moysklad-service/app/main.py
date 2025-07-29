from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import httpx
import asyncio
import logging
from typing import Dict, List, Optional
import json
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.database import get_database, close_database
from app.core.redis_client import get_redis_client, close_redis
from app.utils.logging_config import setup_logging, get_logger

# Настройка логирования
setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="MoySklad Service",
    description="Сервис для интеграции с API МойСклад",
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

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info("Запуск MoySklad Service...")
    await get_database()
    await get_redis_client()

@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при завершении"""
    logger.info("Остановка MoySklad Service...")
    await close_database()
    await close_redis()

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "service": "moysklad-service",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/products")
async def get_all_products():
    """Получить все продукты из МойСклад"""
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {settings.moysklad_api_token}",
                "Content-Type": "application/json"
            }
            
            response = await client.get(
                f"{settings.moysklad_api_url}/entity/product",
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "data": data,
                    "count": len(data.get("rows", []))
                }
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ошибка API МойСклад: {response.text}"
                )
    except Exception as e:
        logger.error(f"Ошибка при получении продуктов: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/products/{product_id}")
async def get_product_info(product_id: str):
    """Получить информацию о конкретном продукте"""
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {settings.moysklad_api_token}",
                "Content-Type": "application/json"
            }
            
            response = await client.get(
                f"{settings.moysklad_api_url}/entity/product/{product_id}",
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                return {
                    "status": "success",
                    "data": response.json()
                }
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Продукт не найден: {response.text}"
                )
    except Exception as e:
        logger.error(f"Ошибка при получении продукта {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/stock")
async def get_stock_info():
    """Получить информацию о складских остатках"""
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {settings.moysklad_api_token}",
                "Content-Type": "application/json"
            }
            
            response = await client.get(
                f"{settings.moysklad_api_url}/report/stock/all",
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "data": data,
                    "total_products": len(data.get("rows", []))
                }
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ошибка при получении остатков: {response.text}"
                )
    except Exception as e:
        logger.error(f"Ошибка при получении остатков: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/sales")
async def get_sales_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Получить данные о продажах"""
    try:
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
            
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {settings.moysklad_api_token}",
                "Content-Type": "application/json"
            }
            
            params = {
                "momentFrom": f"{start_date}T00:00:00",
                "momentTo": f"{end_date}T23:59:59"
            }
            
            response = await client.get(
                f"{settings.moysklad_api_url}/entity/demand",
                headers=headers,
                params=params,
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "data": data,
                    "period": {"start": start_date, "end": end_date},
                    "count": len(data.get("rows", []))
                }
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ошибка при получении продаж: {response.text}"
                )
    except Exception as e:
        logger.error(f"Ошибка при получении продаж: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/orders")
async def create_order(order_data: Dict):
    """Создать заказ в МойСклад"""
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {settings.moysklad_api_token}",
                "Content-Type": "application/json"
            }
            
            response = await client.post(
                f"{settings.moysklad_api_url}/entity/purchaseorder",
                headers=headers,
                json=order_data,
                timeout=30.0
            )
            
            if response.status_code == 200:
                return {
                    "status": "success",
                    "data": response.json(),
                    "message": "Заказ успешно создан"
                }
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ошибка при создании заказа: {response.text}"
                )
    except Exception as e:
        logger.error(f"Ошибка при создании заказа: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/suppliers")
async def get_suppliers():
    """Получить список поставщиков"""
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {settings.moysklad_api_token}",
                "Content-Type": "application/json"
            }
            
            response = await client.get(
                f"{settings.moysklad_api_url}/entity/counterparty",
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "data": data,
                    "count": len(data.get("rows", []))
                }
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ошибка при получении поставщиков: {response.text}"
                )
    except Exception as e:
        logger.error(f"Ошибка при получении поставщиков: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=True
    ) 