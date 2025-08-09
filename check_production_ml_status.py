#!/usr/bin/env python3
"""
Скрипт для проверки статуса ML моделей в продакшене
"""

import requests
import json
import sys
from datetime import datetime
import time

def check_api_health(base_url="http://localhost:8001"):
    """Проверка здоровья API"""
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            print("✅ API доступен")
            return True
        else:
            print(f"❌ API недоступен: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка подключения к API: {e}")
        return False

def check_models_status(base_url="http://localhost:8001"):
    """Проверка статуса моделей"""
    try:
        response = requests.get(f"{base_url}/models/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ Статус моделей получен")
            print(f"📊 Ответ: {json.dumps(data, indent=2, ensure_ascii=False)}")
            return data
        else:
            print(f"❌ Ошибка получения статуса моделей: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка запроса статуса моделей: {e}")
        return None

def test_forecast_api(base_url="http://localhost:8001"):
    """Тест API прогнозирования"""
    print("\n🧪 Тестирование API прогнозирования...")
    
    # Тест с разными товарами
    test_products = [
        {"product_code": "30001", "forecast_days": 30},
        {"product_code": "60800", "forecast_days": 30},
        {"product_code": "360360", "forecast_days": 30}
    ]
    
    for test_data in test_products:
        try:
            print(f"\n📦 Тестируем товар: {test_data['product_code']}")
            response = requests.post(
                f"{base_url}/forecast",
                json=test_data,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Прогноз получен для товара {test_data['product_code']}")
                print(f"   Модели: {result.get('models_used', 'не указаны')}")
                print(f"   Уверенность: {result.get('confidence', 'не указана')}")
                print(f"   Прогноз потребления: {result.get('forecast_consumption', 'не указан')}")
            else:
                print(f"❌ Ошибка прогноза для товара {test_data['product_code']}: {response.status_code}")
                print(f"   Ответ: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка запроса для товара {test_data['product_code']}: {e}")

def check_container_logs():
    """Проверка логов контейнеров (если доступен Docker)"""
    print("\n🐳 Проверка логов контейнеров...")
    
    try:
        import subprocess
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Docker доступен")
            
            # Проверяем логи moysklad-service
            print("\n📋 Логи moysklad-service:")
            logs_result = subprocess.run(
                ['docker', 'logs', 'moysklad-service', '--tail', '20'],
                capture_output=True, text=True, timeout=15
            )
            if logs_result.returncode == 0:
                print(logs_result.stdout)
            else:
                print("❌ Не удалось получить логи moysklad-service")
                
        else:
            print("❌ Docker недоступен или контейнеры не запущены")
            
    except (ImportError, subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ Docker не установлен или недоступен")

def check_file_system():
    """Проверка файловой системы на наличие моделей"""
    print("\n📁 Проверка файловой системы...")
    
    import os
    
    # Проверяем основные папки с данными
    data_paths = [
        "./data",
        "./services/moysklad-service/data",
        "./services/ml-service/data"
    ]
    
    for path in data_paths:
        if os.path.exists(path):
            print(f"✅ Папка {path} существует")
            
            # Ищем файлы моделей
            model_files = []
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith(('.pkl', '.joblib')) or 'model' in file.lower():
                        model_files.append(os.path.join(root, file))
            
            if model_files:
                print(f"   📦 Найдено файлов моделей: {len(model_files)}")
                for model_file in model_files[:5]:  # Показываем первые 5
                    print(f"      - {model_file}")
                if len(model_files) > 5:
                    print(f"      ... и еще {len(model_files) - 5} файлов")
            else:
                print(f"   ❌ Файлы моделей не найдены")
        else:
            print(f"❌ Папка {path} не существует")
    
    # Проверяем папку real_models
    real_models_path = "./data/real_models"
    if os.path.exists(real_models_path):
        print(f"✅ Папка {real_models_path} существует")
        real_models_files = os.listdir(real_models_path)
        print(f"   📦 Файлов в real_models: {len(real_models_files)}")
        for file in real_models_files[:10]:  # Показываем первые 10
            print(f"      - {file}")
    else:
        print(f"❌ Папка {real_models_path} не существует - модели не обучены!")

def main():
    """Основная функция"""
    print("🔍 ПРОВЕРКА СТАТУСА ML МОДЕЛЕЙ В ПРОДАКШЕНЕ")
    print("=" * 60)
    print(f"📅 Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Проверяем API
    if not check_api_health():
        print("\n❌ API недоступен. Проверьте:")
        print("   1. Запущены ли контейнеры?")
        print("   2. Правильный ли порт? (по умолчанию 8001)")
        print("   3. Нет ли ошибок в логах?")
        return
    
    # Проверяем статус моделей
    models_status = check_models_status()
    
    # Тестируем API прогнозирования
    test_forecast_api()
    
    # Проверяем логи контейнеров
    check_container_logs()
    
    # Проверяем файловую систему
    check_file_system()
    
    # Вывод рекомендаций
    print("\n" + "=" * 60)
    print("📋 РЕКОМЕНДАЦИИ:")
    
    if models_status and models_status.get('total_models', 0) > 0:
        print("✅ ML модели работают корректно")
    else:
        print("❌ ML модели не работают или не обучены")
        print("   Рекомендуется:")
        print("   1. Запустить обучение моделей:")
        print("      ./train_models_in_container.sh")
        print("   2. Проверить логи контейнеров:")
        print("      docker logs moysklad-service")
        print("   3. Убедиться в наличии данных в MoySklad")
    
    print("\n🔧 Для детальной диагностики используйте:")
    print("   - docker logs moysklad-service")
    print("   - docker logs forecast-api")
    print("   - ./check_models_status.sh")

if __name__ == "__main__":
    main()
