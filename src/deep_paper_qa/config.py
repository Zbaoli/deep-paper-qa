"""应用配置：通过 pydantic-settings 加载环境变量"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用全局配置"""

    # PostgreSQL
    pg_database_url: str = "postgresql://localhost:5432/deep_paper_qa"
    # 只读连接（用于 search_abstracts/vector_search 的安全隔离，可选）
    pg_readonly_url: str = ""

    # LLM
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o"
    llm_api_key: str = ""

    # Embedding 服务（OpenAI 兼容接口）
    embedding_base_url: str = "http://localhost:11434/v1"
    embedding_model: str = "bge-m3"
    embedding_dim: int = 1024

    # 查询限制
    sql_max_rows: int = 20
    sql_timeout_seconds: float = 10.0
    vector_search_top_k: int = 5
    abstract_max_chars: int = 800

    # Agent
    max_conversation_turns: int = 6

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()


def get_llm(temperature: float = 0):
    """获取 LLM 客户端（全局复用配置）"""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=temperature,
    )
