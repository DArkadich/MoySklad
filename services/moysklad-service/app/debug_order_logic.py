#!/usr/bin/env python3
"""
Отладочный скрипт для проверки логики расчета заказов
"""

from product_rules import ProductRules

def debug_order_calculation(product_code, current_stock, daily_consumption):
    """Отлаживаем расчет заказа"""
    
    print(f"🔍 ОТЛАДКА РАСЧЕТА ЗАКАЗА ДЛЯ {product_code}")
    print("=" * 50)
    
    # Получаем правила
    rules = ProductRules.get_product_rules(product_code)
    if not rules:
        print(f"❌ Товар {product_code} не найден в правилах")
        return
    
    print(f"📦 Текущие остатки: {current_stock} ед.")
    print(f"📊 Дневное потребление: {daily_consumption} ед./день")
    
    # Рассчитываем дни до OoS
    days_until_oos = int(current_stock / daily_consumption) if daily_consumption > 0 else 999
    print(f"⏰ Остатков хватит на: {days_until_oos} дней")
    
    # Рассчитываем страховой запас
    safety_stock_days = rules['safety_stock_days']
    safety_stock = daily_consumption * safety_stock_days
    print(f"🛡️ Страховой запас: {safety_stock} ед. ({safety_stock_days} дней)")
    
    # Рассчитываем общий необходимый запас
    required_stock = ProductRules.calculate_required_stock(product_code, daily_consumption, False)
    total_lead_time = ProductRules.get_total_lead_time(product_code, False)
    print(f"📦 Общий необходимый запас: {required_stock} ед. ({safety_stock_days + total_lead_time} дней)")
    
    # Рассчитываем рекомендуемый заказ
    recommended_order = max(0, required_stock - current_stock)
    print(f"📋 Рекомендуемый заказ: {recommended_order} ед.")
    
    # Проверяем минимальный заказ
    min_order = rules['min_order']
    print(f"📏 Минимальный заказ: {min_order} ед.")
    
    # Применяем ограничения
    final_order = ProductRules.apply_order_constraints(product_code, recommended_order)
    print(f"✅ Финальный заказ: {final_order} ед.")
    
    # Проверяем условия создания заказа
    total_lead_time = ProductRules.get_total_lead_time(product_code, False)
    critical_days = total_lead_time + safety_stock_days
    print(f"🏭 Общий срок поставки: {total_lead_time} дней")
    print(f"⚠️ Критический период: {critical_days} дней")
    
    should_create = ProductRules.should_create_order(product_code, days_until_oos, recommended_order, False)
    print(f"🤔 Нужен заказ: {'✅ ДА' if should_create else '❌ НЕТ'}")
    
    print()
    print("🔍 АНАЛИЗ ПРОБЛЕМЫ:")
    if recommended_order == 0:
        print("  ❌ Рекомендуемый заказ = 0")
        print(f"     Причина: общий необходимый запас ({required_stock}) <= текущие остатки ({current_stock})")
        print(f"     {required_stock} <= {current_stock} = {required_stock <= current_stock}")
    elif recommended_order < min_order:
        print(f"  ❌ Рекомендуемый заказ ({recommended_order}) < минимального ({min_order})")
    elif days_until_oos > critical_days:
        print(f"  ❌ Остатков хватит на {days_until_oos} дней > критического периода {critical_days} дней")
    else:
        print("  ✅ Все условия выполнены")
    
    return {
        'recommended_order': recommended_order,
        'final_order': final_order,
        'should_create': should_create,
        'safety_stock': safety_stock,
        'current_stock': current_stock
    }

def main():
    """Тестируем с вашими данными"""
    
    test_cases = [
        ('30001', 385, 1),   # -0.5, остатков на 385 дней
        ('30002', 154, 1),   # -0.75, остатков на 154 дня
        ('30003', 103, 1),   # -1.00, остатков на 103 дня
        ('30004', 80, 1),    # -1.25, остатков на 80 дней
        ('30005', 5, 1),     # -1.50, остатков на 5 дней
    ]
    
    print("🧮 ОТЛАДКА ЛОГИКИ ЗАКАЗОВ")
    print("Проверяем почему заказы не создаются")
    print()
    
    for code, stock, consumption in test_cases:
        result = debug_order_calculation(code, stock, consumption)
        print("-" * 50)
        print()

if __name__ == "__main__":
    main() 