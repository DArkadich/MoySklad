#!/usr/bin/env python3
"""
Экспорт продаж с отдельными запросами для получения полных данных позиций
"""

import asyncio
import csv
import time
import httpx
from datetime import datetime, timedelta
import os
from app.core.config import settings

# Настройки API
MOYSKLAD_API_URL = "https://api.moysklad.ru/api/remap/1.2"
HEADERS = {
    "Authorization": f"Bearer {settings.moysklad_api_token}",
    "Content-Type": "application/json"
}

def daterange(start_date, end_date, step_days=30):
    """Генератор дат с шагом"""
    current_date = start_date
    while current_date < end_date:
        next_date = min(current_date + timedelta(days=step_days), end_date)
        yield current_date, next_date
        current_date = next_date

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

async def export_sales_with_positions(start_date, end_date, filename):
    """Экспорт продаж с полными данными позиций"""
    print(f"Экспорт продаж с полными позициями с {start_date} по {end_date}...")
    
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
                        # Получаем список спросов
                        params = {
                            "momentFrom": f"{period_start.strftime('%Y-%m-%d')}T00:00:00",
                            "momentTo": f"{period_end.strftime('%Y-%m-%d')}T23:59:59",
                            "offset": offset,
                            "limit": 20,  # Ограничиваем для тестирования
                        }
                        resp = await client.get(f"{MOYSKLAD_API_URL}/entity/demand", headers=HEADERS, params=params)
                        resp.raise_for_status()
                        data = resp.json()
                        demands = data.get("rows", [])
                        
                        if not demands:
                            break
                        
                        # Обрабатываем каждый спрос
                        for demand in demands:
                            if total_rows >= 50:  # Ограничиваем для тестирования
                                print(f"Достигнут лимит в 50 записей. Остановка экспорта.")
                                break
                            
                            demand_id = demand.get('id')
                            if not demand_id:
                                continue
                            
                            # Получаем полные данные позиций
                            positions = await get_positions_for_demand(demand_id, client)
                            
                            # Добавляем позиции к данным спроса
                            demand['positions_data'] = positions
                            
                            # Проверяем, есть ли новые поля
                            new_fields = set(demand.keys()) - fieldnames
                            if new_fields:
                                print(f"Добавляем новые поля: {new_fields}")
                                fieldnames.update(new_fields)
                                # Пересоздаем writer с новыми полями
                                fieldnames_list = sorted(list(fieldnames))
                                writer = csv.DictWriter(csvfile, fieldnames=fieldnames_list)
                                # Перезаписываем заголовки
                                csvfile.seek(0)
                                csvfile.truncate()
                                writer.writeheader()
                            elif writer is None:
                                # Создаем writer в первый раз
                                fieldnames_list = sorted(list(fieldnames))
                                writer = csv.DictWriter(csvfile, fieldnames=fieldnames_list)
                                writer.writeheader()
                            
                            writer.writerow(demand)
                            total_rows += 1
                            period_rows += 1
                        
                        # Проверяем лимит после обработки записей
                        if total_rows >= 50:
                            print(f"Достигнут лимит в 50 записей. Остановка экспорта.")
                            break
                        
                        if len(demands) < 20:
                            break
                        offset += 20
                        
                        # Показываем прогресс
                        if total_rows % 10 == 0:
                            elapsed = time.time() - start_time
                            print(f"Обработано записей: {total_rows}, время: {elapsed:.1f}с")
                        
                    except Exception as e:
                        print(f"Ошибка при запросе: {e}")
                        break
                
                # Проверяем лимит после обработки всех записей периода
                if total_rows >= 50:
                    print(f"Достигнут лимит в 50 записей. Остановка экспорта.")
                    break
                
                print(f"Период завершен: {period_rows} записей")
                
                # Небольшая пауза между запросами
                await asyncio.sleep(0.1)
    
    elapsed = time.time() - start_time
    print(f"Продажи с позициями экспортированы в {filename}: {total_rows} записей за {elapsed:.1f} секунд")

async def main():
    """Основная функция"""
    # Создаем директорию data если её нет
    os.makedirs("/app/data", exist_ok=True)
    
    # Параметры экспорта
    start_date = datetime(2014, 1, 1)  # Начало истории
    end_date = datetime.now()
    sales_csv = "/app/data/sales_with_positions.csv"
    
    print(f"Начинаем экспорт данных из МойСклад...")
    print(f"Период: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
    
    # Экспорт продаж с полными позициями
    await export_sales_with_positions(start_date, end_date, sales_csv)
    
    print("Экспорт завершен!")

if __name__ == "__main__":
    asyncio.run(main()) 