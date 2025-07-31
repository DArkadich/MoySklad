#!/usr/bin/env python3
"""
Экспорт реальных данных из МойСклад для обучения ML-моделей
Собирает данные по 86 SKU за последние 4 года
"""

import asyncio
import httpx
import pandas as pd
import logging
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MoyskladDataExporter:
    """Экспортер данных из МойСклад"""
    
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://api.moysklad.ru/api/remap/1.2"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
    async def get_all_products(self) -> List[Dict]:
        """Получает все товары из МойСклад"""
        logger.info("Получение списка всех товаров...")
        
        all_products = []
        limit = 100
        offset = 0
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                params = {
                    "limit": limit,
                    "offset": offset
                }
                
                try:
                    resp = await client.get(f"{self.base_url}/entity/assortment", 
                                          headers=self.headers, params=params)
                    
                    if resp.status_code != 200:
                        logger.error(f"Ошибка получения товаров: {resp.status_code}")
                        break
                    
                    data = resp.json()
                    products = data.get('rows', [])
                    
                    if not products:
                        break
                    
                    # Фильтруем только товары с кодами
                    for product in products:
                        if product.get('code') and product.get('archived') == False:
                            all_products.append({
                                'id': product.get('id'),
                                'code': product.get('code'),
                                'name': product.get('name', ''),
                                'type': product.get('meta', {}).get('type', '')
                            })
                    
                    logger.info(f"Получено {len(all_products)} товаров...")
                    offset += limit
                    
                    # Небольшая пауза между запросами
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Ошибка запроса товаров: {e}")
                    break
        
        logger.info(f"Всего получено {len(all_products)} товаров")
        return all_products
    
    async def get_stock_data(self, product_code: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Получает данные об остатках товара за период"""
        logger.info(f"Получение данных об остатках для {product_code}...")
        
        stock_data = []
        current_date = start_date
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while current_date <= end_date:
                try:
                    # Получаем остатки на конкретную дату
                    moment = current_date.strftime("%Y-%m-%dT00:00:00")
                    params = {
                        "moment": moment,
                        "filter": f"code={product_code}"
                    }
                    
                    resp = await client.get(f"{self.base_url}/report/stock/all", 
                                          headers=self.headers, params=params)
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get('rows'):
                            stock_quantity = data['rows'][0].get('quantity', 0)
                            stock_data.append({
                                'date': current_date.strftime('%Y-%m-%d'),
                                'product_code': product_code,
                                'stock_quantity': stock_quantity
                            })
                    
                    current_date += timedelta(days=1)
                    
                    # Пауза между запросами
                    await asyncio.sleep(0.05)
                    
                except Exception as e:
                    logger.error(f"Ошибка получения остатков для {product_code} на {current_date}: {e}")
                    current_date += timedelta(days=1)
        
        return stock_data
    
    async def get_sales_data(self, product_code: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Получает данные о продажах товара за период"""
        logger.info(f"Получение данных о продажах для {product_code}...")
        
        sales_data = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Получаем отчет о продажах
                params = {
                    "momentFrom": start_date.strftime("%Y-%m-%dT00:00:00"),
                    "momentTo": end_date.strftime("%Y-%m-%dT23:59:59"),
                    "filter": f"code={product_code}"
                }
                
                resp = await client.get(f"{self.base_url}/report/sales", 
                                      headers=self.headers, params=params)
                
                if resp.status_code == 200:
                    data = resp.json()
                    rows = data.get('rows', [])
                    
                    # Группируем продажи по дням
                    daily_sales = {}
                    for row in rows:
                        date = row.get('moment', '').split('T')[0]
                        quantity = row.get('quantity', 0)
                        
                        if date in daily_sales:
                            daily_sales[date] += quantity
                        else:
                            daily_sales[date] = quantity
                    
                    # Создаем записи для каждого дня
                    current_date = start_date
                    while current_date <= end_date:
                        date_str = current_date.strftime('%Y-%m-%d')
                        quantity = daily_sales.get(date_str, 0)
                        
                        sales_data.append({
                            'date': date_str,
                            'product_code': product_code,
                            'sales_quantity': quantity
                        })
                        
                        current_date += timedelta(days=1)
                
            except Exception as e:
                logger.error(f"Ошибка получения продаж для {product_code}: {e}")
        
        return sales_data
    
    def calculate_daily_consumption(self, stock_data: List[Dict], sales_data: List[Dict]) -> List[Dict]:
        """Рассчитывает ежедневное потребление на основе остатков и продаж"""
        logger.info("Расчет ежедневного потребления...")
        
        # Создаем DataFrame для удобства
        stock_df = pd.DataFrame(stock_data)
        sales_df = pd.DataFrame(sales_data)
        
        if stock_df.empty or sales_df.empty:
            return []
        
        # Объединяем данные
        merged_df = stock_df.merge(sales_df, on=['date', 'product_code'], how='outer')
        merged_df = merged_df.fillna(0)
        
        # Сортируем по дате
        merged_df = merged_df.sort_values('date')
        
        # Рассчитываем потребление как изменение остатков + продажи
        consumption_data = []
        
        for i in range(1, len(merged_df)):
            prev_row = merged_df.iloc[i-1]
            curr_row = merged_df.iloc[i]
            
            # Потребление = продажи + (предыдущие остатки - текущие остатки)
            stock_change = prev_row['stock_quantity'] - curr_row['stock_quantity']
            sales = curr_row['sales_quantity']
            consumption = sales + max(0, stock_change)  # Не учитываем отрицательные изменения
            
            consumption_data.append({
                'date': curr_row['date'],
                'product_code': curr_row['product_code'],
                'daily_consumption': consumption,
                'current_stock': curr_row['stock_quantity'],
                'sales_quantity': sales,
                'stock_change': stock_change
            })
        
        return consumption_data
    
    async def export_product_data(self, product_code: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Экспортирует все данные по товару"""
        logger.info(f"Экспорт данных для товара {product_code}...")
        
        # Получаем данные об остатках
        stock_data = await self.get_stock_data(product_code, start_date, end_date)
        
        # Получаем данные о продажах
        sales_data = await self.get_sales_data(product_code, start_date, end_date)
        
        # Рассчитываем потребление
        consumption_data = self.calculate_daily_consumption(stock_data, sales_data)
        
        # Добавляем дополнительные признаки
        for record in consumption_data:
            date_obj = datetime.strptime(record['date'], '%Y-%m-%d')
            record['year'] = date_obj.year
            record['month'] = date_obj.month
            record['day_of_year'] = date_obj.timetuple().tm_yday
            record['day_of_week'] = date_obj.weekday()
            record['is_month_start'] = date_obj.day == 1
            record['is_quarter_start'] = date_obj.day == 1 and date_obj.month in [1, 4, 7, 10]
        
        logger.info(f"Экспортировано {len(consumption_data)} записей для {product_code}")
        return consumption_data
    
    async def export_all_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Экспортирует данные по всем товарам"""
        logger.info("Начало экспорта всех данных...")
        
        # Получаем все товары
        products = await self.get_all_products()
        
        # Фильтруем только нужные товары (86 SKU)
        target_products = []
        
        # Однодневные линзы (код 30хххх)
        daily_lenses = [p for p in products if p['code'].startswith('30')]
        target_products.extend(daily_lenses[:20])  # Берем первые 20
        
        # Месячные линзы по 6 шт (код 6хххх)
        monthly_lenses_6 = [p for p in products if p['code'].startswith('6')]
        target_products.extend(monthly_lenses_6[:20])  # Берем первые 20
        
        # Месячные линзы по 3 шт (код 3хххх)
        monthly_lenses_3 = [p for p in products if p['code'].startswith('3')]
        target_products.extend(monthly_lenses_3[:20])  # Берем первые 20
        
        # Растворы
        solutions = [p for p in products if p['code'] in ['360360', '500500', '120120', '360361', '500501', '120121']]
        target_products.extend(solutions)
        
        # Дополняем до 86 товаров
        other_products = [p for p in products if p not in target_products]
        target_products.extend(other_products[:6])  # Добавляем еще 6 товаров
        
        logger.info(f"Отобрано {len(target_products)} товаров для экспорта")
        
        # Экспортируем данные по каждому товару
        all_data = []
        
        for i, product in enumerate(target_products):
            logger.info(f"Экспорт {i+1}/{len(target_products)}: {product['code']}")
            
            try:
                product_data = await self.export_product_data(
                    product['code'], start_date, end_date
                )
                all_data.extend(product_data)
                
                # Пауза между товарами
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Ошибка экспорта товара {product['code']}: {e}")
                continue
        
        # Создаем DataFrame
        df = pd.DataFrame(all_data)
        
        logger.info(f"Экспорт завершен. Всего записей: {len(df)}")
        return df

async def main():
    """Основная функция"""
    logger.info("Запуск экспорта данных из МойСклад...")
    
    # Получаем токен из переменных окружения
    api_token = os.getenv('MOYSKLAD_API_TOKEN')
    if not api_token:
        logger.error("MOYSKLAD_API_TOKEN не настроен")
        return
    
    # Создаем экспортер
    exporter = MoyskladDataExporter(api_token)
    
    # Период экспорта (последние 4 года)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=4*365)  # 4 года
    
    logger.info(f"Период экспорта: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
    
    # Экспортируем данные
    df = await exporter.export_all_data(start_date, end_date)
    
    if not df.empty:
        # Сохраняем данные
        data_dir = os.path.join(os.getcwd(), 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        output_file = os.path.join(data_dir, 'production_stock_data.csv')
        df.to_csv(output_file, index=False)
        
        logger.info(f"Данные сохранены в {output_file}")
        logger.info(f"Статистика:")
        logger.info(f"  Всего записей: {len(df)}")
        logger.info(f"  Уникальных товаров: {df['product_code'].nunique()}")
        logger.info(f"  Период: {df['date'].min()} - {df['date'].max()}")
        
        # Показываем распределение по типам товаров
        from app.product_rules import ProductRules
        
        product_types = {}
        for code in df['product_code'].unique():
            product_type = ProductRules.get_product_type(str(code))
            if product_type:
                product_types[product_type] = product_types.get(product_type, 0) + 1
        
        logger.info("Распределение по типам товаров:")
        for product_type, count in product_types.items():
            logger.info(f"  {product_type}: {count} SKU")
    else:
        logger.error("Не удалось экспортировать данные")

if __name__ == "__main__":
    asyncio.run(main()) 