#!/usr/bin/env python3
"""
Точный ML-тренер для объединения данных продаж и остатков
Реализует формулу: среднее потребление = продажи за период / (дни в периоде - дни когда остатки > 3 шт.)
"""

import pandas as pd
import numpy as np
import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_sales_data(filename: str) -> pd.DataFrame:
    """Загружает данные продаж из CSV"""
    logger.info(f"Загрузка данных продаж из {filename}")
    
    try:
        df = pd.read_csv(filename)
        logger.info(f"Загружено {len(df)} записей продаж")
        
        # Проверяем доступные поля
        logger.info(f"Доступные поля в продажах: {list(df.columns)}")
        
        # Ищем поле с датой (может быть 'moment', 'created', 'updated' и т.д.)
        date_columns = [col for col in df.columns if any(date_word in col.lower() for date_word in ['moment', 'created', 'updated', 'date'])]
        if date_columns:
            date_column = date_columns[0]
            logger.info(f"Используем поле даты: {date_column}")
        else:
            logger.error("Не найдено поле с датой в продажах")
            return pd.DataFrame()
        
        # Конвертируем даты
        df[date_column] = pd.to_datetime(df[date_column])
        
        # Используем существующее поле product_code
        if 'product_code' in df.columns:
            logger.info("Используем существующее поле product_code")
        else:
            logger.error("Поле product_code не найдено в продажах")
            return pd.DataFrame()
        
        # Фильтруем записи с валидными кодами
        valid_sales = df[df['product_code'].notna() & (df['product_code'] != 'unknown') & (df['product_code'] != 'nan')]
        logger.info(f"Валидных записей продаж: {len(valid_sales)}")
        
        # Сохраняем имя поля даты для использования в расчетах
        valid_sales.attrs['date_column'] = date_column
        
        return valid_sales
        
    except Exception as e:
        logger.error(f"Ошибка загрузки продаж: {e}")
        return pd.DataFrame()

def load_stock_data(filename: str) -> pd.DataFrame:
    """Загружает данные остатков из CSV"""
    logger.info(f"Загрузка данных остатков из {filename}")
    
    try:
        df = pd.read_csv(filename)
        logger.info(f"Загружено {len(df)} записей остатков")
        
        # Проверяем доступные поля
        logger.info(f"Доступные поля в остатках: {list(df.columns)}")
        
        # Конвертируем даты
        df['export_date'] = pd.to_datetime(df['export_date'])
        
        # Конвертируем quantity в числовой формат
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
        
        # Фильтруем записи с валидными кодами
        valid_stock = df[df['code'].notna() & (df['code'] != 'nan')]
        logger.info(f"Валидных записей остатков: {len(valid_stock)}")
        
        return valid_stock
        
    except Exception as e:
        logger.error(f"Ошибка загрузки остатков: {e}")
        return pd.DataFrame()

def calculate_accurate_consumption(sales_df: pd.DataFrame, stock_df: pd.DataFrame, 
                                 product_code: str, start_date: datetime, end_date: datetime) -> Dict:
    """Рассчитывает точное среднее потребление по формуле пользователя"""
    
    logger.info(f"Расчет потребления для товара {product_code} с {start_date} по {end_date}")
    
    # Получаем имя поля даты из атрибутов DataFrame
    date_column = sales_df.attrs.get('date_column', 'date')
    
    # Фильтруем продажи по товару и периоду
    product_sales = sales_df[
        (sales_df['product_code'] == product_code) & 
        (sales_df[date_column] >= start_date) & 
        (sales_df[date_column] <= end_date)
    ]
    
    # Фильтруем остатки по товару и периоду
    product_stock = stock_df[
        (stock_df['code'] == product_code) & 
        (stock_df['export_date'] >= start_date) & 
        (stock_df['export_date'] <= end_date)
    ]
    
    # Общее количество дней в периоде
    total_days = (end_date - start_date).days + 1
    
    # Количество дней с остатками > 3 шт.
    days_with_stock = 0
    if not product_stock.empty:
        days_with_stock = len(product_stock[product_stock['quantity'] > 3])
    
    # Дни для расчета потребления (исключаем дни с OoS)
    days_for_consumption = total_days - days_with_stock
    
    # Общее количество продаж за период
    total_sales = product_sales['quantity'].sum() if not product_sales.empty else 0
    
    # Рассчитываем среднее потребление по формуле
    if days_for_consumption > 0:
        avg_consumption = total_sales / days_for_consumption
    else:
        avg_consumption = 0
    
    # Дополнительная статистика
    days_with_sales = len(product_sales) if not product_sales.empty else 0
    max_stock = product_stock['quantity'].max() if not product_stock.empty else 0
    min_stock = product_stock['quantity'].min() if not product_stock.empty else 0
    
    result = {
        'product_code': product_code,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'total_days': total_days,
        'days_with_stock_above_3': days_with_stock,
        'days_for_consumption': days_for_consumption,
        'total_sales': total_sales,
        'avg_consumption': avg_consumption,
        'days_with_sales': days_with_sales,
        'max_stock': max_stock,
        'min_stock': min_stock,
        'formula': f"{total_sales} / {days_for_consumption} = {avg_consumption:.2f}"
    }
    
    logger.info(f"Результат для {product_code}: {result['formula']}")
    return result

