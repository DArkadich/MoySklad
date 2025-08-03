#!/usr/bin/env python3
"""
Тест с критическими данными для демонстрации работы алгоритма
"""

from order_calculator import calculate_order_timing, print_order_analysis
from product_rules import ProductRules

def test_critical_scenario():
    """Тестируем критический сценарий"""
    
    print("🚨 ТЕСТ КРИТИЧЕСКОГО СЦЕНАРИЯ")
    print("Демонстрируем работу алгоритма с разными уровнями остатков")
    print()
    
    # Критические данные (код, остатки, дневное потребление, диоптрии)
    critical_data = [
        ('30001', 100, 5, -0.5),    # -0.5, остатков на 20 дней
        ('30002', 50, 8, -0.75),    # -0.75, остатков на 6.25 дней
        ('30003', 30, 10, -1.00),   # -1.00, остатков на 3 дня
        ('30004', 15, 12, -1.25),   # -1.25, остатков на 1.25 дня
        ('30005', 5, 15, -1.50),    # -1.50, остатков на 0.33 дня
    ]
    
    print("📊 ИСХОДНЫЕ ДАННЫЕ:")
    print("Код SKU | Диоптрии | Остатки | Потребление/день | Дней до OoS")
    print("-" * 70)
    for code, stock, consumption, diopter in critical_data:
        days_until_oos = stock / consumption
        print(f"{code:8} | {diopter:8.2f} | {stock:7} | {consumption:16} | {days_until_oos:10.1f}")
    print()
    
    # Анализируем каждый SKU
    results = []
    for code, stock, consumption, diopter in critical_data:
        result = calculate_order_timing(code, stock, consumption, combined_delivery=False)
        if result:
            result['diopter'] = diopter
            results.append(result)
    
    # Группируем по датам заказа
    order_groups = {}
    for result in results:
        order_date = result['order_date']
        if order_date not in order_groups:
            order_groups[order_date] = []
        order_groups[order_date].append(result)
    
    # Сортируем группы по дате
    sorted_dates = sorted(order_groups.keys())
    
    print("📅 ПЛАН ЗАКАЗОВ ПО ДАТАМ:")
    print("=" * 80)
    
    total_orders = 0
    for order_date in sorted_dates:
        skus = order_groups[order_date]
        print(f"\n📅 ДАТА ЗАКАЗА: {order_date}")
        print("-" * 40)
        
        group_total = 0
        for sku in skus:
            if sku['should_create_order']:
                print(f"  ✅ {sku['product_code']} ({sku['diopter']:+.2f}) - {sku['final_order']} ед.")
                group_total += sku['final_order']
            else:
                print(f"  ❌ {sku['product_code']} ({sku['diopter']:+.2f}) - заказ не нужен")
        
        if group_total > 0:
            print(f"  📦 ИТОГО В ГРУППЕ: {group_total} ед.")
            total_orders += group_total
        else:
            print(f"  📦 ИТОГО В ГРУППЕ: заказов нет")
    
    print("\n" + "=" * 80)
    print(f"📊 ОБЩАЯ СТАТИСТИКА:")
    print(f"  Всего групп заказов: {len([d for d in sorted_dates if any(s['should_create_order'] for s in order_groups[d])])}")
    print(f"  Общий объем заказов: {total_orders} ед.")
    
    return results, order_groups

def main():
    """Основная функция"""
    results, order_groups = test_critical_scenario()
    
    # Показываем детальный анализ для каждого SKU
    print("\n🔍 ДЕТАЛЬНЫЙ АНАЛИЗ ПО SKU:")
    print("=" * 80)
    
    for result in results:
        print(f"\n📋 {result['product_code']} ({result['diopter']:+.2f}):")
        print(f"  Остатков: {result['current_stock']} ед.")
        print(f"  Потребление: {result['daily_consumption']} ед./день")
        print(f"  Дней до OoS: {result['days_until_oos']}")
        print(f"  Рекомендуемый заказ: {result['recommended_order']} ед.")
        print(f"  Финальный заказ: {result['final_order']} ед.")
        print(f"  Нужен заказ: {'✅ ДА' if result['should_create_order'] else '❌ НЕТ'}")
        print(f"  Дата заказа: {result['order_date']}")
        print(f"  Дата поставки: {result['delivery_date']}")

if __name__ == "__main__":
    main() 