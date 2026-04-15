"""DeepAgent 构建测试"""


class TestBuildAgent:
    """DeepAgent 构建测试"""

    def test_agent_builds_successfully(self) -> None:
        """agent 能正常构建"""
        from deep_paper_qa.agent import build_agent

        agent, checkpointer = build_agent()
        assert agent is not None
        assert checkpointer is not None

    def test_agent_has_invoke_methods(self) -> None:
        """agent 应支持 invoke 和 ainvoke"""
        from deep_paper_qa.agent import build_agent

        agent, _ = build_agent()
        assert hasattr(agent, "invoke")
        assert hasattr(agent, "ainvoke")

    def test_agent_has_stream_methods(self) -> None:
        """agent 应支持流式输出"""
        from deep_paper_qa.agent import build_agent

        agent, _ = build_agent()
        assert hasattr(agent, "astream_events")

    def test_agent_without_ask_user(self) -> None:
        """eval 模式不含 ask_user"""
        from deep_paper_qa.agent import build_agent

        agent, _ = build_agent(include_ask_user=False)
        assert agent is not None


class TestSearchSubAgent:
    """Search SubAgent 构建测试"""

    def test_search_subagent_builds(self) -> None:
        """search subagent 能正常构建"""
        from deep_paper_qa.agent import _build_search_subagent

        subagent = _build_search_subagent()
        assert subagent["name"] == "search-agent"

    def test_search_subagent_has_description(self) -> None:
        """search subagent 有描述"""
        from deep_paper_qa.agent import _build_search_subagent

        subagent = _build_search_subagent()
        assert "研究" in subagent["description"]


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
