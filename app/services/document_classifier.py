from pathlib import Path
from typing import Any

from app.llm.dashscope_client import dashscope_client

KNOWN_COMPANIES = [
    "飞书",
    "钉钉",
    "企业微信",
    "Slack",
    "Teams",
    "Notion",
    "Lark",
    "Trello",
    "Asana",
]

CATEGORY_KEYWORDS = {
    "财报": ["财报", "年报", "营收", "利润", "收入", "财务"],
    "白皮书": ["白皮书", "解决方案", "行业报告", "技术方案"],
    "用户评论": ["评论", "评价", "用户反馈", "差评", "好评", "体验"],
    "官网介绍": ["官网", "产品介绍", "功能", "价格", "客户", "优势"],
}


def _keyword_company(text: str, filename: str) -> str:
    haystack = f"{filename}\n{text[:4000]}".lower()
    for company in KNOWN_COMPANIES:
        if company.lower() in haystack:
            return company
    return Path(filename).stem[:40] or "未知竞品"


def _keyword_category(text: str, filename: str) -> str:
    haystack = f"{filename}\n{text[:4000]}"
    best = ("资料", 0)
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(haystack.count(keyword) for keyword in keywords)
        if score > best[1]:
            best = (category, score)
    return best[0]


def classify_document(text: str, filename: str) -> dict[str, Any]:
    fallback = {
        "company": _keyword_company(text, filename),
        "category": _keyword_category(text, filename),
        "confidence": 0.55,
        "reason": "基于文件名和关键词推断",
    }

    result = dashscope_client.json_chat(
        "你是文档分类助手。只输出 JSON，不要输出 Markdown。",
        (
            "请判断这份竞品资料主要属于哪家公司/产品，以及资料类型。"
            "如果无法判断公司，company 写“未知竞品”。"
            "category 只能从 官网介绍、财报、白皮书、用户评论、资料 中选择。"
            '输出 JSON：{"company":"", "category":"", "confidence":0.0, "reason":""}。\n'
            f"文件名：{filename}\n正文片段：{text[:5000]}"
        ),
    )
    if not result:
        return fallback

    company = str(result.get("company") or fallback["company"]).strip()
    category = str(result.get("category") or fallback["category"]).strip()
    if category not in {"官网介绍", "财报", "白皮书", "用户评论", "资料"}:
        category = fallback["category"]

    try:
        confidence = float(result.get("confidence", fallback["confidence"]))
    except Exception:
        confidence = fallback["confidence"]

    return {
        "company": company or fallback["company"],
        "category": category,
        "confidence": max(0.0, min(1.0, confidence)),
        "reason": str(result.get("reason") or fallback["reason"]),
    }
