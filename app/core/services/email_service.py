"""
Email Service for InfraZen
Handles sending emails using Beget SMTP or configured SMTP server
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP"""
    
    @staticmethod
    def send_email(
        to_email: str, 
        subject: str, 
        body_html: str, 
        body_text: Optional[str] = None
    ) -> bool:
        """
        Send an email using configured SMTP server (Beget by default)
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body_html: HTML body of the email
            body_text: Plain text body (optional, fallback for non-HTML clients)
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Get SMTP configuration from app config
            mail_server = current_app.config.get('MAIL_SERVER', 'smtp.beget.com')
            mail_port = current_app.config.get('MAIL_PORT', 465)
            mail_use_ssl = current_app.config.get('MAIL_USE_SSL', True)
            mail_username = current_app.config.get('MAIL_USERNAME')
            mail_password = current_app.config.get('MAIL_PASSWORD')
            mail_sender = current_app.config.get('MAIL_DEFAULT_SENDER', mail_username)
            
            # Validate configuration
            if not mail_username or not mail_password:
                logger.error("SMTP credentials not configured. Set MAIL_USERNAME and MAIL_PASSWORD in config.")
                return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = mail_sender
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add plain text part if provided
            if body_text:
                part1 = MIMEText(body_text, 'plain', 'utf-8')
                msg.attach(part1)
            
            # Add HTML part
            part2 = MIMEText(body_html, 'html', 'utf-8')
            msg.attach(part2)
            
            # Connect to SMTP server and send
            if mail_use_ssl:
                # Use SMTP_SSL for port 465
                with smtplib.SMTP_SSL(mail_server, mail_port, timeout=30) as server:
                    server.login(mail_username, mail_password)
                    server.send_message(msg)
            else:
                # Use SMTP with STARTTLS for port 587
                with smtplib.SMTP(mail_server, mail_port, timeout=30) as server:
                    server.starttls()
                    server.login(mail_username, mail_password)
                    server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {str(e)}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email to {to_email}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email to {to_email}: {str(e)}")
            return False
    
    @staticmethod
    def send_registration_confirmation(
        to_email: str, 
        username: str, 
        confirmation_link: Optional[str] = None
    ) -> bool:
        """
        Send a registration confirmation email
        
        Args:
            to_email: User's email address
            username: User's name
            confirmation_link: Optional link to confirm email
            
        Returns:
            bool: True if email sent successfully
        """
        subject = "Добро пожаловать в InfraZen - Подтвердите регистрацию"
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 10px 10px 0 0;
                    text-align: center;
                }}
                .content {{
                    background: #ffffff;
                    padding: 30px;
                    border: 1px solid #e2e8f0;
                    border-top: none;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background-color: #4299e1;
                    color: white;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: 600;
                    margin: 20px 0;
                }}
                .features {{
                    background: #f7fafc;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .features ul {{
                    margin: 10px 0;
                    padding-left: 20px;
                }}
                .footer {{
                    text-align: center;
                    color: #718096;
                    font-size: 14px;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #e2e8f0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1 style="margin: 0; font-size: 28px;">Добро пожаловать в InfraZen!</h1>
            </div>
            <div class="content">
                <p>Здравствуйте, {username}!</p>
                <p>Спасибо за регистрацию в <strong>InfraZen</strong> — интеллектуальной FinOps-платформе для управления облачными ресурсами и оптимизации расходов.</p>
                
                {f'''
                <div style="text-align: center;">
                    <a href="{confirmation_link}" class="button">Подтвердить email</a>
                </div>
                <p style="font-size: 14px; color: #718096;">Или скопируйте и вставьте эту ссылку в браузер:<br>
                <a href="{confirmation_link}" style="color: #4299e1; word-break: break-all;">{confirmation_link}</a></p>
                ''' if confirmation_link else ''}
                
                <div class="features">
                    <p><strong>Что вы можете делать в InfraZen:</strong></p>
                    <ul>
                        <li>🔗 Подключать несколько облачных провайдеров (Яндекс Облако, Selectel, Beget)</li>
                        <li>📊 Отслеживать облачные ресурсы в режиме реального времени</li>
                        <li>💰 Получать рекомендации по оптимизации расходов на основе AI</li>
                        <li>📈 Контролировать расходы и использование всей вашей инфраструктуры</li>
                        <li>🏢 Организовывать ресурсы по бизнес-контексту</li>
                    </ul>
                </div>
                
                <p>Готовы оптимизировать расходы на облачную инфраструктуру? Войдите в панель управления и начните подключать облачных провайдеров!</p>
                
                <p>Если у вас возникнут вопросы или понадобится помощь, обращайтесь в нашу службу поддержки.</p>
                
                <p style="margin-top: 30px;">С уважением,<br><strong>Команда InfraZen</strong></p>
            </div>
            <div class="footer">
                <p>© 2025 InfraZen. Все права защищены.</p>
                <p>Это автоматическое сообщение, пожалуйста, не отвечайте на него.</p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Добро пожаловать в InfraZen!
        
        Здравствуйте, {username}!
        
        Спасибо за регистрацию в InfraZen — интеллектуальной FinOps-платформе для управления облачными ресурсами и оптимизации расходов.
        
        {f'Подтвердите ваш email, перейдя по ссылке: {confirmation_link}' if confirmation_link else ''}
        
        Что вы можете делать в InfraZen:
        - Подключать несколько облачных провайдеров (Яндекс Облако, Selectel, Beget)
        - Отслеживать облачные ресурсы в режиме реального времени
        - Получать рекомендации по оптимизации расходов на основе AI
        - Контролировать расходы и использование всей вашей инфраструктуры
        - Организовывать ресурсы по бизнес-контексту
        
        Готовы оптимизировать расходы на облачную инфраструктуру? Войдите в панель управления и начните подключать облачных провайдеров!
        
        Если у вас возникнут вопросы или понадобится помощь, обращайтесь в нашу службу поддержки.
        
        С уважением,
        Команда InfraZen
        
        ---
        © 2025 InfraZen. Все права защищены.
        Это автоматическое сообщение, пожалуйста, не отвечайте на него.
        """
        
        return EmailService.send_email(to_email, subject, html_body, text_body)
    
    @staticmethod
    def send_email_confirmation(
        to_email: str, 
        username: str, 
        confirmation_link: str
    ) -> bool:
        """
        Send an email confirmation request (for existing users)
        
        Args:
            to_email: User's email address
            username: User's name
            confirmation_link: Link to confirm email
            
        Returns:
            bool: True if email sent successfully
        """
        subject = "InfraZen - Подтвердите ваш email"
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 10px 10px 0 0;
                    text-align: center;
                }}
                .content {{
                    background: #ffffff;
                    padding: 30px;
                    border: 1px solid #e2e8f0;
                    border-top: none;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background-color: #10b981;
                    color: white;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: 600;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    color: #718096;
                    font-size: 14px;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #e2e8f0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1 style="margin: 0; font-size: 28px;">Подтвердите ваш email</h1>
            </div>
            <div class="content">
                <p>Здравствуйте, {username}!</p>
                <p>Пожалуйста, подтвердите ваш email для завершения настройки аккаунта InfraZen.</p>
                
                <div style="text-align: center;">
                    <a href="{confirmation_link}" class="button">Подтвердить email</a>
                </div>
                
                <p style="font-size: 14px; color: #718096;">Или скопируйте и вставьте эту ссылку в браузер:<br>
                <a href="{confirmation_link}" style="color: #4299e1; word-break: break-all;">{confirmation_link}</a></p>
                
                <p style="margin-top: 30px; padding: 15px; background: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 4px;">
                    <strong>⚠️ Важно:</strong> Эта ссылка действительна в течение 24 часов и может быть использована только один раз.
                </p>
                
                <p style="margin-top: 20px;">Если вы не запрашивали подтверждение email, проигнорируйте это сообщение.</p>
                
                <p style="margin-top: 30px;">С уважением,<br><strong>Команда InfraZen</strong></p>
            </div>
            <div class="footer">
                <p>© 2025 InfraZen. Все права защищены.</p>
                <p>Это автоматическое сообщение, пожалуйста, не отвечайте на него.</p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Подтвердите ваш email
        
        Здравствуйте, {username}!
        
        Пожалуйста, подтвердите ваш email для завершения настройки аккаунта InfraZen.
        
        Перейдите по ссылке для подтверждения: {confirmation_link}
        
        ⚠️ Важно: Эта ссылка действительна в течение 24 часов и может быть использована только один раз.
        
        Если вы не запрашивали подтверждение email, проигнорируйте это сообщение.
        
        С уважением,
        Команда InfraZen
        
        ---
        © 2025 InfraZen. Все права защищены.
        Это автоматическое сообщение, пожалуйста, не отвечайте на него.
        """
        
        return EmailService.send_email(to_email, subject, html_body, text_body)

