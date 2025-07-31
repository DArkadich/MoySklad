#!/usr/bin/env python3
"""
Правила закупок для разных типов товаров
Специализированные правила для контактных линз и растворов
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
            'lead_time_days': 14,
            'safety_stock_days': 10,
            'description': 'Однодневные линзы'
        },
        
        # Месячные линзы по 6 шт (код 6хххх)
        'monthly_lenses_6': {
            'pattern': r'^6\d{4}$',
            'min_order': 5000,
            'multiple': 50,
            'lead_time_days': 21,
            'safety_stock_days': 14,
            'description': 'Месячные линзы по 6 шт'
        },
        
        # Месячные линзы по 3 шт (код 3хххх)
        'monthly_lenses_3': {
            'pattern': r'^3\d{4}$',
            'min_order': 5000,
            'multiple': 50,
            'lead_time_days': 21,
            'safety_stock_days': 14,
            'description': 'Месячные линзы по 3 шт'
        },
        
        # Растворы 360 мл (код 360360)
        'solution_360': {
            'pattern': r'^360360$',
            'min_order': 5000,
            'multiple': 24,
            'lead_time_days': 7,
            'safety_stock_days': 21,
            'description': 'Растворы 360 мл'
        },
        
        # Растворы 500 мл (код 500500)
        'solution_500': {
            'pattern': r'^500500$',
            'min_order': 5000,
            'multiple': 24,
            'lead_time_days': 7,
            'safety_stock_days': 21,
            'description': 'Растворы 500 мл'
        },
        
        # Растворы 120 мл (код 120120)
        'solution_120': {
            'pattern': r'^120120$',
            'min_order': 5000,
            'multiple': 48,
            'lead_time_days': 7,
            'safety_stock_days': 21,
            'description': 'Растворы 120 мл'
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
    def get_lead_time_days(cls, product_code: str) -> int:
        """Получает срок поставки для товара"""
        rules = cls.get_product_rules(product_code)
        if not rules:
            return 7  # Базовый срок поставки
        
        return rules['lead_time_days']
    
    @classmethod
    def should_create_order(cls, product_code: str, days_until_oos: int, recommended_order: float) -> bool:
        """Определяет, нужно ли создавать заказ"""
        rules = cls.get_product_rules(product_code)
        if not rules:
            # Базовые правила для неизвестных товаров
            return days_until_oos <= 7 and recommended_order > 0
        
        # Используем специализированные правила
        # Создаем заказ если остатков хватит менее чем на срок поставки + страховой запас
        critical_days = rules['lead_time_days'] + rules['safety_stock_days']
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
                'lead_time_days': 7,
                'safety_stock_days': 7
            }
        
        return {
            'type': cls.get_product_type(product_code),
            'description': rules['description'],
            'min_order': rules['min_order'],
            'multiple': rules['multiple'],
            'lead_time_days': rules['lead_time_days'],
            'safety_stock_days': rules['safety_stock_days']
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
        print(f"  Срок поставки: {info['lead_time_days']} дней")
        print(f"  Страховой запас: {info['safety_stock_days']} дней")
        print() 