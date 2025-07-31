#!/usr/bin/env python3
"""
API для прогнозирования спроса и автоматизации закупок
Интеграция с производственными ML-моделями и правилами закупок
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

from app.product_rules import ProductRules

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# FastAPI приложение
app = FastAPI(title="ML Forecast API", description="API для прогнозирования спроса и автоматизации закупок")

# Модели для загрузки
PRODUCTION_MODELS_FILE = "/app/data/production_forecast_models.pkl"
PRODUCTION_DATA_FILE = "/app/data/production_stock_data.csv"

# Настройки API МойСклад
MOYSKLAD_API_URL = "https://api.moysklad.ru/api/remap/1.2"
MOYSKLAD_API_TOKEN = None  # Будет загружен из настроек

# Производственные модели ML
production_models = None
production_data = None

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
    model_type: str = "production"
    product_info: Dict
    order_validation: Dict

class PurchaseOrder(BaseModel):
    """Заказ поставщику"""
    supplier_id: str
    items: List[Dict]
    total_amount: float
    delivery_date: str

def load_production_models():
    """Загружает производственные ML-модели"""
    global production_models, production_data
    
    try:
        # Пытаемся загрузить производственные модели
        try:
            model_file = os.path.join(os.getcwd(), 'data', 'production_forecast_models.pkl')
            with open(model_file, 'rb') as f:
                model_data = pickle.load(f)
                production_models = model_data['models']
                logger.info(f"Загружены производственные модели: {list(production_models.keys())}")
        except FileNotFoundError:
            logger.warning("Производственные модели не найдены, используем универсальные модели")
            # Fallback к универсальным моделям
            model_file = os.path.join(os.getcwd(), 'data', 'universal_forecast_models.pkl')
            with open(model_file, 'rb') as f:
                model_data = pickle.load(f)
                production_models = model_data['models']
                logger.info(f"Загружены универсальные модели: {list(production_models.keys())}")
        
        # Загружаем данные о потреблении
        data_file = os.path.join(os.getcwd(), 'data', 'production_stock_data.csv')
        if os.path.exists(data_file):
            production_data = pd.read_csv(data_file)
            logger.info(f"Загружены производственные данные: {len(production_data)} записей")
        else:
            logger.warning("Производственные данные не найдены")
            production_data = None
        
    except Exception as e:
        logger.error(f"Ошибка загрузки моделей: {e}")
        raise

def create_production_features(product_code: str, current_date: datetime, 
                             current_stock: float = None) -> pd.DataFrame:
    """Создает признаки для производственного прогнозирования"""
    
    # Получаем исторические данные для товара
    if production_data is not None:
        product_history = production_data[production_data['product_code'] == product_code]
    else:
        product_history = pd.DataFrame()
    
    # Получаем информацию о товаре
    product_info = ProductRules.get_product_info(product_code)
    
    # Базовые признаки времени
    features = {
        'year': current_date.year,
        'month': current_date.month,
        'day_of_year': current_date.timetuple().tm_yday,
        'day_of_week': current_date.weekday(),
        'is_month_start': current_date.day == 1,
        'is_quarter_start': current_date.day == 1 and current_date.month in [1, 4, 7, 10]
    }
    
    # Добавляем признаки товара
    features['product_code_numeric'] = float(product_code) if product_code.replace('.', '').isdigit() else 0
    features['product_category'] = features['product_code_numeric'] % 1000
    features['product_group'] = features['product_code_numeric'] // 1000
    
    # Статистики по товару (если есть история)
    if not product_history.empty:
        features['daily_consumption_mean'] = product_history['daily_consumption'].mean()
        features['daily_consumption_std'] = product_history['daily_consumption'].std()
        features['daily_consumption_min'] = product_history['daily_consumption'].min()
        features['daily_consumption_max'] = product_history['daily_consumption'].max()
        features['current_stock_mean'] = product_history['current_stock'].mean()
        features['current_stock_std'] = product_history['current_stock'].std()
        features['current_stock_min'] = product_history['current_stock'].min()
        features['current_stock_max'] = product_history['current_stock'].max()
    else:
        # Используем базовые значения в зависимости от типа товара
        if product_code.startswith('30'):  # Однодневные линзы
            base_consumption = 100
        elif product_code.startswith('6') or product_code.startswith('3'):  # Месячные линзы
            base_consumption = 50
        elif '360' in product_code or '500' in product_code or '120' in product_code:  # Растворы
            base_consumption = 25
        else:  # Прочие товары
            base_consumption = 10
        
        features['daily_consumption_mean'] = base_consumption
        features['daily_consumption_std'] = base_consumption * 0.3
        features['daily_consumption_min'] = base_consumption * 0.5
        features['daily_consumption_max'] = base_consumption * 1.5
        features['current_stock_mean'] = base_consumption * 30
        features['current_stock_std'] = base_consumption * 10
        features['current_stock_min'] = base_consumption * 10
        features['current_stock_max'] = base_consumption * 50
    
    return pd.DataFrame([features])

def predict_consumption_production(product_code: str, current_date: datetime, 
                                 current_stock: float = None) -> Dict:
    """Делает производственный прогноз потребления для товара"""
    
    if production_models is None:
        raise HTTPException(status_code=500, detail="ML-модели не загружены")
    
    # Создаем признаки для прогноза
    features = create_production_features(product_code, current_date, current_stock)
    
    # Делаем прогноз всеми моделями
    predictions = {}
    for model_name, model in production_models.items():
        try:
            if model_name == 'linear_regression':
                # Для линейной регрессии нужна нормализация
                # Используем простой подход без сохранения scaler
                pred = model.predict(features)[0]
            else:
                # Для случайного леса нормализация не нужна
                pred = model.predict(features)[0]
            
            predictions[model_name] = max(0, pred)
        except Exception as e:
            logger.error(f"Ошибка прогноза для {model_name}: {e}")
            predictions[model_name] = 0
    
    # Усредняем прогнозы
    avg_consumption = np.mean(list(predictions.values()))
    
    return {
        'predictions': predictions,
        'avg_consumption': avg_consumption,
        'confidence': 0.8 if len(predictions) > 1 else 0.6
    }

async def get_current_stock(product_code: str) -> float:
    """Получает текущие остатки товара из МойСклад"""
    
    if not MOYSKLAD_API_TOKEN:
        logger.warning("Токен МойСклад не настроен, используем 0")
        return 0
    
    try:
        headers = {
            "Authorization": f"Bearer {MOYSKLAD_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Получаем остатки на текущую дату
        current_date = datetime.now().strftime("%Y-%m-%dT00:00:00")
        params = {
            "moment": current_date,
            "filter": f"code={product_code}"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{MOYSKLAD_API_URL}/report/stock/all", 
                                  headers=headers, params=params)
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get('rows'):
                    return data['rows'][0].get('quantity', 0)
            
            return 0
            
    except Exception as e:
        logger.error(f"Ошибка получения остатков: {e}")
        return 0

async def create_purchase_order(product_code: str, quantity: float) -> PurchaseOrder:
    """Создает заказ поставщику в МойСклад"""
    
    if not MOYSKLAD_API_TOKEN:
        raise HTTPException(status_code=500, detail="Токен МойСклад не настроен")
    
    try:
        headers = {
            "Authorization": f"Bearer {MOYSKLAD_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Получаем информацию о товаре
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{MOYSKLAD_API_URL}/entity/assortment", 
                                  headers=headers, params={"filter": f"code={product_code}"})
            
            if resp.status_code != 200:
                raise HTTPException(status_code=404, detail="Товар не найден")
            
            data = resp.json()
            if not data.get('rows'):
                raise HTTPException(status_code=404, detail="Товар не найден")
            
            product = data['rows'][0]
            
            # Получаем правила товара
            product_info = ProductRules.get_product_info(product_code)
            lead_time_days = ProductRules.get_lead_time_days(product_code)
            
            # Создаем заказ поставщику
            order_data = {
                "name": f"Автозаказ {product_code}",
                "description": f"Автоматический заказ на основе ML-прогноза. {product_info['description']}",
                "moment": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "organization": {
                    "meta": {
                        "href": "https://api.moysklad.ru/api/remap/1.2/entity/organization/...",
                        "type": "organization",
                        "mediaType": "application/json"
                    }
                },
                "positions": [
                    {
                        "assortment": {
                            "meta": {
                                "href": product['meta']['href'],
                                "type": product['meta']['type'],
                                "mediaType": "application/json"
                            }
                        },
                        "quantity": quantity,
                        "price": product.get('salePrices', [{}])[0].get('value', 0)
                    }
                ]
            }
            
            # Отправляем заказ
            resp = await client.post(f"{MOYSKLAD_API_URL}/entity/purchaseorder", 
                                   headers=headers, json=order_data)
            
            if resp.status_code == 200:
                order_info = resp.json()
                return PurchaseOrder(
                    supplier_id=order_info.get('id', ''),
                    items=[{"product_code": product_code, "quantity": quantity}],
                    total_amount=quantity * order_data['positions'][0]['price'],
                    delivery_date=(datetime.now() + timedelta(days=lead_time_days)).strftime('%Y-%m-%d')
                )
            else:
                raise HTTPException(status_code=resp.status_code, 
                                 detail=f"Ошибка создания заказа: {resp.text}")
                
    except Exception as e:
        logger.error(f"Ошибка создания заказа: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания заказа: {str(e)}")

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info("Запуск API для прогнозирования...")
    load_production_models()

@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {"message": "ML Forecast API", "status": "running", "model_type": "production"}

@app.post("/forecast", response_model=ForecastResponse)
async def forecast_demand(request: ForecastRequest):
    """Прогнозирование спроса для товара"""
    
    try:
        # Получаем текущие остатки
        current_stock = await get_current_stock(request.product_code)
        
        # Делаем производственный прогноз
        forecast_result = predict_consumption_production(
            request.product_code, 
            datetime.now(), 
            current_stock
        )
        
        # Рассчитываем дни до OoS
        daily_consumption = forecast_result['avg_consumption']
        days_until_oos = int(current_stock / daily_consumption) if daily_consumption > 0 else 999
        
        # Получаем информацию о товаре
        product_info = ProductRules.get_product_info(request.product_code)
        
        # Рассчитываем страховой запас
        safety_stock = ProductRules.calculate_safety_stock(request.product_code, daily_consumption)
        
        # Рассчитываем рекомендуемый заказ
        recommended_order = max(0, safety_stock - current_stock)
        
        # Применяем ограничения к заказу
        final_order = ProductRules.apply_order_constraints(request.product_code, recommended_order)
        
        # Валидируем заказ
        order_validation = ProductRules.validate_order(request.product_code, final_order)
        
        return ForecastResponse(
            product_code=request.product_code,
            current_stock=current_stock,
            forecast_consumption=daily_consumption,
            days_until_oos=days_until_oos,
            recommended_order=recommended_order,
            final_order=final_order,
            confidence=forecast_result['confidence'],
            models_used=list(forecast_result['predictions'].keys()),
            model_type="production",
            product_info=product_info,
            order_validation=order_validation
        )
        
    except Exception as e:
        logger.error(f"Ошибка прогнозирования: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auto-purchase")
async def auto_purchase_order(request: ForecastRequest):
    """Автоматическое создание заказа поставщику"""
    
    try:
        # Получаем прогноз
        forecast_response = await forecast_demand(request)
        
        # Проверяем, нужно ли создавать заказ
        should_create = ProductRules.should_create_order(
            request.product_code,
            forecast_response.days_until_oos,
            forecast_response.recommended_order
        )
        
        if should_create and forecast_response.final_order > 0:
            purchase_order = await create_purchase_order(
                request.product_code, 
                forecast_response.final_order
            )
            
            return {
                "message": "Заказ создан автоматически",
                "forecast": forecast_response.dict(),
                "purchase_order": purchase_order.dict(),
                "reason": f"Остатков хватит на {forecast_response.days_until_oos} дней"
            }
        else:
            return {
                "message": "Заказ не требуется",
                "forecast": forecast_response.dict(),
                "reason": f"Остатков хватит на {forecast_response.days_until_oos} дней или заказ меньше минимального"
            }
            
    except Exception as e:
        logger.error(f"Ошибка автоматического заказа: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Проверка здоровья API"""
    return {
        "status": "healthy",
        "models_loaded": production_models is not None,
        "data_loaded": production_data is not None,
        "model_type": "production",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 