#!/usr/bin/env python3
"""
Упрощенная проверка ML-моделей без aiohttp
"""

import requests
import json
import os
from datetime import datetime
from typing import Dict, Any

def check_ml_service_health():
    """Проверка здоровья ML-сервиса"""
    try:
        response = requests.get("http://localhost:8002/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print("✅ ML-сервис здоров")
            print(f"   Загружено моделей: {health_data.get('models_loaded', 0)}")
            return True
        else:
            print(f"❌ ML-сервис недоступен: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ ML-сервис недоступен: соединение отклонено")
        return False
    except Exception as e:
        print(f"❌ Ошибка подключения к ML-сервису: {e}")
        return False

def get_models_status():
    """Получение статуса всех моделей"""
    try:
        response = requests.get("http://localhost:8002/models/status", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Ошибка получения статуса моделей: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Ошибка получения статуса моделей: {e}")
        return None

def get_model_performance(product_id: str):
    """Получение производительности модели для конкретного продукта"""
    try:
        url = f"http://localhost:8002/models/{product_id}/performance"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Ошибка получения производительности для {product_id}: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Ошибка получения производительности: {e}")
        return None

def test_forecast(product_id: str = "30001"):
    """Тестирование прогноза для продукта"""
    try:
        forecast_request = {
            "product_id": product_id,
            "forecast_days": 30,
            "model_type": None
        }
        
        response = requests.post(
            "http://localhost:8002/forecast", 
            json=forecast_request, 
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Ошибка получения прогноза для {product_id}: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Ошибка тестирования прогноза: {e}")
        return None

def check_models_directory():
    """Проверка файлов моделей в директории"""
    models_dir = "/app/data/models"
    if not os.path.exists(models_dir):
        print(f"❌ Директория моделей не найдена: {models_dir}")
        return []
    
    model_files = []
    for filename in os.listdir(models_dir):
        if filename.endswith('.pkl') or filename.endswith('.joblib'):
            model_files.append(filename)
    
    return model_files

def check_docker_containers():
    """Проверка Docker контейнеров"""
    try:
        import subprocess
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            ml_service_found = any('ml-service' in line for line in lines)
            if ml_service_found:
                print("✅ ML-сервис запущен в Docker")
                return True
            else:
                print("❌ ML-сервис не найден в запущенных контейнерах")
                return False
        else:
            print("❌ Ошибка проверки Docker контейнеров")
            return False
    except Exception as e:
        print(f"❌ Ошибка проверки Docker: {e}")
        return False

def main():
    """Основная функция проверки"""
    
    print("🔍 УПРОЩЕННАЯ ПРОВЕРКА ML-МОДЕЛЕЙ")
    print("=" * 50)
    
    # 1. Проверяем Docker контейнеры
    print("\n1️⃣ Проверка Docker контейнеров...")
    docker_ok = check_docker_containers()
    
    # 2. Проверяем здоровье сервиса
    print("\n2️⃣ Проверка здоровья ML-сервиса...")
    service_healthy = check_ml_service_health()
    
    if not service_healthy:
        print("\n💡 РЕКОМЕНДАЦИИ:")
        print("   1. Запустите систему: ./start_system.sh")
        print("   2. Или запустите только ML-сервис: docker-compose up ml-service")
        print("   3. Проверьте логи: docker logs ml-service")
        return
    
    # 3. Получаем статус моделей
    print("\n3️⃣ Получение статуса моделей...")
    models_status = get_models_status()
    
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
    
    # 4. Проверяем файлы моделей
    print("\n4️⃣ Проверка файлов моделей...")
    model_files = check_models_directory()
    
    if model_files:
        print(f"📁 Найдено файлов моделей: {len(model_files)}")
        for filename in model_files[:5]:  # Показываем первые 5
            print(f"   {filename}")
        if len(model_files) > 5:
            print(f"   ... и еще {len(model_files) - 5} файлов")
    else:
        print("❌ Файлы моделей не найдены")
    
    # 5. Тестируем прогноз для конкретного продукта
    print("\n5️⃣ Тестирование прогноза...")
    test_products = ["30001", "30002", "60001", "360360"]
    
    for product_id in test_products:
        print(f"\n   Тестирование продукта {product_id}...")
        
        # Получаем производительность модели
        performance = get_model_performance(product_id)
        if performance:
            print(f"     Производительность:")
            for perf in performance:
                print(f"       {perf['model_type']}: точность {perf['accuracy']:.2%}")
        
        # Тестируем прогноз
        forecast = test_forecast(product_id)
        if forecast:
            print(f"     Прогноз:")
            print(f"       Дневной спрос: {forecast.get('daily_demand', 0):.2f}")
            print(f"       Точность: {forecast.get('accuracy', 0):.2%}")
            print(f"       Модель: {forecast.get('model_type', 'unknown')}")
        else:
            print(f"     ❌ Прогноз недоступен")
    
    # 6. Сохраняем результаты
    print("\n6️⃣ Сохранение результатов...")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "docker_ok": docker_ok,
        "service_healthy": service_healthy,
        "models_status": models_status,
        "model_files": model_files,
        "test_results": {}
    }
    
    # Добавляем результаты тестов
    for product_id in test_products:
        performance = get_model_performance(product_id)
        forecast = test_forecast(product_id)
        
        results["test_results"][product_id] = {
            "performance": performance,
            "forecast": forecast
        }
    
    # Сохраняем в файл
    with open('ml_models_status_simple.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    print("✅ Результаты сохранены в файл: ml_models_status_simple.json")
    
    # 7. Вывод итогового статуса
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
    main() 