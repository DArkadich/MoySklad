#!/usr/bin/env python3
"""
Скрипт для анализа структуры данных остатков и продаж
"""

import pandas as pd
import json
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_stock_data():
    """Анализ данных остатков"""
    stock_file = "/app/data/stock_history.csv"
    
    if not Path(stock_file).exists():
        logger.error(f"Файл остатков не найден: {stock_file}")
        return
    
    logger.info("Анализ данных остатков...")
    stock_df = pd.read_csv(stock_file)
    
    logger.info(f"Загружено {len(stock_df)} записей остатков")
    logger.info(f"Колонки: {list(stock_df.columns)}")
    
    # Анализируем поле code
    if 'code' in stock_df.columns:
        unique_codes = stock_df['code'].dropna().unique()
        logger.info(f"Уникальных кодов товаров: {len(unique_codes)}")
        logger.info(f"Примеры кодов: {unique_codes[:10].tolist()}")
        
        # Анализируем поле name
        if 'name' in stock_df.columns:
            unique_names = stock_df['name'].dropna().unique()
            logger.info(f"Уникальных названий товаров: {len(unique_names)}")
            logger.info(f"Примеры названий: {unique_names[:5].tolist()}")
    
    # Анализируем поле meta
    if 'meta' in stock_df.columns:
        logger.info("Анализ поля meta в остатках...")
        meta_sample = stock_df['meta'].dropna().iloc[0] if len(stock_df) > 0 else None
        if meta_sample:
            try:
                meta_data = json.loads(meta_sample.replace("'", '"'))
                logger.info(f"Структура meta: {list(meta_data.keys())}")
                if 'href' in meta_data:
                    logger.info(f"Пример href: {meta_data['href']}")
            except:
                logger.info(f"Meta не является JSON: {meta_sample[:100]}...")

def analyze_sales_data():
    """Анализ данных продаж"""
    sales_file = "/app/data/sales_history.csv"
    
    if not Path(sales_file).exists():
        logger.error(f"Файл продаж не найден: {sales_file}")
        return
    
    logger.info("Анализ данных продаж...")
    sales_df = pd.read_csv(sales_file)
    
    logger.info(f"Загружено {len(sales_df)} записей продаж")
    logger.info(f"Колонки: {list(sales_df.columns)}")
    
    # Анализируем поле positions
    if 'positions' in sales_df.columns:
        logger.info("Анализ поля positions в продажах...")
        positions_sample = sales_df['positions'].dropna().iloc[0] if len(sales_df) > 0 else None
        if positions_sample:
            logger.info(f"Пример positions: {positions_sample[:200]}...")
            
            # Пробуем извлечь информацию из href
            if 'href' in positions_sample:
                try:
                    # Ищем ID товара в href
                    if '/entity/product/' in positions_sample:
                        product_id = positions_sample.split('/entity/product/')[1].split('/')[0]
                        logger.info(f"Найден ID товара в href: {product_id}")
                    elif '/entity/service/' in positions_sample:
                        service_id = positions_sample.split('/entity/service/')[1].split('/')[0]
                        logger.info(f"Найден ID услуги в href: {service_id}")
                except:
                    pass

def analyze_agent_data():
    """Анализ поля agent в продажах"""
    sales_file = "/app/data/sales_history.csv"
    
    if not Path(sales_file).exists():
        return
    
    sales_df = pd.read_csv(sales_file)
    
    if 'agent' in sales_df.columns:
        logger.info("Анализ поля agent в продажах...")
        agent_sample = sales_df['agent'].dropna().iloc[0] if len(sales_df) > 0 else None
        if agent_sample:
            logger.info(f"Пример agent: {agent_sample[:200]}...")
            
            try:
                agent_data = json.loads(agent_sample.replace("'", '"'))
                logger.info(f"Структура agent: {list(agent_data.keys())}")
                if 'name' in agent_data:
                    logger.info(f"Название агента: {agent_data['name']}")
            except:
                logger.info("Agent не является JSON")

def main():
    """Основная функция анализа"""
    logger.info("Начинаем анализ структуры данных...")
    
    analyze_stock_data()
    analyze_sales_data()
    analyze_agent_data()
    
    logger.info("Анализ завершен!")

if __name__ == "__main__":
    main() 