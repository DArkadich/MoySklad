#!/usr/bin/env python3
"""
Тестирование интеллектуального оптимизатора заказов
"""

import asyncio
import json
from datetime import datetime
from services.moysklad_service.app.intelligent_order_optimizer import IntelligentOrderOptimizer

async def test_intelligent_optimizer():
    """Тестирование интеллектуального оптимизатора"""
    
    print("🧪 ТЕСТИРОВАНИЕ ИНТЕЛЛЕКТУАЛЬНОГО ОПТИМИЗАТОРА")
    print("=" * 60)
    
    # Тестовые данные
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
    
    try:
        # Создаем оптимизатор
        optimizer = IntelligentOrderOptimizer()
        
        print("📊 Анализ данных:")
        print(f"  Количество SKU: {len(test_data)}")
        print(f"  Исторические данные: {len(historical_data)} товаров")
        print()
        
        # Выполняем оптимизацию
        print("🔄 Выполнение оптимизации...")
        result = await optimizer.analyze_intelligent_order(test_data, historical_data)
        
        # Выводим результаты
        print("\n" + "=" * 60)
        print("📋 РЕЗУЛЬТАТЫ ОПТИМИЗАЦИИ:")
        print("=" * 60)
        
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
        
        # Сохраняем результаты в файл
        with open('intelligent_optimizer_results.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n💾 Результаты сохранены в файл: intelligent_optimizer_results.json")
        
        return result
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return None

async def test_api_endpoint():
    """Тестирование API endpoint"""
    
    print("\n🌐 ТЕСТИРОВАНИЕ API ENDPOINT")
    print("=" * 40)
    
    try:
        import httpx
        
        # Тестовые данные для API
        test_request = {
            "sku_data": [
                {"code": "30001", "stock": 385, "consumption": 1, "diopter": -0.5},
                {"code": "30002", "stock": 154, "consumption": 1, "diopter": -0.75},
                {"code": "30003", "stock": 103, "consumption": 1, "diopter": -1.00},
                {"code": "30004", "stock": 80, "consumption": 1, "diopter": -1.25},
                {"code": "30005", "stock": 5, "consumption": 1, "diopter": -1.50},
            ],
            "historical_data": [
                {
                    "product_code": "30001",
                    "consumption_history": [1.2, 1.1, 1.3, 1.0, 1.2, 1.4, 1.1, 1.3, 1.2, 1.1, 1.3, 1.2, 1.4, 1.1]
                },
                {
                    "product_code": "30002",
                    "consumption_history": [0.8, 0.9, 1.0, 0.8, 0.9, 1.1, 0.8, 0.9, 1.0, 0.8, 0.9, 1.1, 0.8, 0.9]
                },
                {
                    "product_code": "30003",
                    "consumption_history": [1.0, 1.1, 1.0, 1.2, 1.0, 1.1, 1.0, 1.2, 1.0, 1.1, 1.0, 1.2, 1.0, 1.1]
                },
                {
                    "product_code": "30004",
                    "consumption_history": [0.7, 0.8, 0.7, 0.9, 0.7, 0.8, 0.7, 0.9, 0.7, 0.8, 0.7, 0.9, 0.7, 0.8]
                },
                {
                    "product_code": "30005",
                    "consumption_history": [0.5, 0.6, 0.5, 0.7, 0.5, 0.6, 0.5, 0.7, 0.5, 0.6, 0.5, 0.7, 0.5, 0.6]
                }
            ],
            "ml_forecasting": True,
            "delivery_optimization": True
        }
        
        # Отправляем запрос к API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/optimize",
                json=test_request,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ API запрос выполнен успешно")
                print(f"📦 Общий объем: {result.get('total_volume', 0)} ед.")
                print(f"📊 Использование: {result.get('utilization', 0):.1f}%")
                print(f"⏱️ Время обработки: {result.get('processing_time', 0):.2f} сек")
                
                # Сохраняем результаты API
                with open('api_optimizer_results.json', 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2, default=str)
                
                print(f"💾 Результаты API сохранены в файл: api_optimizer_results.json")
                
                return result
            else:
                print(f"❌ API вернул ошибку: {response.status_code}")
                print(f"Ответ: {response.text}")
                return None
                
    except Exception as e:
        print(f"❌ Ошибка тестирования API: {e}")
        return None

async def main():
    """Основная функция тестирования"""
    
    print("🚀 ЗАПУСК ТЕСТИРОВАНИЯ ИНТЕЛЛЕКТУАЛЬНОГО ОПТИМИЗАТОРА")
    print("=" * 70)
    
    # Тестируем оптимизатор
    result = await test_intelligent_optimizer()
    
    if result:
        print("\n✅ Тестирование оптимизатора завершено успешно")
    else:
        print("\n❌ Тестирование оптимизатора завершено с ошибками")
    
    # Тестируем API (если сервис запущен)
    print("\n" + "=" * 70)
    api_result = await test_api_endpoint()
    
    if api_result:
        print("\n✅ Тестирование API завершено успешно")
    else:
        print("\n❌ Тестирование API завершено с ошибками")
    
    print("\n" + "=" * 70)
    print("🏁 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")

if __name__ == "__main__":
    asyncio.run(main()) 