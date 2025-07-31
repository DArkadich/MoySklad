#!/usr/bin/env python3
"""
Создание тестовых данных для обучения универсальных ML-моделей
Генерирует данные для нескольких товаров
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def create_test_data():
    """Создает тестовые данные для нескольких товаров"""
    
    # Создаем папку data если её нет
    data_dir = os.path.join(os.getcwd(), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # Список товаров для тестирования
    products = [60800, 60801, 60802, 60803, 60804, 60805, 60806, 60807, 60808, 60809]
    
    all_data = []
    
    for product_code in products:
        # Генерируем данные для каждого товара
        for quarter in range(1, 5):  # 4 квартала
            for month in range(1, 13):  # 12 месяцев
                if month in [(quarter-1)*3+1, (quarter-1)*3+2, (quarter-1)*3+3]:
                    # Базовые параметры товара
                    base_sales = np.random.randint(50, 200)
                    base_stock = np.random.randint(100, 500)
                    
                    # Сезонность
                    seasonal_factor = 1 + 0.3 * np.sin(2 * np.pi * month / 12)
                    
                    # Случайные вариации
                    noise = np.random.normal(0, 0.1)
                    
                    # Рассчитываем параметры
                    total_sales = int(base_sales * seasonal_factor * (1 + noise))
                    max_stock = int(base_stock * (1 + noise * 0.5))
                    min_stock = max(1, int(max_stock * 0.1))
                    
                    # Дни
                    total_days = 90
                    days_with_sales = np.random.randint(20, 60)
                    days_with_stock_above_3 = np.random.randint(40, 80)
                    days_for_consumption = total_days - days_with_stock_above_3
                    
                    # Производные параметры
                    sales_per_day = total_sales / total_days
                    stock_availability_ratio = days_with_stock_above_3 / total_days
                    sales_frequency = days_with_sales / total_days
                    stock_range = max_stock - min_stock
                    avg_stock = (max_stock + min_stock) / 2
                    
                    # Потребление в день (целевая переменная)
                    consumption_per_day = sales_per_day * 0.8 + np.random.normal(0, 0.1)
                    
                    # Дата
                    start_date = datetime(2024, month, 1)
                    
                    # Создаем запись
                    record = {
                        'product_code': str(product_code),
                        'start_date': start_date.strftime('%Y-%m-%d'),
                        'year': start_date.year,
                        'quarter': quarter,
                        'month': month,
                        'total_days': total_days,
                        'days_with_stock_above_3': days_with_stock_above_3,
                        'days_for_consumption': days_for_consumption,
                        'total_sales': total_sales,
                        'days_with_sales': days_with_sales,
                        'max_stock': max_stock,
                        'min_stock': min_stock,
                        'sales_per_day': sales_per_day,
                        'stock_availability_ratio': stock_availability_ratio,
                        'sales_frequency': sales_frequency,
                        'stock_range': stock_range,
                        'avg_stock': avg_stock,
                        'consumption_per_day': max(0, consumption_per_day)
                    }
                    
                    all_data.append(record)
    
    # Создаем DataFrame
    df = pd.DataFrame(all_data)
    
    # Сохраняем данные
    output_file = os.path.join(data_dir, 'accurate_consumption_results.csv')
    df.to_csv(output_file, index=False)
    
    print(f"Создано {len(df)} записей для {df['product_code'].nunique()} товаров")
    print(f"Данные сохранены в {output_file}")
    
    # Показываем статистику
    print("\nСтатистика по товарам:")
    product_stats = df.groupby('product_code').agg({
        'total_sales': ['mean', 'std'],
        'max_stock': ['mean', 'std'],
        'consumption_per_day': ['mean', 'std']
    }).round(2)
    
    print(product_stats)
    
    return df

if __name__ == "__main__":
    create_test_data() 