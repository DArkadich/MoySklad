#!/usr/bin/env python3
"""
Оптимизатор заказов по категориям
Правильная логика: минимальный заказ на всю категорию, распределение по приоритету OoS
"""

from product_rules import ProductRules
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json

class CategoryOrderOptimizer:
    """Оптимизатор заказов по категориям товаров"""
    
    def __init__(self):
        self.product_rules = ProductRules()
    
    def analyze_category_order(self, category_sku_data: List[Dict]) -> Dict:
        """Анализирует оптимальный заказ для категории товаров"""
        
        print(f"🧮 АНАЛИЗ ЗАКАЗА КАТЕГОРИИ")
        print(f"Количество SKU: {len(category_sku_data)}")
        print()
        
        # 1. Анализируем каждый SKU
        analyzed_skus = []
        for sku_data in category_sku_data:
            analysis = self.analyze_single_sku(sku_data)
            analyzed_skus.append(analysis)
        
        # 2. Сортируем по приоритету (угроза OoS)
        analyzed_skus.sort(key=lambda x: x['priority_score'], reverse=True)
        
        # 3. Определяем категорию и минимальный заказ
        category_info = self.get_category_info(analyzed_skus[0]['product_code'])
        min_order = category_info['min_order']
        
        print(f"📦 МИНИМАЛЬНЫЙ ЗАКАЗ КАТЕГОРИИ: {min_order} ед.")
        print()
        
        # 4. Формируем оптимальный заказ
        optimal_order = self.build_optimal_order(analyzed_skus, min_order)
        
        return optimal_order
    
    def analyze_single_sku(self, sku_data: Dict) -> Dict:
        """Анализирует один SKU"""
        product_code = sku_data['code']
        current_stock = sku_data['stock']
        daily_consumption = sku_data['consumption']
        diopter = sku_data.get('diopter', 0)
        
        # Получаем правила
        rules = self.product_rules.get_product_rules(product_code)
        if not rules:
            return None
        
        # Рассчитываем дни до OoS
        days_until_oos = int(current_stock / daily_consumption) if daily_consumption > 0 else 999
        
        # Рассчитываем необходимый запас
        required_stock = self.product_rules.calculate_required_stock(product_code, daily_consumption, False)
        recommended_order = max(0, required_stock - current_stock)
        
        # Определяем приоритет (чем меньше дней до OoS, тем выше приоритет)
        priority_score = 1000 - days_until_oos  # Инвертируем для сортировки
        
        # Определяем критичность
        if days_until_oos <= 0:
            criticality = "CRITICAL"
        elif days_until_oos <= 7:
            criticality = "HIGH"
        elif days_until_oos <= 30:
            criticality = "MEDIUM"
        else:
            criticality = "LOW"
        
        return {
            'product_code': product_code,
            'diopter': diopter,
            'current_stock': current_stock,
            'daily_consumption': daily_consumption,
            'days_until_oos': days_until_oos,
            'required_stock': required_stock,
            'recommended_order': recommended_order,
            'priority_score': priority_score,
            'criticality': criticality,
            'rules': rules
        }
    
    def get_category_info(self, product_code: str) -> Dict:
        """Получает информацию о категории товара"""
        rules = self.product_rules.get_product_rules(product_code)
        if not rules:
            return {'min_order': 5000, 'multiple': 30}
        
        return {
            'min_order': rules['min_order'],
            'multiple': rules['multiple'],
            'category': rules.get('category', 'unknown')
        }
    
    def build_optimal_order(self, analyzed_skus: List[Dict], min_order: int) -> Dict:
        """Строит оптимальный заказ"""
        
        print("📋 ФОРМИРОВАНИЕ ОПТИМАЛЬНОГО ЗАКАЗА:")
        print("=" * 60)
        
        # Фильтруем SKU с угрозой OoS
        critical_skus = [sku for sku in analyzed_skus if sku['days_until_oos'] <= 30]
        
        if not critical_skus:
            print("✅ Нет SKU с угрозой OoS - заказ не нужен")
            return {
                'order_needed': False,
                'reason': 'Нет угрозы OoS',
                'total_volume': 0,
                'sku_orders': []
            }
        
        print(f"🚨 SKU с угрозой OoS: {len(critical_skus)}")
        for sku in critical_skus:
            print(f"  {sku['product_code']} ({sku['diopter']:+.2f}): {sku['days_until_oos']} дней до OoS")
        print()
        
        # Распределяем объем по приоритету
        remaining_volume = min_order
        sku_orders = []
        
        for sku in critical_skus:
            if remaining_volume <= 0:
                break
            
            # Определяем объем для этого SKU
            needed_volume = min(sku['recommended_order'], remaining_volume)
            
            # Применяем кратность
            multiple = sku['rules']['multiple']
            if multiple > 1:
                needed_volume = ((needed_volume + multiple - 1) // multiple) * multiple
            
            # Ограничиваем оставшимся объемом
            final_volume = min(needed_volume, remaining_volume)
            
            if final_volume > 0:
                sku_order = {
                    'product_code': sku['product_code'],
                    'diopter': sku['diopter'],
                    'volume': final_volume,
                    'days_until_oos': sku['days_until_oos'],
                    'criticality': sku['criticality'],
                    'coverage_days': final_volume / sku['daily_consumption'] if sku['daily_consumption'] > 0 else 0
                }
                sku_orders.append(sku_order)
                remaining_volume -= final_volume
                
                print(f"  ✅ {sku['product_code']} ({sku['diopter']:+.2f}): {final_volume} ед.")
                print(f"     Покрытие: {sku_order['coverage_days']:.1f} дней")
        
        # Если остался объем, добавляем менее критичные SKU
        if remaining_volume > 0:
            print(f"\n📦 Осталось объема: {remaining_volume} ед.")
            print("Добавляем менее критичные SKU:")
            
            for sku in analyzed_skus:
                if sku['days_until_oos'] > 30 and remaining_volume > 0:
                    # Определяем объем для этого SKU
                    needed_volume = min(sku['recommended_order'], remaining_volume)
                    
                    # Применяем кратность
                    multiple = sku['rules']['multiple']
                    if multiple > 1:
                        needed_volume = ((needed_volume + multiple - 1) // multiple) * multiple
                    
                    final_volume = min(needed_volume, remaining_volume)
                    
                    if final_volume > 0:
                        sku_order = {
                            'product_code': sku['product_code'],
                            'diopter': sku['diopter'],
                            'volume': final_volume,
                            'days_until_oos': sku['days_until_oos'],
                            'criticality': sku['criticality'],
                            'coverage_days': final_volume / sku['daily_consumption'] if sku['daily_consumption'] > 0 else 0
                        }
                        sku_orders.append(sku_order)
                        remaining_volume -= final_volume
                        
                        print(f"  ✅ {sku['product_code']} ({sku['diopter']:+.2f}): {final_volume} ед.")
                        print(f"     Покрытие: {sku_order['coverage_days']:.1f} дней")
        
        total_volume = sum(order['volume'] for order in sku_orders)
        
        print(f"\n📊 ИТОГО:")
        print(f"  Общий объем: {total_volume} ед.")
        print(f"  Количество SKU: {len(sku_orders)}")
        print(f"  Использование минимального заказа: {total_volume}/{min_order} ({total_volume/min_order*100:.1f}%)")
        
        return {
            'order_needed': True,
            'total_volume': total_volume,
            'min_order': min_order,
            'utilization': total_volume / min_order * 100,
            'sku_orders': sku_orders,
            'order_date': datetime.now().strftime('%Y-%m-%d'),
            'delivery_date': (datetime.now() + timedelta(days=57)).strftime('%Y-%m-%d')
        }

def main():
    """Тестирование оптимизатора"""
    
    # Тестовые данные (ваш пример)
    test_data = [
        {'code': '30001', 'stock': 385, 'consumption': 1, 'diopter': -0.5},
        {'code': '30002', 'stock': 154, 'consumption': 1, 'diopter': -0.75},
        {'code': '30003', 'stock': 103, 'consumption': 1, 'diopter': -1.00},
        {'code': '30004', 'stock': 80, 'consumption': 1, 'diopter': -1.25},
        {'code': '30005', 'stock': 5, 'consumption': 1, 'diopter': -1.50},
    ]
    
    optimizer = CategoryOrderOptimizer()
    result = optimizer.analyze_category_order(test_data)
    
    print("\n" + "=" * 60)
    print("📋 РЕЗУЛЬТАТ ОПТИМИЗАЦИИ:")
    print("=" * 60)
    
    if result['order_needed']:
        print(f"✅ Заказ НУЖЕН")
        print(f"📦 Общий объем: {result['total_volume']} ед.")
        print(f"📅 Дата заказа: {result['order_date']}")
        print(f"🚚 Дата поставки: {result['delivery_date']}")
        print(f"📊 Использование: {result['utilization']:.1f}%")
        
        print("\n📋 ДЕТАЛИ ЗАКАЗА:")
        for order in result['sku_orders']:
            print(f"  {order['product_code']} ({order['diopter']:+.2f}): {order['volume']} ед.")
            print(f"    Критичность: {order['criticality']}")
            print(f"    Покрытие: {order['coverage_days']:.1f} дней")
    else:
        print(f"❌ Заказ НЕ НУЖЕН")
        print(f"Причина: {result['reason']}")

if __name__ == "__main__":
    main() 