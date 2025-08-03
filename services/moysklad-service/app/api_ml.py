#!/usr/bin/env python3
"""
Улучшенный API для прогнозирования с реальными ML моделями
"""

import asyncio
import httpx
import pandas as pd
import numpy as np
import logging
import pickle
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from product_rules import ProductRules

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_real_models():
    """Загрузка реальных моделей из data/real_models"""
    real_models = {}
    real_models_dir = "data/real_models"
    
    if not os.path.exists(real_models_dir):
        logger.warning(f"Директория реальных моделей не найдена: {real_models_dir}")
        return real_models
    
    try:
        # Ищем файлы метаданных
        for filename in os.listdir(real_models_dir):
            if filename.endswith('_metadata.json'):
                metadata_path = os.path.join(real_models_dir, filename)
                
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                product_id = metadata.get('product_id')
                if not product_id:
                    continue
                
                # Загружаем модели для этого товара
                product_models = {}
                for model_name, model_path in metadata.get('models', {}).items():
                    if os.path.exists(model_path):
                        with open(model_path, 'rb') as f:
                            model = pickle.load(f)
                        product_models[model_name] = model
                
                if product_models:
                    real_models[product_id] = {
                        'models': product_models,
                        'metadata': metadata
                    }
                    logger.info(f"Загружены реальные модели для товара {product_id}")
        
        logger.info(f"Загружено {len(real_models)} товаров с реальными моделями")
        return real_models
        
    except Exception as e:
        logger.error(f"Ошибка загрузки реальных моделей: {e}")
        return real_models


# FastAPI приложение
app = FastAPI(title="ML Forecast API", description="API для прогнозирования спроса с ML моделями")

# Настройки API МойСклад
MOYSKLAD_API_URL = "https://api.moysklad.ru/api/remap/1.2"
MOYSKLAD_API_TOKEN = os.getenv('MOYSKLAD_API_TOKEN')

HEADERS = {
    "Authorization": f"Bearer {MOYSKLAD_API_TOKEN}",
    "Content-Type": "application/json"
}

# ML модели
ml_models = {}
model_scalers = {}
model_metadata = {}

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
    model_type: str = "ml_enhanced"
    product_info: Dict
    order_validation: Dict
    model_metadata: Dict

