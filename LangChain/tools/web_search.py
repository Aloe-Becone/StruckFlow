import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class WebSearchConfig:
    """SearXNG 检索工具配置。"""

    base_url: str
    max_results: int = 5
    timeout: float = 10.0
    language: str = ""


class SearxngSearchTool:
    """通过 SearXNG JSON API 获取资料搜索 Agent 可消费的结构化结果。"""

    def __init__(self, config: WebSearchConfig) -> None:
        self.config = config

    def search(self, query: str) -> dict[str, Any]:
        """执行检索并统一返回 provider、query、results、suggestions 等字段。"""
        query_params = {
            "q": query,
            "format": "json",
        }
        if self.config.language:
            query_params["language"] = self.config.language
        params = urlencode(query_params)
        url = f"{self.config.base_url.rstrip('/')}/search?{params}"
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )
        try:
            with urlopen(request, timeout=self.config.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 403:
                raise RuntimeError(
                    "SearXNG 返回 403。请检查 settings.yml 中 search.formats 是否包含 json，"
                    "并确认实例允许 /search?format=json API 请求。"
                ) from exc
            raise
        return {
            "provider": "searxng",
            "query": data.get("query", query),
            "total_results": len(data.get("results", [])),
            "result_count": len(data.get("results", [])),
            "results": self._normalize_results(data),
            "answers": data.get("answers", []),
            "suggestions": data.get("suggestions", []),
            "unresponsive_engines": [
                {"engine": item[0], "reason": item[1]}
                for item in data.get("unresponsive_engines", [])
            ],
        }

    def _normalize_results(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """把不同搜索引擎字段规整为 Agent prompt 约定的结果结构。"""
        results = []
        for item in data.get("results", [])[: self.config.max_results]:
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", ""),
                    "content": item.get("content", ""),
                    "score": item.get("score", 0),
                    "source": item.get("engine", ""),
                    "engine": item.get("engine") or item.get("engines", ""),
                    "published": item.get("publishedDate", None),
                }
            )
        return results


class DisabledSearchTool:
    """关闭联网检索时的占位工具，保持工作流接口一致。"""

    def search(self, query: str) -> dict[str, Any]:
        """返回明确的禁用错误，避免资料搜索 Agent 编造外部结果。"""
        return {
            "provider": "disabled",
            "query": query,
            "results": [],
            "error": "web search is disabled",
        }
