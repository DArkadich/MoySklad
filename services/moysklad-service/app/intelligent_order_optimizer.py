#!/usr/bin/env python3
"""
Интеллектуальный оптимизатор заказов
Прогнозирует будущие потребности и динамически формирует заказ до достижения минимального объема
Обновлено с интеграцией ML-моделей и анализом сезонности
"""

from product_rules import ProductRules
from ml_integration import MLServiceIntegration
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
import logging
import numpy as np
import asyncio
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MLForecast:
    """Прогноз от ML-модели"""
    predicted_consumption: float
    confidence: float
    trend: str  # 'increasing', 'decreasing', 'stable'
    seasonality_factor: float
    next_month_forecast: float

@dataclass
class DeliveryOptimization:
    """Оптимизация доставки"""
    can_combine: bool
    delivery_savings_days: int
    recommended_delivery_date: str
    combined_products: List[str]
    separate_products: List[str]

class IntelligentOrderOptimizer:
    """Интеллектуальный оптимизатор заказов с прогнозированием и ML-интеграцией"""
    
    def __init__(self):
        self.product_rules = ProductRules()
        self.ml_models = {}  # Кэш ML-моделей
        self.seasonality_data = {}  # Данные о сезонности
        
    def load_ml_models(self):
        """Загружает ML-модели для прогнозирования"""
        try:
            # Здесь должна быть интеграция с ML-сервисом
            # Пока используем заглушки
            logger.info("Загрузка ML-моделей...")
            return True
        except Exception as e:
            logger.error(f"Ошибка загрузки ML-моделей: {e}")
            return False
    
    async def get_ml_forecast(self, product_code: str, historical_data: List[float]) -> MLForecast:
        """Получает прогноз от ML-модели"""
        try:
            # Используем интеграцию с ML-сервисом
            async with MLServiceIntegration() as ml_service:
                forecast_data = await ml_service.get_forecast(product_code, historical_data)
                
                return MLForecast(
                    predicted_consumption=forecast_data['predicted_consumption'],
                    confidence=forecast_data['confidence'],
                    trend=forecast_data['trend'],
                    seasonality_factor=forecast_data['seasonality_factor'],
                    next_month_forecast=forecast_data['next_month_forecast']
                )
        except Exception as e:
            logger.error(f"Ошибка получения ML-прогноза для {product_code}: {e}")
            # Fallback на простую логику
            if len(historical_data) < 7:
                return MLForecast(
                    predicted_consumption=1.0,
                    confidence=0.5,
                    trend='stable',
                    seasonality_factor=1.0,
                    next_month_forecast=30.0
                )
            
            # Простой анализ тренда
            recent_avg = np.mean(historical_data[-7:])
            older_avg = np.mean(historical_data[-14:-7]) if len(historical_data) >= 14 else recent_avg
            
            trend = 'increasing' if recent_avg > older_avg * 1.1 else 'decreasing' if recent_avg < older_avg * 0.9 else 'stable'
            
            # Сезонность (упрощенная)
            seasonality_factor = 1.0
            current_month = datetime.now().month
            if current_month in [12, 1, 2]:  # Зима
                seasonality_factor = 0.9
            elif current_month in [6, 7, 8]:  # Лето
                seasonality_factor = 1.1
            
            return MLForecast(
                predicted_consumption=recent_avg * seasonality_factor,
                confidence=0.8,
                trend=trend,
                seasonality_factor=seasonality_factor,
                next_month_forecast=recent_avg * 30 * seasonality_factor
            )
    
    async def analyze_intelligent_order(self, category_sku_data: List[Dict], 
                                      historical_data: Optional[Dict[str, List[float]]] = None) -> Dict:
        """Анализирует интеллектуальный заказ для категории товаров с ML-прогнозированием"""
        
        print(f"🧠 ИНТЕЛЛЕКТУАЛЬНЫЙ АНАЛИЗ ЗАКАЗА (ML-версия)")
        print(f"Количество SKU: {len(category_sku_data)}")
        print()
        
        # Загружаем ML-модели
        self.load_ml_models()
        
        # 1. Анализируем каждый SKU с ML-прогнозированием
        analyzed_skus = []
        for sku_data in category_sku_data:
            historical = historical_data.get(sku_data['code'], []) if historical_data else []
            analysis = await self.analyze_single_sku_ml(sku_data, historical)
            if analysis:
                analyzed_skus.append(analysis)
        
        # 2. Сортируем по приоритету (угроза OoS + ML-прогноз)
        analyzed_skus.sort(key=lambda x: x['priority_score'], reverse=True)
        
        # 3. Определяем категорию и минимальный заказ
        category_info = self.get_category_info(analyzed_skus[0]['product_code'])
        min_order = category_info['min_order']
        
        print(f"📦 МИНИМАЛЬНЫЙ ЗАКАЗ КАТЕГОРИИ: {min_order} ед.")
        print()
        
        # 4. Анализируем оптимизацию доставки
        delivery_optimization = self.analyze_delivery_optimization(analyzed_skus)
        
        # 5. Формируем интеллектуальный заказ
        optimal_order = self.build_intelligent_order_ml(analyzed_skus, min_order, delivery_optimization)
        
        return optimal_order
    
    async def analyze_single_sku_ml(self, sku_data: Dict, historical_data: List[float]) -> Optional[Dict]:
        """Анализирует один SKU с ML-прогнозированием"""
        product_code = sku_data['code']
        current_stock = sku_data['stock']
        daily_consumption = sku_data['consumption']
        diopter = sku_data.get('diopter', 0)
        
        # Получаем правила
        rules = self.product_rules.get_product_rules(product_code)
        if not rules:
            return None
        
        # Получаем ML-прогноз
        ml_forecast = await self.get_ml_forecast(product_code, historical_data)
        
        # Используем ML-прогноз для расчета потребления
        adjusted_consumption = ml_forecast.predicted_consumption
        
        # Рассчитываем дни до OoS с учетом ML-прогноза
        days_until_oos = int(current_stock / adjusted_consumption) if adjusted_consumption > 0 else 999
        
        # Рассчитываем необходимый запас с учетом ML-прогноза
        required_stock = self.product_rules.calculate_required_stock(product_code, adjusted_consumption, False)
        recommended_order = max(0, required_stock - current_stock)
        
        # Определяем приоритет с учетом ML-прогноза
        base_priority = 1000 - days_until_oos
        ml_confidence_bonus = ml_forecast.confidence * 100
        trend_bonus = 50 if ml_forecast.trend == 'increasing' else -20 if ml_forecast.trend == 'decreasing' else 0
        priority_score = base_priority + ml_confidence_bonus + trend_bonus
        
        # Определяем критичность с учетом ML-прогноза
        if days_until_oos <= 0:
            criticality = "CRITICAL"
        elif days_until_oos <= 7:
            criticality = "HIGH"
        elif days_until_oos <= 30:
            criticality = "MEDIUM"
        else:
            criticality = "LOW"
        
        # Добавляем информацию о ML-прогнозе
        ml_info = {
            'predicted_consumption': adjusted_consumption,
            'confidence': ml_forecast.confidence,
            'trend': ml_forecast.trend,
            'seasonality_factor': ml_forecast.seasonality_factor,
            'next_month_forecast': ml_forecast.next_month_forecast
        }
        
        return {
            'product_code': product_code,
            'diopter': diopter,
            'current_stock': current_stock,
            'daily_consumption': daily_consumption,
            'adjusted_consumption': adjusted_consumption,
            'days_until_oos': days_until_oos,
            'required_stock': required_stock,
            'recommended_order': recommended_order,
            'priority_score': priority_score,
            'criticality': criticality,
            'rules': rules,
            'ml_forecast': ml_info
        }
    
    def analyze_delivery_optimization(self, analyzed_skus: List[Dict]) -> DeliveryOptimization:
        """Анализирует возможность оптимизации доставки"""
        product_codes = [sku['product_code'] for sku in analyzed_skus]
        optimization = self.product_rules.get_delivery_optimization(product_codes)
        
        # Определяем рекомендуемую дату доставки
        delivery_date = datetime.now() + timedelta(days=57)  # Стандартный срок
        
        return DeliveryOptimization(
            can_combine=optimization['can_combine_delivery'],
            delivery_savings_days=optimization['delivery_savings_days'],
            recommended_delivery_date=delivery_date.strftime('%Y-%m-%d'),
            combined_products=product_codes if optimization['can_combine_delivery'] else [],
            separate_products=product_codes if not optimization['can_combine_delivery'] else []
        )
    
    def build_intelligent_order_ml(self, analyzed_skus: List[Dict], min_order: int, 
                                 delivery_optimization: DeliveryOptimization) -> Dict:
        """Строит интеллектуальный заказ с ML-прогнозированием"""
        
        print("🧠 ИНТЕЛЛЕКТУАЛЬНОЕ ФОРМИРОВАНИЕ ЗАКАЗА (ML-версия):")
        print("=" * 70)
        
        # Анализ оптимизации доставки
        print("🚚 АНАЛИЗ ОПТИМИЗАЦИИ ДОСТАВКИ:")
        if delivery_optimization.can_combine:
            print(f"  ✅ Может объединить доставку")
            print(f"  💰 Экономия: {delivery_optimization.delivery_savings_days} дней")
            print(f"  📦 Объединяемые товары: {len(delivery_optimization.combined_products)}")
        else:
            print(f"  ❌ Раздельная доставка")
        print()
        
        # Фильтруем SKU с угрозой OoS (с учетом ML-прогноза)
        critical_skus = [sku for sku in analyzed_skus if sku['days_until_oos'] <= 30]
        
        if not critical_skus:
            print("✅ Нет SKU с угрозой OoS - заказ не нужен")
            return {
                'order_needed': False,
                'reason': 'Нет угрозы OoS',
                'total_volume': 0,
                'sku_orders': [],
                'ml_insights': self.generate_ml_insights(analyzed_skus)
            }
        
        print(f"🚨 SKU с угрозой OoS: {len(critical_skus)}")
        for sku in critical_skus:
            ml_info = sku['ml_forecast']
            print(f"  {sku['product_code']} ({sku['diopter']:+.2f}): {sku['days_until_oos']} дней до OoS")
            print(f"    ML-прогноз: {ml_info['predicted_consumption']:.2f} ед/день (уверенность: {ml_info['confidence']:.1%})")
            print(f"    Тренд: {ml_info['trend']}, Сезонность: {ml_info['seasonality_factor']:.2f}")
        print()
        
        # Интеллектуальное формирование заказа с ML-учетом
        sku_orders = []
        remaining_volume = min_order
        current_date = 0
        
        print("📊 ДИНАМИЧЕСКОЕ ФОРМИРОВАНИЕ ЗАКАЗА (ML-версия):")
        print("-" * 50)
        
        while remaining_volume > 0:
            # Находим самый критичный SKU с учетом ML-прогноза
            current_sku = None
            for sku in critical_skus:
                if sku['days_until_oos'] <= current_date:
                    current_sku = sku
                    break
            
            if not current_sku:
                # Если нет критичных SKU, добавляем менее критичные с учетом ML-прогноза
                for sku in analyzed_skus:
                    if sku['days_until_oos'] > current_date and sku['recommended_order'] > 0:
                        current_sku = sku
                        break
            
            if not current_sku:
                break
            
            # Определяем объем для текущего SKU с учетом ML-прогноза
            needed_volume = min(current_sku['recommended_order'], remaining_volume)
            
            # Применяем кратность
            multiple = current_sku['rules']['multiple']
            if multiple > 1:
                needed_volume = ((needed_volume + multiple - 1) // multiple) * multiple
            
            # Ограничиваем оставшимся объемом
            final_volume = min(needed_volume, remaining_volume)
            
            if final_volume > 0:
                # Рассчитываем новую дату OoS с учетом заказа и ML-прогноза
                adjusted_consumption = current_sku['adjusted_consumption']
                new_oos_date = self.calculate_future_oos_date_ml(current_sku, final_volume, adjusted_consumption)
                
                sku_order = {
                    'product_code': current_sku['product_code'],
                    'diopter': current_sku['diopter'],
                    'volume': final_volume,
                    'days_until_oos': current_sku['days_until_oos'],
                    'new_oos_date': new_oos_date,
                    'criticality': current_sku['criticality'],
                    'coverage_days': final_volume / adjusted_consumption if adjusted_consumption > 0 else 0,
                    'ml_forecast': current_sku['ml_forecast']
                }
                sku_orders.append(sku_order)
                remaining_volume -= final_volume
                
                print(f"  ✅ {current_sku['product_code']} ({current_sku['diopter']:+.2f}): {final_volume} ед.")
                print(f"     Было дней до OoS: {current_sku['days_until_oos']}")
                print(f"     Станет дней до OoS: {new_oos_date}")
                print(f"     Покрытие: {sku_order['coverage_days']:.1f} дней")
                print(f"     ML-прогноз: {adjusted_consumption:.2f} ед/день")
                
                # Обновляем дату OoS для этого SKU
                current_sku['days_until_oos'] = new_oos_date
                current_date = new_oos_date
            else:
                break
        
        # Если остался объем, заполняем менее критичными SKU
        if remaining_volume > 0:
            print(f"\n📦 Осталось объема: {remaining_volume} ед.")
            print("Заполняем менее критичными SKU:")
            
            for sku in analyzed_skus:
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
                        adjusted_consumption = sku['adjusted_consumption']
                        new_oos_date = self.calculate_future_oos_date_ml(sku, final_volume, adjusted_consumption)
                        
                        sku_order = {
                            'product_code': sku['product_code'],
                            'diopter': sku['diopter'],
                            'volume': final_volume,
                            'days_until_oos': sku['days_until_oos'],
                            'new_oos_date': new_oos_date,
                            'criticality': sku['criticality'],
                            'coverage_days': final_volume / adjusted_consumption if adjusted_consumption > 0 else 0,
                            'ml_forecast': sku['ml_forecast']
                        }
                        sku_orders.append(sku_order)
                        remaining_volume -= final_volume
                        
                        print(f"  ✅ {sku['product_code']} ({sku['diopter']:+.2f}): {final_volume} ед.")
                        print(f"     Покрытие: {sku_order['coverage_days']:.1f} дней")
                        print(f"     ML-прогноз: {adjusted_consumption:.2f} ед/день")
        
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
            'delivery_date': delivery_optimization.recommended_delivery_date,
            'delivery_optimization': {
                'can_combine': delivery_optimization.can_combine,
                'savings_days': delivery_optimization.delivery_savings_days,
                'combined_products': delivery_optimization.combined_products,
                'separate_products': delivery_optimization.separate_products
            },
            'ml_insights': self.generate_ml_insights(analyzed_skus)
        }
    
    def calculate_future_oos_date_ml(self, sku: Dict, additional_stock: int, adjusted_consumption: float) -> int:
        """Рассчитывает дату OoS с учетом дополнительного запаса и ML-прогноза"""
        total_stock = sku['current_stock'] + additional_stock
        if adjusted_consumption <= 0:
            return 999
        return int(total_stock / adjusted_consumption)
    
    def generate_ml_insights(self, analyzed_skus: List[Dict]) -> Dict:
        """Генерирует инсайты на основе ML-анализа"""
        insights = {
            'trends': {},
            'seasonality_impact': {},
            'confidence_levels': {},
            'recommendations': []
        }
        
        # Анализируем тренды
        trends = {}
        for sku in analyzed_skus:
            ml_info = sku['ml_forecast']
            trend = ml_info['trend']
            if trend not in trends:
                trends[trend] = []
            trends[trend].append(sku['product_code'])
        
        insights['trends'] = trends
        
        # Анализируем сезонность
        seasonality_impact = {}
        for sku in analyzed_skus:
            ml_info = sku['ml_forecast']
            factor = ml_info['seasonality_factor']
            if factor > 1.05:
                seasonality_impact['increasing'] = seasonality_impact.get('increasing', []) + [sku['product_code']]
            elif factor < 0.95:
                seasonality_impact['decreasing'] = seasonality_impact.get('decreasing', []) + [sku['product_code']]
        
        insights['seasonality_impact'] = seasonality_impact
        
        # Анализируем уровни уверенности
        high_confidence = [sku['product_code'] for sku in analyzed_skus if sku['ml_forecast']['confidence'] > 0.8]
        low_confidence = [sku['product_code'] for sku in analyzed_skus if sku['ml_forecast']['confidence'] < 0.5]
        
        insights['confidence_levels'] = {
            'high': high_confidence,
            'low': low_confidence
        }
        
        # Генерируем рекомендации
        recommendations = []
        
        if len(trends.get('increasing', [])) > len(analyzed_skus) * 0.3:
            recommendations.append("Рекомендуется увеличить заказы для растущих товаров")
        
        if len(seasonality_impact.get('increasing', [])) > 0:
            recommendations.append("Учитывайте сезонный рост спроса")
        
        if len(low_confidence) > 0:
            recommendations.append("Необходимо больше данных для точного прогнозирования")
        
        insights['recommendations'] = recommendations
        
        return insights
    
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

