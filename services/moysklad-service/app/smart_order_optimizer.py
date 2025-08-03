#!/usr/bin/env python3
"""
Умный оптимизатор заказов
Правильная логика: прогнозируем будущие потребности и добавляем разные SKU до достижения минимального объема
"""

from product_rules import ProductRules
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json

class SmartOrderOptimizer:
    """Умный оптимизатор заказов с правильной логикой"""
    
    def __init__(self):
        self.product_rules = ProductRules()
    
    def analyze_smart_order(self, category_sku_data: List[Dict]) -> Dict:
        """Анализирует умный заказ для категории товаров"""
        
        print(f"🧠 УМНЫЙ АНАЛИЗ ЗАКАЗА")
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
        
        # 4. Формируем умный заказ
        optimal_order = self.build_smart_order(analyzed_skus, min_order)
        
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
    
    def calculate_future_oos_date(self, sku: Dict, additional_stock: int) -> int:
        """Рассчитывает дату OoS с учетом дополнительного запаса"""
        total_stock = sku['current_stock'] + additional_stock
        if sku['daily_consumption'] <= 0:
            return 999
        return int(total_stock / sku['daily_consumption'])
    
    def find_next_oos_sku(self, analyzed_skus: List[Dict], target_date: int) -> Dict:
        """Находит SKU, который закончится в указанную дату или раньше"""
        for sku in analyzed_skus:
            if sku['days_until_oos'] <= target_date and sku['recommended_order'] > 0:
                return sku
        return None
    
    def build_smart_order(self, analyzed_skus: List[Dict], min_order: int) -> Dict:
        """Строит умный заказ с правильной логикой"""
        
        print("🧠 УМНОЕ ФОРМИРОВАНИЕ ЗАКАЗА:")
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
        
        # Умное формирование заказа
        sku_orders = []
        remaining_volume = min_order
        current_date = 0
        
        print("📊 ДИНАМИЧЕСКОЕ ФОРМИРОВАНИЕ ЗАКАЗА:")
        print("-" * 40)
        
        # Создаем копию для отслеживания изменений
        working_skus = [sku.copy() for sku in analyzed_skus]
        
        while remaining_volume > 0:
            # Находим самый критичный SKU
            current_sku = None
            for sku in working_skus:
                if sku['days_until_oos'] <= current_date and sku['recommended_order'] > 0:
                    current_sku = sku
                    break
            
            if not current_sku:
                # Если нет критичных SKU, добавляем менее критичные
                for sku in working_skus:
                    if sku['recommended_order'] > 0:
                        current_sku = sku
                        break
            
            if not current_sku:
                break
            
            # Определяем объем для текущего SKU
            needed_volume = min(current_sku['recommended_order'], remaining_volume)
            
            # Применяем кратность
            multiple = current_sku['rules']['multiple']
            if multiple > 1:
                needed_volume = ((needed_volume + multiple - 1) // multiple) * multiple
            
            # Ограничиваем оставшимся объемом
            final_volume = min(needed_volume, remaining_volume)
            
            if final_volume > 0:
                # Рассчитываем новую дату OoS с учетом заказа
                new_oos_date = self.calculate_future_oos_date(current_sku, final_volume)
                
                sku_order = {
                    'product_code': current_sku['product_code'],
                    'diopter': current_sku['diopter'],
                    'volume': final_volume,
                    'days_until_oos': current_sku['days_until_oos'],
                    'new_oos_date': new_oos_date,
                    'criticality': current_sku['criticality'],
                    'coverage_days': final_volume / current_sku['daily_consumption'] if current_sku['daily_consumption'] > 0 else 0
                }
                sku_orders.append(sku_order)
                remaining_volume -= final_volume
                
                print(f"  ✅ {current_sku['product_code']} ({current_sku['diopter']:+.2f}): {final_volume} ед.")
                print(f"     Было дней до OoS: {current_sku['days_until_oos']}")
                print(f"     Станет дней до OoS: {new_oos_date}")
                print(f"     Покрытие: {sku_order['coverage_days']:.1f} дней")
                
                # Обновляем дату OoS для этого SKU
                current_sku['days_until_oos'] = new_oos_date
                current_sku['current_stock'] += final_volume
                current_sku['recommended_order'] = max(0, current_sku['required_stock'] - current_sku['current_stock'])
                
                # Ищем следующий SKU, который закончится
                next_sku = self.find_next_oos_sku(working_skus, new_oos_date)
                if next_sku:
                    print(f"     Следующий OoS: {next_sku['product_code']} через {next_sku['days_until_oos']} дней")
                
                current_date = new_oos_date
            else:
                break
        
        # Если остался объем, заполняем менее критичными SKU
        if remaining_volume > 0:
            print(f"\n📦 Осталось объема: {remaining_volume} ед.")
            print("Заполняем менее критичными SKU:")
            
            for sku in working_skus:
                if remaining_volume <= 0:
                    break
                
                if sku['recommended_order'] > 0:
                    needed_volume = min(sku['recommended_order'], remaining_volume)
                    
                    # Применяем кратность
                    multiple = sku['rules']['multiple']
                    if multiple > 1:
                        needed_volume = ((needed_volume + multiple - 1) // multiple) * multiple
                    
                    final_volume = min(needed_volume, remaining_volume)
                    
                    if final_volume > 0:
                        new_oos_date = self.calculate_future_oos_date(sku, final_volume)
                        
                        sku_order = {
                            'product_code': sku['product_code'],
                            'diopter': sku['diopter'],
                            'volume': final_volume,
                            'days_until_oos': sku['days_until_oos'],
                            'new_oos_date': new_oos_date,
                            'criticality': sku['criticality'],
                            'coverage_days': final_volume / sku['daily_consumption'] if sku['daily_consumption'] > 0 else 0
                        }
                        sku_orders.append(sku_order)
                        remaining_volume -= final_volume
                        
                        print(f"  ✅ {sku['product_code']} ({sku['diopter']:+.2f}): {final_volume} ед.")
                        print(f"     Покрытие: {sku_order['coverage_days']:.1f} дней")
        
        # Группируем заказы по SKU
        grouped_orders = {}
        for order in sku_orders:
            key = order['product_code']
            if key not in grouped_orders:
                grouped_orders[key] = {
                    'product_code': order['product_code'],
                    'diopter': order['diopter'],
                    'total_volume': 0,
                    'criticality': order['criticality'],
                    'coverage_days': 0
                }
            grouped_orders[key]['total_volume'] += order['volume']
            grouped_orders[key]['coverage_days'] += order['coverage_days']
        
        final_orders = list(grouped_orders.values())
        total_volume = sum(order['total_volume'] for order in final_orders)
        
        print(f"\n📊 ИТОГО:")
        print(f"  Общий объем: {total_volume} ед.")
        print(f"  Количество SKU: {len(final_orders)}")
        print(f"  Использование минимального заказа: {total_volume}/{min_order} ({total_volume/min_order*100:.1f}%)")
        
        return {
            'order_needed': True,
            'total_volume': total_volume,
            'min_order': min_order,
            'utilization': total_volume / min_order * 100,
            'sku_orders': final_orders,
            'order_date': datetime.now().strftime('%Y-%m-%d'),
            'delivery_date': (datetime.now() + timedelta(days=57)).strftime('%Y-%m-%d')
        }

def main():
    """Тестирование умного оптимизатора"""
    
    # Тестовые данные (ваш пример)
    test_data = [
        {'code': '30001', 'stock': 385, 'consumption': 1, 'diopter': -0.5},
        {'code': '30002', 'stock': 154, 'consumption': 1, 'diopter': -0.75},
        {'code': '30003', 'stock': 103, 'consumption': 1, 'diopter': -1.00},
        {'code': '30004', 'stock': 80, 'consumption': 1, 'diopter': -1.25},
        {'code': '30005', 'stock': 5, 'consumption': 1, 'diopter': -1.50},
    ]
    
    optimizer = SmartOrderOptimizer()
    result = optimizer.analyze_smart_order(test_data)
    
    print("\n" + "=" * 60)
    print("📋 РЕЗУЛЬТАТ УМНОЙ ОПТИМИЗАЦИИ:")
    print("=" * 60)
    
    if result['order_needed']:
        print(f"✅ Заказ НУЖЕН")
        print(f"📦 Общий объем: {result['total_volume']} ед.")
        print(f"📅 Дата заказа: {result['order_date']}")
        print(f"🚚 Дата поставки: {result['delivery_date']}")
        print(f"📊 Использование: {result['utilization']:.1f}%")
        
        print("\n📋 ДЕТАЛИ ЗАКАЗА:")
        for order in result['sku_orders']:
            print(f"  {order['product_code']} ({order['diopter']:+.2f}): {order['total_volume']} ед.")
            print(f"    Критичность: {order['criticality']}")
            print(f"    Покрытие: {order['coverage_days']:.1f} дней")
    else:
        print(f"❌ Заказ НЕ НУЖЕН")
        print(f"Причина: {result['reason']}")

if __name__ == "__main__":
    main() 