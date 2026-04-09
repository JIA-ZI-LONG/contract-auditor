# backend/chains/llm.py

"""
LLM 单例配置

演示 ChatOpenAI 配置：
- 支持任意 OpenAI 兼容 API
- 通过 base_url 配置自定义端点
"""

from langchain_openai import ChatOpenAI
from config import settings

_llm = None


def get_llm() -> ChatOpenAI:
    """
    获取 LLM 实例（单例模式）

    Returns:
        ChatOpenAI: 配置好的 LLM 实例
    """
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=settings.bailian_model,
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=settings.bailian_base_url,
            temperature=0.3
        )
    return _llm