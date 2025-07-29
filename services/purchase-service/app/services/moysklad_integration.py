"""
Интеграция с API МойСклад
Получение данных о товарах, остатках и создание заказов
"""

import httpx
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.redis_client import cache_get, cache_set, cache_delete

logger = logging.getLogger(__name__)

class MoySkladService:
    """Сервис интеграции с API МойСклад согласно официальной документации"""
    
    def __init__(self):
        self.base_url = settings.moysklad_api_url
        self.token = settings.moysklad_api_token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/json"
        }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict:
        """Выполнение запроса к API МойСклад с retry логикой"""
        try:
            url = f"{self.base_url}/{endpoint}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=self.headers, params=params)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=self.headers, json=data)
                elif method.upper() == "PUT":
                    response = await client.put(url, headers=self.headers, json=data)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=self.headers)
                else:
                    raise ValueError(f"Неподдерживаемый метод: {method}")
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    logger.error("Ошибка аутентификации в МойСклад API")
                    raise Exception("Ошибка аутентификации в МойСклад API")
                elif response.status_code == 429:
                    logger.warning("Превышен лимит запросов к МойСклад API")
                    raise Exception("Превышен лимит запросов к МойСклад API")
                else:
                    logger.error(f"Ошибка API МойСклад: {response.status_code} - {response.text}")
                    raise Exception(f"Ошибка API МойСклад: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Ошибка запроса к МойСклад API: {e}")
            raise
    
    async def get_product_stock(self, product_id: str) -> float:
        """Получение остатков товара с кэшированием"""
        cache_key = f"stock_{product_id}"
        
        # Проверка кэша
        cached_data = await cache_get(cache_key)
        if cached_data:
            return cached_data.get("quantity", 0)
        
        try:
            # Получение остатков через отчет
            response = await self._make_request(
                "GET", 
                "report/stock/all",
                params={"filter": f"assortmentId={product_id}"}
            )
            
            quantity = 0
            if response.get("rows"):
                quantity = response["rows"][0].get("quantity", 0)
            
            # Кэширование на 5 минут
            await cache_set(cache_key, {"quantity": quantity}, ttl=300)
            
            return quantity
        except Exception as e:
            logger.error(f"Ошибка получения остатков для {product_id}: {e}")
            return 0
    
    async def get_product_info(self, product_id: str) -> Dict:
        """Получение информации о товаре"""
        try:
            response = await self._make_request("GET", f"entity/product/{product_id}")
            return response
        except Exception as e:
            logger.error(f"Ошибка получения информации о товаре {product_id}: {e}")
            raise
    
    async def get_all_products(self) -> Dict:
        """Получение всех товаров"""
        try:
            response = await self._make_request("GET", "entity/product")
            return response
        except Exception as e:
            logger.error(f"Ошибка получения списка товаров: {e}")
            raise
    
    async def create_purchase_order(self, order_data: Dict) -> Dict:
        """Создание заказа на поставку согласно документации МойСклад"""
        try:
            # Формирование данных заказа согласно API МойСклад
            purchase_order = {
                "name": order_data.get("name", "Заказ через Horiens Purchase Agent"),
                "description": order_data.get("description", ""),
                "moment": datetime.now().isoformat(),
                "organization": order_data.get("organization"),
                "agent": order_data.get("agent"),  # Поставщик
                "positions": order_data.get("positions", []),
                "applicable": True,
                "vatEnabled": True,
                "vatIncluded": True
            }
            
            response = await self._make_request("POST", "entity/purchaseorder", data=purchase_order)
            return response
        except Exception as e:
            logger.error(f"Ошибка создания заказа на поставку: {e}")
            raise
    
    async def get_sales_data(
        self, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        product_id: Optional[str] = None
    ) -> Dict:
        """Получение данных о продажах"""
        try:
            params = {}
            
            if start_date:
                params["momentFrom"] = f"{start_date}T00:00:00"
            if end_date:
                params["momentTo"] = f"{end_date}T23:59:59"
            if product_id:
                params["filter"] = f"assortmentId={product_id}"
            
            response = await self._make_request("GET", "entity/demand", params=params)
            return response
        except Exception as e:
            logger.error(f"Ошибка получения данных о продажах: {e}")
            raise
    
    async def get_inventory_movements(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """Получение движений товаров"""
        try:
            params = {}
            
            if start_date:
                params["momentFrom"] = f"{start_date}T00:00:00"
            if end_date:
                params["momentTo"] = f"{end_date}T23:59:59"
            
            response = await self._make_request("GET", "entity/move", params=params)
            return response
        except Exception as e:
            logger.error(f"Ошибка получения движений товаров: {e}")
            raise
    
    async def update_product_price(self, product_id: str, new_price: float) -> Dict:
        """Обновление цены товара"""
        try:
            # Получение текущих данных товара
            product_data = await self.get_product_info(product_id)
            
            # Обновление цены
            product_data["salePrices"] = [
                {
                    "value": new_price * 100,  # Цена в копейках
                    "currency": {
                        "meta": {
                            "href": "https://api.moysklad.ru/api/remap/1.2/entity/currency/your_currency_id",
                            "type": "currency",
                            "mediaType": "application/json"
                        }
                    }
                }
            ]
            
            response = await self._make_request("PUT", f"entity/product/{product_id}", data=product_data)
            return response
        except Exception as e:
            logger.error(f"Ошибка обновления цены товара {product_id}: {e}")
            raise
    
    async def get_supplier_info(self, supplier_id: str) -> Dict:
        """Получение информации о поставщике"""
        try:
            response = await self._make_request("GET", f"entity/counterparty/{supplier_id}")
            return response
        except Exception as e:
            logger.error(f"Ошибка получения информации о поставщике {supplier_id}: {e}")
            raise
    
    async def get_stock_info(self) -> Dict:
        """Получение информации об остатках всех товаров"""
        try:
            response = await self._make_request("GET", "report/stock/all")
            return response
        except Exception as e:
            logger.error(f"Ошибка получения информации об остатках: {e}")
            raise
    
    async def get_organization_info(self) -> Dict:
        """Получение информации об организации"""
        try:
            response = await self._make_request("GET", "entity/organization")
            return response
        except Exception as e:
            logger.error(f"Ошибка получения информации об организации: {e}")
            raise
    
    async def create_supplier(self, supplier_data: Dict) -> Dict:
        """Создание поставщика"""
        try:
            counterparty_data = {
                "name": supplier_data.get("name"),
                "companyType": "legal",
                "legalTitle": supplier_data.get("legal_title", ""),
                "inn": supplier_data.get("inn", ""),
                "kpp": supplier_data.get("kpp", ""),
                "actualAddress": supplier_data.get("address", ""),
                "phone": supplier_data.get("phone", ""),
                "email": supplier_data.get("email", "")
            }
            
            response = await self._make_request("POST", "entity/counterparty", data=counterparty_data)
            return response
        except Exception as e:
            logger.error(f"Ошибка создания поставщика: {e}")
            raise
    
    async def get_purchase_orders(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict:
        """Получение заказов на поставку"""
        try:
            params = {}
            
            if start_date:
                params["momentFrom"] = f"{start_date}T00:00:00"
            if end_date:
                params["momentTo"] = f"{end_date}T23:59:59"
            if status:
                params["filter"] = f"state={status}"
            
            response = await self._make_request("GET", "entity/purchaseorder", params=params)
            return response
        except Exception as e:
            logger.error(f"Ошибка получения заказов на поставку: {e}")
            raise
    
    async def update_purchase_order(self, order_id: str, order_data: Dict) -> Dict:
        """Обновление заказа на поставку"""
        try:
            response = await self._make_request("PUT", f"entity/purchaseorder/{order_id}", data=order_data)
            return response
        except Exception as e:
            logger.error(f"Ошибка обновления заказа {order_id}: {e}")
            raise
    
    async def delete_purchase_order(self, order_id: str) -> bool:
        """Удаление заказа на поставку"""
        try:
            await self._make_request("DELETE", f"entity/purchaseorder/{order_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления заказа {order_id}: {e}")
            return False
    
    async def get_warehouses(self) -> Dict:
        """Получение списка складов"""
        try:
            response = await self._make_request("GET", "entity/store")
            return response
        except Exception as e:
            logger.error(f"Ошибка получения списка складов: {e}")
            raise
    
    async def get_warehouse_stock(self, warehouse_id: str) -> Dict:
        """Получение остатков по конкретному складу"""
        try:
            response = await self._make_request(
                "GET", 
                "report/stock/all",
                params={"storeId": warehouse_id}
            )
            return response
        except Exception as e:
            logger.error(f"Ошибка получения остатков по складу {warehouse_id}: {e}")
            raise
    
    async def health_check(self) -> Dict:
        """Проверка здоровья API МойСклад"""
        try:
            # Простой запрос для проверки доступности API
            response = await self._make_request("GET", "entity/organization")
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "api_version": "1.2",
                "organization_count": len(response.get("rows", []))
            }
        except Exception as e:
            logger.error(f"Ошибка проверки здоровья API МойСклад: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_token_info(self) -> Dict:
        """Получение информации о токене доступа"""
        try:
            # Запрос информации о текущем пользователе
            response = await self._make_request("GET", "entity/employee/current")
            return {
                "user_id": response.get("id"),
                "user_name": response.get("name"),
                "email": response.get("email"),
                "position": response.get("position"),
                "permissions": response.get("permissions", [])
            }
        except Exception as e:
            logger.error(f"Ошибка получения информации о токене: {e}")
            raise 