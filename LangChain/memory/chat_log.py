import json
import time
from pathlib import Path
from typing import Any


class JsonChatLogger:
    """JSON 对话日志器，记录每轮 SemanticObject 三层协作轨迹。"""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.records = self._load()

    def _load(self) -> list[dict[str, Any]]:
        """读取已有日志。"""
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("records", [])
        if not isinstance(data, list):
            raise ValueError(f"对话日志文件格式错误: {self.path}")
        return data

    def append_turn(self, final_state: dict[str, Any]) -> None:
        """从最终状态抽取三层协议信息并追加为一轮对话记录。

        记录包含每步性能指标(step_metrics)和总性能指标(performance_summary)。
        """
        control_stack = final_state.get("control_stack", [])
        precise_stack = final_state.get("precise_stack", [])
        metrics_data = final_state.get("metrics", {})
        turns = metrics_data.get("turns", [])
        summary = metrics_data.get("summary", {})

        # 从三层协议栈中提取每个 Agent 的协作记录，并附加每步性能指标
        agent_outputs = []
        for i, precise in enumerate(precise_stack):
            control = control_stack[i] if i < len(control_stack) else {}
            turn_metrics = turns[i] if i < len(turns) else {}
            token_usage = turn_metrics.get("token_usage", {})
            agent_outputs.append(
                {
                    "agent": control.get("dst", ""),
                    "action": control.get("action", ""),
                    "precise": precise,
                    "step": control.get("step", 0),
                    "step_metrics": {
                        "prompt_tokens": token_usage.get("prompt_tokens", 0),
                        "completion_tokens": token_usage.get("completion_tokens", 0),
                        "total_tokens": token_usage.get("total_tokens", 0),
                        "precise_chars": turn_metrics.get("precise_chars", 0),
                        "precise_request_chars": turn_metrics.get("precise_request_chars", 0),
                        "precise_response_chars": turn_metrics.get("precise_response_chars", 0),
                        "duration_seconds": turn_metrics.get("duration_seconds", 0),
                        "memory_hits": turn_metrics.get("memory_hits", 0),
                        "semantic_transfers": turn_metrics.get("semantic_transfers", 0),
                        "semantic_bytes": turn_metrics.get("semantic_bytes", 0),
                        "control_decisions": turn_metrics.get("control_decisions", 0),
                    },
                }
            )

        # 构建总性能摘要
        summary_token_usage = summary.get("token_usage", {})
        performance_summary = {
            "total_tokens": summary_token_usage.get("total_tokens", 0),
            "prompt_tokens": summary_token_usage.get("prompt_tokens", 0),
            "completion_tokens": summary_token_usage.get("completion_tokens", 0),
            "total_duration_seconds": summary.get("total_duration_seconds", 0),
            "message_count": summary.get("message_count", 0),
            "precise_chars": summary.get("precise_chars", 0),
            "semantic_transfers": summary.get("semantic_transfers", 0),
            "semantic_bytes": summary.get("semantic_bytes", 0),
            "control_decisions": summary.get("control_decisions", 0),
            "memory_hits": summary.get("memory_hits", 0),
            "memory_hit_rate": summary.get("memory_hit_rate", 0.0),
        }

        record = {
            "trace_id": final_state.get("trace_id"),
            "mode": final_state.get("mode", "structured"),
            "created_at": time.time(),
            "user_question": final_state.get("user_question", ""),
            "agent_outputs": agent_outputs,
            "metrics": metrics_data,
            "performance_summary": performance_summary,
            "final_answer": final_state.get("final_answer", ""),
        }
        self.records.append(record)
        self._save()

    def _save(self) -> None:
        """保存日志文件。"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": "chatlog-json-0.3",
            "updated_at": time.time(),
            "records": self.records,
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )