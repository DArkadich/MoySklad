#!/usr/bin/env python3
"""
Скрипт для проверки статуса ML-моделей
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, Any

async def check_ml_service_health():
    """Проверка здоровья ML-сервиса"""
    try:
        async with aiohttp.ClientSession() as session:
            # Проверяем здоровье сервиса
            async with session.get("http://localhost:8002/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    print("✅ ML-сервис здоров")
                    print(f"   Загружено моделей: {health_data.get('models_loaded', 0)}")
                    return True
                else:
                    print(f"❌ ML-сервис недоступен: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Ошибка подключения к ML-сервису: {e}")
        return False

async def get_models_status():
    """Получение статуса всех моделей"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8002/models/status") as response:
                if response.status == 200:
                    status_data = await response.json()
                    return status_data
                else:
                    print(f"❌ Ошибка получения статуса моделей: {response.status}")
                    return None
    except Exception as e:
        print(f"❌ Ошибка получения статуса моделей: {e}")
        return None

async def get_model_performance(product_id: str):
    """Получение производительности модели для конкретного продукта"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"http://localhost:8002/models/{product_id}/performance"
            async with session.get(url) as response:
                if response.status == 200:
                    performance_data = await response.json()
                    return performance_data
                else:
                    print(f"❌ Ошибка получения производительности для {product_id}: {response.status}")
                    return None
    except Exception as e:
        print(f"❌ Ошибка получения производительности: {e}")
        return None

async def test_forecast(product_id: str = "30001"):
    """Тестирование прогноза для продукта"""
    try:
        async with aiohttp.ClientSession() as session:
            # Тестовые данные для прогноза
            forecast_request = {
                "product_id": product_id,
                "forecast_days": 30,
                "model_type": None  # Автоматический выбор лучшей модели
            }
            
            async with session.post("http://localhost:8002/forecast", json=forecast_request) as response:
                if response.status == 200:
                    forecast_data = await response.json()
                    return forecast_data
                else:
                    print(f"❌ Ошибка получения прогноза для {product_id}: {response.status}")
                    return None
    except Exception as e:
        print(f"❌ Ошибка тестирования прогноза: {e}")
        return None

async def check_models_directory():
    """Проверка файлов моделей в директории"""
    import os
    
    models_dir = "/app/data/models"
    if not os.path.exists(models_dir):
        print(f"❌ Директория моделей не найдена: {models_dir}")
        return []
    
    model_files = []
    for filename in os.listdir(models_dir):
        if filename.endswith('.pkl') or filename.endswith('.joblib'):
            model_files.append(filename)
    
    return model_files

async def main():
    """Основная функция проверки"""
    
    print("🔍 ПРОВЕРКА СТАТУСА ML-МОДЕЛЕЙ")
    print("=" * 50)
    
    # 1. Проверяем здоровье сервиса
    print("\n1️⃣ Проверка здоровья ML-сервиса...")
    service_healthy = await check_ml_service_health()
    
    if not service_healthy:
        print("❌ ML-сервис недоступен. Проверьте, что сервис запущен.")
        return
    
    # 2. Получаем статус моделей
    print("\n2️⃣ Получение статуса моделей...")
    models_status = await get_models_status()
    
    if models_status:
        print("📊 СТАТУС МОДЕЛЕЙ:")
        print(f"   Всего моделей: {models_status.get('total_models', 0)}")
        print(f"   Средняя точность: {models_status.get('average_accuracy', 0):.2%}")
        
        models_by_type = models_status.get('models_by_type', {})
        if models_by_type:
            print("   Модели по типам:")
            for model_type, count in models_by_type.items():
                print(f"     {model_type}: {count} моделей")
        else:
            print("   ⚠️ Нет загруженных моделей")
    
    # 3. Проверяем файлы моделей
    print("\n3️⃣ Проверка файлов моделей...")
    model_files = await check_models_directory()
    
    if model_files:
        print(f"📁 Найдено файлов моделей: {len(model_files)}")
        for filename in model_files[:5]:  # Показываем первые 5
            print(f"   {filename}")
        if len(model_files) > 5:
            print(f"   ... и еще {len(model_files) - 5} файлов")
    else:
        print("❌ Файлы моделей не найдены")
    
    # 4. Тестируем прогноз для конкретного продукта
    print("\n4️⃣ Тестирование прогноза...")
    test_products = ["30001", "30002", "60001", "360360"]
    
    for product_id in test_products:
        print(f"\n   Тестирование продукта {product_id}...")
        
        # Получаем производительность модели
        performance = await get_model_performance(product_id)
        if performance:
            print(f"     Производительность:")
            for perf in performance:
                print(f"       {perf['model_type']}: точность {perf['accuracy']:.2%}")
        
        # Тестируем прогноз
        forecast = await test_forecast(product_id)
        if forecast:
            print(f"     Прогноз:")
            print(f"       Дневной спрос: {forecast.get('daily_demand', 0):.2f}")
            print(f"       Точность: {forecast.get('accuracy', 0):.2%}")
            print(f"       Модель: {forecast.get('model_type', 'unknown')}")
        else:
            print(f"     ❌ Прогноз недоступен")
    
    # 5. Сохраняем результаты
    print("\n5️⃣ Сохранение результатов...")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "service_healthy": service_healthy,
        "models_status": models_status,
        "model_files": model_files,
        "test_results": {}
    }
    
    # Добавляем результаты тестов
    for product_id in test_products:
        performance = await get_model_performance(product_id)
        forecast = await test_forecast(product_id)
        
        results["test_results"][product_id] = {
            "performance": performance,
            "forecast": forecast
        }
    
    # Сохраняем в файл
    with open('ml_models_status.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    print("✅ Результаты сохранены в файл: ml_models_status.json")
    
    # 6. Вывод итогового статуса
    print("\n" + "=" * 50)
    print("📋 ИТОГОВЫЙ СТАТУС:")
    
    if service_healthy and models_status and models_status.get('total_models', 0) > 0:
        print("✅ ML-модели обучены и готовы к использованию")
        print(f"   Загружено моделей: {models_status.get('total_models', 0)}")
        print(f"   Средняя точность: {models_status.get('average_accuracy', 0):.2%}")
    elif service_healthy:
        print("⚠️ ML-сервис работает, но модели не загружены")
        print("   Необходимо обучить модели")
    else:
        print("❌ ML-сервис недоступен")
        print("   Проверьте, что сервис запущен")

if __name__ == "__main__":
    asyncio.run(main()) 