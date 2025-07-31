#!/usr/bin/env python3
"""
Ежедневная автоматизация закупок с ML-прогнозированием
Запускается раз в сутки для проверки остатков и создания заказов
"""

import asyncio
import httpx
import pandas as pd
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict
import sys
import os

# Добавляем путь к модулям
sys.path.append('/app')

from app.core.config import settings

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Настройки API
MOYSKLAD_API_URL = "https://api.moysklad.ru/api/remap/1.2"
MOYSKLAD_API_TOKEN = settings.moysklad_api_token
FORECAST_API_URL = "http://localhost:8000"  # Локальный API для прогнозирования

HEADERS = {
    "Authorization": f"Bearer {MOYSKLAD_API_TOKEN}",
    "Content-Type": "application/json"
}

class DailyAutomation:
    """Класс для ежедневной автоматизации закупок"""
    
    def __init__(self):
        self.products_to_check = []
        self.orders_created = []
        self.errors = []
    
    async def get_all_products(self) -> List[Dict]:
        """Получает список всех товаров из МойСклад"""
        logger.info("Получение списка всех товаров...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                params = {"limit": 1000}  # Получаем все товары
                resp = await client.get(f"{MOYSKLAD_API_URL}/entity/assortment", 
                                      headers=HEADERS, params=params)
                
                if resp.status_code == 200:
                    data = resp.json()
                    products = data.get('rows', [])
                    logger.info(f"Найдено товаров: {len(products)}")
                    return products
                else:
                    logger.error(f"Ошибка получения товаров: {resp.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Ошибка получения товаров: {e}")
            return []
    
    async def get_current_stocks(self, product_codes: List[str]) -> Dict[str, float]:
        """Получает текущие остатки для списка товаров"""
        logger.info(f"Получение остатков для {len(product_codes)} товаров...")
        
        stocks = {}
        current_date = datetime.now().strftime("%Y-%m-%dT00:00:00")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Получаем все остатки на текущую дату
                params = {"moment": current_date, "limit": 1000}
                resp = await client.get(f"{MOYSKLAD_API_URL}/report/stock/all", 
                                      headers=HEADERS, params=params)
                
                if resp.status_code == 200:
                    data = resp.json()
                    stock_items = data.get('rows', [])
                    
                    # Создаем словарь остатков по кодам
                    for item in stock_items:
                        code = item.get('code')
                        quantity = item.get('quantity', 0)
                        if code:
                            stocks[code] = quantity
                    
                    logger.info(f"Получено остатков: {len(stocks)}")
                    return stocks
                else:
                    logger.error(f"Ошибка получения остатков: {resp.status_code}")
                    return {}
                    
        except Exception as e:
            logger.error(f"Ошибка получения остатков: {e}")
            return {}
    
    async def get_forecast(self, product_code: str, current_stock: float) -> Dict:
        """Получает прогноз от ML API"""
        logger.info(f"Получение прогноза для товара {product_code}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                forecast_data = {
                    "product_code": product_code,
                    "forecast_days": 30,
                    "current_stock": current_stock
                }
                
                resp = await client.post(f"{FORECAST_API_URL}/forecast", 
                                       json=forecast_data)
                
                if resp.status_code == 200:
                    forecast = resp.json()
                    logger.info(f"Прогноз для {product_code}: {forecast['forecast_consumption']:.4f} ед/день")
                    return forecast
                else:
                    logger.error(f"Ошибка прогноза для {product_code}: {resp.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Ошибка получения прогноза для {product_code}: {e}")
            return None
    
    async def create_purchase_order(self, product_code: str, quantity: float) -> Dict:
        """Создает заказ поставщику"""
        logger.info(f"Создание заказа для товара {product_code}: {quantity} ед.")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                order_data = {
                    "product_code": product_code,
                    "forecast_days": 30
                }
                
                resp = await client.post(f"{FORECAST_API_URL}/auto-purchase", 
                                       json=order_data)
                
                if resp.status_code == 200:
                    result = resp.json()
                    if "purchase_order" in result:
                        logger.info(f"Заказ создан для {product_code}")
                        return result
                    else:
                        logger.info(f"Заказ не требуется для {product_code}: {result.get('reason', '')}")
                        return result
                else:
                    logger.error(f"Ошибка создания заказа для {product_code}: {resp.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Ошибка создания заказа для {product_code}: {e}")
            return None
    
    async def check_product_stock(self, product: Dict) -> Dict:
        """Проверяет остатки и прогноз для товара"""
        product_code = product.get('code')
        if not product_code:
            return None
        
        # Получаем текущие остатки
        stocks = await self.get_current_stocks([product_code])
        current_stock = stocks.get(product_code, 0)
        
        # Получаем прогноз
        forecast = await self.get_forecast(product_code, current_stock)
        if not forecast:
            return None
        
        return {
            'product_code': product_code,
            'product_name': product.get('name', ''),
            'current_stock': current_stock,
            'forecast': forecast
        }
    
    async def run_daily_check(self):
        """Запускает ежедневную проверку"""
        logger.info("Запуск ежедневной автоматизации закупок...")
        
        # Сначала обучаем/обновляем ML модели
        logger.info("Обновление ML моделей...")
        await self.update_ml_models()
        
        # Получаем все товары
        products = await self.get_all_products()
        if not products:
            logger.error("Не удалось получить список товаров")
            return
        
        # Проверяем каждый товар
        for product in products[:50]:  # Ограничиваем для тестирования
            try:
                result = await self.check_product_stock(product)
                if result:
                    self.products_to_check.append(result)
                    
                    # Если остатков мало, создаем заказ
                    forecast = result['forecast']
                    if forecast['days_until_oos'] <= 7 and forecast['recommended_order'] > 0:
                        order_result = await self.create_purchase_order(
                            result['product_code'], 
                            forecast['recommended_order']
                        )
                        if order_result:
                            self.orders_created.append(order_result)
                
                # Небольшая пауза между запросами
                await asyncio.sleep(0.1)
                
            except Exception as e:
                error_msg = f"Ошибка проверки товара {product.get('code', 'unknown')}: {e}"
                logger.error(error_msg)
                self.errors.append(error_msg)
        
        # Сохраняем результаты
        await self.save_results()
        
        logger.info(f"Проверка завершена. Проверено товаров: {len(self.products_to_check)}")
        logger.info(f"Создано заказов: {len(self.orders_created)}")
        logger.info(f"Ошибок: {len(self.errors)}")
    
    async def update_ml_models(self):
        """Обновляет ML модели на основе новых данных"""
        logger.info("Обновление ML моделей...")
        
        try:
            # Проверяем, есть ли уже обученные модели
            models_dir = "/app/data/models"
            existing_models = [f for f in os.listdir(models_dir) if f.endswith('.joblib')] if os.path.exists(models_dir) else []
            
            if existing_models:
                # Если есть модели, используем дообучение
                logger.info(f"Найдено {len(existing_models)} существующих моделей, используем дообучение")
                from app.incremental_learning import IncrementalModelTrainer
                
                trainer = IncrementalModelTrainer()
                await trainer.incremental_train_all_models()
            else:
                # Если моделей нет, обучаем на исторических данных
                logger.info("Модели не найдены, обучаем на исторических данных")
                from app.train_historical_models import HistoricalModelTrainer
                
                trainer = HistoricalModelTrainer()
                await trainer.train_models_on_historical_data()
            
            logger.info("ML модели обновлены успешно")
            
        except Exception as e:
            logger.error(f"Ошибка обновления ML моделей: {e}")
    
    async def save_results(self):
        """Сохраняет результаты проверки"""
        timestamp = datetime.now().isoformat()
        
        # Сохраняем детальный отчет
        report = {
            'timestamp': timestamp,
            'products_checked': len(self.products_to_check),
            'orders_created': len(self.orders_created),
            'errors': len(self.errors),
            'products': self.products_to_check,
            'orders': self.orders_created,
            'error_details': self.errors
        }
        
        report_file = f"/app/data/daily_report_{datetime.now().strftime('%Y%m%d')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Отчет сохранен в {report_file}")
        
        # Сохраняем краткую статистику
        summary = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'products_checked': len(self.products_to_check),
            'orders_created': len(self.orders_created),
            'errors': len(self.errors),
            'low_stock_products': len([p for p in self.products_to_check 
                                     if p['forecast']['days_until_oos'] <= 7])
        }
        
        summary_file = "/app/data/daily_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Сводка сохранена в {summary_file}")

async def main():
    """Основная функция"""
    logger.info("Запуск ежедневной автоматизации закупок...")
    
    automation = DailyAutomation()
    await automation.run_daily_check()
    
    logger.info("Ежедневная автоматизация завершена!")

if __name__ == "__main__":
    asyncio.run(main()) 