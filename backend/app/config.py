from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"

    # LLM
    anthropic_api_key: str = ""
    llm_provider: str = "anthropic"  # anthropic | ollama
    anthropic_model: str = "claude-haiku-4-5"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3.5:9b"

    # Literature sources
    ncbi_email: str = ""
    ncbi_api_key: str = ""
    semantic_scholar_api_key: str = ""

    # Vector store -- a direct Postgres connection string works against both a local
    # Postgres+pgvector instance (dev) and Supabase's Postgres (prod, using the
    # connection string from Project Settings -> Database, not the REST API).
    database_url: str = "postgresql://localhost:5432/rag_health_fitness"

    # Rate limiting -- standard Redis protocol works against both a local redis-server
    # (dev) and Upstash's Redis (prod, Upstash supports the standard protocol over TLS
    # via a rediss:// URL, not just its REST API).
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_per_ip_per_day: int = 20
    rate_limit_global_per_day: int = 300

    # Pipeline tuning
    max_subtopics: int = 4
    max_chunks_per_subtopic: int = 8
    max_synthesis_output_tokens: int = 1800
    max_question_length: int = 500

    # Embeddings
    embedding_provider: str = "fastembed"  # fastembed | voyage | openai
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    cors_allowed_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
