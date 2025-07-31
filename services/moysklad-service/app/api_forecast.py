#!/usr/bin/env python3
"""
API для прогнозирования спроса и автоматизации закупок
Интеграция с универсальными ML-моделями и МойСклад
"""

import asyncio
import httpx
import pandas as pd
import numpy as np
import logging
import pickle
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# FastAPI приложение
app = FastAPI(title="ML Forecast API", description="API для прогнозирования спроса и автоматизации закупок")

# Модели для загрузки
UNIVERSAL_MODELS_FILE = "/app/data/universal_forecast_models.pkl"
CONSUMPTION_DATA_FILE = "/app/data/accurate_consumption_results.csv"

# Настройки API МойСклад
MOYSKLAD_API_URL = "https://api.moysklad.ru/api/remap/1.2"
MOYSKLAD_API_TOKEN = None  # Будет загружен из настроек

# Универсальные модели ML
universal_models = None
consumption_data = None

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
    confidence: float
    models_used: List[str]
    model_type: str = "universal"

class PurchaseOrder(BaseModel):
    """Заказ поставщику"""
    supplier_id: str
    items: List[Dict]
    total_amount: float
    delivery_date: str

def load_universal_models():
    """Загружает универсальные ML-модели"""
    global universal_models, consumption_data
    
    try:
        # Пытаемся загрузить универсальные модели
        try:
            with open(UNIVERSAL_MODELS_FILE, 'rb') as f:
                model_data = pickle.load(f)
                universal_models = model_data['models']
                logger.info(f"Загружены универсальные модели: {list(universal_models.keys())}")
        except FileNotFoundError:
            logger.warning("Универсальные модели не найдены, используем старые модели")
            # Fallback к старым моделям
            with open("/app/data/forecast_models.pkl", 'rb') as f:
                model_data = pickle.load(f)
                universal_models = model_data['models']
                logger.info(f"Загружены старые модели: {list(universal_models.keys())}")
        
        # Загружаем данные о потреблении
        consumption_data = pd.read_csv(CONSUMPTION_DATA_FILE)
        consumption_data['start_date'] = pd.to_datetime(consumption_data['start_date'])
        
        logger.info(f"Загружены данные о потреблении: {len(consumption_data)} записей")
        
    except Exception as e:
        logger.error(f"Ошибка загрузки моделей: {e}")
        raise

def get_quarter(date: datetime) -> int:
    """Возвращает номер квартала для даты"""
    return (date.month - 1) // 3 + 1

def create_universal_features(product_code: str, current_date: datetime, 
                            current_stock: float = None) -> pd.DataFrame:
    """Создает универсальные признаки для любого товара"""
    
    # Получаем исторические данные для товара
    product_history = consumption_data[consumption_data['product_code'] == product_code]
    
    if product_history.empty:
        # Если нет истории, используем средние значения
        avg_stock = 50
        avg_sales = 10
        sales_frequency = 0.3
        product_code_numeric = float(product_code) if product_code.replace('.', '').isdigit() else 0
    else:
        # Используем средние значения из истории
        avg_stock = product_history['max_stock'].mean()
        avg_sales = product_history['total_sales'].mean()
        sales_frequency = product_history['days_with_sales'].sum() / product_history['total_days'].sum()
        product_code_numeric = float(product_code) if product_code.replace('.', '').isdigit() else 0
    
    # Базовые признаки времени
    features = {
        'year': current_date.year,
        'quarter': get_quarter(current_date),
        'month': current_date.month,
        'total_days': 90,  # Квартал
        'days_with_stock_above_3': 60,  # Предполагаем 2/3 дней с остатками
        'days_for_consumption': 30,  # 1/3 дней без остатков
        'total_sales': avg_sales,
        'days_with_sales': int(90 * sales_frequency),
        'max_stock': avg_stock,
        'min_stock': max(1, avg_stock * 0.1),
    }
    
    # Производные признаки
    features['sales_per_day'] = features['total_sales'] / features['total_days']
    features['stock_availability_ratio'] = features['days_with_stock_above_3'] / features['total_days']
    features['sales_frequency'] = features['days_with_sales'] / features['total_days']
    features['stock_range'] = features['max_stock'] - features['min_stock']
    features['avg_stock'] = (features['max_stock'] + features['min_stock']) / 2
    
    # Универсальные признаки товара
    features['product_code_numeric'] = product_code_numeric
    features['product_category'] = product_code_numeric % 1000 if product_code_numeric > 0 else 0
    features['product_group'] = product_code_numeric // 1000 if product_code_numeric > 0 else 0
    
    # Статистики по товару (если есть история)
    if not product_history.empty:
        features['total_sales_mean'] = product_history['total_sales'].mean()
        features['total_sales_std'] = product_history['total_sales'].std()
        features['max_stock_mean'] = product_history['max_stock'].mean()
        features['max_stock_std'] = product_history['max_stock'].std()
        features['sales_per_day_mean'] = product_history['sales_per_day'].mean()
        features['sales_per_day_std'] = product_history['sales_per_day'].std()
    else:
        # Используем общие средние значения
        features['total_sales_mean'] = avg_sales
        features['total_sales_std'] = avg_sales * 0.5
        features['max_stock_mean'] = avg_stock
        features['max_stock_std'] = avg_stock * 0.5
        features['sales_per_day_mean'] = features['sales_per_day']
        features['sales_per_day_std'] = features['sales_per_day'] * 0.5
    
    return pd.DataFrame([features])