def load_ml_models():
    """Загружает ML модели"""
    global ml_models, model_scalers, model_metadata
    
    models_dir = "/app/data"
    if not os.path.exists(models_dir):
        logger.warning(f"Директория данных не найдена: {models_dir}")
        return
    
    try:
        # Загружаем универсальную модель из файла
        universal_model_path = os.path.join(models_dir, "universal_forecast_models.pkl")
        if os.path.exists(universal_model_path):
            logger.info(f"Загрузка модели из: {universal_model_path}")
            
            with open(universal_model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            logger.info(f"Тип загруженных данных: {type(model_data)}")
            
            # Загружаем модели из универсального файла
            if isinstance(model_data, dict):
                logger.info(f"Ключи в данных: {list(model_data.keys())}")
                
                # Проверяем структуру models
                if 'models' in model_data:
                    models = model_data['models']
                    logger.info(f"Найдено моделей в 'models': {len(models)}")
                    
                    for model_name, model_obj in models.items():
                        if hasattr(model_obj, 'predict'):
                            # Используем model_name как product_code
                            # Получаем реальный product_code из запроса или используем ID товара
product_code = request.product_code if hasattr(request, 'product_code') else product_id
                            ml_models[product_code] = model_obj
                            logger.info(f"Загружена модель {model_name} для товара {product_code}")
                
                # Проверяем структуру results для метаданных
                if 'results' in model_data:
                    results = model_data['results']
                    logger.info(f"Найдено результатов: {len(results) if isinstance(results, dict) else 'не dict'}")
                    
                    if isinstance(results, dict):
                        for model_name, result_info in results.items():
                            if isinstance(result_info, dict):
                                # Используем реальный product_code
product_code = request.product_code if hasattr(request, 'product_code') else product_id
                                if product_code in ml_models:
                                    if 'metadata' in result_info:
                                        model_metadata[product_code] = result_info['metadata']
                                    if 'scaler' in result_info:
                                        model_scalers[product_code] = result_info['scaler']
                                    logger.info(f"Добавлены метаданные для модели {model_name}")
                
                # Проверяем features
                if 'features' in model_data:
                    features = model_data['features']
                    logger.info(f"Найдено признаков: {len(features) if isinstance(features, list) else 'не список'}")
            
            logger.info(f"Загружено моделей: {len(ml_models)}")
            
            if len(ml_models) == 0:
                logger.warning("Модели не загружены. Проверьте структуру данных.")
            else:
                logger.info("✅ Модели успешно загружены!")
                
        else:
            logger.warning(f"Файл универсальной модели не найден: {universal_model_path}")
        
    except Exception as e:
        logger.error(f"Ошибка загрузки моделей: {e}")
        import traceback
        logger.error(f"Полная ошибка: {traceback.format_exc()}")

def create_ml_features(product_code: str, current_date: datetime, 
                      current_stock: float = None) -> pd.DataFrame:
    """Создает признаки для ML прогнозирования"""
    
    # Базовые временные признаки
    features = {
        'year': current_date.year,
        'month': current_date.month,
        'day': current_date.day,
        'day_of_year': current_date.timetuple().tm_yday,
        'day_of_week': current_date.weekday(),
        'is_month_start': current_date.day == 1,
        'is_quarter_start': current_date.day == 1 and current_date.month in [1, 4, 7, 10],
        'is_weekend': current_date.weekday() >= 5
    }
    
    # Признаки товара
    features['product_code_numeric'] = float(product_code) if product_code.replace('.', '').isdigit() else 0
    features['product_category'] = features['product_code_numeric'] % 1000
    features['product_group'] = features['product_code_numeric'] // 1000
    
    # Признаки остатков
    features['current_stock'] = current_stock or 0
    features['stock_level'] = 'low' if (current_stock or 0) < 50 else 'medium' if (current_stock or 0) < 200 else 'high'
    
    # Сезонные признаки
    features['is_holiday_season'] = current_date.month in [12, 1, 2]  # Зимние праздники
    features['is_summer_season'] = current_date.month in [6, 7, 8]    # Летний сезон
    
    # Признаки дня недели (one-hot encoding)
    for i in range(7):
        features[f'day_of_week_{i}'] = 1 if current_date.weekday() == i else 0
    
    # Признаки месяца (one-hot encoding)
    for i in range(1, 13):
        features[f'month_{i}'] = 1 if current_date.month == i else 0
    
    return pd.DataFrame([features])

async def get_real_stock_data(product_code: str, days_back: int = 30) -> pd.DataFrame:
    """Получает реальные данные об остатках из МойСклад"""
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Получаем исторические данные об остатках
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            stock_data = []
            current_date = start_date
            
            while current_date <= end_date:
                params = {
                    "moment": current_date.strftime("%Y-%m-%dT00:00:00"),
                    "limit": 1000
                }
                
                resp = await client.get(f"{MOYSKLAD_API_URL}/report/stock/all", 
                                      headers=HEADERS, params=params)
                
                if resp.status_code == 200:
                    data = resp.json()
                    stock_items = data.get('rows', [])
                    
                    for item in stock_items:
                        if item.get('code') == product_code:
                            stock_data.append({
                                'date': current_date.strftime('%Y-%m-%d'),
                                'product_code': product_code,
                                'stock': item.get('quantity', 0),
                                'product_name': item.get('name', '')
                            })
                            break
                
                current_date += timedelta(days=1)
                await asyncio.sleep(0.1)  # Пауза между запросами
            
            return pd.DataFrame(stock_data)
            
    except Exception as e:
        logger.error(f"Ошибка получения данных об остатках: {e}")
        return pd.DataFrame()

async def get_real_sales_data(product_code: str, days_back: int = 30) -> pd.DataFrame:
    """Получает реальные данные о продажах из МойСклад"""
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Получаем документы продаж
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            params = {
                "momentFrom": start_date.strftime('%Y-%m-%d') + "T00:00:00",
                "momentTo": end_date.strftime('%Y-%m-%d') + "T23:59:59",
                "limit": 1000
            }
            
            resp = await client.get(f"{MOYSKLAD_API_URL}/entity/demand", 
                                  headers=HEADERS, params=params)
            
            if resp.status_code == 200:
                data = resp.json()
                demands = data.get('rows', [])
                
                sales_data = []
                
                for demand in demands:
                    demand_id = demand.get('id')
                    demand_date = demand.get('moment', '')[:10]
                    
                    # Получаем позиции для документа
                    pos_resp = await client.get(f"{MOYSKLAD_API_URL}/entity/demand/{demand_id}/positions",
                                              headers=HEADERS, params={"expand": "assortment"})
                    
                    if pos_resp.status_code == 200:
                        pos_data = pos_resp.json()
                        positions = pos_data.get('rows', [])
                        
                        for position in positions:
                            assortment = position.get('assortment', {})
                            if isinstance(assortment, dict) and assortment.get('code') == product_code:
                                sales_data.append({
                                    'date': demand_date,
                                    'product_code': product_code,
                                    'quantity': position.get('quantity', 0),
                                    'product_name': assortment.get('name', '')
                                })
                
                return pd.DataFrame(sales_data)
            
            return pd.DataFrame()
            
    except Exception as e:
        logger.error(f"Ошибка получения данных о продажах: {e}")
        return pd.DataFrame()

def predict_with_ml_model(product_code: str, features: pd.DataFrame) -> Dict:
    """Делает прогноз с использованием ML модели"""
    
    if product_code not in ml_models:
        # Если модель не найдена, используем базовый прогноз
        return {
            'consumption': 5.0,  # Базовое потребление
            'confidence': 0.5,
            'model_type': 'fallback',
            'metadata': {'reason': 'ML модель не найдена'}
        }
    
    try:
        model = ml_models[product_code]
        scaler = model_scalers[product_code]
        metadata = model_metadata[product_code]
        
        # Подготавливаем признаки
        feature_columns = [col for col in features.columns if col not in ['date', 'product_code']]
        X = features[feature_columns].values
        
        # Масштабируем признаки
        X_scaled = scaler.transform(X)
        
        # Делаем прогноз
        prediction = model.predict(X_scaled)[0]
        
        # Рассчитываем уверенность на основе метаданных модели
        confidence = metadata.get('model_score', 0.7)
        
        return {
            'consumption': max(0, prediction),
            'confidence': confidence,
            'model_type': 'ml_enhanced',
            'metadata': metadata
        }
        
    except Exception as e:
        logger.error(f"Ошибка ML прогноза для {product_code}: {e}")
        return {
            'consumption': 5.0,
            'confidence': 0.3,
            'model_type': 'error_fallback',
            'metadata': {'error': str(e)}
        }

async def get_current_stock(product_code: str) -> float:
    """Получает текущие остатки товара"""
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            current_date = datetime.now().strftime("%Y-%m-%dT00:00:00")
            params = {"moment": current_date, "limit": 1000}
            
            resp = await client.get(f"{MOYSKLAD_API_URL}/report/stock/all", 
                                  headers=HEADERS, params=params)
            
            if resp.status_code == 200:
                data = resp.json()
                stock_items = data.get('rows', [])
                
                for item in stock_items:
                    if item.get('code') == product_code:
                        return item.get('quantity', 0)
            
            return 0
            
    except Exception as e:
        logger.error(f"Ошибка получения остатков: {e}")
        return 0

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info("Запуск ML API для прогнозирования...")
    load_ml_models()

@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "ML Forecast API", 
        "status": "running", 
        "model_type": "ml_enhanced",
        "models_loaded": len(ml_models)
    }

