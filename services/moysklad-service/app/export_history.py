import csv
import asyncio
from datetime import datetime, timedelta
import httpx
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
        async with httpx.AsyncClient() as client:
            for period_start, period_end in daterange(start_date, end_date, step_days=90):
                offset = 0
                while True:
                    params = {
                        "momentFrom": f"{period_start.strftime('%Y-%m-%d')}T00:00:00",
                        "momentTo": f"{period_end.strftime('%Y-%m-%d')}T23:59:59",
                        "offset": offset,
                        "limit": 1000
                    }
                    resp = await client.get(f"{MOYSKLAD_API_URL}/entity/demand", headers=HEADERS, params=params, timeout=60.0)
                    resp.raise_for_status()
                    data = resp.json()
                    rows = data.get("rows", [])
                    if not rows:
                        break
                    
                    # Обрабатываем каждую строку
                    for row in rows:
                        # Проверяем, есть ли новые поля
                        new_fields = set(row.keys()) - fieldnames
                        if new_fields:
                            fieldnames.update(new_fields)
                            # Пересоздаем writer с новыми полями
                            fieldnames_list = sorted(list(fieldnames))
                            if writer is None:
                                writer = csv.DictWriter(csvfile, fieldnames=fieldnames_list)
                                writer.writeheader()
                            else:
                                # Если writer уже создан, нужно пересоздать его
                                # Это сложно, поэтому просто пропускаем строки с новыми полями
                                print(f"Пропускаем строку с новыми полями: {new_fields}")
                                continue
                        elif writer is None:
                            # Создаем writer в первый раз
                            fieldnames_list = sorted(list(fieldnames))
                            writer = csv.DictWriter(csvfile, fieldnames=fieldnames_list)
                            writer.writeheader()
                        
                        writer.writerow(row)
                    
                    if len(rows) < 1000:
                        break
                    offset += 1000
    print(f"Продажи экспортированы в {filename}")

# --- Экспорт остатков ---
async def export_stock_history(date_points, filename):
    print(f"Экспорт остатков на даты: {[d.strftime('%Y-%m-%d') for d in date_points]}")
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = None
        fieldnames = set()
        async with httpx.AsyncClient() as client:
            for date in date_points:
                params = {"moment": f"{date.strftime('%Y-%m-%d')}T23:59:59"}
                resp = await client.get(f"{MOYSKLAD_API_URL}/report/stock/all", headers=HEADERS, params=params, timeout=60.0)
                resp.raise_for_status()
                data = resp.json()
                rows = data.get("rows", [])
                
                # Обрабатываем каждую строку
                for row in rows:
                    row["date"] = date.strftime('%Y-%m-%d')
                    
                    # Проверяем, есть ли новые поля
                    new_fields = set(row.keys()) - fieldnames
                    if new_fields:
                        fieldnames.update(new_fields)
                        # Пересоздаем writer с новыми полями
                        fieldnames_list = sorted(list(fieldnames))
                        if writer is None:
                            writer = csv.DictWriter(csvfile, fieldnames=fieldnames_list)
                            writer.writeheader()
                        else:
                            # Если writer уже создан, пропускаем строки с новыми полями
                            print(f"Пропускаем строку с новыми полями: {new_fields}")
                            continue
                    elif writer is None:
                        # Создаем writer в первый раз
                        fieldnames_list = sorted(list(fieldnames))
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames_list)
                        writer.writeheader()
                    
                    writer.writerow(row)
    print(f"Остатки экспортированы в {filename}")

# --- Основная функция ---
async def main():
    # Параметры экспорта
    start_date = datetime(2014, 1, 1)  # Начало истории
    end_date = datetime.now()
    sales_csv = "sales_history.csv"
    stock_csv = "stock_history.csv"

    # Экспорт продаж
    await export_sales_history(start_date, end_date, sales_csv)

    # Экспорт остатков (на конец каждого месяца)
    date_points = [datetime(y, m, 1) + timedelta(days=32) for y in range(start_date.year, end_date.year+1) for m in range(1, 13)]
    date_points = [d.replace(day=1) - timedelta(days=1) for d in date_points if d < end_date]
    date_points = sorted(set(date_points))
    await export_stock_history(date_points, stock_csv)

if __name__ == "__main__":
    asyncio.run(main())