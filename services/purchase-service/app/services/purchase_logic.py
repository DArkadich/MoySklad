"""
Бизнес-логика закупок
Управление правилами закупок и расчетами
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

from app.models.purchase_models import (
    ProductInfo, InventoryStatus, PurchaseRecommendation, 
    ForecastData, PurchaseRequest, PurchaseResponse
)
from app.services.moysklad_integration import MoySkladService
from app.services.ml_service import MLService

logger = logging.getLogger(__name__)

class ProductType(Enum):
    """Типы продуктов с учетом сроков доставки"""
    SOLUTION_360_500 = "solution_360_500"  # Растворы 360/500 мл
    SOLUTION_120 = "solution_120"          # Растворы 120 мл
    MONTHLY_LENSES = "monthly_lenses"      # Месячные линзы
    DAILY_LENSES = "daily_lenses"          # Однодневные линзы

class DeliveryTime(Enum):
    """Сроки доставки в днях"""
    SOLUTION_360_500 = 30  # Растворы 360/500 мл: 30-45 дней
    SOLUTION_120 = 30      # Растворы 120 мл: 30-45 дней
    MONTHLY_LENSES = 10    # Месячные линзы: 10-15 дней
    DAILY_LENSES = 10      # Однодневные линзы: 10-15 дней
    MANUFACTURING_TIME = 45  # Срок изготовления: 30-60 дней (берем среднее)

class PurchaseLogicService:
    def __init__(self):
        self.moysklad_service = MoySkladService()
        self.ml_service = MLService()
        
        # Правила закупок с учетом сроков доставки
        self.purchase_rules = {
            ProductType.SOLUTION_360_500: {
                "min_batch": 5000,
                "multiplicity": 24,
                "delivery_time": DeliveryTime.SOLUTION_360_500.value,
                "manufacturing_time": DeliveryTime.MANUFACTURING_TIME.value,
                "safety_stock_days": 30,  # Страховой запас на 30 дней
                "reorder_point_days": 45   # Точка перезаказа за 45 дней до исчерпания
            },
            ProductType.SOLUTION_120: {
                "min_batch": 5000,
                "multiplicity": 48,
                "delivery_time": DeliveryTime.SOLUTION_120.value,
                "manufacturing_time": DeliveryTime.MANUFACTURING_TIME.value,
                "safety_stock_days": 30,
                "reorder_point_days": 45
            },
            ProductType.MONTHLY_LENSES: {
                "min_batch": 5000,
                "multiplicity": 50,
                "delivery_time": DeliveryTime.MONTHLY_LENSES.value,
                "manufacturing_time": DeliveryTime.MANUFACTURING_TIME.value,
                "safety_stock_days": 15,  # Меньший страховой запас для быстрой доставки
                "reorder_point_days": 20
            },
            ProductType.DAILY_LENSES: {
                "min_batch": 3000,
                "multiplicity": 30,
                "delivery_time": DeliveryTime.DAILY_LENSES.value,
                "manufacturing_time": DeliveryTime.MANUFACTURING_TIME.value,
                "safety_stock_days": 15,
                "reorder_point_days": 20
            }
        }
    
    def get_product_type(self, product_name: str) -> ProductType:
        """Определение типа продукта по названию"""
        product_name_lower = product_name.lower()
        
        if "раствор" in product_name_lower and ("360" in product_name_lower or "500" in product_name_lower):
            return ProductType.SOLUTION_360_500
        elif "раствор" in product_name_lower and "120" in product_name_lower:
            return ProductType.SOLUTION_120
        elif "месячные" in product_name_lower or "месяц" in product_name_lower:
            return ProductType.MONTHLY_LENSES
        elif "однодневные" in product_name_lower or "день" in product_name_lower:
            return ProductType.DAILY_LENSES
        else:
            # По умолчанию считаем раствором
            return ProductType.SOLUTION_360_500
    
    async def get_products_info(self) -> List[ProductInfo]:
        """Получение информации о продуктах с учетом сроков доставки"""
        try:
            products = await self.moysklad_service.get_all_products()
            product_info_list = []
            
            for product in products.get("rows", []):
                product_type = self.get_product_type(product.get("name", ""))
                rules = self.purchase_rules[product_type]
                
                product_info = ProductInfo(
                    id=product.get("id"),
                    name=product.get("name"),
                    code=product.get("code"),
                    product_type=product_type.value,
                    min_batch=rules["min_batch"],
                    multiplicity=rules["multiplicity"],
                    delivery_time_days=rules["delivery_time"],
                    manufacturing_time_days=rules["manufacturing_time"],
                    safety_stock_days=rules["safety_stock_days"],
                    reorder_point_days=rules["reorder_point_days"]
                )
                product_info_list.append(product_info)
            
            return product_info_list
        except Exception as e:
            logger.error(f"Ошибка получения информации о продуктах: {e}")
            raise
    
    async def get_inventory_status(self, product_id: Optional[str] = None) -> List[InventoryStatus]:
        """Получение статуса склада с учетом прогнозов и сроков доставки"""
        try:
            # Получение текущих остатков
            stock_data = await self.moysklad_service.get_stock_info()
            inventory_status_list = []
            
            for item in stock_data.get("rows", []):
                if product_id and item.get("meta", {}).get("href", "").split("/")[-1] != product_id:
                    continue
                
                product_name = item.get("name", "")
                current_stock = item.get("quantity", 0)
                product_type = self.get_product_type(product_name)
                rules = self.purchase_rules[product_type]
                
                # Получение прогноза спроса
                forecast = await self.ml_service.get_forecast(
                    product_id=item.get("meta", {}).get("href", "").split("/")[-1],
                    days_ahead=rules["delivery_time"] + rules["manufacturing_time"] + rules["safety_stock_days"]
                )
                
                # Расчет критических дат
                daily_consumption = forecast.get("daily_consumption", 0)
                days_until_stockout = current_stock / daily_consumption if daily_consumption > 0 else float('inf')
                
                # Расчет точки перезаказа
                reorder_point = daily_consumption * rules["reorder_point_days"]
                is_reorder_needed = current_stock <= reorder_point
                
                # Расчет рекомендуемого количества заказа
                recommended_quantity = self._calculate_recommended_quantity(
                    current_stock=current_stock,
                    daily_consumption=daily_consumption,
                    delivery_time=rules["delivery_time"],
                    manufacturing_time=rules["manufacturing_time"],
                    safety_stock_days=rules["safety_stock_days"],
                    min_batch=rules["min_batch"],
                    multiplicity=rules["multiplicity"]
                )
                
                inventory_status = InventoryStatus(
                    product_id=item.get("meta", {}).get("href", "").split("/")[-1],
                    product_name=product_name,
                    current_stock=current_stock,
                    product_type=product_type.value,
                    daily_consumption=daily_consumption,
                    days_until_stockout=days_until_stockout,
                    reorder_point=reorder_point,
                    is_reorder_needed=is_reorder_needed,
                    recommended_quantity=recommended_quantity,
                    delivery_time_days=rules["delivery_time"],
                    manufacturing_time_days=rules["manufacturing_time"],
                    safety_stock_days=rules["safety_stock_days"]
                )
                inventory_status_list.append(inventory_status)
            
            return inventory_status_list
        except Exception as e:
            logger.error(f"Ошибка получения статуса склада: {e}")
            raise
    
    def _calculate_recommended_quantity(
        self, 
        current_stock: float, 
        daily_consumption: float,
        delivery_time: int,
        manufacturing_time: int,
        safety_stock_days: int,
        min_batch: int,
        multiplicity: int
    ) -> int:
        """Расчет рекомендуемого количества заказа с учетом сроков доставки"""
        if daily_consumption <= 0:
            return min_batch
        
        # Расчет необходимого количества на период доставки + изготовления + страховой запас
        total_days = delivery_time + manufacturing_time + safety_stock_days
        needed_quantity = daily_consumption * total_days
        
        # Учет текущего остатка
        required_quantity = max(0, needed_quantity - current_stock)
        
        # Применение минимальной партии и кратности
        if required_quantity < min_batch:
            required_quantity = min_batch
        else:
            # Округление до кратности
            remainder = required_quantity % multiplicity
            if remainder > 0:
                required_quantity += multiplicity - remainder
        
        return int(required_quantity)
    
    async def generate_purchase_recommendations(self) -> List[PurchaseRecommendation]:
        """Генерация рекомендаций по закупкам с учетом сроков доставки"""
        try:
            inventory_status_list = await self.get_inventory_status()
            recommendations = []
            
            for status in inventory_status_list:
                if not status.is_reorder_needed:
                    continue
                
                # Определение срочности заказа
                urgency = self._calculate_urgency(
                    days_until_stockout=status.days_until_stockout,
                    delivery_time=status.delivery_time_days,
                    manufacturing_time=status.manufacturing_time_days
                )
                
                # Определение уровня уверенности
                confidence = self._calculate_confidence(
                    daily_consumption=status.daily_consumption,
                    forecast_accuracy=0.85  # Предполагаемая точность прогноза
                )
                
                # Расчет оптимальной даты заказа
                optimal_order_date = self._calculate_optimal_order_date(
                    days_until_stockout=status.days_until_stockout,
                    delivery_time=status.delivery_time_days,
                    manufacturing_time=status.manufacturing_time_days
                )
                
                # Генерация обоснования
                reasoning = self._generate_reasoning(
                    product_name=status.product_name,
                    current_stock=status.current_stock,
                    daily_consumption=status.daily_consumption,
                    days_until_stockout=status.days_until_stockout,
                    delivery_time=status.delivery_time_days,
                    manufacturing_time=status.manufacturing_time_days,
                    urgency=urgency
                )
                
                recommendation = PurchaseRecommendation(
                    product_id=status.product_id,
                    product_name=status.product_name,
                    product_type=status.product_type,
                    recommended_quantity=status.recommended_quantity,
                    urgency=urgency,
                    confidence=confidence,
                    reasoning=reasoning,
                    optimal_order_date=optimal_order_date,
                    delivery_time_days=status.delivery_time_days,
                    manufacturing_time_days=status.manufacturing_time_days
                )
                recommendations.append(recommendation)
            
            # Сортировка по срочности
            recommendations.sort(key=lambda x: x.urgency, reverse=True)
            return recommendations
        except Exception as e:
            logger.error(f"Ошибка генерации рекомендаций: {e}")
            raise
    
    def _calculate_urgency(
        self, 
        days_until_stockout: float, 
        delivery_time: int,
        manufacturing_time: int
    ) -> str:
        """Расчет срочности заказа"""
        total_lead_time = delivery_time + manufacturing_time
        
        if days_until_stockout <= total_lead_time:
            return "critical"
        elif days_until_stockout <= total_lead_time + 30:
            return "high"
        elif days_until_stockout <= total_lead_time + 60:
            return "medium"
        else:
            return "low"
    
    def _calculate_confidence(self, daily_consumption: float, forecast_accuracy: float) -> float:
        """Расчет уровня уверенности в рекомендации"""
        if daily_consumption <= 0:
            return 0.0
        
        # Базовая уверенность на основе точности прогноза
        base_confidence = forecast_accuracy
        
        # Корректировка на основе стабильности потребления
        # (упрощенная логика - в реальности нужен анализ исторических данных)
        if daily_consumption > 100:
            base_confidence += 0.1
        elif daily_consumption < 10:
            base_confidence -= 0.1
        
        return min(1.0, max(0.0, base_confidence))
    
    def _calculate_optimal_order_date(
        self, 
        days_until_stockout: float,
        delivery_time: int,
        manufacturing_time: int
    ) -> datetime:
        """Расчет оптимальной даты заказа"""
        total_lead_time = delivery_time + manufacturing_time
        safety_margin = 7  # Неделя в запасе
        
        optimal_days_before_stockout = total_lead_time + safety_margin
        order_date = datetime.now() + timedelta(days=days_until_stockout - optimal_days_before_stockout)
        
        return order_date
    
    def _generate_reasoning(
        self,
        product_name: str,
        current_stock: float,
        daily_consumption: float,
        days_until_stockout: float,
        delivery_time: int,
        manufacturing_time: int,
        urgency: str
    ) -> str:
        """Генерация обоснования рекомендации"""
        reasoning = f"Продукт: {product_name}\n"
        reasoning += f"Текущий остаток: {current_stock:.0f} шт\n"
        reasoning += f"Среднее потребление: {daily_consumption:.1f} шт/день\n"
        reasoning += f"Дней до исчерпания: {days_until_stockout:.0f}\n"
        reasoning += f"Срок изготовления: {manufacturing_time} дней\n"
        reasoning += f"Срок доставки: {delivery_time} дней\n"
        reasoning += f"Общий срок поставки: {manufacturing_time + delivery_time} дней\n"
        reasoning += f"Срочность: {urgency}\n"
        
        if urgency == "critical":
            reasoning += "⚠️ КРИТИЧЕСКАЯ СИТУАЦИЯ: Заказ необходимо разместить немедленно!"
        elif urgency == "high":
            reasoning += "🚨 ВЫСОКАЯ СРОЧНОСТЬ: Заказ рекомендуется разместить в ближайшие дни"
        elif urgency == "medium":
            reasoning += "📅 СРЕДНЯЯ СРОЧНОСТЬ: Заказ можно планировать в течение недели"
        else:
            reasoning += "📋 НИЗКАЯ СРОЧНОСТЬ: Заказ можно планировать заблаговременно"
        
        return reasoning
    
    async def validate_purchase_request(self, request: PurchaseRequest) -> Tuple[bool, str]:
        """Валидация запроса на закупку с учетом сроков доставки"""
        try:
            product_info = await self.moysklad_service.get_product_info(request.product_id)
            product_type = self.get_product_type(product_info.get("name", ""))
            rules = self.purchase_rules[product_type]
            
            # Проверка минимальной партии
            if request.quantity < rules["min_batch"]:
                return False, f"Количество {request.quantity} меньше минимальной партии {rules['min_batch']}"
            
            # Проверка кратности
            if request.quantity % rules["multiplicity"] != 0:
                return False, f"Количество {request.quantity} не кратно {rules['multiplicity']}"
            
            # Проверка сроков доставки
            if request.expected_delivery_date:
                min_delivery_date = datetime.now() + timedelta(days=rules["delivery_time"] + rules["manufacturing_time"])
                if request.expected_delivery_date < min_delivery_date:
                    return False, f"Ожидаемая дата доставки раньше минимально возможной ({min_delivery_date.strftime('%Y-%m-%d')})"
            
            return True, "Запрос валиден"
        except Exception as e:
            logger.error(f"Ошибка валидации запроса: {e}")
            return False, f"Ошибка валидации: {str(e)}"
    
    async def execute_purchase(self, request: PurchaseRequest) -> PurchaseResponse:
        """Выполнение закупки с учетом сроков доставки"""
        try:
            # Валидация запроса
            is_valid, message = await self.validate_purchase_request(request)
            if not is_valid:
                return PurchaseResponse(
                    success=False,
                    message=message,
                    order_id=None,
                    estimated_delivery_date=None
                )
            
            # Получение информации о продукте
            product_info = await self.moysklad_service.get_product_info(request.product_id)
            product_type = self.get_product_type(product_info.get("name", ""))
            rules = self.purchase_rules[product_type]
            
            # Расчет ожидаемой даты доставки
            manufacturing_time = rules["manufacturing_time"]
            delivery_time = rules["delivery_time"]
            total_lead_time = manufacturing_time + delivery_time
            
            estimated_delivery_date = datetime.now() + timedelta(days=total_lead_time)
            
            # Создание заказа в МойСклад
            order_data = {
                "name": f"Заказ {product_info.get('name', '')}",
                "description": f"Автоматический заказ через Horiens Purchase Agent. Количество: {request.quantity}",
                "moment": datetime.now().isoformat(),
                "organization": {
                    "meta": {
                        "href": "https://api.moysklad.ru/api/remap/1.2/entity/organization/your_org_id",
                        "type": "organization",
                        "mediaType": "application/json"
                    }
                },
                "positions": [
                    {
                        "quantity": request.quantity,
                        "price": product_info.get("salePrices", [{}])[0].get("value", 0) * 100,
                        "assortment": {
                            "meta": {
                                "href": f"https://api.moysklad.ru/api/remap/1.2/entity/product/{request.product_id}",
                                "type": "product",
                                "mediaType": "application/json"
                            }
                        }
                    }
                ]
            }
            
            order_result = await self.moysklad_service.create_purchase_order(order_data)
            
            return PurchaseResponse(
                success=True,
                message=f"Заказ успешно создан. Ожидаемая доставка: {estimated_delivery_date.strftime('%Y-%m-%d')}",
                order_id=order_result.get("id"),
                estimated_delivery_date=estimated_delivery_date.isoformat(),
                manufacturing_time_days=manufacturing_time,
                delivery_time_days=delivery_time,
                total_lead_time_days=total_lead_time
            )
        except Exception as e:
            logger.error(f"Ошибка выполнения закупки: {e}")
            return PurchaseResponse(
                success=False,
                message=f"Ошибка создания заказа: {str(e)}",
                order_id=None,
                estimated_delivery_date=None
            ) 