import csv
import asyncio
from datetime import datetime, timedelta
import httpx
import time
from app.core.config import settings

MOYSKLAD_API_URL = settings.moysklad_api_url
TOKEN = settings.moysklad_api_token
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# --- Вспомогательные функции ---

def daterange(start_date, end_date, step_days=30):
    current = start_date
    while current < end_date:
        next_date = min(current + timedelta(days=step_days), end_date)
        yield current, next_date
        current = next_date

# --- Экспорт продаж ---
async def export_sales_history(start_date, end_date, filename):
    print(f"Экспорт продаж с {start_date} по {end_date}...")
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = None
        fieldnames = set()
        total_rows = 0
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for period_start, period_end in daterange(start_date, end_date, step_days=90):
                print(f"Обрабатываем период: {period_start.strftime('%Y-%m-%d')} - {period_end.strftime('%Y-%m-%d')}")
                offset = 0
                period_rows = 0
                
                while True:
                    try:
                        params = {
                            "momentFrom": f"{period_start.strftime('%Y-%m-%d')}T00:00:00",
                            "momentTo": f"{period_end.strftime('%Y-%m-%d')}T23:59:59",
                            "offset": offset,
                            "limit": 100,  # Увеличиваем лимит для получения больше данных
                            "expand": "positions.assortment"  # Получаем полную информацию о позициях и товарах
                        }
                        resp = await client.get(f"{MOYSKLAD_API_URL}/entity/demand", headers=HEADERS, params=params)
                        resp.raise_for_status()
                        data = resp.json()
                        rows = data.get("rows", [])
                        
                        # Отладочная информация для первых записей
                        if total_rows == 0 and rows:
                            print(f"DEBUG: Первая запись positions: {str(rows[0].get('positions', 'НЕТ'))[:200]}...")
                        
                        if not rows:
                            break
                        
                        # Обрабатываем каждую строку
                        for row in rows:
                            # Ограничиваем первыми 100 записями для тестирования
                            if total_rows >= 100:
                                print(f"Достигнут лимит в 100 записей. Остановка экспорта.")
                                break
                            # Проверяем, есть ли новые поля
                            new_fields = set(row.keys()) - fieldnames
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
                            
                            writer.writerow(row)
                            total_rows += 1
                            period_rows += 1
                        
                        # Проверяем лимит после обработки записей
                        if total_rows >= 100:
                            print(f"Достигнут лимит в 100 записей. Остановка экспорта.")
                            break
                        
                        if len(rows) < 100:  # Изменено с 1000 на 100
                            break
                        offset += 100  # Изменено с 1000 на 100
                        
                        # Показываем прогресс каждые 1000 записей
                        if total_rows % 1000 == 0:
                            elapsed = time.time() - start_time
                            print(f"Обработано записей: {total_rows}, время: {elapsed:.1f}с")
                        
                    except Exception as e:
                        print(f"Ошибка при запросе: {e}")
                        break
                
                # Проверяем лимит после обработки всех записей периода
                if total_rows >= 100:
                    print(f"Достигнут лимит в 100 записей. Остановка экспорта.")
                    break
                
                print(f"Период завершен: {period_rows} записей")
                
                # Проверяем общее время выполнения
                elapsed = time.time() - start_time
                if elapsed > 3600:  # Больше часа
                    print(f"ВНИМАНИЕ: Процесс выполняется уже {elapsed:.1f} секунд")
                
                # Небольшая пауза между запросами
                await asyncio.sleep(0.1)
    
    elapsed = time.time() - start_time
    print(f"Продажи экспортированы в {filename}: {total_rows} записей за {elapsed:.1f} секунд")

# --- Экспорт остатков ---
async def export_stock_history(date_points, filename):
    print(f"Экспорт остатков на даты: {[d.strftime('%Y-%m-%d') for d in date_points]}")
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = None
        fieldnames = set()
        total_rows = 0
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i, date in enumerate(date_points):
                print(f"Обрабатываем остатки на {date.strftime('%Y-%m-%d')} ({i+1}/{len(date_points)})")
                
                try:
                    params = {"moment": f"{date.strftime('%Y-%m-%d')}T23:59:59"}
                    resp = await client.get(f"{MOYSKLAD_API_URL}/report/stock/all", headers=HEADERS, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    rows = data.get("rows", [])
                    
                    # Обрабатываем каждую строку
                    for row in rows:
                        row["date"] = date.strftime('%Y-%m-%d')
                        
                        # Проверяем, есть ли новые поля
                        new_fields = set(row.keys()) - fieldnames
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
                        
                        writer.writerow(row)
                        total_rows += 1
                    
                    # Показываем прогресс каждые 10 дат
                    if (i + 1) % 10 == 0:
                        elapsed = time.time() - start_time
                        print(f"Обработано дат: {i+1}/{len(date_points)}, записей: {total_rows}")
                    
                except Exception as e:
                    print(f"Ошибка при запросе остатков на {date.strftime('%Y-%m-%d')}: {e}")
                    continue
                
                # Небольшая пауза между запросами
                await asyncio.sleep(0.1)
    
    elapsed = time.time() - start_time
    print(f"Остатки экспортированы в {filename}: {total_rows} записей за {elapsed:.1f} секунд")

# --- Основная функция ---
async def main():
    # Параметры экспорта
    start_date = datetime(2014, 1, 1)  # Начало истории
    end_date = datetime.now()
    sales_csv = "/app/data/sales_history.csv"
    stock_csv = "/app/data/stock_history.csv"

    # Создаем директорию data если её нет
    import os
    os.makedirs("/app/data", exist_ok=True)

    print(f"Начинаем экспорт данных из МойСклад...")
    print(f"Период: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")

    # Экспорт продаж
    await export_sales_history(start_date, end_date, sales_csv)

    # Экспорт остатков (на конец каждого месяца)
    date_points = [datetime(y, m, 1) + timedelta(days=32) for y in range(start_date.year, end_date.year+1) for m in range(1, 13)]
    date_points = [d.replace(day=1) - timedelta(days=1) for d in date_points if d < end_date]
    date_points = sorted(set(date_points))
    await export_stock_history(date_points, stock_csv)

    print("Экспорт завершен!")

if __name__ == "__main__":
    asyncio.run(main())