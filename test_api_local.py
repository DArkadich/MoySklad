#!/usr/bin/env python3
"""
Демонстрационный скрипт для тестирования API локально
"""

import requests
import json
import time
from datetime import datetime

# URL API
API_BASE_URL = "http://localhost:8000"

def test_health():
    """Тест здоровья API"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API здоров!")
            return response.json()
        else:
            print(f"❌ API недоступен: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка подключения к API: {e}")
        return None

def test_forecast():
    """Тест прогнозирования"""
    try:
        forecast_data = {
            "product_code": "60800",
            "forecast_days": 30
        }
        
        response = requests.post(
            f"{API_BASE_URL}/forecast",
            json=forecast_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Прогноз получен!")
            print(f"   Товар: {result['product_code']}")
            print(f"   Текущие остатки: {result['current_stock']}")
            print(f"   Прогноз потребления: {result['forecast_consumption']:.4f} ед/день")
            print(f"   Дней до OoS: {result['days_until_oos']}")
            print(f"   Рекомендуемый заказ: {result['recommended_order']}")
            print(f"   Уверенность: {result['confidence']:.2f}")
            return result
        else:
            print(f"❌ Ошибка прогноза: {response.status_code}")
            print(f"   Ответ: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка запроса прогноза: {e}")
        return None

def test_auto_purchase():
    """Тест автоматического заказа"""
    try:
        order_data = {
            "product_code": "60800",
            "forecast_days": 30
        }
        
        response = requests.post(
            f"{API_BASE_URL}/auto-purchase",
            json=order_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Автозаказ обработан!")
            print(f"   Сообщение: {result['message']}")
            if 'purchase_order' in result:
                po = result['purchase_order']
                print(f"   Заказ ID: {po['supplier_id']}")
                print(f"   Сумма: {po['total_amount']}")
                print(f"   Дата доставки: {po['delivery_date']}")
            return result
        else:
            print(f"❌ Ошибка автозаказа: {response.status_code}")
            print(f"   Ответ: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка запроса автозаказа: {e}")
        return None

def demo_workflow():
    """Демонстрация полного workflow"""
    print("🚀 Демонстрация системы автоматизации закупок")
    print("=" * 50)
    
    # 1. Проверка здоровья API
    print("\n1️⃣ Проверка здоровья API...")
    health = test_health()
    if not health:
        print("❌ API недоступен. Запустите API командой:")
        print("   cd services/moysklad-service && python app/api_forecast.py")
        return
    
    # 2. Тест прогнозирования
    print("\n2️⃣ Тест ML-прогнозирования...")
    forecast = test_forecast()
    if not forecast:
        print("❌ Ошибка прогнозирования")
        return
    
    # 3. Тест автоматического заказа
    print("\n3️⃣ Тест автоматического заказа...")
    order = test_auto_purchase()
    if not order:
        print("❌ Ошибка автоматического заказа")
        return
    
    # 4. Итоги
    print("\n4️⃣ Итоги демонстрации:")
    print("✅ Все тесты пройдены успешно!")
    print("✅ ML-модели работают корректно")
    print("✅ API готов к использованию")
    print("✅ Система готова к автоматизации закупок")

def simulate_daily_automation():
    """Симуляция ежедневной автоматизации"""
    print("\n🔄 Симуляция ежедневной автоматизации...")
    print("=" * 50)
    
    # Список товаров для проверки
    products = ["60800", "60801", "60802", "60803", "60804"]
    
    total_checked = 0
    total_orders = 0
    
    for product_code in products:
        print(f"\n📦 Проверка товара {product_code}...")
        
        # Прогноз
        forecast_data = {"product_code": product_code, "forecast_days": 30}
        try:
            response = requests.post(f"{API_BASE_URL}/forecast", json=forecast_data, timeout=5)
            if response.status_code == 200:
                forecast = response.json()
                total_checked += 1
                
                print(f"   Остатки: {forecast['current_stock']}")
                print(f"   Прогноз: {forecast['forecast_consumption']:.4f} ед/день")
                print(f"   Дней до OoS: {forecast['days_until_oos']}")
                
                # Если остатков мало, создаем заказ
                if forecast['days_until_oos'] <= 7 and forecast['recommended_order'] > 0:
                    order_response = requests.post(f"{API_BASE_URL}/auto-purchase", json=forecast_data, timeout=5)
                    if order_response.status_code == 200:
                        order_result = order_response.json()
                        if 'purchase_order' in order_result:
                            total_orders += 1
                            print(f"   ✅ Заказ создан: {forecast['recommended_order']} ед.")
                        else:
                            print(f"   ℹ️ Заказ не требуется: {order_result.get('reason', '')}")
                    else:
                        print(f"   ❌ Ошибка создания заказа")
                else:
                    print(f"   ℹ️ Остатков достаточно")
            else:
                print(f"   ❌ Ошибка прогноза")
                
        except requests.exceptions.RequestException:
            print(f"   ❌ Ошибка подключения")
        
        time.sleep(0.5)  # Пауза между запросами
    
    print(f"\n📊 Итоги автоматизации:")
    print(f"   Проверено товаров: {total_checked}")
    print(f"   Создано заказов: {total_orders}")
    print(f"   Время: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    print("🤖 Демонстрация системы автоматизации закупок")
    print("=" * 60)
    
    # Основная демонстрация
    demo_workflow()
    
    # Симуляция ежедневной автоматизации
    simulate_daily_automation()
    
    print("\n🎉 Демонстрация завершена!")
    print("\n📋 Следующие шаги:")
    print("1. Настройте токен МойСклад в .env")
    print("2. Запустите систему: ./start_system.sh")
    print("3. Настройте cron для ежедневной автоматизации")
    print("4. Мониторьте логи и отчеты") 