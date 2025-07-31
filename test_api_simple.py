#!/usr/bin/env python3
"""
Простой тест API для проверки работы системы
"""

import requests
import json
import time
from datetime import datetime

# URL API
API_BASE_URL = "http://localhost:8001"

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

def main():
    """Основная функция тестирования"""
    print("🤖 Тестирование упрощенного API")
    print("=" * 50)
    
    # 1. Проверка здоровья API
    print("\n1️⃣ Проверка здоровья API...")
    health = test_health()
    if not health:
        print("❌ API недоступен. Проверьте, что система запущена.")
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
    print("\n4️⃣ Итоги тестирования:")
    print("✅ Все тесты пройдены успешно!")
    print("✅ API работает корректно")
    print("✅ Система готова к использованию")

if __name__ == "__main__":
    main() 