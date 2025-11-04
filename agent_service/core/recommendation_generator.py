"""
Recommendation text generator using LLM
"""
import logging
import json
import re
from typing import Dict, Any
from sqlalchemy.orm import Session

from agent_service.tools.data_access import DataAccessTools
from agent_service.llm.gateway import LLMGateway
from agent_service.llm.prompts import build_recommendation_prompt, RECOMMENDATION_FALLBACK

logger = logging.getLogger(__name__)


class RecommendationGenerator:
    """Generate user-friendly recommendation texts using LLM"""
    
    def __init__(self, db_session: Session):
        self.data_tools = DataAccessTools(db_session)
        self.llm = LLMGateway()
    
    def generate(self, recommendation_id: int) -> Dict[str, Any]:
        """
        Generate short and detailed HTML descriptions for a recommendation
        
        Args:
            recommendation_id: Recommendation ID
            
        Returns:
            Dict with short_description_html and detailed_description_html
        """
        try:
            # Fetch recommendation data
            data = self.data_tools.get_recommendation(recommendation_id)
            if not data:
                logger.error(f"Recommendation {recommendation_id} not found")
                return {
                    "recommendation_id": recommendation_id,
                    "error": "Recommendation not found",
                    **RECOMMENDATION_FALLBACK
                }
            
            # Build prompt
            prompt = build_recommendation_prompt(data)
            
            # Generate with LLM
            logger.info(f"Generating text for recommendation {recommendation_id}")
            result = self.llm.generate(
                prompt=prompt,
                temperature=0.3,  # Lower for consistent, factual output
                max_tokens=500
            )
            
            # Parse JSON response
            text = result['text'].strip()
            
            # Extract JSON from response (in case LLM adds markdown)
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                text = json_match.group(0)
            
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}\nResponse: {text}")
                return {
                    "recommendation_id": recommendation_id,
                    "error": "Failed to parse LLM response",
                    **RECOMMENDATION_FALLBACK
                }
            
            # Sanitize HTML (basic - prevent script injection)
            short_html = self._sanitize_html(parsed.get('short_description_html', ''))
            detailed_html = self._sanitize_html(parsed.get('detailed_description_html', ''))
            
            if not short_html or not detailed_html:
                logger.warning(f"LLM returned empty descriptions for rec {recommendation_id}")
                return {
                    "recommendation_id": recommendation_id,
                    "error": "Empty LLM response",
                    **RECOMMENDATION_FALLBACK
                }
            
            return {
                "recommendation_id": recommendation_id,
                "short_description_html": short_html,
                "detailed_description_html": detailed_html,
                "model": result.get('model'),
                "tokens": result.get('tokens')
            }
            
        except Exception as e:
            logger.error(f"Error generating recommendation text: {e}", exc_info=True)
            return {
                "recommendation_id": recommendation_id,
                "error": str(e),
                **RECOMMENDATION_FALLBACK
            }
    
    def _sanitize_html(self, html: str) -> str:
        """
        Basic HTML sanitization - allow only safe tags
        
        Allowed: strong, span, em, b, i, br
        Removes: script, style, onclick, etc.
        """
        if not html:
            return ""
        
        # Remove script tags and their content
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove style tags and their content
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove event handlers (onclick, onerror, etc.)
        html = re.sub(r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
        
        # Remove javascript: URLs
        html = re.sub(r'javascript:', '', html, flags=re.IGNORECASE)
        
        # Allow only safe tags (basic whitelist)
        allowed_tags = r'(strong|span|em|b|i|br|p)'
        # Remove tags not in whitelist (but keep their content)
        html = re.sub(r'<(?!/?' + allowed_tags + r'\b)[^>]+>', '', html, flags=re.IGNORECASE)
        
        return html.strip()

