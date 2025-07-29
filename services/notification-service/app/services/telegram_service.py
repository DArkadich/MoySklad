import httpx
import logging
from typing import List, Optional, Dict
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self):
        self.bot_token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.client: Optional[httpx.AsyncClient] = None
    
    async def initialize(self):
        """Инициализация сервиса"""
        try:
            self.client = httpx.AsyncClient(timeout=30.0)
            # Проверка подключения
            await self.test_connection()
            logger.info("Telegram сервис инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации Telegram сервиса: {e}")
            raise
    
    async def close(self):
        """Закрытие сервиса"""
        if self.client:
            await self.client.aclose()
            logger.info("Telegram сервис закрыт")
    
    async def test_connection(self) -> bool:
        """Тест подключения к Telegram API"""
        try:
            response = await self.client.get(f"{self.base_url}/getMe")
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    logger.info(f"Telegram бот подключен: {data['result']['username']}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Ошибка тестирования Telegram подключения: {e}")
            return False
    
    async def send_message(self, message: str, chat_ids: List[str] = None) -> Dict:
        """Отправить сообщение в Telegram"""
        try:
            if not chat_ids:
                chat_ids = [self.chat_id]
            
            results = []
            for chat_id in chat_ids:
                payload = {
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "HTML"
                }
                
                response = await self.client.post(
                    f"{self.base_url}/sendMessage",
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        results.append({
                            "chat_id": chat_id,
                            "status": "success",
                            "message_id": data["result"]["message_id"]
                        })
                    else:
                        results.append({
                            "chat_id": chat_id,
                            "status": "error",
                            "error": data.get("description", "Unknown error")
                        })
                else:
                    results.append({
                        "chat_id": chat_id,
                        "status": "error",
                        "error": f"HTTP {response.status_code}"
                    })
            
            return {
                "status": "success" if any(r["status"] == "success" for r in results) else "error",
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка отправки Telegram сообщения: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def send_photo(self, photo_url: str, caption: str = "", chat_ids: List[str] = None) -> Dict:
        """Отправить фото в Telegram"""
        try:
            if not chat_ids:
                chat_ids = [self.chat_id]
            
            results = []
            for chat_id in chat_ids:
                payload = {
                    "chat_id": chat_id,
                    "photo": photo_url,
                    "caption": caption,
                    "parse_mode": "HTML"
                }
                
                response = await self.client.post(
                    f"{self.base_url}/sendPhoto",
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        results.append({
                            "chat_id": chat_id,
                            "status": "success",
                            "message_id": data["result"]["message_id"]
                        })
                    else:
                        results.append({
                            "chat_id": chat_id,
                            "status": "error",
                            "error": data.get("description", "Unknown error")
                        })
                else:
                    results.append({
                        "chat_id": chat_id,
                        "status": "error",
                        "error": f"HTTP {response.status_code}"
                    })
            
            return {
                "status": "success" if any(r["status"] == "success" for r in results) else "error",
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка отправки Telegram фото: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def send_document(self, document_url: str, caption: str = "", chat_ids: List[str] = None) -> Dict:
        """Отправить документ в Telegram"""
        try:
            if not chat_ids:
                chat_ids = [self.chat_id]
            
            results = []
            for chat_id in chat_ids:
                payload = {
                    "chat_id": chat_id,
                    "document": document_url,
                    "caption": caption,
                    "parse_mode": "HTML"
                }
                
                response = await self.client.post(
                    f"{self.base_url}/sendDocument",
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        results.append({
                            "chat_id": chat_id,
                            "status": "success",
                            "message_id": data["result"]["message_id"]
                        })
                    else:
                        results.append({
                            "chat_id": chat_id,
                            "status": "error",
                            "error": data.get("description", "Unknown error")
                        })
                else:
                    results.append({
                        "chat_id": chat_id,
                        "status": "error",
                        "error": f"HTTP {response.status_code}"
                    })
            
            return {
                "status": "success" if any(r["status"] == "success" for r in results) else "error",
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка отправки Telegram документа: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 