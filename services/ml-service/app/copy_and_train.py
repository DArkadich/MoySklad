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
    
    # Возможные пути к файлам
    possible_paths = [
        "/app/../moysklad-service/app/sales_history.csv",
        "/app/sales_history.csv",  # Если файлы уже в ml-service
        "/app/../sales_history.csv",  # В корне проекта
        "/app/../services/moysklad-service/app/sales_history.csv",
        "/app/../services/ml-service/app/sales_history.csv"
    ]
    
    source_sales = None
    source_stock = None
    
    # Ищем файлы продаж
    for path in possible_paths:
        if os.path.exists(path):
            source_sales = path
            logger.info(f"Найден файл продаж: {path}")
            break
    
    # Ищем файлы остатков
    for path in possible_paths:
        stock_path = path.replace("sales_history.csv", "stock_history.csv")
        if os.path.exists(stock_path):
            source_stock = stock_path
            logger.info(f"Найден файл остатков: {stock_path}")
            break
    
    target_sales = "/app/sales_history.csv"
    target_stock = "/app/stock_history.csv"
    
    try:
        # Копируем файлы продаж
        if source_sales:
            shutil.copy2(source_sales, target_sales)
            logger.info(f"Скопирован файл продаж: {os.path.getsize(target_sales)} байт")
        else:
            logger.error("Файл продаж не найден ни в одном из мест:")
            for path in possible_paths:
                logger.error(f"  - {path}")
            return False
        
        # Копируем файлы остатков
        if source_stock:
            shutil.copy2(source_stock, target_stock)
            logger.info(f"Скопирован файл остатков: {os.path.getsize(target_stock)} байт")
        else:
            logger.error("Файл остатков не найден ни в одном из мест:")
            for path in possible_paths:
                stock_path = path.replace("sales_history.csv", "stock_history.csv")
                logger.error(f"  - {stock_path}")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка копирования файлов: {e}")
        return False
    
    return True


async def main():
    """Основная функция"""
    logger.info("Запуск копирования данных и обучения моделей...")
    
    try:
        # Копируем данные
        if not await copy_data_files():
            logger.error("Не удалось скопировать данные. Завершение работы.")
            return
        
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