#!/usr/bin/env python3
"""
Скрипт для копирования исторических данных в контейнер
"""

import os
import shutil
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def copy_historical_data():
    """Копирует исторические данные в контейнер"""
    logger.info("📊 Копирование исторических данных...")
    
    # Источник данных
    source_dir = "services/moysklad-service/data"
    
    # Проверяем наличие данных
    if not os.path.exists(source_dir):
        logger.error(f"❌ Папка {source_dir} не найдена")
        return False
    
    # Список файлов для копирования
    files_to_copy = [
        "production_stock_data.csv",
        "universal_forecast_models.pkl",
        "accurate_consumption_results.csv"
    ]
    
    copied_files = []
    
    for file_name in files_to_copy:
        source_path = os.path.join(source_dir, file_name)
        if os.path.exists(source_path):
            # Копируем в корень проекта для доступа из контейнера
            dest_path = os.path.join("data", file_name)
            os.makedirs("data", exist_ok=True)
            
            try:
                shutil.copy2(source_path, dest_path)
                copied_files.append(file_name)
                logger.info(f"✅ Скопирован {file_name}")
            except Exception as e:
                logger.error(f"❌ Ошибка копирования {file_name}: {e}")
        else:
            logger.warning(f"⚠️ Файл {file_name} не найден")
    
    logger.info(f"📊 Скопировано файлов: {len(copied_files)}")
    return len(copied_files) > 0

def main():
    """Основная функция"""
    logger.info("🚀 Запуск копирования исторических данных...")
    
    try:
        success = copy_historical_data()
        
        if success:
            logger.info("✅ Исторические данные скопированы успешно!")
            logger.info("📋 Теперь можно запускать обучение моделей")
        else:
            logger.error("❌ Ошибка копирования данных")
            
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main() 