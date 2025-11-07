"""Reports API endpoints for agent service."""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from agent_service.reports.report_builder import ReportDataBuilder
from agent_service.reports.report_renderer import render_report_html
from agent_service.reports.narrative_builder import ReportNarrativeBuilder

logger = logging.getLogger(__name__)
router = APIRouter()


class ReportDataRequest(BaseModel):
    user_id: int = Field(..., description="User ID for whom the report is generated")
    role: str = Field(..., description="Report persona key (e.g., cfo, cto)")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional generation context")


def _get_builder(app_state) -> ReportDataBuilder:
    builder = getattr(app_state, "report_builder", None)
    if builder is None:
        flask_app = getattr(app_state, "flask_app", None)
        if flask_app is None:
            logger.error("Flask app context not available in agent service state")
            raise RuntimeError("Flask app context not available")
        builder = ReportDataBuilder(flask_app)
        app_state.report_builder = builder
    return builder


def _get_narrative_builder(app_state) -> ReportNarrativeBuilder:
    builder = getattr(app_state, "report_narrative_builder", None)
    if builder is None:
        builder = ReportNarrativeBuilder()
        app_state.report_narrative_builder = builder
    return builder


@router.post("/v1/reports/data", tags=["reports"])
async def build_report_data(request: Request, payload: ReportDataRequest):
    try:
        app_state = request.app.state
        builder = _get_builder(app_state)
        narrative_builder = _get_narrative_builder(app_state)
        snapshot = builder.build_snapshot(
            user_id=payload.user_id,
            role=payload.role,
            context=payload.context or {}
        )
        snapshot["narrative"] = narrative_builder.generate(snapshot, payload.role)
        return {"success": True, "snapshot": snapshot}
    except ValueError as exc:
        logger.warning("Invalid report request: %s", exc)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Failed to build report snapshot: %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to build report data") from exc


@router.post("/v1/reports/render", tags=["reports"])
async def render_report(request: Request, payload: ReportDataRequest):
    try:
        app_state = request.app.state
        builder = _get_builder(app_state)
        narrative_builder = _get_narrative_builder(app_state)
        snapshot = builder.build_snapshot(
            user_id=payload.user_id,
            role=payload.role,
            context=payload.context or {}
        )
        snapshot["narrative"] = narrative_builder.generate(snapshot, payload.role)
        html = render_report_html(snapshot, payload.role)
        return {"success": True, "snapshot": snapshot, "html": html}
    except ValueError as exc:
        logger.warning("Invalid report render request: %s", exc)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Failed to render report: %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to render report") from exc

