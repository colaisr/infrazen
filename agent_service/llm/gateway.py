"""
LLM Gateway - Provider-agnostic interface to language models
Supports OpenRouter, direct providers, and local models
"""
import logging
from typing import Dict, Any, Optional, List
import json

from agent_service.core.config import settings

logger = logging.getLogger(__name__)


class LLMGateway:
    """Provider-agnostic LLM client with fallback support"""
    
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.text_model = settings.LLM_MODEL_TEXT
        self.vision_model = settings.LLM_MODEL_VISION
        
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        model_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate text using configured LLM provider
        
        Args:
            prompt: User prompt
            system_prompt: System/role prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            model_override: Override default model
            
        Returns:
            Dict with 'text', 'model', 'tokens', 'cost'
        """
        model = model_override or self.text_model
        
        try:
            if self.provider == 'openrouter':
                return self._generate_openrouter(prompt, system_prompt, temperature, max_tokens, model)
            elif self.provider == 'openai':
                return self._generate_openai(prompt, system_prompt, temperature, max_tokens, model)
            elif self.provider == 'anthropic':
                return self._generate_anthropic(prompt, system_prompt, temperature, max_tokens, model)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
                
        except Exception as e:
            logger.error(f"LLM generation failed: {e}", exc_info=True)
            raise
    
    def _generate_openrouter(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        model: str
    ) -> Dict[str, Any]:
        """Generate using OpenRouter API"""
        from openai import OpenAI
        
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
        )
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        logger.info(f"Calling OpenRouter with model: {model}")
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        text = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else 0
        
        logger.info(f"OpenRouter response: {tokens} tokens")
        
        return {
            'text': text,
            'model': model,
            'tokens': tokens,
            'cost': 0.0,  # TODO: Calculate based on model pricing
            'provider': 'openrouter'
        }
    
    def _generate_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        model: str
    ) -> Dict[str, Any]:
        """Generate using OpenAI API directly"""
        from openai import OpenAI
        
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        text = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else 0
        
        return {
            'text': text,
            'model': model,
            'tokens': tokens,
            'cost': 0.0,
            'provider': 'openai'
        }
    
    def _generate_anthropic(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        model: str
    ) -> Dict[str, Any]:
        """Generate using Anthropic API directly"""
        # TODO: Implement when needed
        raise NotImplementedError("Anthropic support coming soon")

