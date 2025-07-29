import smtplib
import logging
from typing import List, Optional, Dict
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        self.sender_email = settings.sender_email
        self.sender_name = settings.sender_name
    
    async def initialize(self):
        """Инициализация сервиса"""
        try:
            # Проверка подключения к SMTP серверу
            await self.test_connection()
            logger.info("Email сервис инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации Email сервиса: {e}")
            raise
    
    async def close(self):
        """Закрытие сервиса"""
        logger.info("Email сервис закрыт")
    
    async def test_connection(self) -> bool:
        """Тест подключения к SMTP серверу"""
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                logger.info("SMTP сервер подключен успешно")
                return True
        except Exception as e:
            logger.error(f"Ошибка подключения к SMTP серверу: {e}")
            return False
    
    async def send_email(self, subject: str, message: str, recipients: List[str], 
                        html_content: str = None, attachments: List[Dict] = None) -> Dict:
        """Отправить email"""
        try:
            msg = MIMEMultipart()
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            msg['To'] = ", ".join(recipients)
            msg['Subject'] = subject
            
            # Текстовое содержимое
            text_part = MIMEText(message, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # HTML содержимое (если есть)
            if html_content:
                html_part = MIMEText(html_content, 'html', 'utf-8')
                msg.attach(html_part)
            
            # Вложения (если есть)
            if attachments:
                for attachment in attachments:
                    filename = attachment.get('filename', 'attachment')
                    content = attachment.get('content', b'')
                    content_type = attachment.get('content_type', 'application/octet-stream')
                    
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(content)
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename= {filename}')
                    msg.attach(part)
            
            # Отправка
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                text = msg.as_string()
                server.sendmail(self.sender_email, recipients, text)
            
            return {
                "status": "success",
                "recipients": recipients,
                "subject": subject,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка отправки email: {e}")
            return {
                "status": "error",
                "error": str(e),
                "recipients": recipients,
                "timestamp": datetime.now().isoformat()
            }
    
    async def send_purchase_alert_email(self, alert_data: Dict) -> Dict:
        """Отправить email с алертом закупки"""
        try:
            product_name = alert_data.get("product_name", "")
            quantity = alert_data.get("quantity", 0)
            urgency = alert_data.get("urgency", "normal")
            
            subject = f"🚨 Алерт закупки: {product_name}"
            
            message = f"""
Алерт закупки

Товар: {product_name}
Количество: {quantity}
Срочность: {urgency}
Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Это автоматическое уведомление от системы Horiens Purchase Agent.
            """
            
            html_content = f"""
            <html>
            <body>
                <h2>🚨 Алерт закупки</h2>
                <p><strong>Товар:</strong> {product_name}</p>
                <p><strong>Количество:</strong> {quantity}</p>
                <p><strong>Срочность:</strong> {urgency}</p>
                <p><strong>Время:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <hr>
                <p><em>Это автоматическое уведомление от системы Horiens Purchase Agent.</em></p>
            </body>
            </html>
            """
            
            return await self.send_email(
                subject=subject,
                message=message,
                recipients=[settings.admin_email],
                html_content=html_content
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки email алерта закупки: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def send_stock_alert_email(self, alert_data: Dict) -> Dict:
        """Отправить email с алертом склада"""
        try:
            product_name = alert_data.get("product_name", "")
            current_stock = alert_data.get("current_stock", 0)
            min_stock = alert_data.get("min_stock", 0)
            
            subject = f"📦 Алерт склада: {product_name}"
            
            message = f"""
Алерт склада

Товар: {product_name}
Текущий остаток: {current_stock}
Минимальный остаток: {min_stock}
Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Это автоматическое уведомление от системы Horiens Purchase Agent.
            """
            
            html_content = f"""
            <html>
            <body>
                <h2>📦 Алерт склада</h2>
                <p><strong>Товар:</strong> {product_name}</p>
                <p><strong>Текущий остаток:</strong> {current_stock}</p>
                <p><strong>Минимальный остаток:</strong> {min_stock}</p>
                <p><strong>Время:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <hr>
                <p><em>Это автоматическое уведомление от системы Horiens Purchase Agent.</em></p>
            </body>
            </html>
            """
            
            return await self.send_email(
                subject=subject,
                message=message,
                recipients=[settings.admin_email],
                html_content=html_content
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки email алерта склада: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def send_weekly_report_email(self, report_data: Dict) -> Dict:
        """Отправить еженедельный отчет по email"""
        try:
            subject = "📊 Еженедельный отчет Horiens Purchase Agent"
            
            message = f"""
Еженедельный отчет

Период: {report_data.get('period', 'Неизвестно')}
Всего закупок: {report_data.get('total_purchases', 0)}
Общая сумма: {report_data.get('total_amount', 0)}
Алертов: {report_data.get('total_alerts', 0)}

Это автоматический отчет от системы Horiens Purchase Agent.
            """
            
            html_content = f"""
            <html>
            <body>
                <h2>📊 Еженедельный отчет</h2>
                <p><strong>Период:</strong> {report_data.get('period', 'Неизвестно')}</p>
                <p><strong>Всего закупок:</strong> {report_data.get('total_purchases', 0)}</p>
                <p><strong>Общая сумма:</strong> {report_data.get('total_amount', 0)}</p>
                <p><strong>Алертов:</strong> {report_data.get('total_alerts', 0)}</p>
                <hr>
                <p><em>Это автоматический отчет от системы Horiens Purchase Agent.</em></p>
            </body>
            </html>
            """
            
            return await self.send_email(
                subject=subject,
                message=message,
                recipients=[settings.admin_email],
                html_content=html_content
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки еженедельного отчета: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 