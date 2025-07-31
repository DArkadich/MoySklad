#!/usr/bin/env python3
"""
Быстрый экспорт исторических остатков через расширенный отчет
Один запрос на день = все остатки на конкретную дату
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

# Настройки для избежания блокировки
REQUEST_DELAY = 0.5  # секунды между днями
MAX_REQUESTS_PER_MINUTE = 150

class RateLimiter:
    """Ограничитель частоты запросов"""
    
    def __init__(self, max_requests_per_minute: int):
        self.max_requests = max_requests_per_minute
        self.requests = []
    
    async def wait_if_needed(self):
        """Ждет если нужно ограничить частоту"""
        now = datetime.now()
        
        # Удаляем запросы старше 1 минуты
        self.requests = [req_time for req_time in self.requests 
                        if (now - req_time).total_seconds() < 60]
        
        # Если достигли лимита, ждем
        if len(self.requests) >= self.max_requests:
            oldest_request = min(self.requests)
            wait_time = 60 - (now - oldest_request).total_seconds()
            if wait_time > 0:
                print(f"Достигнут лимит запросов. Ждем {wait_time:.1f} секунд...")
                await asyncio.sleep(wait_time)
        
        # Добавляем текущий запрос
        self.requests.append(now)

# Глобальный ограничитель
rate_limiter = RateLimiter(MAX_REQUESTS_PER_MINUTE)

def daterange(start_date: datetime, end_date: datetime, step_days: int = 30):
    """Генерирует диапазоны дат для экспорта"""
    current_date = start_date
    while current_date < end_date:
        period_end = min(current_date + timedelta(days=step_days), end_date)
        yield current_date, period_end
        current_date = period_end

async def make_api_request(client: httpx.AsyncClient, url: str, params: dict, max_retries: int = 3):
    """Выполняет API запрос с обработкой ошибок и повторными попытками"""
    
    for attempt in range(max_retries):
        try:
            # Ждем если нужно ограничить частоту
            await rate_limiter.wait_if_needed()
            
            # Выполняем запрос
            resp = await client.get(url, headers=HEADERS, params=params)
            
            if resp.status_code == 200:
                return resp
            elif resp.status_code == 429:
                # Too Many Requests - ждем дольше
                wait_time = (attempt + 1) * 3
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
                    await asyncio.sleep(1)
                else:
                    return resp
                    
        except Exception as e:
            print(f"Ошибка запроса: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
            else:
                raise
    
    return None

async def export_stock_history_fast(start_date: datetime, end_date: datetime, filename: str):
    """Экспортирует исторические остатки - один запрос на день"""
    
    print(f"Быстрый экспорт остатков с {start_date} по {end_date}...")
    print(f"Настройки: задержка между днями {REQUEST_DELAY} сек")
    print()
    
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
                "limit": 1000  # Увеличиваем лимит для получения всех товаров
            }
            
            resp = await make_api_request(client, f"{MOYSKLAD_API_URL}/report/stock/all", params)
            if resp and resp.status_code == 200:
                data = resp.json()
                if data.get('rows'):
                    for row in data['rows']:
                        fieldnames.update(row.keys())
                    # Добавляем поле export_date
                    fieldnames.add('export_date')
                    print(f"Найдено полей: {len(fieldnames)}")
                    print(f"Поля: {sorted(fieldnames)}")
                else:
                    print("Нет данных для анализа структуры")
                    return
            else:
                print(f"Ошибка при получении структуры: {resp.status_code if resp else 'No response'}")
                return
        
        # Создаем writer с собранными полями
        fieldnames = sorted(fieldnames)
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Экспортируем данные по дням
        total_records = 0
        processed_dates = 0
        
        for period_start, period_end in daterange(start_date, end_date, step_days=30):
            print(f"Обрабатываем период: {period_start.strftime('%Y-%m-%d')} - {period_end.strftime('%Y-%m-%d')}")
            
            current_date = period_start
            while current_date < period_end:
                date_str = current_date.strftime("%Y-%m-%dT00:00:00")
                print(f"  Обрабатываем дату: {current_date.strftime('%Y-%m-%d')}")
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    # ОДИН ЗАПРОС НА ДЕНЬ - получаем все остатки
                    params = {
                        "moment": date_str,
                        "limit": 10000  # Большой лимит для получения всех товаров
                    }
                    
                    resp = await make_api_request(client, f"{MOYSKLAD_API_URL}/report/stock/all", params)
                    
                    if not resp:
                        print(f"    Пропускаем дату {current_date.strftime('%Y-%m-%d')} из-за ошибок")
                        current_date += timedelta(days=1)
                        continue
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        rows = data.get('rows', [])
                        
                        if rows:
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
                        else:
                            print(f"    Нет данных на дату {current_date.strftime('%Y-%m-%d')}")
                    else:
                        print(f"    Ошибка {resp.status_code}: {resp.text}")
                
                processed_dates += 1
                current_date += timedelta(days=1)
                
                # Пауза между днями
                await asyncio.sleep(REQUEST_DELAY)
        
        print(f"Экспорт завершен! Обработано дат: {processed_dates}, записей: {total_records}")

async def main():
    """Основная функция"""
    print("Начинаем БЫСТРЫЙ экспорт исторических остатков...")
    print("Один запрос на день = все остатки на конкретную дату")
    print()
    
    # Период экспорта
    start_date = datetime(2021, 1, 1)  # С 2021 года
    end_date = datetime(2025, 7, 30)   # До текущего времени
    
    # Файлы для экспорта
    stock_csv = "/app/data/stock_history_fast.csv"
    
    print(f"Период: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
    print(f"Файл остатков: {stock_csv}")
    print()
    
    # Экспортируем остатки
    await export_stock_history_fast(start_date, end_date, stock_csv)
    
    print("Экспорт завершен!")

if __name__ == "__main__":
    asyncio.run(main()) 