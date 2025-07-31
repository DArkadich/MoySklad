#!/usr/bin/env python3
"""
Тестирование различных вариантов API запросов для получения исторических остатков
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

async def test_stock_endpoints():
    """Тестирует различные варианты получения остатков"""
    
    test_date = "2024-01-01"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Тест 1: Текущие остатки
        print("=== ТЕСТ 1: Текущие остатки ===")
        try:
            resp = await client.get(f"{MOYSKLAD_API_URL}/report/stock/all", headers=HEADERS)
            print(f"Статус: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Найдено товаров: {len(data.get('rows', []))}")
            else:
                print(f"Ошибка: {resp.text}")
        except Exception as e:
            print(f"Ошибка: {e}")
        
        print()
        
        # Тест 2: Исторические остатки с moment
        print("=== ТЕСТ 2: Исторические остатки с moment ===")
        try:
            params = {"moment": f"{test_date}T00:00:00"}
            resp = await client.get(f"{MOYSKLAD_API_URL}/report/stock/all", headers=HEADERS, params=params)
            print(f"Статус: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Найдено товаров: {len(data.get('rows', []))}")
            else:
                print(f"Ошибка: {resp.text}")
        except Exception as e:
            print(f"Ошибка: {e}")
        
        print()
        
        # Тест 3: Остатки по складам
        print("=== ТЕСТ 3: Остатки по складам ===")
        try:
            resp = await client.get(f"{MOYSKLAD_API_URL}/report/stock/bystore", headers=HEADERS)
            print(f"Статус: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Найдено складов: {len(data.get('rows', []))}")
            else:
                print(f"Ошибка: {resp.text}")
        except Exception as e:
            print(f"Ошибка: {e}")
        
        print()
        
        # Тест 4: Исторические остатки по складам
        print("=== ТЕСТ 4: Исторические остатки по складам ===")
        try:
            params = {"moment": f"{test_date}T00:00:00"}
            resp = await client.get(f"{MOYSKLAD_API_URL}/report/stock/bystore", headers=HEADERS, params=params)
            print(f"Статус: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Найдено складов: {len(data.get('rows', []))}")
            else:
                print(f"Ошибка: {resp.text}")
        except Exception as e:
            print(f"Ошибка: {e}")
        
        print()
        
        # Тест 5: Остатки с фильтром по товару
        print("=== ТЕСТ 5: Остатки с фильтром по товару ===")
        try:
            # Сначала получим список товаров
            resp = await client.get(f"{MOYSKLAD_API_URL}/entity/assortment", headers=HEADERS, params={"limit": 1})
            if resp.status_code == 200:
                data = resp.json()
                if data.get('rows'):
                    product_id = data['rows'][0]['id']
                    params = {"filter": f"assortmentId={product_id}"}
                    resp = await client.get(f"{MOYSKLAD_API_URL}/report/stock/all", headers=HEADERS, params=params)
                    print(f"Статус: {resp.status_code}")
                    if resp.status_code == 200:
                        data = resp.json()
                        print(f"Найдено позиций: {len(data.get('rows', []))}")
                    else:
                        print(f"Ошибка: {resp.text}")
        except Exception as e:
            print(f"Ошибка: {e}")
        
        print()
        
        # Тест 6: Проверка прав доступа
        print("=== ТЕСТ 6: Проверка прав доступа ===")
        try:
            resp = await client.get(f"{MOYSKLAD_API_URL}/entity/organization", headers=HEADERS)
            print(f"Статус: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Организация: {data.get('rows', [{}])[0].get('name', 'Неизвестно')}")
            else:
                print(f"Ошибка: {resp.text}")
        except Exception as e:
            print(f"Ошибка: {e}")

async def main():
    print("Тестирование API МойСклад для получения исторических остатков...")
    print(f"Дата тестирования: 2024-01-01")
    print(f"API URL: {MOYSKLAD_API_URL}")
    print()
    
    await test_stock_endpoints()
    
    print("Тестирование завершено!")

if __name__ == "__main__":
    asyncio.run(main()) 