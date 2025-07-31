#!/usr/bin/env python3
"""
Тестирование расширенного отчета об остатках с фильтром moment
Документация: https://dev.moysklad.ru/doc/api/remap/1.2/reports/#otchety-otchet-ostatki-rasshirennyj-otchet-ob-ostatkah

ВАЖНО: Добавлены задержки для избежания блокировки API
- Пауза 1 секунда между тестами
- Обработка ошибок 429 и 403
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

async def make_api_request(client: httpx.AsyncClient, url: str, params: dict, max_retries: int = 3):
    """Выполняет API запрос с обработкой ошибок и повторными попытками"""
    
    for attempt in range(max_retries):
        try:
            # Выполняем запрос
            resp = await client.get(url, headers=HEADERS, params=params)
            
            if resp.status_code == 200:
                return resp
            elif resp.status_code == 429:
                # Too Many Requests - ждем дольше
                wait_time = (attempt + 1) * 5  # 5, 10, 15 секунд
                print(f"Ошибка 429 (Too Many Requests). Ждем {wait_time} секунд...")
                await asyncio.sleep(wait_time)
            elif resp.status_code == 403:
                # Forbidden - возможно заблокирован
                print(f"Ошибка 403 (Forbidden). Возможно API заблокирован.")
                print(f"Ответ: {resp.text}")
                return resp
            else:
                print(f"Ошибка {resp.status_code}: {resp.text}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                else:
                    return resp
                    
        except Exception as e:
            print(f"Ошибка запроса: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            else:
                raise
    
    return None

async def test_extended_stock_report():
    """Тестирует расширенный отчет об остатках с фильтром moment"""
    
    test_date = "2024-01-01"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Тест 1: Расширенный отчет об остатках на конкретную дату
        print("=== ТЕСТ 1: Расширенный отчет об остатках на дату ===")
        try:
            params = {"moment": f"{test_date}T00:00:00"}
            resp = await make_api_request(client, f"{MOYSKLAD_API_URL}/report/stock/all", params)
            print(f"Статус: {resp.status_code if resp else 'No response'}")
            if resp and resp.status_code == 200:
                data = resp.json()
                print(f"Найдено товаров: {len(data.get('rows', []))}")
                if data.get('rows'):
                    print("Пример первой записи:")
                    first_row = data['rows'][0]
                    print(f"  Товар: {first_row.get('name', 'N/A')}")
                    print(f"  Код: {first_row.get('code', 'N/A')}")
                    print(f"  Остаток: {first_row.get('quantity', 'N/A')}")
                    print(f"  Склад: {first_row.get('store', {}).get('name', 'N/A')}")
            else:
                print(f"Ошибка: {resp.text if resp else 'No response'}")
        except Exception as e:
            print(f"Ошибка: {e}")
        
        print()
        await asyncio.sleep(1)  # Пауза между тестами
        
        # Тест 2: Расширенный отчет с дополнительными параметрами
        print("=== ТЕСТ 2: Расширенный отчет с дополнительными параметрами ===")
        try:
            params = {
                "moment": f"{test_date}T00:00:00",
                "limit": 10,
                "offset": 0
            }
            resp = await make_api_request(client, f"{MOYSKLAD_API_URL}/report/stock/all", params)
            print(f"Статус: {resp.status_code if resp else 'No response'}")
            if resp and resp.status_code == 200:
                data = resp.json()
                print(f"Найдено товаров: {len(data.get('rows', []))}")
                print(f"Всего записей: {data.get('meta', {}).get('size', 'N/A')}")
            else:
                print(f"Ошибка: {resp.text if resp else 'No response'}")
        except Exception as e:
            print(f"Ошибка: {e}")
        
        print()
        await asyncio.sleep(1)  # Пауза между тестами
        
        # Тест 3: Расширенный отчет с фильтром по складу
        print("=== ТЕСТ 3: Расширенный отчет с фильтром по складу ===")
        try:
            # Сначала получим склады
            resp = await make_api_request(client, f"{MOYSKLAD_API_URL}/entity/store", {})
            if resp and resp.status_code == 200:
                stores_data = resp.json()
                if stores_data.get('rows'):
                    store_id = stores_data['rows'][0]['id']
                    store_name = stores_data['rows'][0]['name']
                    print(f"Тестируем склад: {store_name} (ID: {store_id})")
                    
                    params = {
                        "moment": f"{test_date}T00:00:00",
                        "storeId": store_id,
                        "limit": 5
                    }
                    resp = await make_api_request(client, f"{MOYSKLAD_API_URL}/report/stock/all", params)
                    print(f"Статус: {resp.status_code if resp else 'No response'}")
                    if resp and resp.status_code == 200:
                        data = resp.json()
                        print(f"Найдено товаров на складе: {len(data.get('rows', []))}")
                    else:
                        print(f"Ошибка: {resp.text if resp else 'No response'}")
        except Exception as e:
            print(f"Ошибка: {e}")
        
        print()
        await asyncio.sleep(1)  # Пауза между тестами
        
        # Тест 4: Различные форматы даты для moment
        print("=== ТЕСТ 4: Различные форматы даты для moment ===")
        date_formats = [
            f"{test_date}T00:00:00",
            f"{test_date}T00:00:00.000",
            f"{test_date}",
            f"{test_date}T00:00:00Z",
            f"{test_date}T12:00:00"
        ]
        
        for i, date_format in enumerate(date_formats, 1):
            try:
                params = {"moment": date_format, "limit": 1}
                resp = await make_api_request(client, f"{MOYSKLAD_API_URL}/report/stock/all", params)
                print(f"Формат {i} ({date_format}): {resp.status_code if resp else 'No response'}")
                if resp and resp.status_code == 200:
                    data = resp.json()
                    print(f"  Найдено товаров: {len(data.get('rows', []))}")
                else:
                    print(f"  Ошибка: {resp.text[:100] if resp else 'No response'}...")
                
                if i < len(date_formats):  # Пауза между форматами, кроме последнего
                    await asyncio.sleep(0.5)
            except Exception as e:
                print(f"  Ошибка: {e}")
        
        print()
        await asyncio.sleep(1)  # Пауза между тестами
        
        # Тест 5: Проверка структуры ответа
        print("=== ТЕСТ 5: Проверка структуры ответа ===")
        try:
            params = {"moment": f"{test_date}T00:00:00", "limit": 1}
            resp = await make_api_request(client, f"{MOYSKLAD_API_URL}/report/stock/all", params)
            if resp and resp.status_code == 200:
                data = resp.json()
                print("Структура ответа:")
                print(f"  meta: {list(data.get('meta', {}).keys())}")
                if data.get('rows'):
                    first_row = data['rows'][0]
                    print(f"  Поля в записи: {list(first_row.keys())}")
                    print(f"  Доступные поля:")
                    for key, value in first_row.items():
                        if isinstance(value, dict):
                            print(f"    {key}: {list(value.keys())}")
                        else:
                            print(f"    {key}: {type(value).__name__}")
            else:
                print(f"Ошибка: {resp.text if resp else 'No response'}")
        except Exception as e:
            print(f"Ошибка: {e}")

async def main():
    print("Тестирование расширенного отчета об остатках с фильтром moment...")
    print("ВАЖНО: Добавлены задержки для избежания блокировки API")
    test_date = "2024-01-01"
    print(f"Тестовая дата: {test_date}")
    print(f"API URL: {MOYSKLAD_API_URL}")
    print("Документация: https://dev.moysklad.ru/doc/api/remap/1.2/reports/#otchety-otchet-ostatki-rasshirennyj-otchet-ob-ostatkah")
    print()
    
    await test_extended_stock_report()
    
    print("Тестирование завершено!")

if __name__ == "__main__":
    asyncio.run(main()) 