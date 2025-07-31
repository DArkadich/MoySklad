#!/usr/bin/env python3
"""
Анализ продаж для выявления популярных товаров
"""

import pandas as pd
import os
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

def analyze_sales():
    """Анализирует продажи и выявляет популярные товары"""
    
    # Загружаем данные
    demands_file = "/app/data/demands.csv"
    if not os.path.exists(demands_file):
        logger.error(f"Файл {demands_file} не найден")
        return
    
    logger.info(f"Загружаем данные из {demands_file}")
    df = pd.read_csv(demands_file)
    logger.info(f"Загружено {len(df)} записей")
    
    # Группируем по товарам и считаем статистику
    sales_stats = df.groupby(['product_code', 'product_name']).agg({
        'quantity': ['sum', 'count', 'mean'],
        'date': ['min', 'max']
    }).round(2)
    
    # Переименовываем колонки
    sales_stats.columns = ['total_quantity', 'sales_count', 'avg_quantity', 'first_sale', 'last_sale']
    sales_stats = sales_stats.reset_index()
    
    # Сортируем по общему количеству продаж
    sales_stats = sales_stats.sort_values('total_quantity', ascending=False)
    
    logger.info("=== ТОП-20 САМЫХ ПОПУЛЯРНЫХ ТОВАРОВ ===")
    for i, row in sales_stats.head(20).iterrows():
        logger.info(f"{i+1:2d}. {row['product_name']}")
        logger.info(f"     Код: {row['product_code']}")
        logger.info(f"     Всего продано: {row['total_quantity']:.0f} шт")
        logger.info(f"     Количество продаж: {row['sales_count']}")
        logger.info(f"     Среднее за продажу: {row['avg_quantity']:.1f} шт")
        logger.info(f"     Период: {row['first_sale']} - {row['last_sale']}")
        logger.info("")
    
    # Анализ по типам товаров
    logger.info("=== АНАЛИЗ ПО ТИПАМ ТОВАРОВ ===")
    
    # Определяем тип товара по названию
    def get_product_type(name):
        name_lower = name.lower()
        if 'однодневные' in name_lower:
            return 'Однодневные линзы'
        elif 'diamond' in name_lower:
            return 'Контактные линзы Diamond'
        elif 'капли' in name_lower:
            return 'Увлажняющие капли'
        elif 'раствор' in name_lower:
            return 'Раствор для линз'
        else:
            return 'Другое'
    
    df['product_type'] = df['product_name'].apply(get_product_type)
    
    type_stats = df.groupby('product_type').agg({
        'quantity': ['sum', 'count'],
        'product_code': 'nunique'
    }).round(2)
    
    type_stats.columns = ['total_quantity', 'sales_count', 'unique_products']
    type_stats = type_stats.sort_values('total_quantity', ascending=False)
    
    for product_type, stats in type_stats.iterrows():
        logger.info(f"{product_type}:")
        logger.info(f"  Всего продано: {stats['total_quantity']:.0f} шт")
        logger.info(f"  Количество продаж: {stats['sales_count']}")
        logger.info(f"  Уникальных товаров: {stats['unique_products']}")
        logger.info("")
    
    # Анализ диоптрий для линз
    logger.info("=== АНАЛИЗ ДИОПТРИЙ ===")
    
    # Извлекаем диоптрии из названий линз
    def extract_diopter(name):
        import re
        # Ищем паттерн типа (-3,00) или (-3.00)
        match = re.search(r'\(-(\d+[.,]\d+)\)', name)
        if match:
            return float(match.group(1).replace(',', '.'))
        return None
    
    df['diopter'] = df['product_name'].apply(extract_diopter)
    
    # Анализируем только товары с диоптриями
    diopter_df = df[df['diopter'].notna()]
    
    if len(diopter_df) > 0:
        diopter_stats = diopter_df.groupby('diopter').agg({
            'quantity': ['sum', 'count']
        }).round(2)
        
        diopter_stats.columns = ['total_quantity', 'sales_count']
        diopter_stats = diopter_stats.sort_values('total_quantity', ascending=False)
        
        logger.info("ТОП-10 ДИОПТРИЙ ПО ПОПУЛЯРНОСТИ:")
        for diopter, stats in diopter_stats.head(10).iterrows():
            logger.info(f"  {diopter:5.2f}: {stats['total_quantity']:6.0f} шт ({stats['sales_count']:3d} продаж)")
    
    # Сохраняем результаты анализа
    output_file = "/app/data/sales_analysis.csv"
    sales_stats.to_csv(output_file, index=False)
    logger.info(f"Результаты анализа сохранены в {output_file}")

if __name__ == "__main__":
    analyze_sales() 