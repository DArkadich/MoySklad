import os
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

class StockAwareTrainer:
    def __init__(self):
        self.data_path = "/app/data"
        self.models_path = "/app/ml-models"
        os.makedirs(self.models_path, exist_ok=True)
        
    def load_data(self):
        """Загружает данные продаж и остатков"""
        demands_file = os.path.join(self.data_path, "demands.csv")
        stock_file = os.path.join(self.data_path, "stock_history.csv")
        
        if not os.path.exists(demands_file):
            logger.error(f"Файл {demands_file} не найден")
            return None, None
            
        logger.info(f"Загружаем данные продаж из {demands_file}")
        sales_df = pd.read_csv(demands_file)
        logger.info(f"Загружено {len(sales_df)} записей продаж")
        
        stock_df = None
        if os.path.exists(stock_file):
            logger.info(f"Загружаем данные остатков из {stock_file}")
            stock_df = pd.read_csv(stock_file)
            logger.info(f"Загружено {len(stock_df)} записей остатков")
        else:
            logger.warning(f"Файл {stock_file} не найден - будем использовать упрощенный алгоритм")
        
        return sales_df, stock_df
    
    def extract_sales_by_product(self, df):
        """Извлекает продажи по товарам"""
        logger.info("Извлекаем продажи по товарам...")
        
        sales_by_product = {}
        
        for _, row in df.iterrows():
            product_code = row.get('product_code')
            product_name = row.get('product_name', 'Unknown')
            quantity = row.get('quantity', 0)
            date_str = row.get('date', '')
            
            if pd.isna(product_code) or pd.isna(quantity) or pd.isna(date_str):
                continue
                
            try:
                date = pd.to_datetime(date_str).date()
                quantity = float(quantity)
                
                if product_code not in sales_by_product:
                    sales_by_product[product_code] = {
                        'name': product_name,
                        'sales': []
                    }
                
                sales_by_product[product_code]['sales'].append({
                    'date': date,
                    'quantity': quantity
                })
                
            except (ValueError, TypeError) as e:
                logger.debug(f"Ошибка парсинга строки: {e}")
                continue
        
        logger.info(f"Извлечено продаж для {len(sales_by_product)} товаров")
        return sales_by_product
    
    def calculate_availability_days(self, product_code, stock_df, start_date, end_date):
        """Вычисляет количество дней когда товар был в наличии (остаток > 3)"""
        if stock_df is None:
            # Если нет данных об остатках, считаем все дни доступными
            return (end_date - start_date).days + 1
        
        # Фильтруем данные по товару и периоду
        product_stock = stock_df[
            (stock_df['product_code'] == str(product_code)) &
            (pd.to_datetime(stock_df['date']) >= pd.to_datetime(start_date)) &
            (pd.to_datetime(stock_df['date']) <= pd.to_datetime(end_date))
        ]
        
        if len(product_stock) == 0:
            return 0
        
        # Считаем дни когда остаток > 3
        available_days = len(product_stock[product_stock['available'] > 3])
        
        logger.debug(f"Товар {product_code}: {available_days} дней в наличии из {len(product_stock)} дней")
        
        return available_days
    
    def train_models_with_stock_awareness(self, sales_by_product, stock_df):
        """Обучает модели с учетом дней доступности товара"""
        logger.info("Обучаем модели с учетом остатков...")
        
        trained_models = 0
        errors = 0
        
        for product_code, data in sales_by_product.items():
            try:
                if len(data['sales']) < 5:  # Минимум 5 продаж для обучения
                    logger.debug(f"Товар {product_code}: недостаточно данных ({len(data['sales'])} продаж)")
                    continue
                
                # Сортируем продажи по дате
                sales = sorted(data['sales'], key=lambda x: x['date'])
                
                # Определяем период продаж
                start_date = sales[0]['date']
                end_date = sales[-1]['date']
                total_quantity = sum(sale['quantity'] for sale in sales)
                
                # Вычисляем количество дней когда товар был в наличии
                available_days = self.calculate_availability_days(product_code, stock_df, start_date, end_date)
                
                if available_days == 0:
                    logger.debug(f"Товар {product_code}: нет данных о доступности")
                    continue
                
                # Вычисляем среднее потребление за день доступности
                avg_consumption = total_quantity / available_days
                
                # Определяем критический остаток (50% от среднего потребления, минимум 3)
                critical_stock = max(3, avg_consumption * 0.5)
                
                # Сохраняем модель
                model_data = {
                    'product_code': product_code,
                    'product_name': data['name'],
                    'avg_consumption': avg_consumption,
                    'critical_stock': critical_stock,
                    'total_sales': total_quantity,
                    'sales_count': len(sales),
                    'available_days': available_days,
                    'total_days': (end_date - start_date).days + 1,
                    'last_sale_date': sales[-1]['date'].isoformat(),
                    'first_sale_date': sales[0]['date'].isoformat()
                }
                
                # Сохраняем в CSV
                model_file = os.path.join(self.models_path, f"model_{product_code}.csv")
                pd.DataFrame([model_data]).to_csv(model_file, index=False)
                
                trained_models += 1
                logger.info(f"Обучена модель для {product_code} ({data['name']}): "
                          f"среднее потребление {avg_consumption:.2f} (за день доступности), "
                          f"критический остаток {critical_stock:.1f}, "
                          f"дней в наличии: {available_days}")
                
            except Exception as e:
                errors += 1
                logger.error(f"Ошибка обучения модели для {product_code}: {e}")
        
        logger.info(f"Обучение завершено. Успешно: {trained_models}, Ошибок: {errors}")
        return trained_models, errors

async def main():
    trainer = StockAwareTrainer()
    
    # Загружаем данные
    sales_df, stock_df = trainer.load_data()
    if sales_df is None:
        return
    
    # Извлекаем продажи по товарам
    sales_by_product = trainer.extract_sales_by_product(sales_df)
    
    if not sales_by_product:
        logger.error("Не удалось извлечь продажи по товарам")
        return
    
    # Обучаем модели с учетом остатков
    trainer.train_models_with_stock_awareness(sales_by_product, stock_df)

if __name__ == "__main__":
    asyncio.run(main()) 