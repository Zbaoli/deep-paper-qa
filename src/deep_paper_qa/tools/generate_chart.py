"""通用数据可视化工具：根据数据和图表类型生成 Plotly 图表"""

import plotly.graph_objects as go
from langchain_core.tools import tool
from loguru import logger

# 支持的图表类型
SUPPORTED_TYPES = {"bar", "line", "scatter", "pie", "heatmap", "area", "box"}

# 与前端 Academic Observatory 主题一致的配色方案
_DEFAULT_LAYOUT = {
    "template": "plotly_dark",
    "height": 320,
    "font": {"size": 13, "color": "#e8eaf0", "family": "system-ui, sans-serif"},
    "margin": {"l": 50, "r": 30, "t": 50, "b": 50},
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "title_font": {"size": 15, "color": "#e8eaf0"},
    "xaxis": {"gridcolor": "rgba(255,255,255,0.06)", "zerolinecolor": "rgba(255,255,255,0.06)"},
    "yaxis": {"gridcolor": "rgba(255,255,255,0.06)", "zerolinecolor": "rgba(255,255,255,0.06)"},
    "legend": {"font": {"color": "#8a92a8"}},
}

# 与前端 accent 配色对齐
_COLORS = ["#f0a030", "#4ecdc4", "#e8637a", "#8b5cf6", "#3b82f6", "#10b981", "#06b6d4"]


@tool(response_format="content_and_artifact")
async def generate_chart(
    chart_type: str,
    data: dict,
    title: str,
    x_label: str = "",
    y_label: str = "",
) -> tuple[str, str]:
    """根据数据生成 Plotly 图表。

    支持的图表类型：bar（柱状图）、line（折线图）、scatter（散点图）、
    pie（饼图）、heatmap（热力图）、area（面积图）、box（箱线图）。

    Args:
        chart_type: 图表类型
        data: 图表数据。xy 类图表用 {"x": [...], "y": [...]}；
              饼图用 {"labels": [...], "values": [...]}；
              箱线图用 {"y": [...]} 或 {"groups": {"组名": [数值...]}}
        title: 图表标题
        x_label: X 轴标签（可选）
        y_label: Y 轴标签（可选）

    Returns:
        (content, artifact) 元组：content 为简短确认文本（LLM 可见），
        artifact 为完整 Plotly JSON 字符串（仅前端使用）
    """
    chart_type = chart_type.lower().strip()
    if chart_type not in SUPPORTED_TYPES:
        return (
            f"错误：不支持的图表类型 '{chart_type}'，支持的类型：{', '.join(sorted(SUPPORTED_TYPES))}",
            "",
        )

    try:
        fig = _build_figure(chart_type, data)
    except ValueError as e:
        return (f"错误：{e}", "")

    fig.update_layout(
        title=title,
        xaxis_title=x_label or None,
        yaxis_title=y_label or None,
        **_DEFAULT_LAYOUT,
    )

    chart_json = fig.to_json()
    logger.info("generate_chart | type={} | title={}", chart_type, title)
    # content 仅返回简短确认，避免 LLM 上下文浪费 token；artifact 携带完整 JSON 供前端渲染
    return (f"已生成 {chart_type} 图表：{title}", chart_json)


def _build_figure(chart_type: str, data: dict) -> go.Figure:
    """根据图表类型和数据构建 Plotly Figure"""
    if chart_type == "pie":
        labels = data.get("labels", [])
        values = data.get("values", [])
        if len(labels) != len(values):
            raise ValueError(f"labels 和 values 长度不一致：{len(labels)} vs {len(values)}")
        return go.Figure(data=[go.Pie(labels=labels, values=values, marker_colors=_COLORS)])

    if chart_type == "box":
        groups = data.get("groups", {})
        if groups:
            traces = [go.Box(y=vals, name=name) for name, vals in groups.items()]
            return go.Figure(data=traces)
        return go.Figure(data=[go.Box(y=data.get("y", []))])

    if chart_type == "heatmap":
        z = data.get("z", data.get("y", []))
        x = data.get("x", None)
        y_labels = data.get("y_labels", None)
        return go.Figure(data=[go.Heatmap(z=z, x=x, y=y_labels, colorscale="Blues")])

    # xy 类图表：bar, line, scatter, area
    x = data.get("x", [])
    y = data.get("y", [])
    if len(x) != len(y):
        raise ValueError(f"x 和 y 数据长度不一致：{len(x)} vs {len(y)}")

    trace_map = {
        "bar": go.Bar(x=x, y=y, marker_color=_COLORS[0]),
        "line": go.Scatter(x=x, y=y, mode="lines+markers", line={"color": _COLORS[0]}),
        "scatter": go.Scatter(x=x, y=y, mode="markers", marker={"color": _COLORS[0], "size": 8}),
        "area": go.Scatter(x=x, y=y, fill="tozeroy", line={"color": _COLORS[0]}),
    }
    return go.Figure(data=[trace_map[chart_type]])
