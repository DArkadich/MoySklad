#!/usr/bin/env python3
"""
Тестирование API продаж МойСклад
"""

import asyncio
import httpx
import os
from datetime import datetime

# Настройки API
MOYSKLAD_API_URL = "https://api.moysklad.ru/api/remap/1.2"
MOYSKLAD_API_TOKEN = os.getenv('MOYSKLAD_API_TOKEN')

if not MOYSKLAD_API_TOKEN:
    raise ValueError("MOYSKLAD_API_TOKEN не установлен")

HEADERS = {
    "Authorization": f"Bearer {MOYSKLAD_API_TOKEN}",
    "Content-Type": "application/json"
}

async def test_sales_endpoints():
    """Тестирует API продаж"""
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Тест 1: Документы продаж (demand)
        print("=== ТЕСТ 1: Документы продаж (demand) ===")
        try:
            params = {
                "momentFrom": "2024-01-01T00:00:00",
                "momentTo": "2024-01-31T23:59:59",
                "limit": 10
            }
            resp = await client.get(f"{MOYSKLAD_API_URL}/entity/demand", headers=HEADERS, params=params)
            print(f"Статус: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Найдено документов: {len(data.get('rows', []))}")
            else:
                print(f"Ошибка: {resp.text}")
        except Exception as e:
            print(f"Ошибка: {e}")
        
        print()
        
        # Тест 2: Товары (assortment)
        print("=== ТЕСТ 2: Товары (assortment) ===")
        try:
            params = {"limit": 10}
            resp = await client.get(f"{MOYSKLAD_API_URL}/entity/assortment", headers=HEADERS, params=params)
            print(f"Статус: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Найдено товаров: {len(data.get('rows', []))}")
                if data.get('rows'):
                    first_product = data['rows'][0]
                    print(f"Первый товар: {first_product.get('name', 'Неизвестно')} (код: {first_product.get('code', 'Нет кода')})")
            else:
                print(f"Ошибка: {resp.text}")
        except Exception as e:
            print(f"Ошибка: {e}")
        
        print()
        
        # Тест 3: Организация
        print("=== ТЕСТ 3: Организация ===")
        try:
            resp = await client.get(f"{MOYSKLAD_API_URL}/entity/organization", headers=HEADERS)
            print(f"Статус: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Найдено организаций: {len(data.get('rows', []))}")
                if data.get('rows'):
                    org = data['rows'][0]
                    print(f"Организация: {org.get('name', 'Неизвестно')}")
            else:
                print(f"Ошибка: {resp.text}")
        except Exception as e:
            print(f"Ошибка: {e}")
        
        print()
        
        # Тест 4: Токен
        print("=== ТЕСТ 4: Проверка токена ===")
        print(f"Токен: {MOYSKLAD_API_TOKEN[:10]}...{MOYSKLAD_API_TOKEN[-10:]}")
        print(f"Длина токена: {len(MOYSKLAD_API_TOKEN)} символов")

async def main():
    print("Тестирование API продаж МойСклад...")
    print(f"API URL: {MOYSKLAD_API_URL}")
    print()
    
    await test_sales_endpoints()
    
    print("Тестирование завершено!")

if __name__ == "__main__":
    asyncio.run(main()) 