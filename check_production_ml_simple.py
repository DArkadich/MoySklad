#!/usr/bin/env python3
"""
Простая проверка ML моделей в продакшене
"""

import requests
import json
import sys
from datetime import datetime

def check_production_ml_status():
    """Проверка статуса ML моделей в продакшене"""
    
    print("🔍 ПРОВЕРКА ML-МОДЕЛЕЙ В ПРОДАКШНЕ")
    print("=" * 50)
    print(f"📅 Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Конфигурация продакшена
    PRODUCTION_URLS = [
        "http://localhost:8001",  # forecast-api
        "http://localhost:8002",  # ml-service
        "http://localhost:8000"   # moysklad-service
    ]
    
    working_services = []
    
    # 1. Проверяем доступность сервисов
    print("\n1️⃣ ПРОВЕРКА ДОСТУПНОСТИ СЕРВИСОВ")
    print("-" * 40)
    
    for url in PRODUCTION_URLS:
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ {url} - доступен")
                working_services.append(url)
            else:
                print(f"❌ {url} - недоступен (код: {response.status_code})")
        except requests.exceptions.RequestException as e:
            print(f"❌ {url} - недоступен (ошибка: {e})")
    
    if not working_services:
        print("\n❌ Нет доступных ML-сервисов!")
        print("   Проверьте:")
        print("   1. Запущены ли контейнеры: docker ps")
        print("   2. Правильные ли порты: docker-compose ps")
        print("   3. Логи сервисов: docker-compose logs")
        return False
    
    # 2. Проверяем статус моделей
    print(f"\n2️⃣ ПРОВЕРКА СТАТУСА МОДЕЛЕЙ")
    print("-" * 40)
    
    models_status = None
    for url in working_services:
        try:
            response = requests.get(f"{url}/models/status", timeout=5)
            if response.status_code == 200:
                models_status = response.json()
                print(f"✅ Статус моделей получен с {url}")
                break
        except:
            continue
    
    if models_status:
        print(f"📊 СТАТУС МОДЕЛЕЙ:")
        print(f"   Всего моделей: {models_status.get('total_models', 0)}")
        print(f"   Средняя точность: {models_status.get('average_accuracy', 0):.2%}")
        
        models_by_type = models_status.get('models_by_type', {})
        if models_by_type:
            print(f"   Модели по типам:")
            for model_type, count in models_by_type.items():
                print(f"     {model_type}: {count} моделей")
    else:
        print("❌ Статус моделей не получен")
    
    # 3. Проверяем health endpoint для получения количества загруженных моделей
    print(f"\n3️⃣ ПРОВЕРКА ЗАГРУЖЕННЫХ МОДЕЛЕЙ")
    print("-" * 40)
    
    models_loaded = 0
    for url in working_services:
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                if 'models_loaded' in health_data:
                    models_loaded = health_data['models_loaded']
                    print(f"✅ {url}: загружено моделей: {models_loaded}")
                    break
        except:
            continue
    
    # 4. Тестируем прогнозирование
    print(f"\n4️⃣ ТЕСТИРОВАНИЕ ПРОГНОЗИРОВАНИЯ")
    print("-" * 40)
    
    test_products = ["30001", "60800", "360360"]
    forecast_working = False
    
    for url in working_services:
        for product_code in test_products:
            try:
                forecast_data = {
                    "product_code": product_code,
                    "forecast_days": 30
                }
                
                response = requests.post(
                    f"{url}/forecast",
                    json=forecast_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    forecast_result = response.json()
                    print(f"✅ Прогноз работает на {url}")
                    print(f"   Продукт {product_code}:")
                    print(f"     Потребление: {forecast_result.get('forecast_consumption', 'N/A')}")
                    print(f"     Рекомендуемый заказ: {forecast_result.get('recommended_order', 'N/A')}")
                    print(f"     Дней до OoS: {forecast_result.get('days_until_oos', 'N/A')}")
                    forecast_working = True
                    break
                    
            except Exception as e:
                continue
        
        if forecast_working:
            break
    
    if not forecast_working:
        print("❌ Прогнозирование не работает")
    
    # 5. Итоговая оценка
    print(f"\n5️⃣ ИТОГОВАЯ ОЦЕНКА")
    print("-" * 40)
    
    if models_loaded > 0 or (models_status and models_status.get('total_models', 0) > 0):
        print("✅ ML-МОДЕЛИ ОБУЧЕНЫ И ГОТОВЫ К ИСПОЛЬЗОВАНИЮ")
        print(f"   • Загружено моделей: {models_loaded}")
        if models_status:
            print(f"   • Всего моделей: {models_status.get('total_models', 0)}")
            print(f"   • Средняя точность: {models_status.get('average_accuracy', 0):.2%}")
        
        if forecast_working:
            print("   • API прогнозирования работает")
        else:
            print("   • ⚠️ API прогнозирования требует проверки")
            
    elif working_services:
        print("⚠️ ML-СЕРВИСЫ РАБОТАЮТ, НО МОДЕЛИ НЕ ЗАГРУЖЕНЫ")
        print("   • Необходимо обучить модели")
        print("   • Запустите: docker exec forecast-api python3 train_models_in_container.py")
        
    else:
        print("❌ ML-СЕРВИСЫ НЕ РАБОТАЮТ")
        print("   • Проверьте статус контейнеров")
        print("   • Запустите систему: ./start_system_optimized.sh")
    
    # 6. Рекомендации
    print(f"\n6️⃣ РЕКОМЕНДАЦИИ")
    print("-" * 40)
    
    if models_loaded == 0:
        print("🚀 Для обучения моделей:")
        print("   1. Проверьте наличие исторических данных:")
        print("      docker exec forecast-api ls -la /app/data/")
        print("   2. Запустите обучение:")
        print("      docker exec forecast-api python3 train_models_in_container.py")
        print("   3. Проверьте логи обучения:")
        print("      docker-compose logs forecast-api")
    
    print("🔧 Для диагностики:")
    print("   1. Статус контейнеров: docker ps")
    print("   2. Логи сервисов: docker-compose logs")
    print("   3. Файлы в контейнере: docker exec forecast-api ls -la /app/data/")
    
    # Сохраняем отчет
    report = {
        "timestamp": datetime.now().isoformat(),
        "working_services": working_services,
        "models_loaded": models_loaded,
        "models_status": models_status,
        "forecast_working": forecast_working,
        "summary": {
            "ml_ready": models_loaded > 0 or (models_status and models_status.get('total_models', 0) > 0),
            "services_working": len(working_services) > 0
        }
    }
    
    with open('production_ml_status.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n💾 Отчет сохранен в файл: production_ml_status.json")
    
    return True

if __name__ == "__main__":
    try:
        check_production_ml_status()
    except KeyboardInterrupt:
        print("\n\n❌ Проверка прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Ошибка проверки: {e}")
        sys.exit(1)
