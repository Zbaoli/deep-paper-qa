"""绘制 DeepResearch Pipeline 流程图"""

from deep_paper_qa.pipelines.research import build_research_subgraph

graph = build_research_subgraph()
png_data = graph.get_graph().draw_mermaid_png()

with open("doc/research_pipeline.png", "wb") as f:
    f.write(png_data)

print("已保存到 doc/research_pipeline.png")
