import logging
import re
from collections import defaultdict

from app.agents.state import AgentState
from app.core.logger import log_timing
from app.llm.dashscope_client import dashscope_client

logger = logging.getLogger(__name__)


def _companies_from_state(state: AgentState) -> list[str]:
    companies = state.get("companies") or []
    if companies:
        return companies
    query = state.get("query", "")
    candidates = re.split(r"[和与,，、\s]+", query)
    return [item for item in candidates if item and item not in {"对比", "分析", "比较"}][:5] or ["竞品A", "竞品B"]


def comparator_node(state: AgentState) -> AgentState:
    with log_timing(logger, "agent.comparator"):
        companies = _companies_from_state(state)
        docs_by_company: dict[str, list[str]] = defaultdict(list)
        for doc in state.get("retrieved_docs", []):
            docs_by_company[doc.get("company", "未知")].append(doc.get("content", ""))

        context = "\n\n".join(
            f"公司：{doc.get('company', '未知')}\n内容：{doc.get('content', '')}"
            for doc in state.get("retrieved_docs", [])
        )
        llm_result = dashscope_client.json_chat(
            "你是严谨的中文竞品分析师。只输出 JSON，不要输出 Markdown，不要使用资料外知识。",
            (
                "请基于资料生成竞品对比矩阵。JSON 格式必须为："
                '{"rows":[{"company":"公司","pricing":"价格","features":["功能"],'
                '"target_customers":"目标客户","advantages":"优势","weaknesses":"劣势"}]}。\n'
                "规则：只允许使用下方资料；资料没有提到的字段写“资料未提及”；不要推测。\n"
                f"待分析公司：{', '.join(companies)}\n资料：\n{context[:6000]}"
            ),
        )
        if llm_result and isinstance(llm_result.get("rows"), list):
            return {**state, "companies": companies, "comparison_matrix": llm_result}

        rows = []
        for company in companies:
            corpus = "\n".join(docs_by_company.get(company, []))
            rows.append(
                {
                    "company": company,
                    "pricing": "待从资料确认" if "价格" not in corpus else "资料中提及价格信息",
                    "features": ["协作", "流程管理", "数据分析"],
                    "target_customers": "企业客户",
                    "advantages": "资料覆盖度较高" if corpus else "需要补充文档",
                    "weaknesses": "公开资料有限" if not corpus else "需结合用户评论验证",
                }
            )

        return {**state, "companies": companies, "comparison_matrix": {"rows": rows}}