@app.post("/forecast", response_model=ForecastResponse)
async def forecast_demand(request: ForecastRequest):
    """Прогнозирование спроса с использованием ML моделей"""
    
    try:
        # Получаем текущие остатки
        current_stock = await get_current_stock(request.product_code)
        
        # Создаем признаки для ML модели
        features = create_ml_features(request.product_code, datetime.now(), current_stock)
        
        # Делаем ML прогноз
        ml_prediction = predict_with_ml_model(request.product_code, features)
        
        # Рассчитываем дни до OoS
        daily_consumption = ml_prediction['consumption']
        days_until_oos = int(current_stock / daily_consumption) if daily_consumption > 0 else 999
        
        # Получаем информацию о товаре и правилах
        product_info = ProductRules.get_product_info(request.product_code)
        
        # Рассчитываем страховой запас
        safety_stock = ProductRules.calculate_safety_stock(request.product_code, daily_consumption)
        
        # Рассчитываем рекомендуемый заказ
        recommended_order = max(0, safety_stock - current_stock)
        
        # Применяем ограничения к заказу
        final_order = ProductRules.apply_order_constraints(request.product_code, recommended_order)
        
        # Валидируем заказ
        order_validation = ProductRules.validate_order(request.product_code, final_order)
        
        # Проверяем, нужно ли создавать заказ
        should_create = ProductRules.should_create_order(
            request.product_code, days_until_oos, recommended_order, combined_delivery=False
        )
        
        # Добавляем информацию о доставке
        delivery_info = {
            'production_days': product_info.get('production_days', 45),
            'delivery_days': product_info.get('delivery_days', 12),
            'total_lead_time': product_info.get('total_lead_time', 57),
            'can_combine_delivery': product_info.get('can_combine_delivery', False),
            'category': product_info.get('category', 'unknown')
        }
        
        # Обновляем product_info с информацией о доставке
        enhanced_product_info = {
            "name": f"Товар {request.product_code}",
            "description": product_info.get('description', ''),
            "type": product_info.get('type', ''),
            "min_order": product_info.get('min_order', 1),
            "multiple": product_info.get('multiple', 1),
            "production_days": product_info.get('production_days', 45),
            "delivery_days": product_info.get('delivery_days', 12),
            "total_lead_time": product_info.get('total_lead_time', 57),
            "safety_stock_days": product_info.get('safety_stock_days', 7),
            "category": product_info.get('category', 'unknown'),
            "can_combine_delivery": product_info.get('can_combine_delivery', False),
            "delivery_info": delivery_info
        }
        
        return ForecastResponse(
            product_code=request.product_code,
            current_stock=current_stock,
            forecast_consumption=daily_consumption,
            days_until_oos=days_until_oos,
            recommended_order=recommended_order,
            final_order=final_order,
            confidence=ml_prediction['confidence'],
            models_used=[ml_prediction['model_type']],
            model_type="ml_enhanced",
            product_info=enhanced_product_info,
            order_validation=order_validation,
            model_metadata=ml_prediction['metadata']
        )
        
    except Exception as e:
        logger.error(f"Ошибка прогнозирования: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Проверка здоровья API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "models_loaded": len(ml_models),
        "version": "2.0"
    }

