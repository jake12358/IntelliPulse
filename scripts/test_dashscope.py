import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.llm.dashscope_client import dashscope_client


def main() -> int:
    settings = get_settings()
    print(f"LLM_PROVIDER={settings.llm_provider}")
    print(f"DASHSCOPE_MODEL={settings.dashscope_model}")
    print(f"DASHSCOPE_API_KEY set={dashscope_client.enabled}")

    if not dashscope_client.enabled:
        print("DashScope is not enabled. Please set DASHSCOPE_API_KEY in .env.")
        return 1

    answer = dashscope_client.chat(
        "你是一个简洁的系统自检助手。",
        "请只回复一句话：IntelliPulse DashScope 已连接。",
    )
    if not answer:
        print("DashScope call failed. Check the API key, network, and model name.")
        return 1
    print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
