"""
Настройка логирования
"""

import logging
import sys
from datetime import datetime
from app.core.config import settings


def setup_logging():
    """Настройка логирования"""
    
    # Создание форматтера
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Очистка существующих обработчиков
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Файловый обработчик
    try:
        file_handler = logging.FileHandler('analytics_service.log')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Ошибка создания файлового обработчика: {e}")
    
    # Настройка логгеров для внешних библиотек
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    logging.info("🚀 Логирование настроено")


def get_logger(name: str) -> logging.Logger:
    """Получение логгера с заданным именем"""
    return logging.getLogger(name) 