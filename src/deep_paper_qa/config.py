"""应用配置：通过 pydantic-settings 加载环境变量"""

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# 先加载 .env 到 os.environ，确保 LANGCHAIN_* 等第三方库的环境变量生效
load_dotenv()


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

    # Search Agent LLM（独立配置，未设置时 fallback 到主 LLM）
    search_agent_llm_base_url: str = ""
    search_agent_llm_model: str = ""
    search_agent_llm_api_key: str = ""

    # Agent
    agent_recursion_limit: int = 50

    # 外部搜索 API
    semantic_scholar_api_key: str = ""
    tavily_api_key: str = ""
    external_search_timeout: int = 15

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


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


def get_search_agent_llm(temperature: float = 0):
    """获取 Search Agent 专用 LLM 客户端，未配置时 fallback 到主 LLM"""
    from langchain_openai import ChatOpenAI

    base_url = settings.search_agent_llm_base_url or settings.llm_base_url
    model = settings.search_agent_llm_model or settings.llm_model
    api_key = settings.search_agent_llm_api_key or settings.llm_api_key

    return ChatOpenAI(
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=temperature,
    )
