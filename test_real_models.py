#!/usr/bin/env python3
"""
Скрипт для тестирования реальных моделей
"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_real_models():
    """Тестирование реальных моделей"""
    
    # Получаем список товаров из MoySklad
    async with httpx.AsyncClient() as client:
        # Здесь нужно будет добавить реальный API токен
        headers = {
            "Authorization": "Bearer YOUR_API_TOKEN",
            "Content-Type": "application/json"
        }
        
        response = await client.get(
            "https://api.moysklad.ru/api/remap/1.2/entity/product",
            headers=headers,
            timeout=30.0
        )
        
        if response.status_code == 200:
            products = response.json().get("rows", [])
            print(f"Найдено {len(products)} товаров")
            
            # Тестируем первые 3 товара
            for product in products[:3]:
                product_id = product['id']
                product_name = product.get('name', 'Неизвестный товар')
                product_code = product.get('code', '')
                
                print(f"\n📦 Тестируем товар: {product_name}")
                print(f"   ID: {product_id}")
                print(f"   Код: {product_code}")
                
                # Тестируем прогноз
                forecast_data = {
                    "product_code": product_id,
                    "forecast_days": 30,
                    "current_stock": 100.0
                }
                
                try:
                    forecast_response = await client.post(
                        "http://localhost:8001/forecast",
                        json=forecast_data,
                        timeout=30.0
                    )
                    
                    if forecast_response.status_code == 200:
                        forecast_result = forecast_response.json()
                        print(f"   ✅ Прогноз получен:")
                        print(f"      Потребление: {forecast_result.get('forecast_consumption', 0)}")
                        print(f"      Рекомендуемый заказ: {forecast_result.get('recommended_order', 0)}")
                        print(f"      Дней до OoS: {forecast_result.get('days_until_oos', 0)}")
                    else:
                        print(f"   ❌ Ошибка прогноза: {forecast_response.status_code}")
                        
                except Exception as e:
                    print(f"   ❌ Ошибка тестирования: {e}")
        else:
            print(f"❌ Ошибка получения товаров: {response.status_code}")

if __name__ == "__main__":
    asyncio.run(test_real_models())
