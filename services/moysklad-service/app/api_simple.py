#!/usr/bin/env python3
"""
Упрощенный API для тестирования системы
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# FastAPI приложение
app = FastAPI(title="Simple Test API", description="Упрощенный API для тестирования")

class ForecastRequest(BaseModel):
    """Запрос на прогнозирование"""
    product_code: str
    forecast_days: int = 30
    current_stock: Optional[float] = None

class ForecastResponse(BaseModel):
    """Ответ с прогнозом"""
    product_code: str
    current_stock: float
    forecast_consumption: float
    days_until_oos: int
    recommended_order: float
    final_order: int
    confidence: float
    models_used: List[str]
    model_type: str = "simple"
    product_info: Dict
    order_validation: Dict

@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {"message": "Simple Test API", "status": "running", "model_type": "simple"}

@app.get("/health")
async def health_check():
    """Проверка здоровья API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.post("/forecast", response_model=ForecastResponse)
async def forecast_demand(request: ForecastRequest):
    """Прогнозирование спроса для товара (упрощенная версия)"""
    
    try:
        # Простой прогноз для тестирования
        current_stock = request.current_stock or 100.0
        daily_consumption = 5.0  # Фиксированное потребление
        days_until_oos = int(current_stock / daily_consumption) if daily_consumption > 0 else 999
        recommended_order = max(0, 50 - current_stock)
        final_order = max(0, recommended_order)
        
        return ForecastResponse(
            product_code=request.product_code,
            current_stock=current_stock,
            forecast_consumption=daily_consumption,
            days_until_oos=days_until_oos,
            recommended_order=recommended_order,
            final_order=final_order,
            confidence=0.8,
            models_used=["simple_average"],
            model_type="simple",
            product_info={"name": f"Товар {request.product_code}", "category": "test"},
            order_validation={"valid": True, "reason": "Тестовый заказ"}
        )
        
    except Exception as e:
        logger.error(f"Ошибка прогнозирования: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auto-purchase")
async def auto_purchase_order(request: ForecastRequest):
    """Автоматическое создание заказа поставщику (упрощенная версия)"""
    
    try:
        # Получаем прогноз
        forecast_response = await forecast_demand(request)
        
        if forecast_response.final_order > 0:
            return {
                "message": "Тестовый заказ создан",
                "forecast": forecast_response.dict(),
                "purchase_order": {
                    "supplier_id": "test_supplier",
                    "items": [{"product_code": request.product_code, "quantity": forecast_response.final_order}],
                    "total_amount": forecast_response.final_order * 100,
                    "delivery_date": (datetime.now() + asyncio.get_event_loop().time() * 7).strftime('%Y-%m-%d')
                },
                "reason": f"Остатков хватит на {forecast_response.days_until_oos} дней"
            }
        else:
            return {
                "message": "Заказ не требуется",
                "forecast": forecast_response.dict(),
                "reason": f"Остатков достаточно на {forecast_response.days_until_oos} дней"
            }
            
    except Exception as e:
        logger.error(f"Ошибка автоматического заказа: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 