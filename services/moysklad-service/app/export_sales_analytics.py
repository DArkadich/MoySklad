#!/usr/bin/env python3
"""
Экспорт аналитики продаж из МойСклад API
Получаем данные о продажах через аналитические отчеты
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

async def export_sales_analytics(start_date, end_date, filename):
    """Экспорт аналитики продаж"""
    print(f"Экспорт аналитики продаж с {start_date} по {end_date}...")
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = None
        fieldnames = set()
        total_rows = 0
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Проходим по дням
            current_date = start_date
            while current_date <= end_date:
                print(f"Обрабатываем день: {current_date.strftime('%Y-%m-%d')}")
                
                try:
                    # Получаем аналитику продаж на конкретную дату
                    params = {
                        "momentFrom": f"{current_date.strftime('%Y-%m-%d')}T00:00:00",
                        "momentTo": f"{current_date.strftime('%Y-%m-%d')}T23:59:59",
                        "limit": 1000
                    }
                    
                    # Используем отчет по продажам
                    resp = await client.get(f"{MOYSKLAD_API_URL}/report/sales", headers=HEADERS, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    sales_items = data.get("rows", [])
                    
                    if not sales_items:
                        print(f"Нет данных продаж для {current_date.strftime('%Y-%m-%d')}")
                        current_date += timedelta(days=1)
                        continue
                    
                    # Обрабатываем каждую продажу
                    for item in sales_items:
                        if total_rows >= 1000:  # Ограничиваем для тестирования
                            print(f"Достигнут лимит в 1000 записей. Остановка экспорта.")
                            break
                        
                        # Отладочная информация для первых записей
                        if total_rows < 3:
                            print(f"DEBUG: Обрабатываем продажу {total_rows + 1}")
                            print(f"DEBUG: item keys: {list(item.keys())}")
                        
                        # Извлекаем информацию о продаже
                        product_code = item.get('code', '')
                        product_name = item.get('name', '')
                        quantity = item.get('quantity', 0)
                        sum_value = item.get('sum', 0)
                        
                        # Создаем запись
                        record = {
                            'date': current_date.strftime('%Y-%m-%d'),
                            'product_code': str(product_code) if product_code else '',
                            'product_name': product_name,
                            'quantity': quantity,
                            'sum': sum_value,
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
                    
                    if total_rows >= 1000:
                        break
                    
                    # Переходим к следующему дню
                    current_date += timedelta(days=1)
                    
                    # Небольшая пауза между запросами
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    print(f"Ошибка при получении данных для {current_date.strftime('%Y-%m-%d')}: {e}")
                    current_date += timedelta(days=1)
                    continue
        
        print(f"Аналитика продаж экспортирована в {filename}: {total_rows} записей за {time.time() - start_time:.1f} секунд")

async def main():
    """Основная функция"""
    print("Начинаем экспорт аналитики продаж из МойСклад...")
    
    # Период экспорта (последние 2 года)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)
    
    print(f"Период: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
    
    # Создаем директорию для данных
    os.makedirs("/app/data", exist_ok=True)
    
    # Экспортируем аналитику продаж
    await export_sales_analytics(start_date, end_date, "/app/data/sales_analytics.csv")
    
    print("Экспорт завершен!")

if __name__ == "__main__":
    asyncio.run(main()) 