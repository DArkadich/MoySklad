#!/usr/bin/env python3
"""
Тестирование альтернативных эндпоинтов API для получения остатков
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

async def test_alternative_endpoints():
    """Тестирует альтернативные эндпоинты для остатков"""
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Тест 1: Остатки по складам (bystore)
        print("=== ТЕСТ 1: Остатки по складам (bystore) ===")
        try:
            resp = await client.get(f"{MOYSKLAD_API_URL}/report/stock/bystore", headers=HEADERS)
            print(f"Статус: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Найдено складов: {len(data.get('rows', []))}")
                if data.get('rows'):
                    first_store = data['rows'][0]
                    print(f"Первый склад: {first_store.get('name', 'Неизвестно')}")
            else:
                print(f"Ошибка: {resp.text}")
        except Exception as e:
            print(f"Ошибка: {e}")
        
        print()
        
        # Тест 2: Товары с остатками через assortment
        print("=== ТЕСТ 2: Товары с остатками через assortment ===")
        try:
            params = {"limit": 10}
            resp = await client.get(f"{MOYSKLAD_API_URL}/entity/assortment", headers=HEADERS, params=params)
            print(f"Статус: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Найдено товаров: {len(data.get('rows', []))}")
                if data.get('rows'):
                    first_product = data['rows'][0]
                    print(f"Первый товар: {first_product.get('name', 'Неизвестно')}")
                    print(f"Код: {first_product.get('code', 'Нет кода')}")
                    print(f"ID: {first_product.get('id', 'Нет ID')}")
            else:
                print(f"Ошибка: {resp.text}")
        except Exception as e:
            print(f"Ошибка: {e}")
        
        print()
        
        # Тест 3: Остатки конкретного товара
        print("=== ТЕСТ 3: Остатки конкретного товара ===")
        try:
            # Сначала получим товар
            resp = await client.get(f"{MOYSKLAD_API_URL}/entity/assortment", headers=HEADERS, params={"limit": 1})
            if resp.status_code == 200:
                data = resp.json()
                if data.get('rows'):
                    product_id = data['rows'][0]['id']
                    print(f"Тестируем товар ID: {product_id}")
                    
                    # Пробуем получить остатки этого товара
                    params = {"filter": f"assortmentId={product_id}"}
                    resp = await client.get(f"{MOYSKLAD_API_URL}/report/stock/all", headers=HEADERS, params=params)
                    print(f"Статус остатков: {resp.status_code}")
                    if resp.status_code == 200:
                        stock_data = resp.json()
                        print(f"Найдено позиций остатков: {len(stock_data.get('rows', []))}")
                    else:
                        print(f"Ошибка остатков: {resp.text}")
        except Exception as e:
            print(f"Ошибка: {e}")
        
        print()
        
        # Тест 4: Остатки по складу
        print("=== ТЕСТ 4: Остатки по складу ===")
        try:
            # Сначала получим склады
            resp = await client.get(f"{MOYSKLAD_API_URL}/entity/store", headers=HEADERS)
            print(f"Статус складов: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Найдено складов: {len(data.get('rows', []))}")
                if data.get('rows'):
                    store_id = data['rows'][0]['id']
                    print(f"Тестируем склад ID: {store_id}")
                    
                    # Пробуем получить остатки по складу
                    params = {"storeId": store_id}
                    resp = await client.get(f"{MOYSKLAD_API_URL}/report/stock/all", headers=HEADERS, params=params)
                    print(f"Статус остатков по складу: {resp.status_code}")
                    if resp.status_code == 200:
                        stock_data = resp.json()
                        print(f"Найдено позиций на складе: {len(stock_data.get('rows', []))}")
                    else:
                        print(f"Ошибка остатков по складу: {resp.text}")
        except Exception as e:
            print(f"Ошибка: {e}")
        
        print()
        
        # Тест 5: Отчеты
        print("=== ТЕСТ 5: Отчеты ===")
        try:
            resp = await client.get(f"{MOYSKLAD_API_URL}/report", headers=HEADERS)
            print(f"Статус отчетов: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Доступные отчеты: {data}")
            else:
                print(f"Ошибка отчетов: {resp.text}")
        except Exception as e:
            print(f"Ошибка: {e}")

async def main():
    print("Тестирование альтернативных эндпоинтов API для остатков...")
    print(f"API URL: {MOYSKLAD_API_URL}")
    print()
    
    await test_alternative_endpoints()
    
    print("Тестирование завершено!")

if __name__ == "__main__":
    asyncio.run(main()) 