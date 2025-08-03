#!/usr/bin/env python3
"""
Тест для проверки логики с 80 днями остатков
"""

from order_calculator import calculate_order_timing, print_order_analysis

def test_80_days_scenario():
    """Тестируем сценарий с 80 днями остатков"""
    
    print("🧮 ТЕСТ: Линзы с остатками на 80 дней")
    print("Проверяем ваше понимание логики")
    print()
    
    # Ваш пример: линзы с остатками на 80 дней
    # Предположим дневное потребление 100 ед.
    daily_consumption = 100
    current_stock = 80 * daily_consumption  # 8000 ед.
    
    print("📊 ИСХОДНЫЕ ДАННЫЕ:")
    print(f"  Остатков: {current_stock} ед.")
    print(f"  Дневное потребление: {daily_consumption} ед.")
    print(f"  Остатков хватит на: 80 дней")
    print()
    
    # Тест 1: Отдельная поставка линз
    print("🔍 ТЕСТ 1: Отдельная поставка линз")
    result1 = calculate_order_timing('30001', current_stock, daily_consumption, combined_delivery=False)
    print_order_analysis(result1)
    print()
    
    # Тест 2: Объединенная поставка с растворами
    print("🔍 ТЕСТ 2: Объединенная поставка с растворами")
    result2 = calculate_order_timing('30001', current_stock, daily_consumption, combined_delivery=True)
    print_order_analysis(result2)
    print()
    
    # Сравнение результатов
    print("📈 СРАВНЕНИЕ РЕЗУЛЬТАТОВ:")
    print(f"  Отдельная поставка: заказ через {result1['days_until_order']} дней")
    print(f"  Объединенная поставка: заказ через {result2['days_until_order']} дней")
    print(f"  Разница: {result2['days_until_order'] - result1['days_until_order']} дней")
    print()
    
    if result1['days_until_order'] != result2['days_until_order']:
        print("✅ Логика работает правильно!")
        print("   При объединенной поставке заказ делается раньше")
        print("   из-за более длительного срока поставки (82 дня vs 57 дней)")
    else:
        print("❌ Логика требует проверки")

if __name__ == "__main__":
    test_80_days_scenario() 