"""
Модуль для работы с RabbitMQ
"""

import aio_pika
import logging
import json
from typing import Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

# Глобальное подключение к RabbitMQ
_rabbitmq_connection: Optional[aio_pika.Connection] = None
_rabbitmq_channel: Optional[aio_pika.Channel] = None


async def get_rabbitmq_client() -> aio_pika.Channel:
    """Получение канала RabbitMQ"""
    global _rabbitmq_connection, _rabbitmq_channel
    
    if _rabbitmq_channel is None:
        try:
            _rabbitmq_connection = await aio_pika.connect_robust(
                settings.RABBITMQ_URL
            )
            _rabbitmq_channel = await _rabbitmq_connection.channel()
            
            # Объявление очередей
            await _rabbitmq_channel.declare_queue("notifications", durable=True)
            await _rabbitmq_channel.declare_queue("purchase_events", durable=True)
            await _rabbitmq_channel.declare_queue("ml_tasks", durable=True)
            
            logger.info("✅ Подключение к RabbitMQ установлено")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к RabbitMQ: {e}")
            raise
    
    return _rabbitmq_channel


async def close_rabbitmq():
    """Закрытие подключения к RabbitMQ"""
    global _rabbitmq_connection, _rabbitmq_channel
    
    if _rabbitmq_channel:
        await _rabbitmq_channel.close()
        _rabbitmq_channel = None
    
    if _rabbitmq_connection:
        await _rabbitmq_connection.close()
        _rabbitmq_connection = None
        logger.info("🔌 Подключение к RabbitMQ закрыто")


async def publish_message(queue: str, message: Dict[str, Any]) -> bool:
    """Публикация сообщения в очередь"""
    try:
        channel = await get_rabbitmq_client()
        
        # Сериализация сообщения
        message_body = json.dumps(message, ensure_ascii=False).encode()
        
        # Публикация
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=message_body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=queue
        )
        
        logger.info(f"✅ Сообщение отправлено в очередь {queue}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки сообщения в {queue}: {e}")
        return False


async def consume_messages(queue: str, callback):
    """Потребление сообщений из очереди"""
    try:
        channel = await get_rabbitmq_client()
        
        # Получение очереди
        queue_obj = await channel.declare_queue(queue, durable=True)
        
        # Настройка потребителя
        async def message_handler(message):
            async with message.process():
                try:
                    # Десериализация сообщения
                    body = message.body.decode()
                    data = json.loads(body)
                    
                    # Вызов callback
                    await callback(data)
                    
                    logger.info(f"✅ Сообщение обработано из очереди {queue}")
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки сообщения из {queue}: {e}")
        
        # Запуск потребителя
        await queue_obj.consume(message_handler)
        logger.info(f"✅ Потребитель запущен для очереди {queue}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка настройки потребителя для {queue}: {e}")


async def get_queue_info(queue: str) -> Dict[str, Any]:
    """Получение информации о очереди"""
    try:
        channel = await get_rabbitmq_client()
        queue_obj = await channel.declare_queue(queue, durable=True)
        
        # Получение информации о очереди
        queue_info = await queue_obj.declare(passive=True)
        
        return {
            "name": queue,
            "message_count": queue_info.message_count,
            "consumer_count": queue_info.consumer_count,
            "durable": queue_info.durable
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения информации о очереди {queue}: {e}")
        return {}


async def purge_queue(queue: str) -> bool:
    """Очистка очереди"""
    try:
        channel = await get_rabbitmq_client()
        queue_obj = await channel.declare_queue(queue, durable=True)
        
        await queue_obj.purge()
        logger.info(f"✅ Очередь {queue} очищена")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка очистки очереди {queue}: {e}")
        return False 