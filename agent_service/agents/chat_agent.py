"""
Chat agent for recommendation discussions.
Uses LangGraph for orchestration with tool-calling LLM.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from agent_service.llm.gateway import get_llm_client
from agent_service.llm.chat_prompts import build_chat_system_prompt, build_chat_system_prompt_for_analytics
from agent_service.tools.recommendation_tools import RecommendationTools
from agent_service.tools.analytics_tools import AnalyticsTools
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
        self.analytics_tools = AnalyticsTools(flask_app)
        self.vision_tools = VisionTools()
        self.llm_client = None
        self.current_scenario: Optional[str] = None
        self.current_context: Optional[Dict[str, Any]] = None
        
    def _get_llm_client(self):
        """Get or create LLM client."""
        if self.llm_client is None:
            self.llm_client = get_llm_client()
        return self.llm_client
        
    def _get_tool_definitions(self, scenario: str) -> List[Dict]:
        """Return scenario-specific tool definitions."""
        tools: List[Dict] = []

        if scenario == 'recommendation':
            tools.extend([
                {
                    "type": "function",
                    "function": {
                        "name": "get_recommendation_details",
                        "description": "Получить детали рекомендации: экономия, целевой провайдер, связанный ресурс.",
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
                        "description": "Получить конфигурацию и стоимость ресурса (сервер, диск, IP).",
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
                        "description": "Получить актуальные цены провайдера для выбранного типа ресурса.",
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
                        "description": "Рассчитать экономию при переходе на новую конфигурацию или провайдера.",
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
                        "description": "Оценить риски и сложности миграции ресурса на другого провайдера.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "resource_id": {
                                    "type": "integer",
                                    "description": "ID ресурса для миграции"
                                },
                                "target_provider": {
                                    "type": "string",
                                    "description": "Целевой провайдер",
                                    "enum": ["beget", "selectel", "yandex"]
                                }
                            },
                            "required": ["resource_id", "target_provider"]
                        }
                    }
                }
            ])

        if scenario == 'analytics':
            tools.extend([
                {
                    "type": "function",
                    "function": {
                        "name": "get_analytics_overview",
                        "description": "Краткая сводка KPI за выбранный период (расходы, экономия, синхронизации).",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "time_range_days": {
                                    "type": "integer",
                                    "description": "Период анализа в днях (7, 30, 90)",
                                    "default": 30
                                }
                            }
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_cost_trends",
                        "description": "Получить помесячный тренд расходов и изменение за период.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "time_range_days": {
                                    "type": "integer",
                                    "description": "Период анализа (в днях)",
                                    "default": 30
                                },
                                "include_provider_breakdown": {
                                    "type": "boolean",
                                    "description": "Включить ли детализацию по провайдерам",
                                    "default": False
                                }
                            }
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_service_breakdown",
                        "description": "Топ сервисов по расходам за последний снимок.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "top_n": {
                                    "type": "integer",
                                    "description": "Количество сервисов в выдаче",
                                    "default": 5
                                }
                            }
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_provider_breakdown",
                        "description": "Распределение расходов по провайдерам (последний снимок).",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_anomalies",
                        "description": "Выявить аномальные скачки расходов за период.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "time_range_days": {
                                    "type": "integer",
                                    "description": "Период анализа (дни)",
                                    "default": 30
                                },
                                "sensitivity": {
                                    "type": "number",
                                    "description": "Чувствительность (0.1 = 10% изменения)",
                                    "default": 0.15
                                }
                            }
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "summarize_top_recommendations",
                        "description": "Суммарная потенциальная экономия и топ рекомендаций по аналитике.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "limit": {
                                    "type": "integer",
                                    "description": "Количество рекомендаций",
                                    "default": 5
                                }
                            }
                        }
                    }
                }
            ])

        # Vision analysis is available in all scenarios
        tools.append({
            "type": "function",
            "function": {
                "name": "analyze_screenshot",
                "description": "Анализирует загруженный скриншот, график или изображение с точки зрения FinOps.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "image_id": {
                            "type": "string",
                            "description": "ID загруженного изображения (UUID)"
                        },
                        "question": {
                            "type": "string",
                            "description": "Контекст или вопрос пользователя"
                        }
                    },
                    "required": ["image_id", "question"]
                }
            }
        })

        return tools
        
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
            elif tool_name == "get_analytics_overview":
                return self.analytics_tools.get_analytics_overview(**arguments_with_user)
            elif tool_name == "get_cost_trends":
                return self.analytics_tools.get_cost_trends(**arguments_with_user)
            elif tool_name == "get_service_breakdown":
                return self.analytics_tools.get_service_breakdown(**arguments_with_user)
            elif tool_name == "get_provider_breakdown":
                return self.analytics_tools.get_provider_breakdown(**arguments_with_user)
            elif tool_name == "get_anomalies":
                return self.analytics_tools.get_anomalies(**arguments_with_user)
            elif tool_name == "summarize_top_recommendations":
                return self.analytics_tools.summarize_top_recommendations(**arguments_with_user)
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
        user_id: int,
        scenario: str,
        recommendation_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        chat_history: Optional[List[Dict]] = None
    ) -> tuple[str, int]:
        """
        Process user message and generate response.
        
        Args:
            user_message: User's message
            user_id: User ID (supports impersonation - from JWT token)
            scenario: Chat scenario identifier
            recommendation_id: Recommendation ID (for recommendation scenario)
            context: Optional scenario-specific context (e.g. time range)
            chat_history: Previous messages [{role, content}, ...]
            
        Returns:
            Tuple of (assistant_response, tokens_used)
        """
        try:
            # Store user_id for tool execution context
            self.current_user_id = user_id
            self.current_scenario = scenario
            self.current_context = context or {}

            messages: List[Dict[str, str]] = []
            tools = []

            if scenario == 'recommendation':
                if recommendation_id is None:
                    return "Ошибка: отсутствует ID рекомендации", 0

                rec_details = self.tools.get_recommendation_details(recommendation_id)
                if 'error' in rec_details:
                    return f"Ошибка: {rec_details['error']}", 0

                system_prompt = build_chat_system_prompt(
                    recommendation_id=recommendation_id,
                    recommendation_title=rec_details.get('title', 'Рекомендация'),
                    estimated_savings=rec_details.get('estimated_monthly_savings', 0),
                    resource_name=rec_details.get('resource', {}).get('name') if rec_details.get('resource') else None
                )
                tools = self._get_tool_definitions('recommendation')
            elif scenario == 'analytics':
                time_range = (context or {}).get('time_range_days', 30)
                snapshot = self.analytics_tools.build_context_snapshot(
                    user_id=user_id,
                    time_range_days=time_range
                )
                system_prompt = build_chat_system_prompt_for_analytics(snapshot)
                tools = self._get_tool_definitions('analytics')
            else:
                return "Извините, этот сценарий пока не поддерживается.", 0

            messages.append({"role": "system", "content": system_prompt})

            if chat_history:
                for msg in chat_history[-10:]:
                    messages.append({
                        "role": msg['role'],
                        "content": msg['content']
                    })

            messages.append({"role": "user", "content": user_message})

            client = self._get_llm_client()

            from agent_service.core.config import settings
            text_model = settings.LLM_MODEL_TEXT
            logger.info("Using text model for %s chat: %s", scenario, text_model)

            response = client.chat.completions.create(
                model=text_model,
                messages=messages,
                tools=tools,
                tool_choice="auto" if tools else None,
                temperature=0.7,
                max_tokens=1000
            )

            assistant_message = response.choices[0].message
            tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 0

            if assistant_message.tool_calls:
                messages.append(assistant_message)

                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    logger.info("Executing tool: %s with args: %s", tool_name, tool_args)
                    tool_result = self._execute_tool(tool_name, tool_args)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": json.dumps(tool_result, ensure_ascii=False) if isinstance(tool_result, (dict, list)) else str(tool_result)
                    })

                final_response = client.chat.completions.create(
                    model=text_model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000
                )

                final_message = final_response.choices[0].message.content
                tokens_used += final_response.usage.total_tokens if hasattr(final_response, 'usage') else 0

                return final_message, tokens_used

            return assistant_message.content, tokens_used
                
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return f"Извините, произошла ошибка при обработке сообщения: {str(e)}", 0

