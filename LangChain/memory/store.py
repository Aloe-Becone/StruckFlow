"""共享记忆存储：支持关键词 / 标签 / 语义三模式检索。

记忆单元存储 Agent 输出的 Precise 字段 + 多粒度向量，
检索时支持三种模式：
1. 语义检索：余弦相似度匹配（主模式）
2. 关键词检索：在 task_topic / summary / content 中匹配
3. 标签检索：按 tags 列表精确匹配

命中结果只返回 Precise 层需要的摘要格式：{id, role, summary, score}
"""

import json
import re
import time
from pathlib import Path
from typing import Any, Literal

from .embedding import cosine_similarity


# 检索模式
SearchMode = Literal["semantic", "keyword", "tag", "hybrid"]


class JsonMemoryStore:
    """JSON 持久化共享记忆库，支持三种检索模式。"""

    def __init__(self, path: Path, search_limit: int = 3) -> None:
        self.path = path
        self.search_limit = search_limit
        self.items = self._load()

    # ─── 加载与持久化 ─────────────────────────────────────────────────

    def _load(self) -> list[dict[str, Any]]:
        """读取历史记忆文件。"""
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("items", [])
        if not isinstance(data, list):
            raise ValueError(f"记忆文件格式错误: {self.path}")
        return [
            self._normalize_item(item, index)
            for index, item in enumerate(data, start=1)
            if isinstance(item, dict)
        ]

    def _normalize_item(self, item: dict[str, Any], index: int) -> dict[str, Any]:
        """规范化记忆单元。"""
        content = item.get("content", {})
        if not isinstance(content, dict):
            content = {"value": content}
        source_agent = item.get("source_agent") or item.get("role") or "unknown"
        return {
            **item,
            "id": item.get("id") or f"mem-{index:04d}",
            "source_agent": source_agent,
            "role": source_agent,
            "mode": item.get("mode", "structured"),
            "task_topic": item.get("task_topic") or self._infer_topic(content),
            "summary": item.get("summary") or self._infer_summary(content),
            "created_at": item.get("created_at", time.time()),
            "content": content,
            "sentence_vec": item.get("sentence_vec", []),
            "task_vec": item.get("task_vec", []),
            "tags": item.get("tags", []),
            "performance": item.get("performance", {}),
        }

    def _save(self) -> None:
        """将当前记忆集合写回磁盘。"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": "memcollm-json-0.3",
            "updated_at": time.time(),
            "items": self.items,
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ─── 写入 ─────────────────────────────────────────────────────────

    def add(
        self,
        role: str,
        content: dict[str, Any],
        sentence_vec: list[float],
        *,
        task_vec: list[float] | None = None,
        mode: str = "structured",
        trace_id: str = "",
        task_topic: str = "",
        summary: str = "",
        tags: list[str] | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> str:
        """新增一条记忆单元并返回其 ID。

        支持 sentence_vec 和 task_vec 两种粒度的向量。
        metrics 可包含该步骤的性能指标：token_usage, duration_seconds 等。
        """
        memory_id = f"mem-{len(self.items) + 1:04d}"
        normalized_content = content if isinstance(content, dict) else {"value": content}

        # 自动推断标签
        auto_tags = list(tags or [])
        if role not in auto_tags:
            auto_tags.append(role)
        if mode not in auto_tags:
            auto_tags.append(mode)

        # 规范化性能指标
        performance = {}
        if metrics:
            token_usage = metrics.get("token_usage", {})
            performance = {
                "total_tokens": token_usage.get("total_tokens", 0),
                "prompt_tokens": token_usage.get("prompt_tokens", 0),
                "completion_tokens": token_usage.get("completion_tokens", 0),
                "precise_chars": metrics.get("precise_chars", 0),
                "duration_seconds": metrics.get("duration_seconds", 0),
                "memory_hits": metrics.get("memory_hits", 0),
                "semantic_transfers": metrics.get("semantic_transfers", 0),
                "semantic_bytes": metrics.get("semantic_bytes", 0),
                "control_decisions": metrics.get("control_decisions", 0),
            }

        self.items.append(
            {
                "id": memory_id,
                "source_agent": role,
                "role": role,
                "mode": mode,
                "trace_id": trace_id,
                "task_topic": task_topic or self._infer_topic(normalized_content),
                "summary": summary or self._infer_summary(normalized_content),
                "content": normalized_content,
                "sentence_vec": sentence_vec or [],
                "task_vec": task_vec or [],
                "created_at": time.time(),
                "tags": auto_tags,
                "performance": performance,
            }
        )
        self._save()
        return memory_id

    # ─── 检索（三模式）─────────────────────────────────────────────────

    def search(
        self,
        query_vector: list[float] | None = None,
        *,
        keyword: str = "",
        tags: list[str] | None = None,
        mode: SearchMode = "semantic",
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """多模式检索共享记忆。

        Args:
            query_vector: 查询向量（语义检索用）
            keyword: 关键词（关键词检索用）
            tags: 标签列表（标签检索用）
            mode: 检索模式 semantic/keyword/tag/hybrid
            limit: 返回数量上限
        """
        max_results = limit or self.search_limit

        if mode == "semantic":
            return self._search_semantic(query_vector, max_results)
        if mode == "keyword":
            return self._search_keyword(keyword, max_results)
        if mode == "tag":
            return self._search_tag(tags or [], max_results)
        if mode == "hybrid":
            return self._search_hybrid(
                query_vector, keyword=keyword, tags=tags or [], limit=max_results
            )
        return []

    def search_hits(
        self,
        query_vector: list[float] | None = None,
        *,
        keyword: str = "",
        tags: list[str] | None = None,
        mode: SearchMode = "semantic",
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """检索并返回 Precise 层格式：{id, role, summary, score}。

        这是给 LLM 的 memory_hits 字段，只传摘要不传全文。
        """
        results = self.search(
            query_vector, keyword=keyword, tags=tags, mode=mode, limit=limit
        )
        return [
            {
                "id": item["id"],
                "role": item.get("role", item.get("source_agent", "")),
                "summary": item.get("summary", ""),
                "score": item.get("score", 0),
            }
            for item in results
        ]

    # ─── 内部检索实现 ─────────────────────────────────────────────────

    def _search_semantic(
        self, query_vector: list[float] | None, limit: int
    ) -> list[dict[str, Any]]:
        """语义检索：余弦相似度匹配。"""
        if not query_vector:
            return []
        scored = [
            (cosine_similarity(query_vector, item.get("sentence_vec", [])), item)
            for item in self.items
            if item.get("sentence_vec")
        ]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [self._hit_item(score, item) for score, item in scored[:limit] if score > 0.1]

    def _search_keyword(self, keyword: str, limit: int) -> list[dict[str, Any]]:
        """关键词检索：在 task_topic / summary / content 中匹配。"""
        if not keyword:
            return []
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        results = []
        for item in self.items:
            text = " ".join(
                [
                    item.get("task_topic", ""),
                    item.get("summary", ""),
                    json.dumps(item.get("content", {}), ensure_ascii=False),
                ]
            )
            if pattern.search(text):
                results.append(self._hit_item(1.0, item))
                if len(results) >= limit:
                    break
        return results

    def _search_tag(self, tags: list[str], limit: int) -> list[dict[str, Any]]:
        """标签检索：按 tags 列表精确匹配。"""
        if not tags:
            return []
        tag_set = set(tags)
        results = []
        for item in self.items:
            item_tags = set(item.get("tags", []))
            if tag_set & item_tags:
                results.append(self._hit_item(1.0, item))
                if len(results) >= limit:
                    break
        return results

    def _search_hybrid(
        self,
        query_vector: list[float] | None,
        *,
        keyword: str,
        tags: list[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        """混合检索：语义 + 关键词 + 标签，去重后按语义分数排序。"""
        seen_ids: set[str] = set()
        merged: list[dict[str, Any]] = []

        # 语义检索结果优先
        for item in self._search_semantic(query_vector, limit * 2):
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                merged.append(item)

        # 关键词检索补充
        for item in self._search_keyword(keyword, limit * 2):
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                item["score"] = 0.5  # 关键词匹配给中等分数
                merged.append(item)

        # 标签检索补充
        for item in self._search_tag(tags, limit * 2):
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                item["score"] = 0.3  # 标签匹配给较低分数
                merged.append(item)

        # 按分数降序
        merged.sort(key=lambda x: x.get("score", 0), reverse=True)
        return merged[:limit]

    # ─── 辅助方法 ─────────────────────────────────────────────────────

    def _hit_item(self, score: float, item: dict[str, Any]) -> dict[str, Any]:
        """构造检索命中项。"""
        return {
            "id": item["id"],
            "source_agent": item.get("source_agent") or item.get("role", ""),
            "role": item.get("role", item.get("source_agent", "")),
            "mode": item.get("mode", "structured"),
            "task_topic": item.get("task_topic", ""),
            "summary": item.get("summary", ""),
            "score": round(score, 4),
            "content": item.get("content", {}),
            "tags": item.get("tags", []),
        }

    def summaries(self) -> list[dict[str, Any]]:
        """返回轻量记忆目录。"""
        return [
            {
                "id": item["id"],
                "source_agent": item.get("source_agent") or item.get("role", ""),
                "role": item.get("role", item.get("source_agent", "")),
                "mode": item.get("mode", "structured"),
                "created_at": item["created_at"],
                "task_topic": item.get("task_topic", ""),
                "summary": item.get("summary", ""),
                "tags": item.get("tags", []),
                "content_keys": list(item.get("content", {}).keys()),
                "performance": item.get("performance", {}),
            }
            for item in self.items
        ]

    def _infer_topic(self, content: dict[str, Any]) -> str:
        """从常见 Agent 输出字段中推断记忆主题。"""
        for key in ("goal", "draft", "final_answer", "note"):
            value = content.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:80]
        return "未命名任务"

    def _infer_summary(self, content: dict[str, Any]) -> str:
        """生成短摘要。"""
        for key in ("summary", "note", "final_answer", "draft", "goal"):
            value = content.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:160]
        return json.dumps(content, ensure_ascii=False)[:160]