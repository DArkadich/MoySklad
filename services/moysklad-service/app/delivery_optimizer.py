#!/usr/bin/env python3
"""
Сервис оптимизации доставки
Анализирует возможность объединения поставок линз и растворов
для снижения себестоимости доставки
"""

import asyncio
import httpx
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from product_rules import ProductRules

# Настройки API
MOYSKLAD_API_URL = "https://api.moysklad.ru/api/remap/1.2"
MOYSKLAD_API_TOKEN = os.getenv('MOYSKLAD_API_TOKEN')

HEADERS = {
    "Authorization": f"Bearer {MOYSKLAD_API_TOKEN}",
    "Content-Type": "application/json"
}

class DeliveryOptimizer:
    """Оптимизатор доставки для объединения поставок"""
    
    def __init__(self):
        self.product_rules = ProductRules()
    
    async def get_low_stock_products(self, client: httpx.AsyncClient) -> List[Dict]:
        """Получает товары с низкими остатками"""
        try:
            # Получаем все товары
            resp = await client.get(f"{MOYSKLAD_API_URL}/entity/assortment", headers=HEADERS)
            resp.raise_for_status()
            data = resp.json()
            products = data.get("rows", [])
            
            low_stock_products = []
            
            for product in products:
                product_code = product.get('code', '')
                if not product_code:
                    continue
                
                # Получаем остатки
                stock_resp = await client.get(
                    f"{MOYSKLAD_API_URL}/report/stock/all",
                    headers=HEADERS,
                    params={"filter": f"code={product_code}"}
                )
                stock_resp.raise_for_status()
                stock_data = stock_resp.json()
                
                if stock_data.get("rows"):
                    stock_info = stock_data["rows"][0]
                    current_stock = stock_info.get("quantity", 0)
                    
                    # Проверяем, нужен ли заказ
                    rules = self.product_rules.get_product_rules(product_code)
                    if rules:
                        min_stock = rules.get('safety_stock_days', 7) * 10  # Примерный дневной расход
                        if current_stock < min_stock:
                            low_stock_products.append({
                                'code': product_code,
                                'name': product.get('name', ''),
                                'current_stock': current_stock,
                                'min_stock': min_stock,
                                'category': rules.get('category', 'unknown'),
                                'rules': rules
                            })
            
            return low_stock_products
            
        except Exception as e:
            print(f"Ошибка получения товаров с низкими остатками: {e}")
            return []
    
    def analyze_delivery_optimization(self, products: List[Dict]) -> Dict:
        """Анализирует возможность оптимизации доставки"""
        lenses = []
        solutions = []
        
        for product in products:
            category = product.get('category', 'unknown')
            if category == 'lenses':
                lenses.append(product)
            elif category == 'solutions':
                solutions.append(product)
        
        # Анализируем возможность объединения
        can_combine = len(lenses) > 0 and len(solutions) > 0
        
        # Рассчитываем экономию
        delivery_savings = 0
        if can_combine:
            # Экономия = стоимость доставки линз отдельно
            # Линзы: 12 дней доставки, растворы: 37 дней
            # При объединении линзы доставляются с растворами (37 дней)
            # Но себестоимость доставки линз = 0
            delivery_savings = len(lenses) * 12  # Дни экономии на доставке
        
        # Рассчитываем оптимальные сроки заказа
        optimal_order_dates = self.calculate_optimal_order_dates(lenses, solutions)
        
        return {
            'can_combine_delivery': can_combine,
            'lenses_count': len(lenses),
            'solutions_count': len(solutions),
            'delivery_savings_days': delivery_savings,
            'recommended_action': 'combine_delivery' if can_combine else 'separate_delivery',
            'optimal_order_dates': optimal_order_dates,
            'total_products': len(products),
            'lenses': lenses,
            'solutions': solutions
        }
    
    def calculate_optimal_order_dates(self, lenses: List[Dict], solutions: List[Dict]) -> Dict:
        """Рассчитывает оптимальные даты заказа для объединения поставок"""
        today = datetime.now()
        
        # Для линз: производство 45 дней + доставка 12 дней = 57 дней
        # Для растворов: производство 45 дней + доставка 37 дней = 82 дня
        
        # При объединении: производство 45 дней + доставка 37 дней = 82 дня
        # Но линзы нужно заказывать раньше, чтобы они были готовы к отправке с растворами
        
        optimal_dates = {
            'lenses_order_date': None,
            'solutions_order_date': None,
            'combined_delivery_date': None,
            'separate_delivery_dates': {}
        }
        
        if lenses and solutions:
            # Объединенная поставка
            # Растворы заказываем на 25 дней раньше линз
            # (82 - 57 = 25 дней разница)
            
            solutions_order_date = today + timedelta(days=25)
            lenses_order_date = today
            
            combined_delivery_date = today + timedelta(days=82)
            
            optimal_dates.update({
                'lenses_order_date': lenses_order_date.strftime('%Y-%m-%d'),
                'solutions_order_date': solutions_order_date.strftime('%Y-%m-%d'),
                'combined_delivery_date': combined_delivery_date.strftime('%Y-%m-%d'),
                'delivery_strategy': 'combined'
            })
        else:
            # Отдельные поставки
            separate_dates = {}
            
            for lens in lenses:
                order_date = today
                delivery_date = today + timedelta(days=57)
                separate_dates[lens['code']] = {
                    'order_date': order_date.strftime('%Y-%m-%d'),
                    'delivery_date': delivery_date.strftime('%Y-%m-%d'),
                    'lead_time_days': 57
                }
            
            for solution in solutions:
                order_date = today
                delivery_date = today + timedelta(days=82)
                separate_dates[solution['code']] = {
                    'order_date': order_date.strftime('%Y-%m-%d'),
                    'delivery_date': delivery_date.strftime('%Y-%m-%d'),
                    'lead_time_days': 82
                }
            
            optimal_dates.update({
                'separate_delivery_dates': separate_dates,
                'delivery_strategy': 'separate'
            })
        
        return optimal_dates
    
    def generate_delivery_report(self, optimization_result: Dict) -> str:
        """Генерирует отчет по оптимизации доставки"""
        report = []
        report.append("=" * 60)
        report.append("ОТЧЕТ ПО ОПТИМИЗАЦИИ ДОСТАВКИ")
        report.append("=" * 60)
        report.append(f"Дата анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Статистика
        report.append("СТАТИСТИКА:")
        report.append(f"  Всего товаров с низкими остатками: {optimization_result['total_products']}")
        report.append(f"  Линз: {optimization_result['lenses_count']}")
        report.append(f"  Растворов: {optimization_result['solutions_count']}")
        report.append("")
        
        # Рекомендации
        report.append("РЕКОМЕНДАЦИИ:")
        if optimization_result['can_combine_delivery']:
            report.append("  ✅ РЕКОМЕНДУЕТСЯ объединенная поставка")
            report.append(f"  Экономия на доставке: {optimization_result['delivery_savings_days']} дней")
            report.append("  Себестоимость доставки линз = 0")
            
            dates = optimization_result['optimal_order_dates']
            report.append("")
            report.append("ОПТИМАЛЬНЫЕ ДАТЫ ЗАКАЗА:")
            report.append(f"  Линзы: {dates['lenses_order_date']}")
            report.append(f"  Растворы: {dates['solutions_order_date']}")
            report.append(f"  Дата поставки: {dates['combined_delivery_date']}")
        else:
            report.append("  ⚠️ Рекомендуется отдельная поставка")
            report.append("  (нет товаров обеих категорий для объединения)")
        
        report.append("")
        
        # Детали по товарам
        if optimization_result['lenses']:
            report.append("ЛИНЗЫ С НИЗКИМИ ОСТАТКАМИ:")
            for lens in optimization_result['lenses']:
                report.append(f"  {lens['code']} - {lens['name']}")
                report.append(f"    Остаток: {lens['current_stock']}, Мин. запас: {lens['min_stock']}")
        
        if optimization_result['solutions']:
            report.append("")
            report.append("РАСТВОРЫ С НИЗКИМИ ОСТАТКАМИ:")
            for solution in optimization_result['solutions']:
                report.append(f"  {solution['code']} - {solution['name']}")
                report.append(f"    Остаток: {solution['current_stock']}, Мин. запас: {solution['min_stock']}")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    async def optimize_delivery_schedule(self) -> Dict:
        """Основной метод оптимизации расписания доставки"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Получаем товары с низкими остатками
            low_stock_products = await self.get_low_stock_products(client)
            
            # Анализируем оптимизацию
            optimization_result = self.analyze_delivery_optimization(low_stock_products)
            
            # Генерируем отчет
            report = self.generate_delivery_report(optimization_result)
            optimization_result['report'] = report
            
            return optimization_result

async def main():
    """Тестирование оптимизатора доставки"""
    optimizer = DeliveryOptimizer()
    
    print("Анализ оптимизации доставки...")
    result = await optimizer.optimize_delivery_schedule()
    
    print(result['report'])
    
    # Сохраняем отчет в файл
    with open('delivery_optimization_report.txt', 'w', encoding='utf-8') as f:
        f.write(result['report'])
    
    print(f"\nОтчет сохранен в: delivery_optimization_report.txt")

if __name__ == "__main__":
    asyncio.run(main()) 