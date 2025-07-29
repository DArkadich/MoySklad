"""
Модели данных для сервиса закупок
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ProductInfo(BaseModel):
    """Информация о продукте с учетом сроков доставки"""
    id: str
    name: str
    code: Optional[str] = None
    product_type: str
    min_batch: int
    multiplicity: int
    delivery_time_days: int
    manufacturing_time_days: int
    safety_stock_days: int
    reorder_point_days: int


class InventoryStatus(BaseModel):
    """Статус склада с учетом прогнозов и сроков доставки"""
    product_id: str
    product_name: str
    current_stock: float
    product_type: str
    daily_consumption: float
    days_until_stockout: float
    reorder_point: float
    is_reorder_needed: bool
    recommended_quantity: int
    delivery_time_days: int
    manufacturing_time_days: int
    safety_stock_days: int


class PurchaseRequest(BaseModel):
    """Запрос на закупку"""
    product_id: str
    quantity: int
    expected_delivery_date: Optional[datetime] = None
    notes: Optional[str] = None


class PurchaseResponse(BaseModel):
    """Ответ на запрос закупки"""
    success: bool
    message: str
    order_id: Optional[str] = None
    estimated_delivery_date: Optional[str] = None
    manufacturing_time_days: Optional[int] = None
    delivery_time_days: Optional[int] = None
    total_lead_time_days: Optional[int] = None


class PurchaseRecommendation(BaseModel):
    """Рекомендация по закупке с учетом сроков доставки"""
    product_id: str
    product_name: str
    product_type: str
    recommended_quantity: int
    urgency: str  # critical, high, medium, low
    confidence: float  # 0.0 - 1.0
    reasoning: str
    optimal_order_date: datetime
    delivery_time_days: int
    manufacturing_time_days: int


class ForecastData(BaseModel):
    """Данные прогнозирования"""
    product_id: str
    daily_consumption: float
    weekly_consumption: float
    monthly_consumption: float
    forecast_accuracy: float
    confidence_interval: Dict[str, float]
    seasonal_factors: Dict[str, float]
    trend_factor: float


class PurchaseAnalytics(BaseModel):
    """Аналитика закупок"""
    total_purchases: int
    total_amount: float
    average_order_value: float
    most_purchased_products: List[Dict[str, Any]]
    delivery_performance: Dict[str, float]
    stockout_incidents: int
    reorder_efficiency: float


class NotificationMessage(BaseModel):
    """Сообщение уведомления"""
    type: str  # telegram, email, sms
    message: str
    recipients: List[str]
    priority: str = "normal"  # low, normal, high, urgent


class SystemHealth(BaseModel):
    """Здоровье системы"""
    service: str
    status: str  # healthy, degraded, unhealthy
    timestamp: datetime
    response_time_ms: Optional[float] = None
    error_count: Optional[int] = None


class ErrorResponse(BaseModel):
    """Ответ с ошибкой"""
    error: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    request_id: Optional[str] = None


class SuccessResponse(BaseModel):
    """Успешный ответ"""
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class DeliveryOptimization(BaseModel):
    """Оптимизация доставки"""
    can_combine_delivery: bool
    combined_delivery_date: Optional[datetime] = None
    cost_savings: Optional[float] = None
    delivery_partners: List[str]
    optimal_routes: List[Dict[str, Any]]


class ManufacturingSchedule(BaseModel):
    """Расписание производства"""
    product_id: str
    manufacturing_start_date: datetime
    manufacturing_end_date: datetime
    production_capacity: int
    current_production: int
    bottlenecks: List[str]
    optimization_suggestions: List[str]


class SupplyChainAnalytics(BaseModel):
    """Аналитика цепочки поставок"""
    supplier_performance: Dict[str, float]
    delivery_reliability: float
    cost_efficiency: float
    lead_time_variability: float
    quality_metrics: Dict[str, float]
    risk_assessment: Dict[str, str]


class InventoryOptimization(BaseModel):
    """Оптимизация запасов"""
    current_inventory_value: float
    optimal_inventory_levels: Dict[str, int]
    excess_inventory: Dict[str, int]
    shortage_risk: Dict[str, float]
    cost_optimization_potential: float
    recommendations: List[str] 