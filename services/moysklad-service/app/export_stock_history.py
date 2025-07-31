#!/usr/bin/env python3
"""
Экспорт исторических данных об остатках товаров из МойСклад API
Получаем остатки по дням для анализа доступности товаров
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

async def export_stock_history(start_date, end_date, filename):
    """Экспорт исторических данных об остатках"""
    print(f"Экспорт остатков с {start_date} по {end_date}...")
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = None
        fieldnames = set()
        total_rows = 0
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Итерируем по дням
            current_date = start_date
            while current_date <= end_date:
                print(f"Обрабатываем день: {current_date.strftime('%Y-%m-%d')}")
                
                try:
                    # Получаем остатки на конкретную дату
                    params = {
                        "moment": f"{current_date.strftime('%Y-%m-%d')}T00:00:00",
                        "limit": 1000
                    }
                    
                    resp = await client.get(f"{MOYSKLAD_API_URL}/report/stock/all", 
                                          headers=HEADERS, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    stock_items = data.get("rows", [])
                    
                    print(f"  Найдено {len(stock_items)} позиций остатков")
                    
                    for item in stock_items:
                        # Извлекаем информацию о товаре
                        product_code = item.get('code', '')
                        product_name = item.get('name', '')
                        product_id = item.get('id', '')
                        available = item.get('quantity', 0)
                        
                        if not product_code:
                            continue
                        
                        # Создаем запись
                        record = {
                            'date': current_date.strftime('%Y-%m-%d'),
                            'product_code': str(product_code),
                            'product_name': product_name,
                            'product_id': product_id,
                            'available': available,
                            'meta': json.dumps(item, ensure_ascii=False)
                        }
                        
                        # Проверяем, есть ли новые поля
                        new_fields = set(record.keys()) - fieldnames
                        if new_fields:
                            print(f"  Добавляем новые поля: {new_fields}")
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
                    
                    # Пауза между запросами
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    print(f"Ошибка при получении данных для {current_date}: {e}")
                
                current_date += timedelta(days=1)
        
        print(f"Остатки экспортированы в {filename}: {total_rows} записей за {time.time() - start_time:.1f} секунд")

async def main():
    """Основная функция"""
    print("Начинаем экспорт исторических данных об остатках из МойСклад...")
    
    # Период экспорта (2021-2025 годы)
    start_date = datetime(2021, 1, 1)
    end_date = datetime(2025, 12, 31)
    
    print(f"Период: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
    
    # Создаем директорию для данных
    os.makedirs("/app/data", exist_ok=True)
    
    # Экспортируем остатки
    await export_stock_history(start_date, end_date, "/app/data/stock_history.csv")
    
    print("Экспорт завершен!")

if __name__ == "__main__":
    asyncio.run(main()) 