async def main():
    """Тестирование интеллектуального оптимизатора с ML-интеграцией"""
    
    # Тестовые данные (ваш пример)
    test_data = [
        {'code': '30001', 'stock': 385, 'consumption': 1, 'diopter': -0.5},
        {'code': '30002', 'stock': 154, 'consumption': 1, 'diopter': -0.75},
        {'code': '30003', 'stock': 103, 'consumption': 1, 'diopter': -1.00},
        {'code': '30004', 'stock': 80, 'consumption': 1, 'diopter': -1.25},
        {'code': '30005', 'stock': 5, 'consumption': 1, 'diopter': -1.50},
    ]
    
    # Исторические данные для ML-прогнозирования
    historical_data = {
        '30001': [1.2, 1.1, 1.3, 1.0, 1.2, 1.4, 1.1, 1.3, 1.2, 1.1, 1.3, 1.2, 1.4, 1.1],
        '30002': [0.8, 0.9, 1.0, 0.8, 0.9, 1.1, 0.8, 0.9, 1.0, 0.8, 0.9, 1.1, 0.8, 0.9],
        '30003': [1.0, 1.1, 1.0, 1.2, 1.0, 1.1, 1.0, 1.2, 1.0, 1.1, 1.0, 1.2, 1.0, 1.1],
        '30004': [0.7, 0.8, 0.7, 0.9, 0.7, 0.8, 0.7, 0.9, 0.7, 0.8, 0.7, 0.9, 0.7, 0.8],
        '30005': [0.5, 0.6, 0.5, 0.7, 0.5, 0.6, 0.5, 0.7, 0.5, 0.6, 0.5, 0.7, 0.5, 0.6],
    }
    
    optimizer = IntelligentOrderOptimizer()
    result = await optimizer.analyze_intelligent_order(test_data, historical_data)
    
    print("\n" + "=" * 70)
    print("📋 РЕЗУЛЬТАТ ИНТЕЛЛЕКТУАЛЬНОЙ ОПТИМИЗАЦИИ (ML-версия):")
    print("=" * 70)
    
    if result['order_needed']:
        print(f"✅ Заказ НУЖЕН")
        print(f"📦 Общий объем: {result['total_volume']} ед.")
        print(f"📅 Дата заказа: {result['order_date']}")
        print(f"🚚 Дата поставки: {result['delivery_date']}")
        print(f"📊 Использование: {result['utilization']:.1f}%")
        
        # Информация об оптимизации доставки
        delivery_opt = result.get('delivery_optimization', {})
        if delivery_opt.get('can_combine'):
            print(f"🚚 Оптимизация доставки: ✅ Объединенная доставка")
            print(f"💰 Экономия: {delivery_opt.get('savings_days', 0)} дней")
        else:
            print(f"🚚 Оптимизация доставки: ❌ Раздельная доставка")
        
        print("\n📋 ДЕТАЛИ ЗАКАЗА:")
        for order in result['sku_orders']:
            print(f"  {order['product_code']} ({order['diopter']:+.2f}): {order['volume']} ед.")
            print(f"    Критичность: {order['criticality']}")
            print(f"    Покрытие: {order['coverage_days']:.1f} дней")
            print(f"    Было дней до OoS: {order['days_until_oos']}")
            print(f"    Станет дней до OoS: {order['new_oos_date']}")
            
            # ML-информация
            ml_info = order.get('ml_forecast', {})
            if ml_info:
                print(f"    ML-прогноз: {ml_info.get('predicted_consumption', 0):.2f} ед/день")
                print(f"    Уверенность: {ml_info.get('confidence', 0):.1%}")
                print(f"    Тренд: {ml_info.get('trend', 'stable')}")
        
        # ML-инсайты
        ml_insights = result.get('ml_insights', {})
        if ml_insights:
            print("\n🧠 ML-ИНСАЙТЫ:")
            
            trends = ml_insights.get('trends', {})
            if trends:
                print("📈 Тренды:")
                for trend, products in trends.items():
                    print(f"  {trend}: {', '.join(products)}")
            
            seasonality = ml_insights.get('seasonality_impact', {})
            if seasonality:
                print("🌍 Сезонность:")
                for impact, products in seasonality.items():
                    print(f"  {impact}: {', '.join(products)}")
            
            confidence = ml_insights.get('confidence_levels', {})
            if confidence:
                print("🎯 Уверенность прогнозов:")
                high_conf = confidence.get('high', [])
                low_conf = confidence.get('low', [])
                if high_conf:
                    print(f"  Высокая: {', '.join(high_conf)}")
                if low_conf:
                    print(f"  Низкая: {', '.join(low_conf)}")
            
            recommendations = ml_insights.get('recommendations', [])
            if recommendations:
                print("💡 Рекомендации:")
                for rec in recommendations:
                    print(f"  • {rec}")
    else:
        print(f"❌ Заказ НЕ НУЖЕН")
        print(f"Причина: {result['reason']}")
        
        # Показываем ML-инсайты даже если заказ не нужен
        ml_insights = result.get('ml_insights', {})
        if ml_insights:
            print("\n🧠 ML-ИНСАЙТЫ:")
            trends = ml_insights.get('trends', {})
            if trends:
                print("📈 Тренды:")
                for trend, products in trends.items():
                    print(f"  {trend}: {', '.join(products)}")

if __name__ == "__main__":
    asyncio.run(main()) 