def train_models_accurate():
    """Основная функция обучения точных моделей"""
    
    logger.info("Запуск точного ML-тренера...")
    
    # Загружаем данные
    sales_df = load_sales_data('/app/data/demands.csv')
    stock_df = load_stock_data('/app/data/stock_history_fast.csv')
    
    if sales_df.empty or stock_df.empty:
        logger.error("Не удалось загрузить данные")
        return
    
    # Получаем уникальные коды товаров
    sales_codes = set(sales_df['product_code'].dropna())
    stock_codes = set(stock_df['code'].dropna())
    common_codes = sales_codes.intersection(stock_codes)
    
    logger.info(f"Найдено товаров: продажи={len(sales_codes)}, остатки={len(stock_codes)}, общих={len(common_codes)}")
    
    # Периоды для анализа (кварталы)
    periods = [
        (datetime(2021, 1, 1), datetime(2021, 3, 31)),
        (datetime(2021, 4, 1), datetime(2021, 6, 30)),
        (datetime(2021, 7, 1), datetime(2021, 9, 30)),
        (datetime(2021, 10, 1), datetime(2021, 12, 31)),
        (datetime(2022, 1, 1), datetime(2022, 3, 31)),
        (datetime(2022, 4, 1), datetime(2022, 6, 30)),
        (datetime(2022, 7, 1), datetime(2022, 9, 30)),
        (datetime(2022, 10, 1), datetime(2022, 12, 31)),
        (datetime(2023, 1, 1), datetime(2023, 3, 31)),
        (datetime(2023, 4, 1), datetime(2023, 6, 30)),
        (datetime(2023, 7, 1), datetime(2023, 9, 30)),
        (datetime(2023, 10, 1), datetime(2023, 12, 31)),
        (datetime(2024, 1, 1), datetime(2024, 3, 31)),
        (datetime(2024, 4, 1), datetime(2024, 6, 30)),
        (datetime(2024, 7, 1), datetime(2024, 9, 30)),
        (datetime(2024, 10, 1), datetime(2024, 12, 31)),
        (datetime(2025, 1, 1), datetime(2025, 3, 31)),
        (datetime(2025, 4, 1), datetime(2025, 6, 30)),
    ]
    
    # Результаты для каждого товара и периода
    results = []
    
    # Анализируем каждый товар
    for product_code in list(common_codes)[:10]:  # Берем первые 10 для теста
        logger.info(f"Анализ товара: {product_code}")
        
        product_results = []
        
        # Анализируем каждый период
        for start_date, end_date in periods:
            try:
                result = calculate_accurate_consumption(sales_df, stock_df, product_code, start_date, end_date)
                product_results.append(result)
            except Exception as e:
                logger.error(f"Ошибка расчета для {product_code} в период {start_date}-{end_date}: {e}")
        
        # Сохраняем результаты товара
        if product_results:
            results.extend(product_results)
            
            # Выводим статистику
            avg_consumptions = [r['avg_consumption'] for r in product_results if r['avg_consumption'] > 0]
            if avg_consumptions:
                logger.info(f"Товар {product_code}: среднее потребление = {np.mean(avg_consumptions):.2f}")
    
    # Сохраняем результаты
    if results:
        results_df = pd.DataFrame(results)
        output_file = '/app/data/accurate_consumption_results.csv'
        results_df.to_csv(output_file, index=False)
        logger.info(f"Результаты сохранены в {output_file}")
        
        # Выводим общую статистику
        logger.info(f"Обработано товаров: {len(common_codes)}")
        logger.info(f"Обработано периодов: {len(periods)}")
        logger.info(f"Всего расчетов: {len(results)}")
        
        # Примеры результатов
        logger.info("Примеры результатов:")
        for i, result in enumerate(results[:5]):
            logger.info(f"  {i+1}. {result['product_code']}: {result['formula']}")
    
    logger.info("Обучение завершено!")

if __name__ == "__main__":
    train_models_accurate() 