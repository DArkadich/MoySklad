#!/usr/bin/env python3
"""
Скрипт для тестирования системы Horiens Purchase Agent
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, List

class SystemTester:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.services = {
            "api-gateway": "http://localhost:8000",
            "purchase-service": "http://localhost:8001", 
            "ml-service": "http://localhost:8002",
            "moysklad-service": "http://localhost:8003",
            "notification-service": "http://localhost:8004",
            "analytics-service": "http://localhost:8005"
        }
    
    async def test_service_health(self, service_name: str, url: str) -> Dict:
        """Тест здоровья сервиса"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{url}/health")
                if response.status_code == 200:
                    return {
                        "service": service_name,
                        "status": "healthy",
                        "response": response.json()
                    }
                else:
                    return {
                        "service": service_name,
                        "status": "unhealthy",
                        "error": f"HTTP {response.status_code}"
                    }
        except Exception as e:
            return {
                "service": service_name,
                "status": "error",
                "error": str(e)
            }
    
    async def test_all_services(self) -> List[Dict]:
        """Тест всех сервисов"""
        print("🔍 Тестирование здоровья сервисов...")
        results = []
        
        for service_name, url in self.services.items():
            result = await self.test_service_health(service_name, url)
            results.append(result)
            status_icon = "✅" if result["status"] == "healthy" else "❌"
            print(f"{status_icon} {service_name}: {result['status']}")
        
        return results
    
    async def test_purchase_endpoints(self) -> Dict:
        """Тест эндпоинтов закупок"""
        print("\n🛒 Тестирование эндпоинтов закупок...")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Тест получения продуктов
            try:
                response = await client.get(f"{self.base_url}/api/v1/products")
                if response.status_code == 200:
                    print("✅ GET /api/v1/products - успешно")
                else:
                    print(f"❌ GET /api/v1/products - ошибка {response.status_code}")
            except Exception as e:
                print(f"❌ GET /api/v1/products - ошибка: {e}")
            
            # Тест получения статуса склада
            try:
                response = await client.get(f"{self.base_url}/api/v1/inventory/status")
                if response.status_code == 200:
                    print("✅ GET /api/v1/inventory/status - успешно")
                else:
                    print(f"❌ GET /api/v1/inventory/status - ошибка {response.status_code}")
            except Exception as e:
                print(f"❌ GET /api/v1/inventory/status - ошибка: {e}")
            
            # Тест получения рекомендаций
            try:
                response = await client.get(f"{self.base_url}/api/v1/purchase/recommendations")
                if response.status_code == 200:
                    print("✅ GET /api/v1/purchase/recommendations - успешно")
                else:
                    print(f"❌ GET /api/v1/purchase/recommendations - ошибка {response.status_code}")
            except Exception as e:
                print(f"❌ GET /api/v1/purchase/recommendations - ошибка: {e}")
    
    async def test_ml_endpoints(self) -> Dict:
        """Тест ML эндпоинтов"""
        print("\n🤖 Тестирование ML эндпоинтов...")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Тест прогнозирования
            try:
                response = await client.get(f"{self.base_url}/api/v1/ml/forecast/test-product")
                if response.status_code == 200:
                    print("✅ GET /api/v1/ml/forecast/{product_id} - успешно")
                else:
                    print(f"❌ GET /api/v1/ml/forecast/{product_id} - ошибка {response.status_code}")
            except Exception as e:
                print(f"❌ GET /api/v1/ml/forecast/{product_id} - ошибка: {e}")
    
    async def test_analytics_endpoints(self) -> Dict:
        """Тест аналитических эндпоинтов"""
        print("\n📊 Тестирование аналитических эндпоинтов...")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Тест дашборда
            try:
                response = await client.get(f"{self.base_url}/api/v1/analytics/dashboard/summary")
                if response.status_code == 200:
                    print("✅ GET /api/v1/analytics/dashboard/summary - успешно")
                else:
                    print(f"❌ GET /api/v1/analytics/dashboard/summary - ошибка {response.status_code}")
            except Exception as e:
                print(f"❌ GET /api/v1/analytics/dashboard/summary - ошибка: {e}")
    
    async def test_notification_endpoints(self) -> Dict:
        """Тест эндпоинтов уведомлений"""
        print("\n📱 Тестирование эндпоинтов уведомлений...")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Тест отправки уведомления
            try:
                test_data = {
                    "type": "telegram",
                    "message": "🧪 Тестовое уведомление от системы Horiens Purchase Agent",
                    "recipients": []
                }
                response = await client.post(
                    f"{self.base_url}/api/v1/notifications/send",
                    json=test_data
                )
                if response.status_code == 200:
                    print("✅ POST /api/v1/notifications/send - успешно")
                else:
                    print(f"❌ POST /api/v1/notifications/send - ошибка {response.status_code}")
            except Exception as e:
                print(f"❌ POST /api/v1/notifications/send - ошибка: {e}")
    
    async def run_full_test(self):
        """Запуск полного тестирования системы"""
        print("🚀 Запуск тестирования системы Horiens Purchase Agent")
        print("=" * 60)
        
        # Тест здоровья сервисов
        health_results = await self.test_all_services()
        
        # Подсчет результатов
        healthy_count = sum(1 for r in health_results if r["status"] == "healthy")
        total_count = len(health_results)
        
        print(f"\n📈 Результаты тестирования здоровья сервисов:")
        print(f"✅ Здоровых сервисов: {healthy_count}/{total_count}")
        
        if healthy_count == total_count:
            print("🎉 Все сервисы работают корректно!")
            
            # Тест функциональности
            await self.test_purchase_endpoints()
            await self.test_ml_endpoints()
            await self.test_analytics_endpoints()
            await self.test_notification_endpoints()
            
            print("\n🎯 Тестирование завершено успешно!")
        else:
            print("⚠️  Некоторые сервисы недоступны. Проверьте логи Docker.")
        
        print("\n📋 Доступные URL:")
        print(f"🌐 API Gateway: http://localhost:8000")
        print(f"📊 Grafana Dashboard: http://localhost:3000 (admin/admin)")
        print(f"🐰 RabbitMQ Management: http://localhost:15672 (guest/guest)")
        print(f"📈 Prometheus: http://localhost:9090")

async def main():
    """Основная функция"""
    tester = SystemTester()
    await tester.run_full_test()

if __name__ == "__main__":
    asyncio.run(main()) 