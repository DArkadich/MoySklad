#!/usr/bin/env python3
"""
Скрипт для первоначального обучения ML моделей на исторических данных
Запускается один раз для обучения моделей на данных за 4 года
"""

import asyncio
import logging
import os
import sys

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """Основная функция для первоначального обучения"""
    logger.info("🚀 Запуск первоначального обучения ML моделей на исторических данных...")
    
    try:
        # Импортируем и запускаем обучение на исторических данных
        sys.path.append('services/moysklad-service/app')
        from train_historical_models import HistoricalModelTrainer
        
        trainer = HistoricalModelTrainer()
        await trainer.train_models_on_historical_data()
        
        logger.info("✅ Первоначальное обучение завершено успешно!")
        logger.info("📊 Модели сохранены в /app/data/models/")
        logger.info("🔄 Теперь система будет использовать дообучение свежими данными")
        
    except Exception as e:
        logger.error(f"❌ Ошибка первоначального обучения: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n🎉 Первоначальное обучение завершено успешно!")
        print("📈 Модели готовы к использованию")
        print("🔄 Система будет автоматически дообучать модели свежими данными")
    else:
        print("\n❌ Ошибка при первоначальном обучении")
        sys.exit(1) 