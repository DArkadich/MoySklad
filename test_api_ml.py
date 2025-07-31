#!/usr/bin/env python3
"""
Тестирование ML API с реальными данными
"""

import asyncio
import httpx
import json
from datetime import datetime

# Настройки API
API_BASE_URL = "http://localhost:8001"

async def test_health():
    """Тест здоровья API"""
    print("🔍 Тестирование здоровья API...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{API_BASE_URL}/health")
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ API здоров: {data}")
                return True
            else:
                print(f"❌ API не отвечает: {resp.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Ошибка подключения к API: {e}")
        return False

async def test_models_status():
    """Тест статуса ML моделей"""
    print("\n🔍 Проверка статуса ML моделей...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{API_BASE_URL}/models/status")
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ Статус моделей: {data}")
                return data.get('total_models', 0) > 0
            else:
                print(f"❌ Ошибка получения статуса моделей: {resp.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

async def test_forecast(product_code: str = "12345"):
    """Тест прогнозирования"""
    print(f"\n🔍 Тестирование прогноза для товара {product_code}...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            request_data = {
                "product_code": product_code,
                "forecast_days": 30
            }
            
            resp = await client.post(f"{API_BASE_URL}/forecast", json=request_data)
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ Прогноз получен:")
                print(f"   Товар: {data['product_code']}")
                print(f"   Текущие остатки: {data['current_stock']}")
                print(f"   Прогноз потребления: {data['forecast_consumption']:.2f} ед/день")
                print(f"   Дней до OoS: {data['days_until_oos']}")
                print(f"   Рекомендуемый заказ: {data['recommended_order']:.0f}")
                print(f"   Итоговый заказ: {data['final_order']}")
                print(f"   Уверенность: {data['confidence']:.2f}")
                print(f"   Тип модели: {data['model_type']}")
                print(f"   Модели: {data['models_used']}")
                return True
            else:
                print(f"❌ Ошибка прогнозирования: {resp.status_code}")
                print(f"   Ответ: {resp.text}")
                return False
                
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

async def test_multiple_products():
    """Тест нескольких товаров"""
    print("\n🔍 Тестирование нескольких товаров...")
    
    test_products = ["12345", "67890", "11111", "22222", "33333"]
    results = []
    
    for product_code in test_products:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                request_data = {
                    "product_code": product_code,
                    "forecast_days": 30
                }
                
                resp = await client.post(f"{API_BASE_URL}/forecast", json=request_data)
                
                if resp.status_code == 200:
                    data = resp.json()
                    results.append({
                        'product_code': product_code,
                        'current_stock': data['current_stock'],
                        'forecast_consumption': data['forecast_consumption'],
                        'days_until_oos': data['days_until_oos'],
                        'confidence': data['confidence'],
                        'model_type': data['model_type']
                    })
                    print(f"✅ {product_code}: {data['model_type']} (уверенность: {data['confidence']:.2f})")
                else:
                    print(f"❌ {product_code}: ошибка {resp.status_code}")
                    
        except Exception as e:
            print(f"❌ {product_code}: {e}")
    
    return results

async def test_api_root():
    """Тест корневого эндпоинта"""
    print("\n🔍 Тестирование корневого эндпоинта...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{API_BASE_URL}/")
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ Корневой эндпоинт: {data}")
                return True
            else:
                print(f"❌ Ошибка корневого эндпоинта: {resp.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

async def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестирования ML API...")
    print(f"📡 API URL: {API_BASE_URL}")
    print(f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Тесты
    tests = [
        ("Здоровье API", test_health),
        ("Корневой эндпоинт", test_api_root),
        ("Статус моделей", test_models_status),
        ("Прогноз одного товара", lambda: test_forecast("12345")),
        ("Прогноз нескольких товаров", test_multiple_products)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"🧪 {test_name}")
        print('='*50)
        
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ Ошибка выполнения теста: {e}")
            results[test_name] = False
    
    # Итоговый отчет
    print(f"\n{'='*50}")
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print('='*50)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"{status}: {test_name}")
    
    print(f"\n📈 Результат: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 Все тесты пройдены успешно!")
    else:
        print("⚠️  Некоторые тесты не пройдены")

if __name__ == "__main__":
    asyncio.run(main()) 