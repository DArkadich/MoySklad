#!/usr/bin/env python3
"""
Экспорт исторических остатков через расширенный отчет об остатках
Использует фильтр moment для получения остатков на конкретную дату
Документация: https://dev.moysklad.ru/doc/api/remap/1.2/reports/#otchety-otchet-ostatki-rasshirennyj-otchet-ob-ostatkah
"""

import asyncio
import httpx
import csv
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Добавляем путь к модулям
sys.path.append('/app')

from app.core.config import settings

# Настройки API
MOYSKLAD_API_URL = "https://api.moysklad.ru/api/remap/1.2"
MOYSKLAD_API_TOKEN = settings.moysklad_api_token

HEADERS = {
    "Authorization": f"Bearer {MOYSKLAD_API_TOKEN}",
    "Content-Type": "application/json"
}

def daterange(start_date: datetime, end_date: datetime, step_days: int = 30):
    """Генерирует диапазоны дат для экспорта"""
    current_date = start_date
    while current_date < end_date:
        period_end = min(current_date + timedelta(days=step_days), end_date)
        yield current_date, period_end
        current_date = period_end

async def export_stock_history_extended(start_date: datetime, end_date: datetime, filename: str):
    """Экспортирует исторические остатки через расширенный отчет"""
    
    print(f"Экспорт остатков с {start_date} по {end_date}...")
    
    # Создаем файл и записываем заголовок
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = set()
        writer = None
        
        # Сначала соберем все уникальные поля
        print("Сбор структуры данных...")
        sample_date = start_date
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {
                "moment": sample_date.strftime("%Y-%m-%dT00:00:00"),
                "limit": 100
            }
            
            resp = await client.get(f"{MOYSKLAD_API_URL}/report/stock/all", headers=HEADERS, params=params)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('rows'):
                    for row in data['rows']:
                        fieldnames.update(row.keys())
                    print(f"Найдено полей: {len(fieldnames)}")
                    print(f"Поля: {sorted(fieldnames)}")
                else:
                    print("Нет данных для анализа структуры")
                    return
            else:
                print(f"Ошибка при получении структуры: {resp.status_code}")
                print(f"Ответ: {resp.text}")
                return
        
        # Создаем writer с собранными полями
        fieldnames = sorted(fieldnames)
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Экспортируем данные по периодам
        total_records = 0
        processed_dates = 0
        
        for period_start, period_end in daterange(start_date, end_date, step_days=30):
            print(f"Обрабатываем период: {period_start.strftime('%Y-%m-%d')} - {period_end.strftime('%Y-%m-%d')}")
            
            current_date = period_start
            while current_date < period_end:
                date_str = current_date.strftime("%Y-%m-%dT00:00:00")
                print(f"  Обрабатываем дату: {current_date.strftime('%Y-%m-%d')}")
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    offset = 0
                    limit = 1000
                    
                    while True:
                        params = {
                            "moment": date_str,
                            "limit": limit,
                            "offset": offset
                        }
                        
                        try:
                            resp = await client.get(f"{MOYSKLAD_API_URL}/report/stock/all", headers=HEADERS, params=params)
                            
                            if resp.status_code == 200:
                                data = resp.json()
                                rows = data.get('rows', [])
                                
                                if not rows:
                                    break
                                
                                # Добавляем дату к каждой записи
                                for row in rows:
                                    row['export_date'] = current_date.strftime('%Y-%m-%d')
                                
                                # Записываем в CSV
                                for row in rows:
                                    # Обрабатываем вложенные объекты
                                    processed_row = {}
                                    for key, value in row.items():
                                        if isinstance(value, dict):
                                            # Для вложенных объектов сохраняем как JSON строку
                                            import json
                                            processed_row[key] = json.dumps(value, ensure_ascii=False)
                                        else:
                                            processed_row[key] = value
                                    
                                    writer.writerow(processed_row)
                                
                                total_records += len(rows)
                                print(f"    Получено записей: {len(rows)} (всего: {total_records})")
                                
                                # Проверяем, есть ли еще данные
                                if len(rows) < limit:
                                    break
                                
                                offset += limit
                            else:
                                print(f"    Ошибка {resp.status_code}: {resp.text}")
                                break
                                
                        except Exception as e:
                            print(f"    Ошибка при обработке даты {current_date.strftime('%Y-%m-%d')}: {e}")
                            break
                
                processed_dates += 1
                current_date += timedelta(days=1)
                
                # Небольшая пауза между запросами
                await asyncio.sleep(0.1)
        
        print(f"Экспорт завершен! Обработано дат: {processed_dates}, записей: {total_records}")

async def main():
    """Основная функция"""
    print("Начинаем экспорт исторических остатков через расширенный отчет...")
    
    # Период экспорта
    start_date = datetime(2021, 1, 1)
    end_date = datetime(2025, 7, 30)
    
    # Файлы для экспорта
    stock_csv = "/app/data/stock_history_extended.csv"
    
    print(f"Период: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
    print(f"Файл остатков: {stock_csv}")
    print()
    
    # Экспортируем остатки
    await export_stock_history_extended(start_date, end_date, stock_csv)
    
    print("Экспорт завершен!")

if __name__ == "__main__":
    asyncio.run(main()) 