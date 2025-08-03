#!/usr/bin/env python3
"""
Тест с реалистичными данными потребления
"""

from order_calculator import calculate_order_timing, print_order_analysis
from product_rules import ProductRules

def test_realistic_consumption():
    """Тестируем с реалистичными данными потребления"""
    
    print("🧮 ТЕСТ С РЕАЛИСТИЧНЫМИ ДАННЫМИ ПОТРЕБЛЕНИЯ")
    print("Проверяем логику заказов с реальными объемами потребления")
    print()
    
    # Реалистичные данные (код, остатки, дневное потребление, диоптрии)
    realistic_data = [
        ('30001', 385, 10, -0.5),   # -0.5, остатков на 38.5 дней
        ('30002', 154, 8, -0.75),   # -0.75, остатков на 19.25 дней
        ('30003', 103, 12, -1.00),  # -1.00, остатков на 8.6 дней
        ('30004', 80, 15, -1.25),   # -1.25, остатков на 5.3 дней
        ('30005', 5, 20, -1.50),    # -1.50, остатков на 0.25 дней
    ]
    
    print("📊 ИСХОДНЫЕ ДАННЫЕ:")
    print("Код SKU | Диоптрии | Остатки | Потребление/день | Дней до OoS")
    print("-" * 70)
    for code, stock, consumption, diopter in realistic_data:
        days_until_oos = stock / consumption
        print(f"{code:8} | {diopter:8.2f} | {stock:7} | {consumption:16} | {days_until_oos:10.1f}")
    print()
    
    # Анализируем каждый SKU
    results = []
    for code, stock, consumption, diopter in realistic_data:
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
    results, order_groups = test_realistic_consumption()
    
    # Показываем детальный анализ для одного SKU
    print("\n🔍 ДЕТАЛЬНЫЙ АНАЛИЗ ДЛЯ 30005 (-1.50):")
    print("=" * 50)
    for result in results:
        if result['product_code'] == '30005':
            print_order_analysis(result)
            break

if __name__ == "__main__":
    main() 