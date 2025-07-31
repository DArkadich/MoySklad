#!/usr/bin/env python3
"""
Проверка структуры данных в CSV файлах
"""

import pandas as pd
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_csv_structure(filename: str, description: str):
    """Проверяет структуру CSV файла"""
    logger.info(f"Проверка {description}: {filename}")
    
    try:
        df = pd.read_csv(filename)
        logger.info(f"  Размер: {len(df)} строк, {len(df.columns)} столбцов")
        logger.info(f"  Столбцы: {list(df.columns)}")
        
        # Показываем первые несколько строк
        logger.info(f"  Первые 3 строки:")
        for i in range(min(3, len(df))):
            logger.info(f"    Строка {i+1}: {dict(df.iloc[i])}")
        
        # Проверяем типы данных
        logger.info(f"  Типы данных:")
        for col in df.columns:
            sample_values = df[col].dropna().head(3).tolist()
            logger.info(f"    {col}: {df[col].dtype} (примеры: {sample_values})")
        
        return df
        
    except Exception as e:
        logger.error(f"  Ошибка чтения файла: {e}")
        return None

def main():
    """Основная функция"""
    logger.info("Проверка структуры данных...")
    
    # Проверяем файл продаж
    sales_df = check_csv_structure('/app/data/demands.csv', 'продаж')
    
    # Проверяем файл остатков
    stock_df = check_csv_structure('/app/data/stock_history_fast.csv', 'остатков')
    
    logger.info("Проверка завершена!")

if __name__ == "__main__":
    main() 