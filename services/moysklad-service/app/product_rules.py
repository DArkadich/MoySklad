#!/usr/bin/env python3
"""
Правила закупок для разных типов товаров
Специализированные правила для контактных линз и растворов
Обновлено с учетом реальных сроков производства и доставки
"""

from typing import Dict, Optional
import re

class ProductRules:
    """Правила закупок для разных типов товаров"""
    
    # Правила для разных типов товаров
    PRODUCT_RULES = {
        # Однодневные линзы (код 30хххх)
        'daily_lenses': {
            'pattern': r'^30\d{4}$',
            'min_order': 3000,
            'multiple': 30,
            'production_days': 45,  # Средний срок производства
            'delivery_days': 12,    # Доставка отдельно
            'combined_delivery_days': 0,  # Доставка с растворами
            'safety_stock_days': 15,
            'description': 'Однодневные линзы',
            'category': 'lenses',
            'can_combine_delivery': True
        },
        
        # Месячные линзы по 6 шт (код 6хххх)
        'monthly_lenses_6': {
            'pattern': r'^6\d{4}$',
            'min_order': 5000,
            'multiple': 50,
            'production_days': 45,  # Средний срок производства
            'delivery_days': 12,    # Доставка отдельно
            'combined_delivery_days': 0,  # Доставка с растворами
            'safety_stock_days': 15,
            'description': 'Месячные линзы по 6 шт',
            'category': 'lenses',
            'can_combine_delivery': True
        },
        
        # Месячные линзы по 3 шт (код 3хххх)
        'monthly_lenses_3': {
            'pattern': r'^3\d{4}$',
            'min_order': 5000,
            'multiple': 50,
            'production_days': 45,  # Средний срок производства
            'delivery_days': 12,    # Доставка отдельно
            'combined_delivery_days': 0,  # Доставка с растворами
            'safety_stock_days': 15,
            'description': 'Месячные линзы по 3 шт',
            'category': 'lenses',
            'can_combine_delivery': True
        },
        
        # Растворы 360 мл (код 360360)
        'solution_360': {
            'pattern': r'^360360$',
            'min_order': 5000,
            'multiple': 24,
            'production_days': 45,  # Средний срок производства
            'delivery_days': 37,    # Доставка отдельно (30-45 дней)
            'combined_delivery_days': 37,  # Доставка с линзами
            'safety_stock_days': 25,
            'description': 'Растворы 360 мл',
            'category': 'solutions',
            'can_combine_delivery': True
        },
        
        # Растворы 500 мл (код 500500)
        'solution_500': {
            'pattern': r'^500500$',
            'min_order': 5000,
            'multiple': 24,
            'production_days': 45,  # Средний срок производства
            'delivery_days': 37,    # Доставка отдельно (30-45 дней)
            'combined_delivery_days': 37,  # Доставка с линзами
            'safety_stock_days': 25,
            'description': 'Растворы 500 мл',
            'category': 'solutions',
            'can_combine_delivery': True
        },
        
        # Растворы 120 мл (код 120120)
        'solution_120': {
            'pattern': r'^120120$',
            'min_order': 5000,
            'multiple': 48,
            'production_days': 45,  # Средний срок производства
            'delivery_days': 37,    # Доставка отдельно (30-45 дней)
            'combined_delivery_days': 37,  # Доставка с линзами
            'safety_stock_days': 25,
            'description': 'Растворы 120 мл',
            'category': 'solutions',
            'can_combine_delivery': True
        }
    }
    
    @classmethod
    def get_product_type(cls, product_code: str) -> Optional[str]:
        """Определяет тип товара по коду"""
        for product_type, rules in cls.PRODUCT_RULES.items():
            if re.match(rules['pattern'], str(product_code)):
                return product_type
        return None
    
    @classmethod
    def get_product_rules(cls, product_code: str) -> Optional[Dict]:
        """Получает правила для товара"""
        product_type = cls.get_product_type(product_code)
        if product_type:
            return cls.PRODUCT_RULES[product_type]
        return None
    
    @classmethod
    def get_total_lead_time(cls, product_code: str, combined_delivery: bool = False) -> int:
        """Получает общий срок поставки (производство + доставка)"""
        rules = cls.get_product_rules(product_code)
        if not rules:
            return 52  # Базовый срок поставки
        
        production_days = rules.get('production_days', 45)
        
        if combined_delivery and rules.get('can_combine_delivery', False):
            delivery_days = rules.get('combined_delivery_days', 0)
        else:
            delivery_days = rules.get('delivery_days', 12)
        
        return production_days + delivery_days
    
    @classmethod
    def apply_order_constraints(cls, product_code: str, recommended_quantity: float) -> int:
        """Применяет ограничения к заказу"""
        rules = cls.get_product_rules(product_code)
        if not rules:
            # Для неизвестных товаров используем базовые правила
            return max(1, int(recommended_quantity))
        
        # Применяем минимальный заказ
        quantity = max(recommended_quantity, rules['min_order'])
        
        # Применяем кратность
        if rules['multiple'] > 1:
            quantity = ((quantity + rules['multiple'] - 1) // rules['multiple']) * rules['multiple']
        
        return int(quantity)
    
    @classmethod
    def calculate_safety_stock(cls, product_code: str, daily_consumption: float) -> float:
        """Рассчитывает страховой запас для товара"""
        rules = cls.get_product_rules(product_code)
        if not rules:
            # Базовый страховой запас для неизвестных товаров
            return max(3, daily_consumption * 7)
        
        # Используем специализированный страховой запас
        return daily_consumption * rules['safety_stock_days']
    
    @classmethod
    def calculate_required_stock(cls, product_code: str, daily_consumption: float, combined_delivery: bool = False) -> float:
        """Рассчитывает общий необходимый запас (страховой + на период поставки)"""
        rules = cls.get_product_rules(product_code)
        if not rules:
            # Базовый необходимый запас для неизвестных товаров
            return max(3, daily_consumption * 14)
        
        # Общий необходимый запас = страховой запас + запас на период поставки
        safety_stock_days = rules['safety_stock_days']
        total_lead_time = cls.get_total_lead_time(product_code, combined_delivery)
        total_required_days = safety_stock_days + total_lead_time
        
        return daily_consumption * total_required_days
    
    @classmethod
    def get_lead_time_days(cls, product_code: str) -> int:
        """Получает срок поставки для товара (устаревший метод)"""
        return cls.get_total_lead_time(product_code)
    
    @classmethod
    def should_create_order(cls, product_code: str, days_until_oos: int, recommended_order: float, combined_delivery: bool = False) -> bool:
        """Определяет, нужно ли создавать заказ"""
        rules = cls.get_product_rules(product_code)
        if not rules:
            # Базовые правила для неизвестных товаров
            return days_until_oos <= 7 and recommended_order > 0
        
        # Используем специализированные правила
        # Создаем заказ если остатков хватит менее чем на срок поставки + страховой запас
        total_lead_time = cls.get_total_lead_time(product_code, combined_delivery)
        critical_days = total_lead_time + rules['safety_stock_days']
        return days_until_oos <= critical_days and recommended_order >= rules['min_order']
    
    @classmethod
    def get_product_info(cls, product_code: str) -> Dict:
        """Получает информацию о товаре"""
        rules = cls.get_product_rules(product_code)
        if not rules:
            return {
                'type': 'unknown',
                'description': 'Неизвестный товар',
                'min_order': 1,
                'multiple': 1,
                'production_days': 45,
                'delivery_days': 7,
                'total_lead_time': 52,
                'safety_stock_days': 7,
                'category': 'unknown',
                'can_combine_delivery': False
            }
        
        return {
            'type': cls.get_product_type(product_code),
            'description': rules['description'],
            'min_order': rules['min_order'],
            'multiple': rules['multiple'],
            'production_days': rules.get('production_days', 45),
            'delivery_days': rules.get('delivery_days', 12),
            'combined_delivery_days': rules.get('combined_delivery_days', 0),
            'total_lead_time': cls.get_total_lead_time(product_code),
            'safety_stock_days': rules['safety_stock_days'],
            'category': rules.get('category', 'unknown'),
            'can_combine_delivery': rules.get('can_combine_delivery', False)
        }
    
    @classmethod
    def validate_order(cls, product_code: str, quantity: int) -> Dict:
        """Валидирует заказ"""
        rules = cls.get_product_rules(product_code)
        if not rules:
            return {'valid': True, 'message': 'Базовые правила применены'}
        
        errors = []
        
        # Проверяем минимальный заказ
        if quantity < rules['min_order']:
            errors.append(f"Заказ меньше минимального: {quantity} < {rules['min_order']}")
        
        # Проверяем кратность
        if quantity % rules['multiple'] != 0:
            errors.append(f"Заказ не кратен {rules['multiple']}: {quantity}")
        
        if errors:
            return {'valid': False, 'errors': errors}
        
        return {'valid': True, 'message': 'Заказ соответствует правилам'}
    
    @classmethod
    def get_delivery_optimization(cls, product_codes: list) -> Dict:
        """Анализирует возможность оптимизации доставки"""
        lenses = []
        solutions = []
        
        for code in product_codes:
            rules = cls.get_product_rules(code)
            if rules:
                if rules.get('category') == 'lenses':
                    lenses.append(code)
                elif rules.get('category') == 'solutions':
                    solutions.append(code)
        
        # Если есть и линзы, и растворы, можно объединить доставку
        can_combine = len(lenses) > 0 and len(solutions) > 0
        
        # Рассчитываем экономию на доставке
        delivery_savings = 0
        if can_combine:
            # Экономия = стоимость доставки линз отдельно
            delivery_savings = len(lenses) * 12  # Примерная стоимость доставки в днях
        
        return {
            'can_combine_delivery': can_combine,
            'lenses_count': len(lenses),
            'solutions_count': len(solutions),
            'delivery_savings_days': delivery_savings,
            'recommended_action': 'combine_delivery' if can_combine else 'separate_delivery'
        }

# Пример использования
if __name__ == "__main__":
    # Тестируем правила
    test_codes = ['30001', '60001', '30001', '360360', '500500', '120120', '99999']
    
    for code in test_codes:
        product_type = ProductRules.get_product_type(code)
        rules = ProductRules.get_product_rules(code)
        info = ProductRules.get_product_info(code)
        
        print(f"Код: {code}")
        print(f"  Тип: {product_type}")
        print(f"  Описание: {info['description']}")
        print(f"  Мин. заказ: {info['min_order']}")
        print(f"  Кратность: {info['multiple']}")
        print(f"  Производство: {info['production_days']} дней")
        print(f"  Доставка: {info['delivery_days']} дней")
        print(f"  Общий срок: {info['total_lead_time']} дней")
        print(f"  Страховой запас: {info['safety_stock_days']} дней")
        print(f"  Категория: {info['category']}")
        print(f"  Может объединить доставку: {info['can_combine_delivery']}")
        print()
    
    # Тестируем оптимизацию доставки
    test_combination = ['30001', '60001', '360360', '500500']
    optimization = ProductRules.get_delivery_optimization(test_combination)
    print("Оптимизация доставки:")
    print(f"  Может объединить: {optimization['can_combine_delivery']}")
    print(f"  Линз: {optimization['lenses_count']}")
    print(f"  Растворов: {optimization['solutions_count']}")
    print(f"  Экономия: {optimization['delivery_savings_days']} дней")
    print(f"  Рекомендация: {optimization['recommended_action']}") 