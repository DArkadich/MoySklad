from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import httpx
import asyncio
import logging
from typing import Dict, List, Optional
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from app.core.config import settings
from app.core.database import get_database, close_database
from app.core.redis_client import get_redis_client, close_redis
from app.utils.logging_config import setup_logging, get_logger
from app.services.report_generator import ReportGenerator
from app.services.data_analyzer import DataAnalyzer

# Настройка логирования
setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="Analytics Service",
    description="Сервис для аналитики и отчетности",
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
report_generator = ReportGenerator()
data_analyzer = DataAnalyzer()

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info("Запуск Analytics Service...")
    await get_database()
    await get_redis_client()
    await report_generator.initialize()
    await data_analyzer.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при завершении"""
    logger.info("Остановка Analytics Service...")
    await close_database()
    await close_redis()
    await report_generator.close()
    await data_analyzer.close()

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "service": "analytics-service",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/analytics/sales")
async def get_sales_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    product_id: Optional[str] = None
):
    """Получить аналитику продаж"""
    try:
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        analytics = await data_analyzer.analyze_sales(
            start_date=start_date,
            end_date=end_date,
            product_id=product_id
        )
        
        return {
            "status": "success",
            "data": analytics,
            "period": {"start": start_date, "end": end_date}
        }
    except Exception as e:
        logger.error(f"Ошибка получения аналитики продаж: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/purchases")
async def get_purchases_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Получить аналитику закупок"""
    try:
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        analytics = await data_analyzer.analyze_purchases(
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "status": "success",
            "data": analytics,
            "period": {"start": start_date, "end": end_date}
        }
    except Exception as e:
        logger.error(f"Ошибка получения аналитики закупок: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/inventory")
async def get_inventory_analytics():
    """Получить аналитику складских остатков"""
    try:
        analytics = await data_analyzer.analyze_inventory()
        
        return {
            "status": "success",
            "data": analytics,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Ошибка получения аналитики склада: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/forecasts")
async def get_forecast_analytics(
    product_id: Optional[str] = None,
    days_ahead: int = 30
):
    """Получить аналитику прогнозов"""
    try:
        analytics = await data_analyzer.analyze_forecasts(
            product_id=product_id,
            days_ahead=days_ahead
        )
        
        return {
            "status": "success",
            "data": analytics,
            "days_ahead": days_ahead
        }
    except Exception as e:
        logger.error(f"Ошибка получения аналитики прогнозов: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/reports/generate")
async def generate_report(report_data: Dict):
    """Сгенерировать отчет"""
    try:
        report_type = report_data.get("type", "sales")
        format_type = report_data.get("format", "pdf")
        period = report_data.get("period", {})
        
        report = await report_generator.generate_report(
            report_type=report_type,
            format_type=format_type,
            period=period
        )
        
        return {
            "status": "success",
            "data": report,
            "type": report_type,
            "format": format_type
        }
    except Exception as e:
        logger.error(f"Ошибка генерации отчета: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/reports/sales")
async def get_sales_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    format_type: str = "json"
):
    """Получить отчет по продажам"""
    try:
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        report = await report_generator.generate_sales_report(
            start_date=start_date,
            end_date=end_date,
            format_type=format_type
        )
        
        return {
            "status": "success",
            "data": report,
            "period": {"start": start_date, "end": end_date},
            "format": format_type
        }
    except Exception as e:
        logger.error(f"Ошибка получения отчета по продажам: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/reports/purchases")
async def get_purchases_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    format_type: str = "json"
):
    """Получить отчет по закупкам"""
    try:
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        report = await report_generator.generate_purchases_report(
            start_date=start_date,
            end_date=end_date,
            format_type=format_type
        )
        
        return {
            "status": "success",
            "data": report,
            "period": {"start": start_date, "end": end_date},
            "format": format_type
        }
    except Exception as e:
        logger.error(f"Ошибка получения отчета по закупкам: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/reports/inventory")
async def get_inventory_report(format_type: str = "json"):
    """Получить отчет по складским остаткам"""
    try:
        report = await report_generator.generate_inventory_report(
            format_type=format_type
        )
        
        return {
            "status": "success",
            "data": report,
            "format": format_type,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Ошибка получения отчета по складу: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/dashboard/summary")
async def get_dashboard_summary():
    """Получить сводку для дашборда"""
    try:
        summary = await data_analyzer.get_dashboard_summary()
        
        return {
            "status": "success",
            "data": summary,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Ошибка получения сводки дашборда: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/dashboard/kpi")
async def get_kpi_metrics():
    """Получить KPI метрики"""
    try:
        kpi = await data_analyzer.get_kpi_metrics()
        
        return {
            "status": "success",
            "data": kpi,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Ошибка получения KPI метрик: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8005,
        reload=True
    ) 