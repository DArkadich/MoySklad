#!/usr/bin/env python3
"""
Скрипт для первоначального обучения ML моделей на исторических данных
Запускается внутри Docker контейнера
"""

import os
import sys
import logging
import asyncio
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Основная функция обучения"""
    logger.info("🚀 Запуск первоначального обучения ML моделей на исторических данных...")
    
    try:
        # Добавляем путь к модулям
        sys.path.append('/app')
        
        # Настройка логирования
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Импортируем и запускаем обучение на исторических данных
        from train_historical_models import HistoricalModelTrainer
        
        trainer = HistoricalModelTrainer()
        asyncio.run(trainer.train_models_on_historical_data())
        
        logger.info("✅ Первоначальное обучение завершено успешно!")
        
    except Exception as e:
        logger.error(f"❌ Ошибка первоначального обучения: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 