#!/usr/bin/env python3
"""
Экспорт документов продаж (demand) из МойСклад API
Получаем данные о продажах через документы demand
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

async def get_demand_positions(demand_id, client):
    """Получение позиций для документа продажи"""
    try:
        url = f"{MOYSKLAD_API_URL}/entity/demand/{demand_id}/positions"
        params = {"expand": "assortment"}
        resp = await client.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("rows", [])
    except Exception as e:
        print(f"Ошибка получения позиций для demand {demand_id}: {e}")
        return []

async def export_demands(start_date, end_date, filename):
    """Экспорт документов продаж с позициями"""
    print(f"Экспорт документов продаж с {start_date} по {end_date}...")
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = None
        fieldnames = set()
        total_rows = 0
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Получаем документы продаж
            params = {
                "momentFrom": f"{start_date.strftime('%Y-%m-%d')}T00:00:00",
                "momentTo": f"{end_date.strftime('%Y-%m-%d')}T23:59:59",
                "limit": 1000  # Увеличиваем лимит документов
            }
            
            try:
                resp = await client.get(f"{MOYSKLAD_API_URL}/entity/demand", headers=HEADERS, params=params)
                resp.raise_for_status()
                data = resp.json()
                demands = data.get("rows", [])
                
                print(f"Найдено {len(demands)} документов продаж")
                
                for demand in demands:
                    if total_rows >= 5000:  # Увеличиваем лимит для получения больше данных
                        print(f"Достигнут лимит в 5000 записей. Остановка экспорта.")
                        break
                    
                    demand_id = demand.get('id')
                    demand_date = demand.get('moment', '')
                    
                    if not demand_id:
                        continue
                    
                    # Получаем позиции для этого документа
                    positions = await get_demand_positions(demand_id, client)
                    
                    # Обрабатываем каждую позицию
                    for position in positions:
                        # Отладочная информация для первых записей
                        if total_rows < 3:
                            print(f"DEBUG: Обрабатываем позицию {total_rows + 1}")
                            print(f"DEBUG: position keys: {list(position.keys())}")
                        
                        # Извлекаем информацию о товаре
                        assortment = position.get('assortment', {})
                        quantity = position.get('quantity', 0)
                        
                        product_code = ''
                        product_name = ''
                        product_id = ''
                        
                        if isinstance(assortment, dict):
                            product_code = assortment.get('code', '')
                            product_name = assortment.get('name', '')
                            product_id = assortment.get('id', '')
                        
                        # Создаем запись
                        record = {
                            'date': demand_date[:10] if demand_date else '',
                            'product_code': str(product_code) if product_code else '',
                            'product_name': product_name,
                            'product_id': product_id,
                            'quantity': quantity,
                            'demand_id': demand_id,
                            'meta': json.dumps(assortment if isinstance(assortment, dict) else {}, ensure_ascii=False)
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
                
            except Exception as e:
                print(f"Ошибка при получении документов продаж: {e}")
        
        print(f"Документы продаж экспортированы в {filename}: {total_rows} записей за {time.time() - start_time:.1f} секунд")

async def main():
    """Основная функция"""
    print("Начинаем экспорт документов продаж из МойСклад...")
    
    # Период экспорта (2021-2025 годы)
    start_date = datetime(2021, 1, 1)
    end_date = datetime(2025, 12, 31)
    
    print(f"Период: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
    
    # Создаем директорию для данных
    os.makedirs("/app/data", exist_ok=True)
    
    # Экспортируем документы продаж
    await export_demands(start_date, end_date, "/app/data/demands.csv")
    
    print("Экспорт завершен!")

if __name__ == "__main__":
    asyncio.run(main()) 