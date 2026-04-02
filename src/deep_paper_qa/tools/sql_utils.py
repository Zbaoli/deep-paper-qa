"""SQL 安全校验工具函数"""

import re

# 禁止出现在 WHERE 片段中的关键词（DML/DDL）
_FORBIDDEN_KEYWORD_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|SELECT|UNION)\b",
    re.IGNORECASE,
)

# 禁止 SQL 注释
_SQL_COMMENT_RE = re.compile(r"(--|/\*)")


def validate_where(where: str) -> str | None:
    """校验 WHERE 片段安全性。

    返回错误消息（校验失败）或 None（校验通过）。
    用于 search_abstracts 和 vector_search 的 where 参数校验。
    """
    if not where or not where.strip():
        return None

    if ";" in where:
        return "WHERE 片段不允许包含分号。"

    if _FORBIDDEN_KEYWORD_RE.search(where):
        matched = _FORBIDDEN_KEYWORD_RE.search(where).group()
        return f"WHERE 片段包含禁止关键词: {matched}"

    if _SQL_COMMENT_RE.search(where):
        return "WHERE 片段不允许包含 SQL 注释（-- 或 /*）。"

    return None
