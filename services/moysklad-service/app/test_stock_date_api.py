#!/usr/bin/env python3
"""
Тестирование API отчетов по остаткам на конкретную дату
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

async def test_stock_date_endpoints():
    """Тестирует API остатков на конкретную дату"""
    
    test_date = "2024-01-01"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Тест 1: Остатки на дату через moment
        print("=== ТЕСТ 1: Остатки на дату через moment ===")
        try:
            params = {"moment": f"{test_date}T00:00:00"}
            resp = await client.get(f"{MOYSKLAD_API_URL}/report/stock/all", headers=HEADERS, params=params)
            print(f"Статус: {resp.status_code}")
            print(f"URL: {resp.url}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Найдено товаров: {len(data.get('rows', []))}")
            else:
                print(f"Ошибка: {resp.text}")
        except Exception as e:
            print(f"Ошибка: {e}")
        
        print()
        
        # Тест 2: Остатки на дату через momentFrom/momentTo
        print("=== ТЕСТ 2: Остатки на дату через momentFrom/momentTo ===")
        try:
            params = {
                "momentFrom": f"{test_date}T00:00:00",
                "momentTo": f"{test_date}T23:59:59"
            }
            resp = await client.get(f"{MOYSKLAD_API_URL}/report/stock/all", headers=HEADERS, params=params)
            print(f"Статус: {resp.status_code}")
            print(f"URL: {resp.url}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Найдено товаров: {len(data.get('rows', []))}")
            else:
                print(f"Ошибка: {resp.text}")
        except Exception as e:
            print(f"Ошибка: {e}")
        
        print()
        
        # Тест 3: Остатки по складам на дату
        print("=== ТЕСТ 3: Остатки по складам на дату ===")
        try:
            params = {"moment": f"{test_date}T00:00:00"}
            resp = await client.get(f"{MOYSKLAD_API_URL}/report/stock/bystore", headers=HEADERS, params=params)
            print(f"Статус: {resp.status_code}")
            print(f"URL: {resp.url}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Найдено складов: {len(data.get('rows', []))}")
            else:
                print(f"Ошибка: {resp.text}")
        except Exception as e:
            print(f"Ошибка: {e}")
        
        print()
        
        # Тест 4: Остатки на дату с фильтром по товару
        print("=== ТЕСТ 4: Остатки на дату с фильтром по товару ===")
        try:
            # Сначала получим товар
            resp = await client.get(f"{MOYSKLAD_API_URL}/entity/assortment", headers=HEADERS, params={"limit": 1})
            if resp.status_code == 200:
                data = resp.json()
                if data.get('rows'):
                    product_id = data['rows'][0]['id']
                    print(f"Тестируем товар ID: {product_id}")
                    
                    # Остатки товара на дату
                    params = {
                        "moment": f"{test_date}T00:00:00",
                        "filter": f"assortmentId={product_id}"
                    }
                    resp = await client.get(f"{MOYSKLAD_API_URL}/report/stock/all", headers=HEADERS, params=params)
                    print(f"Статус: {resp.status_code}")
                    print(f"URL: {resp.url}")
                    if resp.status_code == 200:
                        stock_data = resp.json()
                        print(f"Найдено позиций: {len(stock_data.get('rows', []))}")
                    else:
                        print(f"Ошибка: {resp.text}")
        except Exception as e:
            print(f"Ошибка: {e}")
        
        print()
        
        # Тест 5: Остатки на дату по складу
        print("=== ТЕСТ 5: Остатки на дату по складу ===")
        try:
            # Сначала получим склады
            resp = await client.get(f"{MOYSKLAD_API_URL}/entity/store", headers=HEADERS)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('rows'):
                    store_id = data['rows'][0]['id']
                    print(f"Тестируем склад ID: {store_id}")
                    
                    # Остатки по складу на дату
                    params = {
                        "moment": f"{test_date}T00:00:00",
                        "storeId": store_id
                    }
                    resp = await client.get(f"{MOYSKLAD_API_URL}/report/stock/all", headers=HEADERS, params=params)
                    print(f"Статус: {resp.status_code}")
                    print(f"URL: {resp.url}")
                    if resp.status_code == 200:
                        stock_data = resp.json()
                        print(f"Найдено позиций: {len(stock_data.get('rows', []))}")
                    else:
                        print(f"Ошибка: {resp.text}")
        except Exception as e:
            print(f"Ошибка: {e}")
        
        print()
        
        # Тест 6: Различные форматы даты
        print("=== ТЕСТ 6: Различные форматы даты ===")
        date_formats = [
            f"{test_date}T00:00:00",
            f"{test_date}T00:00:00.000",
            f"{test_date}",
            f"{test_date}T00:00:00Z"
        ]
        
        for i, date_format in enumerate(date_formats, 1):
            try:
                params = {"moment": date_format}
                resp = await client.get(f"{MOYSKLAD_API_URL}/report/stock/all", headers=HEADERS, params=params)
                print(f"Формат {i} ({date_format}): {resp.status_code}")
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"  Найдено товаров: {len(data.get('rows', []))}")
            except Exception as e:
                print(f"  Ошибка: {e}")

async def main():
    print("Тестирование API отчетов по остаткам на конкретную дату...")
    print(f"Тестовая дата: {test_date}")
    print(f"API URL: {MOYSKLAD_API_URL}")
    print()
    
    await test_stock_date_endpoints()
    
    print("Тестирование завершено!")

if __name__ == "__main__":
    asyncio.run(main()) 