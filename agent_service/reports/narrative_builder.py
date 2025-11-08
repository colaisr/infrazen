"""Narrative generation orchestrator for persona-aware reports."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from agent_service.llm.gateway import LLMGateway
from agent_service.reports.snippet_manager import SnippetLibrary
from agent_service.reports.snippets import get_snippets


logger = logging.getLogger(__name__)

_JSON_BLOCK_REGEX = re.compile(r"\{.*\}", re.DOTALL)


class ReportNarrativeBuilder:
    """Generate persona-specific narratives using snippet guidance and the LLM."""

    def __init__(self, llm_gateway: Optional[LLMGateway] = None):
        self.llm = llm_gateway or LLMGateway()
        self.snippet_library = SnippetLibrary()

    def generate(self, snapshot: Dict[str, Any], role: str) -> Dict[str, Any]:
        """Generate structured narrative bullets for the provided persona."""

        structured_snippets = get_snippets(role)
        rendered_snippets = snapshot.get("persona_snippets") or self.snippet_library.render_for_role(role, snapshot)
        snippet_context = snapshot.get("snippet_context") or self.snippet_library.build_context(snapshot)

        system_prompt = self._build_system_prompt(structured_snippets)
        prompt = self._build_user_prompt(snapshot, structured_snippets, rendered_snippets, snippet_context)

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.25,
                max_tokens=900,
            )
            narrative = self._parse_response(response.get("text", ""))
            if narrative:
                logger.info("Narrative generated for role=%s via LLM", role)
                return narrative
            logger.warning("Narrative generation returned empty payload for role=%s", role)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Narrative generation failed for role=%s: %s", role, exc)

        fallback = self._fallback(rendered_snippets, snippet_context, structured_snippets, snapshot)
        logger.info("Narrative fallback used for role=%s", role)
        return fallback

    # --------------------------------------------------------------------- #
    # Prompt preparation helpers
    # --------------------------------------------------------------------- #
    def _build_system_prompt(self, snippets: Dict[str, Any]) -> str:
        focus_list = "\n".join(f"- {item}" for item in snippets.get("focus_areas", []))
        tone = snippets.get("tone", "")
        persona = snippets.get("persona", "FinOps аналитик")
        return (
            f"Ты — {persona}. Подготовь аналитическую записку к FinOps отчету.\n"
            f"Тон: {tone}\n"
            "Всегда объясняй цифры через влияние на бизнес.\n"
            "Избегай жаргона, пиши уверенно, короткими абзацами, на русском языке.\n"
            "Отчет отражает оперативный снимок, поэтому не делай выводов о динамике или трендах без явных данных.\n"
            "Фокус-гайды:\n"
            f"{focus_list}"
        )

    def _build_user_prompt(
        self,
        snapshot: Dict[str, Any],
        structured_snippets: Dict[str, Any],
        rendered_snippets: Dict[str, List[str]],
        snippet_context: Dict[str, Any]
    ) -> str:
        metrics = self._extract_relevant_metrics(snapshot)
        insight_guidance = "\n".join(f"• {item}" for item in structured_snippets.get("insight_prompts", []))
        next_step_guidance = "\n".join(f"• {item}" for item in structured_snippets.get("next_steps", []))
        opening_templates = "\n".join(f"• {tpl}" for tpl in structured_snippets.get("opening_templates", []))
        rendered_notes = "\n".join(rendered_snippets.get("notes", []))
        rendered_actions = "\n".join(rendered_snippets.get("actions", []))

        metrics_json = json.dumps(metrics, ensure_ascii=False, indent=2)
        formatted_json = json.dumps(snippet_context, ensure_ascii=False, indent=2)

        return (
            "Сформируй краткий набор текстов для отчета.\n"
            "Это оперативный снимок: избегай сравнений с прошлыми периодами и выводов о трендах, если они явно не указаны.\n"
            "Текущие данные (JSON):\n"
            f"{metrics_json}\n\n"
            "Форматированные значения:\n"
            f"{formatted_json}\n\n"
            "Подсказки для инсайтов:\n"
            f"{insight_guidance}\n\n"
            "Разрешенные шаблоны открывающих формулировок:\n"
            f"{opening_templates}\n\n"
            "Примеры заметок:\n"
            f"{rendered_notes}\n\n"
            "Примеры действий / next steps:\n"
            f"{next_step_guidance}\n\n"
            "Дополнительные варианты действий:\n"
            f"{rendered_actions}\n\n"
            "Сформируй ответ исключительно в JSON следующей структуры:\n"
            "{\n"
            '  "executive_summary": "один абзац текста",\n'
            '  "key_highlights": [{"title": "...", "detail": "..."}],\n'
            '  "risks": ["короткое предложение"],\n'
            '  "next_steps": ["короткое действие"]\n'
            "}\n"
            "Не пиши пояснений вне JSON."
        )

    def _extract_relevant_metrics(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        kpis = snapshot.get("kpis", {})
        analytics = snapshot.get("analytics", {})
        recommendations = snapshot.get("recommendations", {})

        services = analytics.get("service_breakdown", {}).get("services", []) or []
        providers = analytics.get("provider_breakdown", {}).get("providers", []) or []
        anomalies: List[Dict[str, Any]] = []
        trimmed_trends: List[Dict[str, Any]] = []

        return {
            "kpis": {
                "monthly_cost": kpis.get("total_monthly_cost"),
                "daily_cost": kpis.get("total_daily_cost"),
                "pending_savings": kpis.get("pending_savings_total"),
                "active_resources": kpis.get("active_resources"),
                "provider_data_quality": kpis.get("provider_success_rate"),
            },
            "top_services": services[:5],
            "top_providers": providers[:5],
            "pending_recommendations": recommendations.get("pending", [])[:5],
        }

    # --------------------------------------------------------------------- #
    # Response post-processing
    # --------------------------------------------------------------------- #
    def _parse_response(self, text: str) -> Optional[Dict[str, Any]]:
        candidate = text.strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            match = _JSON_BLOCK_REGEX.search(candidate)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    logger.debug("Failed to parse JSON block from narrative response")
        return None

    # --------------------------------------------------------------------- #
    # Fallback when LLM is unavailable
    # --------------------------------------------------------------------- #
    def _fallback(
        self,
        persona_snippets: Dict[str, List[str]],
        snippet_context: Dict[str, Any],
        structured_snippets: Dict[str, Any],
        snapshot: Dict[str, Any]
    ) -> Dict[str, Any]:
        intros = persona_snippets.get("intros") or []
        notes = persona_snippets.get("notes") or []
        actions = persona_snippets.get("actions") or []

        summary = intros[0] if intros else self._default_summary(snippet_context)

        highlights: List[Dict[str, str]] = []
        for note in notes[:3]:
            title, detail = self._split_note(note)
            highlights.append({"title": title, "detail": detail})

        if not highlights:
            highlights.append(
                {
                    "title": "Ключевые показатели",
                    "detail": (
                        f"Месячные расходы {snippet_context.get('total_monthly_cost', '0')} ₽, "
                        f"потенциал экономии {snippet_context.get('pending_savings_total', '0')} ₽."
                    ),
                }
            )

        risks: List[str] = []
        risk_templates = structured_snippets.get("risk_templates", []) or []
        if risk_templates:
            risks.extend(risk_templates[:2])
        top_provider_info = snippet_context.get("top_provider_share")
        if not risks and top_provider_info and top_provider_info != "нет данных":
            risks.append(f"Контроль концентрации расходов: {top_provider_info}.")
        if not risks:
            risks.append("Поддерживать прозрачность распределения расходов и ответственность команд.")

        if actions:
            next_steps = actions[:3]
        else:
            next_steps = structured_snippets.get("next_steps", [])[:3]
        if not next_steps:
            next_steps = [
                "Синхронизировать планы экономии с ответственными командами.",
                "Обновить бюджет и прогноз с учетом новых показателей.",
                "Настроить мониторинг всплесков расходов и алерты.",
            ]

        return {
            "executive_summary": summary,
            "key_highlights": highlights,
            "risks": risks,
            "next_steps": next_steps,
        }

    @staticmethod
    def _default_summary(snippet_context: Dict[str, Any]) -> str:
        total = snippet_context.get("total_monthly_cost", "0")
        savings = snippet_context.get("pending_savings_total", "0")
        return (
            f"Оперативный снимок: расходы {total} ₽/мес, потенциал экономии {savings} ₽."
        )

    @staticmethod
    def _split_note(note: str) -> tuple[str, str]:
        parts = note.split(":", maxsplit=1)
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()
        return "Инсайт", note.strip()


