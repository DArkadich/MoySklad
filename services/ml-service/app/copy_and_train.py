"""
Скрипт для копирования данных и обучения ML-моделей
"""

import shutil
import os
import asyncio
import logging
import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.append('/app')

try:
    from app.utils.logging_config import setup_logging
except ImportError:
    # Fallback если модуль не найден
    def setup_logging():
        logging.basicConfig(level=logging.INFO)
    
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


async def copy_data_files():
    """Копирование CSV файлов из moysklad-service"""
    logger.info("Копирование данных из moysklad-service...")
    
    # Пути к файлам
    source_sales = "/app/../moysklad-service/app/sales_history.csv"
    source_stock = "/app/../moysklad-service/app/stock_history.csv"
    
    target_sales = "/app/sales_history.csv"
    target_stock = "/app/stock_history.csv"
    
    try:
        # Копируем файлы продаж
        if os.path.exists(source_sales):
            shutil.copy2(source_sales, target_sales)
            logger.info(f"Скопирован файл продаж: {os.path.getsize(target_sales)} байт")
        else:
            logger.warning(f"Файл продаж не найден: {source_sales}")
        
        # Копируем файлы остатков
        if os.path.exists(source_stock):
            shutil.copy2(source_stock, target_stock)
            logger.info(f"Скопирован файл остатков: {os.path.getsize(target_stock)} байт")
        else:
            logger.warning(f"Файл остатков не найден: {source_stock}")
            
    except Exception as e:
        logger.error(f"Ошибка копирования файлов: {e}")
        raise


async def main():
    """Основная функция"""
    logger.info("Запуск копирования данных и обучения моделей...")
    
    try:
        # Копируем данные
        await copy_data_files()
        
        # Проверяем наличие файлов
        if not os.path.exists("/app/sales_history.csv"):
            logger.error("Файл sales_history.csv не найден после копирования")
            return
        
        if not os.path.exists("/app/stock_history.csv"):
            logger.error("Файл stock_history.csv не найден после копирования")
            return
        
        logger.info("Данные успешно скопированы. Запуск обучения моделей...")
        
        # Импортируем и запускаем обучение
        from train_models import main as train_main
        await train_main()
        
    except Exception as e:
        logger.error(f"Ошибка в процессе: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main()) 