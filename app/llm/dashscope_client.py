import json
import logging
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class DashScopeClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def enabled(self) -> bool:
        return (
            self.settings.llm_provider.lower() == "dashscope"
            and bool(self.settings.dashscope_api_key)
            and self.settings.dashscope_api_key != "your_key_here"
        )

    def chat(self, system_prompt: str, user_prompt: str) -> str | None:
        if not self.enabled:
            return None
        try:
            import dashscope

            dashscope.api_key = self.settings.dashscope_api_key
            response = dashscope.Generation.call(
                model=self.settings.dashscope_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                result_format="message",
            )
            status_code = getattr(response, "status_code", None)
            if status_code and status_code != 200:
                logger.warning("DashScope call failed: %s", response)
                return None
            return response.output.choices[0].message.content
        except Exception as exc:
            logger.warning("DashScope call failed: %s", exc)
            return None

    def json_chat(self, system_prompt: str, user_prompt: str) -> dict[str, Any] | None:
        content = self.chat(system_prompt, user_prompt)
        if not content:
            return None
        try:
            start = content.find("{")
            end = content.rfind("}")
            if start >= 0 and end > start:
                return json.loads(content[start : end + 1])
            return json.loads(content)
        except Exception as exc:
            logger.warning("DashScope JSON parse failed: %s; content=%s", exc, content[:500])
            return None


dashscope_client = DashScopeClient()
