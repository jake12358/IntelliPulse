from typing import Any

from app.llm.dashscope_client import dashscope_client


def build_radar(matrix: dict[str, Any], sentiment_scores: dict[str, Any]) -> list[dict[str, int | str]]:
    rows = matrix.get("rows", []) if isinstance(matrix, dict) else []
    doc_coverage = min(100, 45 + len(rows) * 12)
    feature_depth = 50
    pricing_clarity = 45
    sentiment_value = 55

    feature_counts = []
    for row in rows:
        features = row.get("features", [])
        if isinstance(features, list):
            feature_counts.append(len(features))
        elif features:
            feature_counts.append(1)
        pricing = str(row.get("pricing", ""))
        if pricing and "待" not in pricing and "未知" not in pricing:
            pricing_clarity += 10

    if feature_counts:
        feature_depth = min(100, 45 + max(feature_counts) * 10)

    if sentiment_scores:
        positives = sum(int(item.get("positive", 0)) for item in sentiment_scores.values())
        negatives = sum(int(item.get("negative", 0)) for item in sentiment_scores.values())
        sentiment_value = max(35, min(95, 55 + positives * 6 - negatives * 6))

    return [
        {"metric": "资料覆盖度", "value": doc_coverage},
        {"metric": "功能清晰度", "value": feature_depth},
        {"metric": "价格清晰度", "value": min(100, pricing_clarity)},
        {"metric": "情感倾向", "value": sentiment_value},
        {"metric": "结论可信度", "value": min(100, (doc_coverage + feature_depth + pricing_clarity) // 3)},
    ]


def _text_score(value: Any, positive_words: list[str] | None = None) -> int:
    text = str(value or "")
    if not text or "资料未提及" in text or "待" in text or "未知" in text:
        return 35
    score = 60
    if len(text) > 12:
        score += 12
    if positive_words and any(word in text for word in positive_words):
        score += 8
    return min(95, score)


def build_company_radars(
    matrix: dict[str, Any],
    sentiment_scores: dict[str, Any],
    sources: list[dict[str, Any]],
) -> dict[str, list[dict[str, int | str]]]:
    rows = matrix.get("rows", []) if isinstance(matrix, dict) else []
    source_counts: dict[str, int] = {}
    for source in sources:
        company = str(source.get("company", ""))
        if company:
            source_counts[company] = source_counts.get(company, 0) + 1

    result: dict[str, list[dict[str, int | str]]] = {}
    for row in rows:
        company = str(row.get("company", "未知竞品"))
        features = row.get("features", [])
        feature_count = len(features) if isinstance(features, list) else (1 if features else 0)
        sentiment = sentiment_scores.get(company, {}) if isinstance(sentiment_scores, dict) else {}
        positive = int(sentiment.get("positive", 0) or 0)
        negative = int(sentiment.get("negative", 0) or 0)

        result[company] = [
            {"metric": "资料覆盖", "value": min(95, 35 + source_counts.get(company, 0) * 15)},
            {"metric": "功能明确", "value": min(95, 35 + feature_count * 15)},
            {"metric": "价格明确", "value": _text_score(row.get("pricing"))},
            {"metric": "优势证据", "value": _text_score(row.get("advantages"), ["强", "高", "丰富", "成熟", "便捷"])},
            {"metric": "情感倾向", "value": max(30, min(95, 55 + positive * 8 - negative * 8))},
        ]
    return result


def build_company_radars_with_llm(
    matrix: dict[str, Any],
    sentiment_scores: dict[str, Any],
    sources: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    fallback = build_company_radars(matrix, sentiment_scores, sources)
    if not fallback:
        return fallback

    result = dashscope_client.json_chat(
        "你是竞品分析评分专家。只输出 JSON，不要输出 Markdown。",
        (
            "请只基于给定资料，为每个竞品输出雷达图评分。"
            "评分为 0-100 的整数，不能所有竞品完全一样；资料不足时给低分并说明原因。"
            "指标固定为：资料覆盖、功能明确、价格明确、优势证据、情感倾向。"
            "资料覆盖要根据该竞品在 sources 中的资料数量和内容充分度判断。"
            "输出 JSON 格式："
            '{"companies":{"公司名":[{"metric":"资料覆盖","value":80,"reason":"..."},'
            '{"metric":"功能明确","value":70,"reason":"..."},'
            '{"metric":"价格明确","value":60,"reason":"..."},'
            '{"metric":"优势证据","value":75,"reason":"..."},'
            '{"metric":"情感倾向","value":65,"reason":"..."}]}}。\n'
            f"对比矩阵：{matrix}\n情感：{sentiment_scores}\n资料切片：{sources}"
        ),
    )
    companies = result.get("companies") if result else None
    if not isinstance(companies, dict):
        return fallback

    normalized: dict[str, list[dict[str, Any]]] = {}
    required = ["资料覆盖", "功能明确", "价格明确", "优势证据", "情感倾向"]
    for company, items in companies.items():
        if not isinstance(items, list):
            continue
        values = []
        by_metric = {str(item.get("metric")): item for item in items if isinstance(item, dict)}
        for metric in required:
            item = by_metric.get(metric, {})
            try:
                value = int(item.get("value", 0))
            except Exception:
                value = 0
            values.append(
                {
                    "metric": metric,
                    "value": max(0, min(100, value)),
                    "reason": str(item.get("reason", ""))[:160],
                }
            )
        normalized[str(company)] = values
    return normalized or fallback


def source_preview(docs: list[dict[str, Any]], limit: int = 6) -> list[dict[str, Any]]:
    previews = []
    for doc in docs[:limit]:
        content = str(doc.get("content", ""))
        previews.append(
            {
                "id": doc.get("id", ""),
                "company": doc.get("company", ""),
                "source_filename": doc.get("source_filename", ""),
                "stored_path": doc.get("stored_path", ""),
                "parsed_path": doc.get("parsed_path", ""),
                "score": doc.get("score", 0),
                "preview": content[:180],
            }
        )
    return previews
