"""纯文本模式指标统计：独立于主系统指标模块。

与主系统 metrics/recorder.py 的区别：
- 纯文本模式没有 Control/Semantic/Precise 三层分离
- 所有通信内容都消耗 token（无零 token 层）
- 没有 向量传递、路由决策等指标
- 专注于 token 开销、字符开销、耗时等基线指标
"""

import math
import time
from typing import Any


def text_estimate_tokens(text: str) -> int:
    """按字符数粗略估算 token（与主系统 estimate_token_count 相同算法）。"""
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def _read_int(mapping: dict[str, Any], *names: str) -> int:
    """从不同模型 SDK 的 usage 字段名中读取整数值。"""
    for name in names:
        value = mapping.get(name)
        if isinstance(value, int):
            return value
    return 0


def text_normalize_usage(response: Any, prompt_text: str, completion_text: str) -> dict[str, Any]:
    """统一 token usage，缺失时退回字符估算。"""
    usage: dict[str, Any] = {}
    usage_metadata = getattr(response, "usage_metadata", None)
    response_metadata = getattr(response, "response_metadata", {}) or {}
    token_usage = response_metadata.get("token_usage", {}) if isinstance(response_metadata, dict) else {}

    if isinstance(usage_metadata, dict):
        usage = {
            "prompt_tokens": _read_int(usage_metadata, "input_tokens", "prompt_tokens"),
            "completion_tokens": _read_int(usage_metadata, "output_tokens", "completion_tokens"),
            "total_tokens": _read_int(usage_metadata, "total_tokens"),
            "source": "model",
        }
    elif isinstance(token_usage, dict) and token_usage:
        usage = {
            "prompt_tokens": _read_int(token_usage, "prompt_tokens", "input_tokens"),
            "completion_tokens": _read_int(token_usage, "completion_tokens", "output_tokens"),
            "total_tokens": _read_int(token_usage, "total_tokens"),
            "source": "model",
        }

    if not usage:
        usage = {
            "prompt_tokens": text_estimate_tokens(prompt_text),
            "completion_tokens": text_estimate_tokens(completion_text),
            "total_tokens": 0,
            "source": "estimated",
        }

    if not usage.get("total_tokens"):
        usage["total_tokens"] = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
    return usage


def text_merge_usage(*usages: dict[str, Any]) -> dict[str, Any]:
    """合并多次 LLM 调用的 token 使用量。"""
    merged = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "source": "none",
    }
    sources = set()
    for usage in usages:
        if not usage:
            continue
        merged["prompt_tokens"] += int(usage.get("prompt_tokens", 0) or 0)
        merged["completion_tokens"] += int(usage.get("completion_tokens", 0) or 0)
        merged["total_tokens"] += int(usage.get("total_tokens", 0) or 0)
        sources.add(str(usage.get("source", "unknown")))
    if sources:
        merged["source"] = "+".join(sorted(sources))
    return merged


def new_text_metrics() -> dict[str, Any]:
    """创建纯文本模式的指标容器。"""
    return {
        "mode": "text",
        "started_at": time.time(),
        "turns": [],
    }


def record_text_turn(
    metrics: dict[str, Any],
    *,
    agent: str,
    prompt_text: str,
    completion_text: str,
    token_usage: dict[str, Any],
    duration_seconds: float,
) -> dict[str, Any]:
    """记录纯文本模式单个 Agent 的指标。"""
    turn = {
        "agent": agent,
        "mode": "text",
        # 全部通信内容都消耗 token（无三层分离）
        "total_chars": len(prompt_text or "") + len(completion_text or ""),
        "prompt_chars": len(prompt_text or ""),
        "completion_chars": len(completion_text or ""),
        "token_usage": token_usage,
        # 通用指标
        "duration_seconds": round(duration_seconds, 4),
    }
    metrics.setdefault("turns", []).append(turn)
    return turn


def finalize_text_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    """汇总纯文本模式的全部指标。"""
    turns = metrics.get("turns", [])
    token_total = text_merge_usage(*(turn.get("token_usage", {}) for turn in turns))
    message_count = len(turns)
    total_chars = sum(int(turn.get("total_chars", 0) or 0) for turn in turns)
    prompt_chars = sum(int(turn.get("prompt_chars", 0) or 0) for turn in turns)
    completion_chars = sum(int(turn.get("completion_chars", 0) or 0) for turn in turns)

    summary = {
        "mode": "text",
        "message_count": message_count,
        # 全部消耗 token
        "total_chars": total_chars,
        "prompt_chars": prompt_chars,
        "completion_chars": completion_chars,
        "token_usage": token_total,
        # 通用
        "total_duration_seconds": round(
            time.time() - float(metrics.get("started_at", time.time())), 4
        ),
    }
    metrics["summary"] = summary
    return metrics