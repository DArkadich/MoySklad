#!/usr/bin/env python3
"""
Тест для анализа заказа нескольких SKU однодневных линз
"""

from order_calculator import calculate_order_timing, print_order_analysis
from product_rules import ProductRules
from datetime import datetime, timedelta

def analyze_multiple_sku_order():
    """Анализируем заказ нескольких SKU однодневных линз"""
    
    print("🧮 АНАЛИЗ ЗАКАЗА НЕСКОЛЬКИХ SKU ОДНОДНЕВНЫХ ЛИНЗ")
    print("Сценарий: разные диоптрии с разными остатками")
    print()
    
    # Данные по SKU (код, остатки, дневное потребление, диоптрии)
    sku_data = [
        ('30001', 385, 1, -0.5),   # -0.5, остатков на 385 дней
        ('30002', 154, 1, -0.75),  # -0.75, остатков на 154 дня
        ('30003', 103, 1, -1.00),  # -1.00, остатков на 103 дня
        ('30004', 80, 1, -1.25),   # -1.25, остатков на 80 дней
        ('30005', 5, 1, -1.50),    # -1.50, остатков на 5 дней
    ]
    
    print("📊 ИСХОДНЫЕ ДАННЫЕ:")
    print("Код SKU | Диоптрии | Остатков на дней | Дневное потребление")
    print("-" * 60)
    for code, days, consumption, diopter in sku_data:
        print(f"{code:8} | {diopter:8.2f} | {days:14} | {consumption:18}")
    print()
    
    # Анализируем каждый SKU
    results = []
    for code, days, consumption, diopter in sku_data:
        current_stock = days * consumption
        result = calculate_order_timing(code, current_stock, consumption, combined_delivery=False)
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
    
    # Анализ оптимизации доставки
    print(f"\n🚚 АНАЛИЗ ОПТИМИЗАЦИИ ДОСТАВКИ:")
    product_codes = [r['product_code'] for r in results if r['should_create_order']]
    if product_codes:
        optimization = ProductRules.get_delivery_optimization(product_codes)
        print(f"  Может объединить доставку: {optimization['can_combine_delivery']}")
        print(f"  Линз в заказе: {optimization['lenses_count']}")
        print(f"  Растворов в заказе: {optimization['solutions_count']}")
        print(f"  Экономия на доставке: {optimization['delivery_savings_days']} дней")
    else:
        print("  Заказов нет - оптимизация не требуется")
    
    return results, order_groups

def analyze_combined_delivery_scenario(results):
    """Анализируем сценарий с объединенной доставкой"""
    
    print("\n" + "=" * 80)
    print("🚚 АНАЛИЗ С ОБЪЕДИНЕННОЙ ДОСТАВКОЙ")
    print("Предположим, что есть растворы для объединения поставок")
    print("=" * 80)
    
    # Те же данные, но с объединенной доставкой
    sku_data = [
        ('30001', 385, 1, -0.5),
        ('30002', 154, 1, -0.75),
        ('30003', 103, 1, -1.00),
        ('30004', 80, 1, -1.25),
        ('30005', 5, 1, -1.50),
    ]
    
    results_combined = []
    for code, days, consumption, diopter in sku_data:
        current_stock = days * consumption
        result = calculate_order_timing(code, current_stock, consumption, combined_delivery=True)
        if result:
            result['diopter'] = diopter
            results_combined.append(result)
    
    # Группируем по датам заказа
    order_groups_combined = {}
    for result in results_combined:
        order_date = result['order_date']
        if order_date not in order_groups_combined:
            order_groups_combined[order_date] = []
        order_groups_combined[order_date].append(result)
    
    sorted_dates_combined = sorted(order_groups_combined.keys())
    
    print("\n📅 ПЛАН ЗАКАЗОВ С ОБЪЕДИНЕННОЙ ДОСТАВКОЙ:")
    print("-" * 60)
    
    total_orders_combined = 0
    for order_date in sorted_dates_combined:
        skus = order_groups_combined[order_date]
        print(f"\n📅 ДАТА ЗАКАЗА: {order_date}")
        print("-" * 30)
        
        group_total = 0
        for sku in skus:
            if sku['should_create_order']:
                print(f"  ✅ {sku['product_code']} ({sku['diopter']:+.2f}) - {sku['final_order']} ед.")
                group_total += sku['final_order']
            else:
                print(f"  ❌ {sku['product_code']} ({sku['diopter']:+.2f}) - заказ не нужен")
        
        if group_total > 0:
            print(f"  📦 ИТОГО В ГРУППЕ: {group_total} ед.")
            total_orders_combined += group_total
        else:
            print(f"  📦 ИТОГО В ГРУППЕ: заказов нет")
    
    print(f"\n📊 СРАВНЕНИЕ СТРАТЕГИЙ:")
    print(f"  Отдельная доставка: {sum(1 for r in results if r['should_create_order'])} SKU")
    print(f"  Объединенная доставка: {sum(1 for r in results_combined if r['should_create_order'])} SKU")
    print(f"  Экономия на доставке: до 60%")

def main():
    """Основная функция"""
    results, order_groups = analyze_multiple_sku_order()
    analyze_combined_delivery_scenario(results)

if __name__ == "__main__":
    main() 