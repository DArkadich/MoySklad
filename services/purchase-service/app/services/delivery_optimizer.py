import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from app.services.moysklad_integration import MoySkladService

logger = logging.getLogger(__name__)

@dataclass
class DeliverySchedule:
    """Расписание доставки"""
    product_id: str
    product_name: str
    product_type: str
    quantity: int
    manufacturing_start: datetime
    manufacturing_end: datetime
    delivery_start: datetime
    delivery_end: datetime
    can_combine: bool
    delivery_partner: str

class DeliveryOptimizer:
    """Сервис оптимизации доставки с учетом возможности одновременной доставки"""
    
    def __init__(self):
        self.moysklad_service = MoySkladService()
        
        # Сроки доставки и изготовления
        self.delivery_times = {
            "solution_360_500": {"manufacturing": 45, "delivery": 30, "can_combine": True},
            "solution_120": {"manufacturing": 45, "delivery": 30, "can_combine": True},
            "monthly_lenses": {"manufacturing": 45, "delivery": 10, "can_combine": False},
            "daily_lenses": {"manufacturing": 45, "delivery": 10, "can_combine": False}
        }
        
        # Партнеры доставки
        self.delivery_partners = {
            "solutions": ["ТК Деловые Линии", "ТК ПЭК", "ТК Байкал-Сервис"],
            "lenses": ["DHL Express", "FedEx", "EMS"],
            "combined": ["ТК Деловые Линии", "ТК ПЭК"]
        }
    
    async def optimize_delivery_schedule(
        self, 
        purchase_orders: List[Dict]
    ) -> List[DeliverySchedule]:
        """Оптимизация расписания доставки"""
        try:
            schedules = []
            
            for order in purchase_orders:
                product_type = self._get_product_type(order["product_name"])
                delivery_config = self.delivery_times[product_type]
                
                # Расчет дат изготовления
                manufacturing_start = datetime.now()
                manufacturing_end = manufacturing_start + timedelta(days=delivery_config["manufacturing"])
                
                # Расчет дат доставки
                delivery_start = manufacturing_end
                delivery_end = delivery_start + timedelta(days=delivery_config["delivery"])
                
                # Определение партнера доставки
                delivery_partner = self._select_delivery_partner(product_type)
                
                schedule = DeliverySchedule(
                    product_id=order["product_id"],
                    product_name=order["product_name"],
                    product_type=product_type,
                    quantity=order["quantity"],
                    manufacturing_start=manufacturing_start,
                    manufacturing_end=manufacturing_end,
                    delivery_start=delivery_start,
                    delivery_end=delivery_end,
                    can_combine=delivery_config["can_combine"],
                    delivery_partner=delivery_partner
                )
                schedules.append(schedule)
            
            # Оптимизация одновременной доставки
            optimized_schedules = self._optimize_combined_delivery(schedules)
            
            return optimized_schedules
        except Exception as e:
            logger.error(f"Ошибка оптимизации расписания доставки: {e}")
            raise
    
    def _get_product_type(self, product_name: str) -> str:
        """Определение типа продукта"""
        product_name_lower = product_name.lower()
        
        if "раствор" in product_name_lower and ("360" in product_name_lower or "500" in product_name_lower):
            return "solution_360_500"
        elif "раствор" in product_name_lower and "120" in product_name_lower:
            return "solution_120"
        elif "месячные" in product_name_lower or "месяц" in product_name_lower:
            return "monthly_lenses"
        elif "однодневные" in product_name_lower or "день" in product_name_lower:
            return "daily_lenses"
        else:
            return "solution_360_500"  # По умолчанию
    
    def _select_delivery_partner(self, product_type: str) -> str:
        """Выбор партнера доставки"""
        if product_type in ["solution_360_500", "solution_120"]:
            return self.delivery_partners["solutions"][0]  # Первый доступный
        elif product_type in ["monthly_lenses", "daily_lenses"]:
            return self.delivery_partners["lenses"][0]
        else:
            return self.delivery_partners["solutions"][0]
    
    def _optimize_combined_delivery(self, schedules: List[DeliverySchedule]) -> List[DeliverySchedule]:
        """Оптимизация одновременной доставки"""
        # Группировка по возможности комбинирования
        solutions = [s for s in schedules if s.can_combine and "solution" in s.product_type]
        lenses = [s for s in schedules if not s.can_combine or "lens" in s.product_type]
        
        optimized_schedules = []
        
        # Оптимизация доставки растворов
        if len(solutions) > 1:
            # Группировка растворов для одновременной доставки
            combined_solutions = self._combine_solutions_delivery(solutions)
            optimized_schedules.extend(combined_solutions)
        else:
            optimized_schedules.extend(solutions)
        
        # Добавление линз (без комбинирования)
        optimized_schedules.extend(lenses)
        
        return optimized_schedules
    
    def _combine_solutions_delivery(self, solutions: List[DeliverySchedule]) -> List[DeliverySchedule]:
        """Комбинирование доставки растворов"""
        if len(solutions) <= 1:
            return solutions
        
        # Группировка по срокам изготовления
        manufacturing_groups = {}
        for solution in solutions:
            manufacturing_end = solution.manufacturing_end
            if manufacturing_end not in manufacturing_groups:
                manufacturing_groups[manufacturing_end] = []
            manufacturing_groups[manufacturing_end].append(solution)
        
        combined_schedules = []
        
        for manufacturing_end, group in manufacturing_groups.items():
            if len(group) > 1:
                # Создание комбинированной доставки
                combined_schedule = self._create_combined_schedule(group)
                combined_schedules.append(combined_schedule)
            else:
                combined_schedules.extend(group)
        
        return combined_schedules
    
    def _create_combined_schedule(self, schedules: List[DeliverySchedule]) -> DeliverySchedule:
        """Создание комбинированного расписания доставки"""
        # Используем самое позднее время изготовления
        max_manufacturing_end = max(s.manufacturing_end for s in schedules)
        
        # Общее количество
        total_quantity = sum(s.quantity for s in schedules)
        
        # Создаем комбинированное расписание
        combined_schedule = DeliverySchedule(
            product_id="combined",
            product_name="Комбинированная доставка растворов",
            product_type="combined_solutions",
            quantity=total_quantity,
            manufacturing_start=min(s.manufacturing_start for s in schedules),
            manufacturing_end=max_manufacturing_end,
            delivery_start=max_manufacturing_end,
            delivery_end=max_manufacturing_end + timedelta(days=30),  # 30 дней для растворов
            can_combine=False,  # Уже скомбинировано
            delivery_partner=self.delivery_partners["combined"][0]
        )
        
        return combined_schedule
    
    async def calculate_delivery_cost(self, schedules: List[DeliverySchedule]) -> Dict:
        """Расчет стоимости доставки"""
        try:
            total_cost = 0
            cost_breakdown = {}
            
            for schedule in schedules:
                # Расчет стоимости доставки (упрощенная модель)
                base_cost = self._get_base_delivery_cost(schedule.product_type)
                weight_cost = self._calculate_weight_cost(schedule.quantity, schedule.product_type)
                distance_cost = self._get_distance_cost(schedule.delivery_partner)
                
                total_schedule_cost = base_cost + weight_cost + distance_cost
                
                cost_breakdown[schedule.product_id] = {
                    "base_cost": base_cost,
                    "weight_cost": weight_cost,
                    "distance_cost": distance_cost,
                    "total_cost": total_schedule_cost,
                    "delivery_partner": schedule.delivery_partner
                }
                
                total_cost += total_schedule_cost
            
            # Расчет экономии от комбинированной доставки
            savings = self._calculate_combined_delivery_savings(schedules)
            
            return {
                "total_cost": total_cost,
                "cost_breakdown": cost_breakdown,
                "savings": savings,
                "net_cost": total_cost - savings
            }
        except Exception as e:
            logger.error(f"Ошибка расчета стоимости доставки: {e}")
            raise
    
    def _get_base_delivery_cost(self, product_type: str) -> float:
        """Получение базовой стоимости доставки"""
        base_costs = {
            "solution_360_500": 5000,  # 5000 руб
            "solution_120": 4000,      # 4000 руб
            "monthly_lenses": 8000,    # 8000 руб (быстрая доставка)
            "daily_lenses": 8000,      # 8000 руб (быстрая доставка)
            "combined_solutions": 6000  # 6000 руб (экономия от комбинирования)
        }
        return base_costs.get(product_type, 5000)
    
    def _calculate_weight_cost(self, quantity: int, product_type: str) -> float:
        """Расчет стоимости по весу"""
        # Упрощенная модель расчета по весу
        weight_per_unit = {
            "solution_360_500": 0.5,  # кг
            "solution_120": 0.2,       # кг
            "monthly_lenses": 0.01,    # кг
            "daily_lenses": 0.01,      # кг
            "combined_solutions": 0.35  # кг (среднее)
        }
        
        weight = quantity * weight_per_unit.get(product_type, 0.1)
        cost_per_kg = 100  # руб/кг
        return weight * cost_per_kg
    
    def _get_distance_cost(self, delivery_partner: str) -> float:
        """Получение стоимости по расстоянию"""
        # Упрощенная модель
        distance_costs = {
            "ТК Деловые Линии": 2000,
            "ТК ПЭК": 1800,
            "ТК Байкал-Сервис": 2200,
            "DHL Express": 15000,
            "FedEx": 12000,
            "EMS": 8000
        }
        return distance_costs.get(delivery_partner, 3000)
    
    def _calculate_combined_delivery_savings(self, schedules: List[DeliverySchedule]) -> float:
        """Расчет экономии от комбинированной доставки"""
        combined_schedules = [s for s in schedules if s.product_type == "combined_solutions"]
        
        if not combined_schedules:
            return 0
        
        savings = 0
        for schedule in combined_schedules:
            # Экономия от комбинирования: 20% от стоимости доставки
            base_cost = self._get_base_delivery_cost("solution_360_500")
            weight_cost = self._calculate_weight_cost(schedule.quantity, "combined_solutions")
            distance_cost = self._get_distance_cost(schedule.delivery_partner)
            
            total_cost = base_cost + weight_cost + distance_cost
            savings += total_cost * 0.2
        
        return savings
    
    async def generate_delivery_report(self, schedules: List[DeliverySchedule]) -> Dict:
        """Генерация отчета по доставке"""
        try:
            # Группировка по типам доставки
            solutions_delivery = [s for s in schedules if "solution" in s.product_type]
            lenses_delivery = [s for s in schedules if "lens" in s.product_type]
            combined_delivery = [s for s in schedules if s.product_type == "combined_solutions"]
            
            # Расчет стоимости
            cost_analysis = await self.calculate_delivery_cost(schedules)
            
            # Статистика
            total_products = len(schedules)
            total_quantity = sum(s.quantity for s in schedules)
            avg_delivery_time = sum((s.delivery_end - s.delivery_start).days for s in schedules) / len(schedules) if schedules else 0
            
            report = {
                "summary": {
                    "total_products": total_products,
                    "total_quantity": total_quantity,
                    "avg_delivery_time_days": avg_delivery_time,
                    "combined_deliveries": len(combined_delivery),
                    "separate_deliveries": len(schedules) - len(combined_delivery)
                },
                "delivery_breakdown": {
                    "solutions": len(solutions_delivery),
                    "lenses": len(lenses_delivery),
                    "combined": len(combined_delivery)
                },
                "cost_analysis": cost_analysis,
                "schedules": [
                    {
                        "product_id": s.product_id,
                        "product_name": s.product_name,
                        "quantity": s.quantity,
                        "manufacturing_period": f"{s.manufacturing_start.strftime('%Y-%m-%d')} - {s.manufacturing_end.strftime('%Y-%m-%d')}",
                        "delivery_period": f"{s.delivery_start.strftime('%Y-%m-%d')} - {s.delivery_end.strftime('%Y-%m-%d')}",
                        "delivery_partner": s.delivery_partner,
                        "can_combine": s.can_combine
                    }
                    for s in schedules
                ]
            }
            
            return report
        except Exception as e:
            logger.error(f"Ошибка генерации отчета по доставке: {e}")
            raise
    
    async def get_optimal_delivery_date(self, product_type: str, quantity: int) -> datetime:
        """Получение оптимальной даты доставки"""
        try:
            delivery_config = self.delivery_times[product_type]
            
            # Расчет времени изготовления
            manufacturing_time = delivery_config["manufacturing"]
            
            # Расчет времени доставки
            delivery_time = delivery_config["delivery"]
            
            # Оптимальная дата = текущая дата + время изготовления + время доставки
            optimal_date = datetime.now() + timedelta(days=manufacturing_time + delivery_time)
            
            return optimal_date
        except Exception as e:
            logger.error(f"Ошибка расчета оптимальной даты доставки: {e}")
            raise 