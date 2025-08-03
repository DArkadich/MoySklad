#!/usr/bin/env python3
"""
Тест с реалистичными данными для демонстрации правильной логики заказов по категориям
"""

from category_order_optimizer import CategoryOrderOptimizer

def test_realistic_scenario():
    """Тестируем реалистичный сценарий"""
    
    print("🧮 ТЕСТ РЕАЛИСТИЧНОГО СЦЕНАРИЯ")
    print("Демонстрируем правильную логику заказов по категориям")
    print()
    
    # Реалистичные данные (код, остатки, потребление/день, диоптрии)
    realistic_data = [
        {'code': '30001', 'stock': 100, 'consumption': 5, 'diopter': -0.5},    # 20 дней до OoS
        {'code': '30002', 'stock': 50, 'consumption': 8, 'diopter': -0.75},    # 6.25 дней до OoS
        {'code': '30003', 'stock': 30, 'consumption': 10, 'diopter': -1.00},   # 3 дня до OoS
        {'code': '30004', 'stock': 15, 'consumption': 12, 'diopter': -1.25},   # 1.25 дня до OoS
        {'code': '30005', 'stock': 5, 'consumption': 15, 'diopter': -1.50},    # 0.33 дня до OoS
    ]
    
    print("📊 ИСХОДНЫЕ ДАННЫЕ:")
    print("Код SKU | Диоптрии | Остатки | Потребление/день | Дней до OoS")
    print("-" * 70)
    for sku in realistic_data:
        days_until_oos = sku['stock'] / sku['consumption']
        print(f"{sku['code']:8} | {sku['diopter']:8.2f} | {sku['stock']:7} | {sku['consumption']:16} | {days_until_oos:10.1f}")
    print()
    
    optimizer = CategoryOrderOptimizer()
    result = optimizer.analyze_category_order(realistic_data)
    
    print("\n" + "=" * 60)
    print("📋 РЕЗУЛЬТАТ ОПТИМИЗАЦИИ:")
    print("=" * 60)
    
    if result['order_needed']:
        print(f"✅ Заказ НУЖЕН")
        print(f"📦 Общий объем: {result['total_volume']} ед.")
        print(f"📅 Дата заказа: {result['order_date']}")
        print(f"🚚 Дата поставки: {result['delivery_date']}")
        print(f"📊 Использование минимального заказа: {result['utilization']:.1f}%")
        
        print("\n📋 ДЕТАЛИ ЗАКАЗА:")
        for order in result['sku_orders']:
            print(f"  {order['product_code']} ({order['diopter']:+.2f}): {order['volume']} ед.")
            print(f"    Критичность: {order['criticality']}")
            print(f"    Покрытие: {order['coverage_days']:.1f} дней")
            print(f"    Дней до OoS: {order['days_until_oos']}")
        
        # Анализ эффективности
        print(f"\n📈 АНАЛИЗ ЭФФЕКТИВНОСТИ:")
        critical_orders = [o for o in result['sku_orders'] if o['criticality'] in ['CRITICAL', 'HIGH']]
        medium_orders = [o for o in result['sku_orders'] if o['criticality'] == 'MEDIUM']
        low_orders = [o for o in result['sku_orders'] if o['criticality'] == 'LOW']
        
        print(f"  Критичные SKU: {len(critical_orders)}")
        print(f"  Средние SKU: {len(medium_orders)}")
        print(f"  Низкие SKU: {len(low_orders)}")
        
        total_coverage = sum(o['coverage_days'] for o in result['sku_orders'])
        print(f"  Общее покрытие: {total_coverage:.1f} дней")
        
    else:
        print(f"❌ Заказ НЕ НУЖЕН")
        print(f"Причина: {result['reason']}")

def test_extreme_scenario():
    """Тестируем экстремальный сценарий с множественными угрозами OoS"""
    
    print("\n" + "=" * 80)
    print("🚨 ЭКСТРЕМАЛЬНЫЙ СЦЕНАРИЙ")
    print("Множественные угрозы OoS - проверяем приоритизацию")
    print("=" * 80)
    
    # Экстремальные данные
    extreme_data = [
        {'code': '30001', 'stock': 10, 'consumption': 5, 'diopter': -0.5},     # 2 дня до OoS
        {'code': '30002', 'stock': 5, 'consumption': 8, 'diopter': -0.75},     # 0.6 дня до OoS
        {'code': '30003', 'stock': 2, 'consumption': 10, 'diopter': -1.00},    # 0.2 дня до OoS
        {'code': '30004', 'stock': 1, 'consumption': 12, 'diopter': -1.25},    # 0.08 дня до OoS
        {'code': '30005', 'stock': 0, 'consumption': 15, 'diopter': -1.50},    # 0 дней до OoS
    ]
    
    print("📊 ИСХОДНЫЕ ДАННЫЕ:")
    print("Код SKU | Диоптрии | Остатки | Потребление/день | Дней до OoS")
    print("-" * 70)
    for sku in extreme_data:
        days_until_oos = sku['stock'] / sku['consumption']
        print(f"{sku['code']:8} | {sku['diopter']:8.2f} | {sku['stock']:7} | {sku['consumption']:16} | {days_until_oos:10.1f}")
    print()
    
    optimizer = CategoryOrderOptimizer()
    result = optimizer.analyze_category_order(extreme_data)
    
    print("\n📋 РЕЗУЛЬТАТ ЭКСТРЕМАЛЬНОГО СЦЕНАРИЯ:")
    print("=" * 60)
    
    if result['order_needed']:
        print(f"✅ Заказ НУЖЕН")
        print(f"📦 Общий объем: {result['total_volume']} ед.")
        print(f"📊 Использование минимального заказа: {result['utilization']:.1f}%")
        
        print("\n📋 ПРИОРИТЕТНЫЙ ЗАКАЗ:")
        for order in result['sku_orders']:
            print(f"  {order['product_code']} ({order['diopter']:+.2f}): {order['volume']} ед.")
            print(f"    Критичность: {order['criticality']}")
            print(f"    Покрытие: {order['coverage_days']:.1f} дней")
            print(f"    Дней до OoS: {order['days_until_oos']}")
    else:
        print(f"❌ Заказ НЕ НУЖЕН")
        print(f"Причина: {result['reason']}")

def main():
    """Основная функция"""
    test_realistic_scenario()
    test_extreme_scenario()

if __name__ == "__main__":
    main() 