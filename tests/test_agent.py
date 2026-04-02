"""Agent 构建和数据模型测试"""



class TestBuildAgent:
    """Agent 构建测试"""

    def test_agent_builds_successfully(self) -> None:
        """Agent 能正常构建"""
        from deep_paper_qa.agent import build_agent

        agent, checkpointer = build_agent()
        assert agent is not None
        assert checkpointer is not None

    def test_agent_has_correct_structure(self) -> None:
        """Agent 应包含正确的图结构"""
        from deep_paper_qa.agent import build_agent

        agent, _ = build_agent()
        # 验证 agent 是一个可运行的 CompiledGraph
        assert hasattr(agent, "invoke")
        assert hasattr(agent, "ainvoke")


class TestModels:
    """数据模型测试"""

    def test_paper_record_creation(self) -> None:
        from deep_paper_qa.models import PaperRecord

        paper = PaperRecord(
            id="arxiv:2312.07559",
            title="Test Paper",
            year=2025,
            authors=["Author A", "Author B"],
            directions=["RAG", "NLP"],
        )
        assert paper.id == "arxiv:2312.07559"
        assert len(paper.authors) == 2
        assert paper.citations == 0

    def test_search_result_creation(self) -> None:
        from deep_paper_qa.models import SearchChunk, SearchResult

        result = SearchResult(
            query="RAG methods",
            chunks=[
                SearchChunk(
                    paper_id="arxiv:2312.10997",
                    paper_title="RAG Survey",
                    content="Retrieval augmented generation...",
                    score=0.95,
                )
            ],
        )
        assert len(result.chunks) == 1
        assert result.chunks[0].score == 0.95
