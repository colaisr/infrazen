"""
Configuration management for Agent Service
Loads from environment variables with sensible defaults
"""
import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Agent Service configuration"""
    
    # Service basics
    VERSION: str = "0.1.0"
    AGENT_PORT: int = int(os.getenv("AGENT_PORT", "8001"))
    AGENT_ENV: str = os.getenv("AGENT_ENV", "dev")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # InfraZen integration
    AGENT_INTERNAL_API_BASE: str = os.getenv(
        "AGENT_INTERNAL_API_BASE", 
        "http://127.0.0.1:5001/internal"
    )
    AGENT_SERVICE_JWT_SECRET: str = os.getenv(
        "AGENT_SERVICE_JWT_SECRET",
        "dev-secret-change-in-production"
    )
    
    # LLM provider configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openrouter")
    LLM_MODEL_TEXT: str = os.getenv("LLM_MODEL_TEXT", "openai/gpt-4o-mini")
    LLM_MODEL_VISION: str = os.getenv("LLM_MODEL_VISION", "openai/gpt-4o")
    
    # Provider-specific API keys
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Redis/Session store
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    
    # Vector store
    VECTOR_STORE: str = os.getenv("VECTOR_STORE", "chroma")
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5001",
        "http://127.0.0.1:5001",
        "https://infrazen.team"
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

