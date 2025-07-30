#!/usr/bin/env python3
"""
Экспорт изменений остатков из МойСклад API
Анализируем изменения остатков для определения продаж
"""

import asyncio
import csv
import time
import httpx
from datetime import datetime, timedelta
import os
import json

# Настройки API
MOYSKLAD_API_URL = "https://api.moysklad.ru/api/remap/1.2"

# Получаем токен из переменной окружения
MOYSKLAD_API_TOKEN = os.getenv('MOYSKLAD_API_TOKEN')
if not MOYSKLAD_API_TOKEN:
    raise ValueError("MOYSKLAD_API_TOKEN не установлен в переменных окружения")

HEADERS = {
    "Authorization": f"Bearer {MOYSKLAD_API_TOKEN}",
    "Content-Type": "application/json"
}

def daterange(start_date, end_date, step_days=30):
    """Генератор дат с шагом"""
    current_date = start_date
    while current_date < end_date:
        next_date = min(current_date + timedelta(days=step_days), end_date)
        yield current_date, next_date
        current_date = next_date

async def export_stock_changes(start_date, end_date, filename):
    """Экспорт изменений остатков"""
    print(f"Экспорт изменений остатков с {start_date} по {end_date}...")
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = None
        fieldnames = set()
        total_rows = 0
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for period_start, period_end in daterange(start_date, end_date):
                print(f"Обрабатываем период: {period_start.strftime('%Y-%m-%d')} - {period_end.strftime('%Y-%m-%d')}")
                offset = 0
                period_rows = 0
                
                while True:
                    try:
                        # Получаем остатки с информацией о товарах
                        params = {
                            "momentFrom": f"{period_start.strftime('%Y-%m-%d')}T00:00:00",
                            "momentTo": f"{period_end.strftime('%Y-%m-%d')}T23:59:59",
                            "offset": offset,
                            "limit": 100
                        }
                        
                        # Используем правильный эндпоинт для остатков
                        resp = await client.get(f"{MOYSKLAD_API_URL}/entity/assortment", headers=HEADERS, params=params)
                        resp.raise_for_status()
                        data = resp.json()
                        items = data.get("rows", [])
                        
                        if not items:
                            break
                        
                        # Обрабатываем каждый товар
                        for item in items:
                            if total_rows >= 1000:  # Ограничиваем для тестирования
                                print(f"Достигнут лимит в 1000 записей. Остановка экспорта.")
                                break
                            
                            # Отладочная информация для первых записей
                            if total_rows < 3:
                                print(f"DEBUG: Обрабатываем запись {total_rows + 1}")
                                print(f"DEBUG: item keys: {list(item.keys())}")
                                print(f"DEBUG: item type: {item.get('meta', {}).get('type', 'unknown')}")
                            
                            # Извлекаем информацию о товаре
                            product_code = item.get('code', '')
                            product_name = item.get('name', '')
                            product_id = item.get('id', '')
                            item_type = item.get('meta', {}).get('type', '')
                            
                            # Получаем остатки для этого товара
                            stock_info = await _get_stock_for_item(product_id, client)
                            
                            # Создаем запись
                            record = {
                                'date': period_start.strftime('%Y-%m-%d'),
                                'product_code': str(product_code) if product_code else '',
                                'product_name': product_name,
                                'product_id': product_id,
                                'item_type': item_type,
                                'quantity': stock_info.get('quantity', 0),
                                'reserve': stock_info.get('reserve', 0),
                                'inTransit': stock_info.get('inTransit', 0),
                                'stock': stock_info.get('stock', 0),
                                'available': stock_info.get('available', 0),
                                'meta': json.dumps(item.get('meta', {}), ensure_ascii=False)
                            }
                            
                            # Проверяем, есть ли новые поля
                            new_fields = set(record.keys()) - fieldnames
                            if new_fields:
                                print(f"Добавляем новые поля: {new_fields}")
                                fieldnames.update(new_fields)
                                if writer is None:
                                    writer = csv.DictWriter(csvfile, fieldnames=sorted(fieldnames))
                                    writer.writeheader()
                                else:
                                    # Пересоздаем writer с новыми полями
                                    csvfile.seek(0)
                                    csvfile.truncate()
                                    writer = csv.DictWriter(csvfile, fieldnames=sorted(fieldnames))
                                    writer.writeheader()
                            
                            if writer is None:
                                writer = csv.DictWriter(csvfile, fieldnames=sorted(fieldnames))
                                writer.writeheader()
                            
                            writer.writerow(record)
                            total_rows += 1
                            period_rows += 1
                        
                        if total_rows >= 1000:
                            break
                        
                        offset += 100
                        
                        # Небольшая пауза между запросами
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        print(f"Ошибка при получении данных: {e}")
                        break
                
                if total_rows >= 1000:
                    break
                
                print(f"Обработано записей: {period_rows}, время: {time.time() - start_time:.1f}с")
        
        print(f"Изменения остатков экспортированы в {filename}: {total_rows} записей за {time.time() - start_time:.1f} секунд")

async def get_positions_for_demand(demand_id, client):
    """Получение полных данных позиций для конкретного спроса"""
    try:
        url = f"{MOYSKLAD_API_URL}/entity/demand/{demand_id}/positions"
        params = {"expand": "assortment"}
        resp = await client.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("rows", [])
    except Exception as e:
        print(f"Ошибка получения позиций для спроса {demand_id}: {e}")
        return []

async def _get_stock_for_item(item_id, client):
    """Получение остатков для конкретного товара"""
    try:
        # Получаем остатки для товара
        params = {
            "filter": f"assortmentId={item_id}"
        }
        resp = await client.get(f"{MOYSKLAD_API_URL}/report/stock/all", headers=HEADERS, params=params)
        resp.raise_for_status()
        data = resp.json()
        stock_items = data.get("rows", [])
        
        if stock_items:
            item = stock_items[0]  # Берем первый результат
            return {
                'quantity': item.get('quantity', 0),
                'reserve': item.get('reserve', 0),
                'inTransit': item.get('inTransit', 0),
                'stock': item.get('stock', 0),
                'available': item.get('stock', 0) - item.get('reserve', 0)
            }
        else:
            return {
                'quantity': 0,
                'reserve': 0,
                'inTransit': 0,
                'stock': 0,
                'available': 0
            }
    except Exception as e:
        print(f"Ошибка получения остатков для товара {item_id}: {e}")
        return {
            'quantity': 0,
            'reserve': 0,
            'inTransit': 0,
            'stock': 0,
            'available': 0
        }

async def main():
    """Основная функция"""
    print("Начинаем экспорт данных из МойСклад...")
    
    # Период экспорта (последние 2 года)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)
    
    print(f"Период: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
    
    # Создаем директорию для данных
    os.makedirs("/app/data", exist_ok=True)
    
    # Экспортируем изменения остатков
    await export_stock_changes(start_date, end_date, "/app/data/stock_changes.csv")
    
    print("Экспорт завершен!")

if __name__ == "__main__":
    asyncio.run(main()) 