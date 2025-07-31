import pandas as pd
import numpy as np
from datetime import datetime
import os

def analyze_demands_data():
    """Анализирует данные из demands.csv для понимания проблемы с вычислением"""
    
    # Загружаем данные
    df = pd.read_csv('/app/data/demands.csv')
    print(f"Загружено {len(df)} записей")
    
    # Анализируем по товарам
    print("\n=== АНАЛИЗ ПО ТОВАРАМ ===")
    product_stats = df.groupby(['product_code', 'product_name']).agg({
        'quantity': ['sum', 'count', 'mean'],
        'date': ['min', 'max']
    }).round(2)
    
    print(product_stats.head(20))
    
    # Показываем детали для проблемных товаров
    print("\n=== ДЕТАЛИ ДЛЯ ПРОБЛЕМНЫХ ТОВАРОВ ===")
    problem_products = ['300850.0', '300900.0', '300950.0']
    
    for product_code in problem_products:
        product_data = df[df['product_code'] == product_code]
        if len(product_data) > 0:
            print(f"\nТовар {product_code}:")
            print(f"  Название: {product_data['product_name'].iloc[0]}")
            print(f"  Всего продаж: {len(product_data)}")
            print(f"  Общее количество: {product_data['quantity'].sum()}")
            print(f"  Среднее за продажу: {product_data['quantity'].mean():.2f}")
            print(f"  Период: {product_data['date'].min()} - {product_data['date'].max()}")
            
            # Показываем все продажи
            print("  Все продажи:")
            for _, row in product_data.iterrows():
                print(f"    {row['date']}: {row['quantity']} шт")
    
    # Анализируем общую статистику
    print("\n=== ОБЩАЯ СТАТИСТИКА ===")
    print(f"Уникальных товаров: {df['product_code'].nunique()}")
    print(f"Период данных: {df['date'].min()} - {df['date'].max()}")
    print(f"Общее количество проданного: {df['quantity'].sum():.0f}")
    
    # Показываем топ-10 товаров по количеству продаж
    print("\n=== ТОП-10 ТОВАРОВ ПО КОЛИЧЕСТВУ ПРОДАЖ ===")
    top_products = df.groupby(['product_code', 'product_name']).size().sort_values(ascending=False).head(10)
    for (code, name), count in top_products.items():
        print(f"{code} ({name}): {count} продаж")
    
    # Показываем топ-10 товаров по общему количеству
    print("\n=== ТОП-10 ТОВАРОВ ПО ОБЩЕМУ КОЛИЧЕСТВУ ===")
    top_quantity = df.groupby(['product_code', 'product_name'])['quantity'].sum().sort_values(ascending=False).head(10)
    for (code, name), quantity in top_quantity.items():
        print(f"{code} ({name}): {quantity:.0f} шт")

if __name__ == "__main__":
    analyze_demands_data() 