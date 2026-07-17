from langchain_openai import ChatOpenAI

from framework.config import Settings


def build_chat_model(settings: Settings) -> ChatOpenAI:
    """构造 JSON 输出模式的聊天模型，减少 Agent 协议解析失败率。"""
    return ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=settings.openai_temperature,
        model_kwargs={"response_format": {"type": "json_object"}},
    )
