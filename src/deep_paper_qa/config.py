"""应用配置：通过 pydantic-settings 加载环境变量"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用全局配置"""

    # PostgreSQL
    database_url: str = "postgresql://localhost:5432/deep_paper_qa"

    # LLM
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o"
    llm_api_key: str = ""

    # RAG 向量检索 API
    rag_api_url: str = "http://localhost:8000/api/search"

    # 查询限制
    sql_max_rows: int = 20
    sql_timeout_seconds: float = 10.0
    vector_search_top_k: int = 5
    vector_chunk_max_chars: int = 500
    abstract_max_chars: int = 200

    # Agent
    recursion_limit: int = 10
    max_conversation_turns: int = 6

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
