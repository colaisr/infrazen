"""
Vision tools for analyzing screenshots, charts, and console outputs.
Uses OpenRouter gpt-4o for vision capabilities.
"""
import base64
import logging
from pathlib import Path
from typing import Dict, Optional

from agent_service.api.upload import get_image_path
from agent_service.llm.gateway import LLMGateway

logger = logging.getLogger(__name__)


class VisionTools:
    """Tools for analyzing images with vision-capable LLMs."""
    
    def __init__(self, llm_gateway: Optional[LLMGateway] = None):
        """
        Initialize vision tools.
        
        Args:
            llm_gateway: Optional LLM gateway instance. If None, creates new one.
        """
        self.llm = llm_gateway or LLMGateway()
    
    def analyze_screenshot(self, image_id: str, question: str, user_id: Optional[int] = None) -> Dict:
        """
        Анализирует загруженный скриншот или изображение.
        
        Используется для:
        - Анализа графиков метрик (CPU, RAM, сеть)
        - Чтения консольных выводов
        - Извлечения информации из скриншотов интерфейсов
        - Анализа счетов и прайс-листов провайдеров
        
        Args:
            image_id: ID загруженного изображения
            question: Вопрос или контекст для анализа (на русском)
            user_id: ID пользователя (для аудита)
        
        Returns:
            {
                'analysis': str,  # Результат анализа
                'success': bool,
                'error': str  # Опционально, если ошибка
            }
        """
        try:
            # Get image path
            image_path = get_image_path(image_id)
            logger.info(f"Analyzing image {image_id} for user {user_id}: {question[:50]}...")
            
            # Load and encode image
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Determine image format from extension
            image_format = image_path.suffix.lower().replace('.', '')
            if image_format == 'jpg':
                image_format = 'jpeg'
            
            # Build vision prompt
            system_prompt = """Ты — FinOps консультант, анализируешь скриншоты и графики для оптимизации инфраструктуры.

При анализе:
- Фокусируйся на конкретных данных и цифрах
- Указывай на аномалии, тренды, возможности оптимизации
- Если это график — опиши динамику, пики, средние значения
- Если это консоль — извлеки ключевую информацию
- Если это прайс-лист — сравни цены и конфигурации
- Отвечай кратко, по делу, на русском языке"""

            user_prompt = f"""Проанализируй это изображение.

Контекст вопроса: {question}

Предоставь детальный анализ с конкретными данными."""

            # Call vision model
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{image_format};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
            
            # Use vision-capable model from settings
            from openai import OpenAI
            from agent_service.core.config import settings
            
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.OPENROUTER_API_KEY,
            )
            
            # Use vision model from settings (Claude Sonnet supports vision)
            vision_model = settings.LLM_MODEL_VISION
            logger.info(f"Using vision model: {vision_model}")
            
            response = client.chat.completions.create(
                model=vision_model,
                messages=messages,
                temperature=0.3,
                max_tokens=2000
            )
            
            analysis = response.choices[0].message.content.strip()
            
            if not analysis:
                return {
                    'success': False,
                    'error': 'Не удалось получить анализ изображения'
                }
            
            logger.info(f"Vision analysis complete for {image_id}: {len(analysis)} chars")
            
            return {
                'success': True,
                'analysis': analysis
            }
            
        except FileNotFoundError:
            logger.warning(f"Image {image_id} not found or expired")
            return {
                'success': False,
                'error': f'Изображение {image_id} не найдено или истекло время жизни'
            }
        except Exception as e:
            logger.error(f"Error analyzing image {image_id}: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Ошибка анализа изображения: {str(e)}'
            }
    
    def get_tool_schema(self) -> Dict:
        """
        Get JSON schema for LangGraph tool registration.
        
        Returns:
            Tool schema compatible with LangGraph
        """
        return {
            "type": "function",
            "function": {
                "name": "analyze_screenshot",
                "description": """Анализирует загруженный скриншот, график или изображение.
                
Используй этот инструмент когда пользователь:
- Загрузил изображение и задал вопрос
- Просит проанализировать график метрик
- Хочет разобрать консольный вывод
- Прикрепил скриншот интерфейса или прайс-листа

Инструмент извлекает данные из изображения и предоставляет детальный анализ.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "image_id": {
                            "type": "string",
                            "description": "ID загруженного изображения (UUID)"
                        },
                        "question": {
                            "type": "string",
                            "description": "Вопрос или контекст для анализа (на русском)"
                        }
                    },
                    "required": ["image_id", "question"]
                }
            }
        }

