from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import aio_pika
import asyncio
import logging
from typing import Dict, List, Optional
import json
from datetime import datetime
import httpx

from app.core.config import settings
from app.core.redis_client import get_redis_client, close_redis
from app.utils.logging_config import setup_logging, get_logger
from app.services.telegram_service import TelegramService
from app.services.email_service import EmailService

# Настройка логирования
setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="Notification Service",
    description="Сервис для отправки уведомлений",
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
telegram_service = TelegramService()
email_service = EmailService()

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info("Запуск Notification Service...")
    await get_redis_client()
    await telegram_service.initialize()
    await email_service.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при завершении"""
    logger.info("Остановка Notification Service...")
    await close_redis()
    await telegram_service.close()
    await email_service.close()

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "service": "notification-service",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/v1/notifications/send")
async def send_notification(notification_data: Dict):
    """Отправить уведомление"""
    try:
        notification_type = notification_data.get("type", "telegram")
        message = notification_data.get("message", "")
        recipients = notification_data.get("recipients", [])
        
        if notification_type == "telegram":
            result = await telegram_service.send_message(message, recipients)
        elif notification_type == "email":
            result = await email_service.send_email(message, recipients)
        else:
            raise HTTPException(status_code=400, detail="Неподдерживаемый тип уведомления")
        
        return {
            "status": "success",
            "message": "Уведомление отправлено",
            "result": result
        }
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/notifications/purchase-alert")
async def send_purchase_alert(alert_data: Dict):
    """Отправить уведомление о закупке"""
    try:
        product_name = alert_data.get("product_name", "")
        quantity = alert_data.get("quantity", 0)
        urgency = alert_data.get("urgency", "normal")
        
        message = f"🚨 АЛЕРТ ЗАКУПКИ\n\n"
        message += f"Товар: {product_name}\n"
        message += f"Количество: {quantity}\n"
        message += f"Срочность: {urgency}\n"
        message += f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        result = await telegram_service.send_message(message)
        
        return {
            "status": "success",
            "message": "Алерт закупки отправлен",
            "result": result
        }
    except Exception as e:
        logger.error(f"Ошибка отправки алерта закупки: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/notifications/stock-alert")
async def send_stock_alert(alert_data: Dict):
    """Отправить уведомление о складских остатках"""
    try:
        product_name = alert_data.get("product_name", "")
        current_stock = alert_data.get("current_stock", 0)
        min_stock = alert_data.get("min_stock", 0)
        
        message = f"📦 АЛЕРТ СКЛАДА\n\n"
        message += f"Товар: {product_name}\n"
        message += f"Текущий остаток: {current_stock}\n"
        message += f"Минимальный остаток: {min_stock}\n"
        message += f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        result = await telegram_service.send_message(message)
        
        return {
            "status": "success",
            "message": "Алерт склада отправлен",
            "result": result
        }
    except Exception as e:
        logger.error(f"Ошибка отправки алерта склада: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/notifications/forecast-alert")
async def send_forecast_alert(alert_data: Dict):
    """Отправить уведомление о прогнозе"""
    try:
        product_name = alert_data.get("product_name", "")
        forecast_value = alert_data.get("forecast_value", 0)
        confidence = alert_data.get("confidence", 0)
        
        message = f"📊 ПРОГНОЗ СПРОСА\n\n"
        message += f"Товар: {product_name}\n"
        message += f"Прогноз спроса: {forecast_value}\n"
        message += f"Уверенность: {confidence:.2%}\n"
        message += f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        result = await telegram_service.send_message(message)
        
        return {
            "status": "success",
            "message": "Алерт прогноза отправлен",
            "result": result
        }
    except Exception as e:
        logger.error(f"Ошибка отправки алерта прогноза: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/notifications/history")
async def get_notification_history(limit: int = 50):
    """Получить историю уведомлений"""
    try:
        redis_client = await get_redis_client()
        history = []
        
        # Получение истории из Redis
        keys = await redis_client.keys("notification:*")
        for key in keys[-limit:]:
            data = await redis_client.get(key)
            if data:
                history.append(json.loads(data))
        
        return {
            "status": "success",
            "data": history,
            "count": len(history)
        }
    except Exception as e:
        logger.error(f"Ошибка получения истории уведомлений: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/notifications/test")
async def test_notification():
    """Тестовое уведомление"""
    try:
        message = f"🧪 ТЕСТОВОЕ УВЕДОМЛЕНИЕ\n\n"
        message += f"Сервис уведомлений работает корректно\n"
        message += f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        result = await telegram_service.send_message(message)
        
        return {
            "status": "success",
            "message": "Тестовое уведомление отправлено",
            "result": result
        }
    except Exception as e:
        logger.error(f"Ошибка тестового уведомления: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8004,
        reload=True
    ) 