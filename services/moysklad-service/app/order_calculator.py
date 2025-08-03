#!/usr/bin/env python3
"""
Калькулятор для проверки логики расчета даты заказа
"""

from product_rules import ProductRules
from datetime import datetime, timedelta

def calculate_order_timing(product_code: str, current_stock: float, daily_consumption: float, combined_delivery: bool = False):
    """Рассчитывает когда нужно сделать заказ"""
    
    # Рассчитываем дни до OoS
    days_until_oos = int(current_stock / daily_consumption) if daily_consumption > 0 else 999
    
    # Получаем правила товара
    rules = ProductRules.get_product_rules(product_code)
    if not rules:
        print(f"❌ Товар {product_code} не найден в правилах")
        return None
    
    # Получаем общий срок поставки
    total_lead_time = ProductRules.get_total_lead_time(product_code, combined_delivery)
    safety_stock_days = rules['safety_stock_days']
    critical_days = total_lead_time + safety_stock_days
    
    # Рассчитываем когда нужно сделать заказ
    days_until_order = days_until_oos - critical_days
    
    # Рассчитываем рекомендуемый заказ
    required_stock = ProductRules.calculate_required_stock(product_code, daily_consumption, combined_delivery)
    recommended_order = max(0, required_stock - current_stock)
    final_order = ProductRules.apply_order_constraints(product_code, recommended_order)
    
    # Проверяем, нужно ли создавать заказ
    should_create = ProductRules.should_create_order(product_code, days_until_oos, recommended_order, combined_delivery)
    
    # Рассчитываем даты
    today = datetime.now()
    order_date = today + timedelta(days=max(0, days_until_order))
    delivery_date = order_date + timedelta(days=total_lead_time)
    
    return {
        'product_code': product_code,
        'product_description': rules['description'],
        'current_stock': current_stock,
        'daily_consumption': daily_consumption,
        'days_until_oos': days_until_oos,
        'production_days': rules.get('production_days', 45),
        'delivery_days': rules.get('delivery_days', 12),
        'total_lead_time': total_lead_time,
        'safety_stock_days': safety_stock_days,
        'critical_days': critical_days,
        'days_until_order': days_until_order,
        'should_create_order': should_create,
        'recommended_order': recommended_order,
        'final_order': final_order,
        'order_date': order_date.strftime('%Y-%m-%d'),
        'delivery_date': delivery_date.strftime('%Y-%m-%d'),
        'combined_delivery': combined_delivery
    }

def print_order_analysis(result):
    """Выводит анализ заказа"""
    if not result:
        return
    
    print("=" * 60)
    print(f"АНАЛИЗ ЗАКАЗА: {result['product_code']} - {result['product_description']}")
    print("=" * 60)
    print(f"📦 Текущие остатки: {result['current_stock']:.1f} ед.")
    print(f"📊 Дневное потребление: {result['daily_consumption']:.2f} ед./день")
    print(f"⏰ Остатков хватит на: {result['days_until_oos']} дней")
    print()
    
    print("🏭 СРОКИ ПОСТАВКИ:")
    print(f"  Производство: {result['production_days']} дней")
    print(f"  Доставка: {result['delivery_days']} дней")
    print(f"  Общий срок: {result['total_lead_time']} дней")
    print(f"  Страховой запас: {result['safety_stock_days']} дней")
    print(f"  Критический период: {result['critical_days']} дней")
    print()
    
    print("📅 РАСЧЕТ ДАТЫ ЗАКАЗА:")
    if result['days_until_order'] > 0:
        print(f"  ✅ Заказ нужно сделать через: {result['days_until_order']} дней")
        print(f"  📅 Дата заказа: {result['order_date']}")
        print(f"  📦 Дата поставки: {result['delivery_date']}")
    elif result['days_until_order'] == 0:
        print(f"  ⚠️ Заказ нужно сделать СЕГОДНЯ")
        print(f"  📅 Дата заказа: {result['order_date']}")
        print(f"  📦 Дата поставки: {result['delivery_date']}")
    else:
        print(f"  ❌ УЖЕ ПОЗДНО! Заказ нужно было сделать {abs(result['days_until_order'])} дней назад")
        print(f"  📅 Дата заказа: {result['order_date']}")
        print(f"  📦 Дата поставки: {result['delivery_date']}")
    print()
    
    print("🛒 РЕКОМЕНДУЕМЫЙ ЗАКАЗ:")
    print(f"  Рекомендуемый объем: {result['recommended_order']:.1f} ед.")
    print(f"  Финальный заказ: {result['final_order']} ед.")
    print(f"  Нужен заказ: {'✅ ДА' if result['should_create_order'] else '❌ НЕТ'}")
    print()
    
    if result['combined_delivery']:
        print("🚚 ОБЪЕДИНЕННАЯ ДОСТАВКА:")
        print(f"  Себестоимость доставки линз = 0")
        print(f"  Экономия на доставке")
    else:
        print("🚚 ОТДЕЛЬНАЯ ДОСТАВКА")
    print("=" * 60)

def main():
    """Тестирование калькулятора"""
    
    # Тестовые данные
    test_cases = [
        # (код товара, остатки, дневное потребление, объединенная доставка)
        ('30001', 8000, 100, False),  # Линзы, отдельная поставка
        ('30001', 8000, 100, True),   # Линзы, объединенная поставка
        ('360360', 5000, 50, False),  # Растворы, отдельная поставка
        ('360360', 5000, 50, True),   # Растворы, объединенная поставка
    ]
    
    print("🧮 КАЛЬКУЛЯТОР ДАТЫ ЗАКАЗА")
    print("Проверка логики расчета когда нужно делать заказ")
    print()
    
    for product_code, stock, consumption, combined in test_cases:
        result = calculate_order_timing(product_code, stock, consumption, combined)
        print_order_analysis(result)
        print()

if __name__ == "__main__":
    main() 