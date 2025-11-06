"""
Chat agent for recommendation discussions.
Uses LangGraph for orchestration with tool-calling LLM.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from agent_service.llm.gateway import get_llm_client
from agent_service.llm.chat_prompts import build_chat_system_prompt
from agent_service.tools.recommendation_tools import RecommendationTools
from agent_service.tools.vision_tools import VisionTools

logger = logging.getLogger(__name__)


class ChatAgent:
    """
    Chat agent for discussing recommendations with users.
    Powered by LLM with read-only tools access.
    """
    
    def __init__(self, flask_app):
        """
        Initialize chat agent.
        
        Args:
            flask_app: Flask application instance for database access
        """
        self.flask_app = flask_app
        self.tools = RecommendationTools(flask_app)
        self.vision_tools = VisionTools()
        self.llm_client = None
        
    def _get_llm_client(self):
        """Get or create LLM client."""
        if self.llm_client is None:
            self.llm_client = get_llm_client()
        return self.llm_client
        
    def _get_tool_definitions(self) -> List[Dict]:
        """
        Get tool definitions in OpenAI function calling format.
        
        Returns:
            List of tool definition dicts
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_recommendation_details",
                    "description": "Получить полные детали рекомендации по оптимизации. Используй для получения информации об экономии, целевом провайдере, связанных ресурсах.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "rec_id": {
                                "type": "integer",
                                "description": "ID рекомендации"
                            }
                        },
                        "required": ["rec_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_resource_details",
                    "description": "Получить детальную информацию о ресурсе (сервер, диск, IP). Используй для получения конфигурации, характеристик, стоимости.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "resource_id": {
                                "type": "integer",
                                "description": "ID ресурса"
                            }
                        },
                        "required": ["resource_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_provider_pricing",
                    "description": "Получить актуальные цены провайдера для типа ресурса. Используй для сравнения цен и поиска альтернатив.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "provider": {
                                "type": "string",
                                "description": "Название провайдера (beget, selectel, yandex)",
                                "enum": ["beget", "selectel", "yandex"]
                            },
                            "resource_type": {
                                "type": "string",
                                "description": "Тип ресурса (server, vm, storage, snapshot)"
                            }
                        },
                        "required": ["provider", "resource_type"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_savings",
                    "description": "Рассчитать экономию при смене конфигурации/провайдера. Используй для точных расчётов экономии.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "current_cost": {
                                "type": "number",
                                "description": "Текущая стоимость (₽/мес)"
                            },
                            "new_cost": {
                                "type": "number",
                                "description": "Новая стоимость (₽/мес)"
                            },
                            "period": {
                                "type": "string",
                                "description": "Период расчёта (month, quarter, year)",
                                "enum": ["month", "quarter", "year"],
                                "default": "month"
                            }
                        },
                        "required": ["current_cost", "new_cost"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_migration_risks",
                    "description": "Оценить риски и сложность миграции ресурса. Используй когда пользователь спрашивает о рисках, downtime, сложности.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "resource_id": {
                                "type": "integer",
                                "description": "ID ресурса для миграции"
                            },
                            "target_provider": {
                                "type": "string",
                                "description": "Целевой провайдер (beget, selectel, yandex)",
                                "enum": ["beget", "selectel", "yandex"]
                            }
                        },
                        "required": ["resource_id", "target_provider"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_screenshot",
                    "description": "Анализирует загруженный скриншот, график или изображение. Используй когда пользователь загрузил изображение и задал вопрос, просит проанализировать график метрик, хочет разобрать консольный вывод, прикрепил скриншот интерфейса или прайс-листа.",
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
        ]
        
    def _execute_tool(self, tool_name: str, arguments: Dict) -> Any:
        """
        Execute a tool call.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments dict
            
        Returns:
            Tool execution result
        """
        try:
            # Add user_id to all tool calls for ownership verification
            arguments_with_user = {**arguments, 'user_id': getattr(self, 'current_user_id', None)}
            
            if tool_name == "get_recommendation_details":
                return self.tools.get_recommendation_details(**arguments_with_user)
            elif tool_name == "get_resource_details":
                return self.tools.get_resource_details(**arguments_with_user)
            elif tool_name == "get_provider_pricing":
                return self.tools.get_provider_pricing(**arguments_with_user)
            elif tool_name == "calculate_savings":
                return self.tools.calculate_savings(**arguments_with_user)
            elif tool_name == "get_migration_risks":
                return self.tools.get_migration_risks(**arguments_with_user)
            elif tool_name == "analyze_screenshot":
                return self.vision_tools.analyze_screenshot(**arguments_with_user)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            return {"error": f"Tool execution error: {str(e)}"}
            
    async def process_message(
        self,
        user_message: str,
        recommendation_id: int,
        user_id: int,
        chat_history: List[Dict] = None
    ) -> tuple[str, int]:
        """
        Process user message and generate response.
        
        Args:
            user_message: User's message
            recommendation_id: Recommendation ID for context
            user_id: User ID (supports impersonation - from JWT token)
            chat_history: Previous messages [{role, content}, ...]
            
        Returns:
            Tuple of (assistant_response, tokens_used)
        """
        try:
            # Store user_id for tool execution context
            self.current_user_id = user_id
            # Get recommendation details for context
            rec_details = self.tools.get_recommendation_details(recommendation_id)
            
            if 'error' in rec_details:
                return f"Ошибка: {rec_details['error']}", 0
            
            # Build system prompt with context
            system_prompt = build_chat_system_prompt(
                recommendation_id=recommendation_id,
                recommendation_title=rec_details.get('title', 'Рекомендация'),
                estimated_savings=rec_details.get('estimated_monthly_savings', 0),
                resource_name=rec_details.get('resource', {}).get('name') if rec_details.get('resource') else None
            )
            
            # Prepare messages
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add chat history (last 10 messages)
            if chat_history:
                for msg in chat_history[-10:]:
                    messages.append({
                        "role": msg['role'],
                        "content": msg['content']
                    })
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Get LLM client
            client = self._get_llm_client()
            
            # Get tool definitions
            tools = self._get_tool_definitions()
            
            # Get text model from settings
            from agent_service.core.config import settings
            text_model = settings.LLM_MODEL_TEXT
            logger.info(f"Using text model for chat: {text_model}")
            
            # Call LLM with tools
            response = client.chat.completions.create(
                model=text_model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1000
            )
            
            # Extract response
            assistant_message = response.choices[0].message
            tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 0
            
            # Check if tool calls are needed
            if assistant_message.tool_calls:
                # Execute tool calls
                messages.append(assistant_message)
                
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)  # JSON string to dict
                    
                    logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                    
                    # Execute tool
                    tool_result = self._execute_tool(tool_name, tool_args)
                    
                    # Add tool response to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": str(tool_result)
                    })
                
                # Get final response with tool results
                final_response = client.chat.completions.create(
                    model=text_model,  # Use same model as before
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000
                )
                
                final_message = final_response.choices[0].message.content
                tokens_used += final_response.usage.total_tokens if hasattr(final_response, 'usage') else 0
                
                return final_message, tokens_used
            else:
                # No tool calls, return direct response
                return assistant_message.content, tokens_used
                
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return f"Извините, произошла ошибка при обработке сообщения: {str(e)}", 0

