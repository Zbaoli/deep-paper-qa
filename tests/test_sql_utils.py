"""sql_utils WHERE 校验测试"""

from deep_paper_qa.tools.sql_utils import validate_where


class TestValidateWhere:
    """WHERE 片段安全校验测试"""

    def test_valid_where_passes(self) -> None:
        """合法 WHERE 片段通过校验"""
        assert validate_where("year=2025 AND conference='ACL'") is None
        assert validate_where("citations >= 10") is None
        assert validate_where("'Hinton' = ANY(authors)") is None
        assert validate_where("") is None
        assert validate_where("   ") is None

    def test_reject_union(self) -> None:
        """拦截 UNION 注入"""
        result = validate_where("year=2025 UNION SELECT * FROM pg_tables")
        assert result is not None
        assert "UNION" in result

    def test_reject_sql_comment(self) -> None:
        """拦截 SQL 注释 --"""
        result = validate_where("year=2025 -- comment")
        assert result is not None
        assert "注释" in result

    def test_reject_block_comment(self) -> None:
        """拦截块注释 /*"""
        result = validate_where("year=2025 /* attack */")
        assert result is not None
        assert "注释" in result

    def test_reject_semicolon(self) -> None:
        """拦截分号"""
        result = validate_where("year=2025; DROP TABLE papers")
        assert result is not None
        assert "分号" in result

    def test_reject_forbidden_keywords(self) -> None:
        """拦截 DML/DDL 关键词"""
        for keyword in ["INSERT", "DELETE", "DROP", "SELECT", "UPDATE"]:
            result = validate_where(f"year=2025 {keyword} something")
            assert result is not None, f"应拦截 {keyword}"
            assert "禁止关键词" in result