def predict_consumption_universal(product_code: str, current_date: datetime, 
                                 current_stock: float = None) -> Dict:
    """Делает универсальный прогноз потребления для любого товара"""
    
    if universal_models is None:
        raise HTTPException(status_code=500, detail="ML-модели не загружены")
    
    # Создаем универсальные признаки для прогноза
    features = create_universal_features(product_code, current_date, current_stock)
    
    # Делаем прогноз всеми моделями
    predictions = {}
    for model_name, model in universal_models.items():
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
            
            # Создаем заказ поставщику
            order_data = {
                "name": f"Автозаказ {product_code}",
                "description": f"Автоматический заказ на основе ML-прогноза",
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
                    delivery_date=(datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
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
    load_universal_models()

@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {"message": "ML Forecast API", "status": "running", "model_type": "universal"}

@app.post("/forecast", response_model=ForecastResponse)
async def forecast_demand(request: ForecastRequest):
    """Прогнозирование спроса для товара"""
    
    try:
        # Получаем текущие остатки
        current_stock = await get_current_stock(request.product_code)
        
        # Делаем универсальный прогноз
        forecast_result = predict_consumption_universal(
            request.product_code, 
            datetime.now(), 
            current_stock
        )
        
        # Рассчитываем дни до OoS
        daily_consumption = forecast_result['avg_consumption']
        days_until_oos = int(current_stock / daily_consumption) if daily_consumption > 0 else 999
        
        # Рассчитываем рекомендуемый заказ
        safety_stock = max(3, daily_consumption * 7)  # 7 дней безопасности
        recommended_order = max(0, safety_stock - current_stock)
        
        return ForecastResponse(
            product_code=request.product_code,
            current_stock=current_stock,
            forecast_consumption=daily_consumption,
            days_until_oos=days_until_oos,
            recommended_order=recommended_order,
            confidence=forecast_result['confidence'],
            models_used=list(forecast_result['predictions'].keys()),
            model_type="universal"
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
        
        # Если остатков мало, создаем заказ
        if forecast_response.days_until_oos <= 7 and forecast_response.recommended_order > 0:
            purchase_order = await create_purchase_order(
                request.product_code, 
                forecast_response.recommended_order
            )
            
            return {
                "message": "Заказ создан автоматически",
                "forecast": forecast_response.dict(),
                "purchase_order": purchase_order.dict()
            }
        else:
            return {
                "message": "Заказ не требуется",
                "forecast": forecast_response.dict(),
                "reason": f"Остатков хватит на {forecast_response.days_until_oos} дней"
            }
            
    except Exception as e:
        logger.error(f"Ошибка автоматического заказа: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Проверка здоровья API"""
    return {
        "status": "healthy",
        "models_loaded": universal_models is not None,
        "data_loaded": consumption_data is not None,
        "model_type": "universal",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 