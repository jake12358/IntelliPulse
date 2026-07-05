import logging

from app.agents.state import AgentState
from app.core.logger import log_timing
from app.llm.dashscope_client import dashscope_client
from app.services.reporting_service import source_preview

logger = logging.getLogger(__name__)


def reporter_node(state: AgentState) -> AgentState:
    with log_timing(logger, "agent.reporter"):
        llm_report = dashscope_client.chat(
            (
                "你是资深战略分析顾问。输出中文 Markdown 报告，结论必须基于给定资料。"
                "禁止输出 HTML 标签，禁止使用 Markdown 表格，使用分级标题和项目列表。"
                "资料没有支持的内容必须写“资料未提及”，不要使用外部常识补全。"
            ),
            (
                "请生成一份竞品战略分析报告，包含：执行摘要、对比矩阵解读、情感倾向、"
                "SWOT、建议行动、引用来源。不要编造资料中没有的事实。\n\n"
                f"查询：{state.get('query', '')}\n"
                f"公司：{state.get('companies', [])}\n"
                f"对比矩阵：{state.get('comparison_matrix', {})}\n"
                f"情感分析：{state.get('sentiment_scores', {})}\n"
                f"检索资料：{source_preview(state.get('retrieved_docs', []), limit=8)}"
            ),
        )
        if llm_report:
            return {**state, "final_report": llm_report}

        rows = state.get("comparison_matrix", {}).get("rows", [])
        lines = [
            "# IntelliPulse 竞品分析报告",
            "",
            "## 对比要点",
            "",
        ]
        for row in rows:
            lines.extend(
                [
                    f"### {row['company']}",
                    f"- 价格：{row['pricing']}",
                    f"- 功能：{', '.join(row['features'])}",
                    f"- 目标客户：{row['target_customers']}",
                    f"- 优势：{row['advantages']}",
                    f"- 劣势：{row['weaknesses']}",
                    "",
                ]
            )

        lines.extend(["", "## 情感分析", ""])
        for company, score in state.get("sentiment_scores", {}).items():
            lines.append(f"- {company}: {score['label']} (正向 {score['positive']} / 负向 {score['negative']})")

        lines.extend(
            [
                "",
                "## SWOT",
                "",
                "- Strengths: 已建立文档解析、检索和多 Agent 汇总链路。",
                "- Weaknesses: 需要补充更多真实用户评论和财报资料以提升结论可靠性。",
                "- Opportunities: 可沉淀行业对比模板，形成可复用的销售与战略分析资产。",
                "- Threats: 公开资料口径不一致，需持续校验来源和更新时间。",
            ]
        )
        return {**state, "final_report": "\n".join(lines)}
