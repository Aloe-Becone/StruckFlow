from pathlib import Path

from ..agents.workflow import MultiAgentSystem
from .config import load_settings
from .llm import build_chat_model
from ..memory.embedding import QwenEmbeddingService
from ..memory.store import JsonMemoryStore
from ..tools.web_search import DisabledSearchTool, SearxngSearchTool, WebSearchConfig


def create_multi_agent_system(memory_path: Path) -> tuple[MultiAgentSystem, str]:
    """按配置组装 LLM、embedding、共享记忆和检索工具。"""
    settings = load_settings()
    llm = build_chat_model(settings)
    embeddings = QwenEmbeddingService.from_settings(settings)
    memory = JsonMemoryStore(memory_path, settings.memory_search_limit)
    search_tool = (
        SearxngSearchTool(
            WebSearchConfig(
                base_url=settings.searxng_base_url,
                max_results=settings.web_search_max_results,
                timeout=settings.web_search_timeout,
                language=settings.web_search_language,
            )
        )
        if settings.web_search_enabled
        else DisabledSearchTool()
    )
    return MultiAgentSystem(llm, embeddings, memory, search_tool), settings.openai_model