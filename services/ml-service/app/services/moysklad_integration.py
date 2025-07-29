"""
Интеграция с API МойСклад (ML Service)
"""

import aiohttp
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = logging.getLogger(__name__)


class MoySkladService:
    """Сервис интеграции с МойСклад API"""
    
    def __init__(self):
        self.base_url = "https://api.moysklad.ru/api/remap/1.2"
        self.api_token = "your_token_here"  # Будет заменено из настроек
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.session = None

    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход"""
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход"""
        if self.session:
            await self.session.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Выполнение HTTP запроса к API МойСклад"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            async with self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    return await response.json()
                elif response.status == 401:
                    logger.error("Ошибка авторизации в МойСклад API")
                    raise Exception("Unauthorized access to MoySklad API")
                elif response.status == 429:
                    logger.warning("Превышен лимит запросов к МойСклад API")
                    await asyncio.sleep(5)
                    raise Exception("Rate limit exceeded")
                else:
                    error_text = await response.text()
                    logger.error(f"Ошибка API МойСклад: {response.status} - {error_text}")
                    raise Exception(f"MoySklad API error: {response.status}")
                    
        except asyncio.TimeoutError:
            logger.error("Таймаут запроса к МойСклад API")
            raise Exception("Request timeout")
        except Exception as e:
            logger.error(f"Ошибка запроса к МойСклад API: {e}")
            raise

    async def get_sales_data(
        self, 
        product_id: str, 
        date_from: datetime, 
        date_to: datetime
    ) -> List[Dict[str, Any]]:
        """Получение данных о продажах"""
        try:
            # Получение документов продаж
            response = await self._make_request(
                "GET",
                "entity/demand",
                params={
                    "filter": f"moment>={date_from.isoformat()},moment<={date_to.isoformat()}",
                    "limit": 1000
                }
            )
            
            sales_data = []
            for demand in response.get("rows", []):
                for position in demand.get("positions", {}).get("rows", []):
                    if position["assortment"]["id"] == product_id:
                        sales_data.append({
                            "date": demand["moment"],
                            "quantity": position["quantity"],
                            "price": position["price"] / 100,  # Цена из копеек
                            "sum": position["sum"] / 100
                        })
            
            return sales_data
            
        except Exception as e:
            logger.error(f"Ошибка получения данных о продажах: {e}")
            return []

    async def get_product_info(self, sku: str) -> Optional[Dict[str, Any]]:
        """Получение информации о товаре"""
        try:
            response = await self._make_request(
                "GET",
                "entity/product",
                params={"filter": f"code={sku}"}
            )
            
            if response.get("rows"):
                product = response["rows"][0]
                return {
                    "id": product["id"],
                    "name": product["name"],
                    "code": product.get("code", ""),
                    "description": product.get("description", ""),
                    "price": product.get("salePrices", [{}])[0].get("value", 0),
                    "currency": product.get("salePrices", [{}])[0].get("currency", "RUB")
                }
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о товаре {sku}: {e}")
            return None 