@app.get("/models/status")
async def models_status():
    """Статус загруженных моделей"""
    return {
        "total_models": len(ml_models),
        "model_codes": list(ml_models.keys()),
        "last_updated": datetime.now().isoformat()
    }

@app.post("/delivery/optimize")
async def optimize_delivery():
    """Оптимизация доставки с учетом объединения поставок"""
    try:
        from delivery_optimizer import DeliveryOptimizer
        
        optimizer = DeliveryOptimizer()
        result = await optimizer.optimize_delivery_schedule()
        
        return {
            "status": "success",
            "optimization_result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка оптимизации доставки: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/delivery/rules")
async def get_delivery_rules():
    """Получение правил доставки для всех типов товаров"""
    try:
        rules_summary = {}
        
        for product_type, rules in ProductRules.PRODUCT_RULES.items():
            rules_summary[product_type] = {
                'description': rules['description'],
                'production_days': rules.get('production_days', 45),
                'delivery_days': rules.get('delivery_days', 12),
                'combined_delivery_days': rules.get('combined_delivery_days', 0),
                'total_lead_time': rules.get('production_days', 45) + rules.get('delivery_days', 12),
                'category': rules.get('category', 'unknown'),
                'can_combine_delivery': rules.get('can_combine_delivery', False),
                'min_order': rules['min_order'],
                'multiple': rules['multiple'],
                'safety_stock_days': rules['safety_stock_days']
            }
        
        return {
            "status": "success",
            "delivery_rules": rules_summary,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения правил доставки: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 