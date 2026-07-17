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
        """从最终状态抽取三层协议信息并追加为一轮对话记录。"""
        control_stack = final_state.get("control_stack", [])
        precise_stack = final_state.get("precise_stack", [])

        # 从三层协议栈中提取每个 Agent 的协作记录
        agent_outputs = []
        for i, precise in enumerate(precise_stack):
            control = control_stack[i] if i < len(control_stack) else {}
            agent_outputs.append(
                {
                    "agent": control.get("dst", ""),
                    "action": control.get("action", ""),
                    "precise": precise,
                    "step": control.get("step", 0),
                }
            )

        record = {
            "trace_id": final_state.get("trace_id"),
            "mode": final_state.get("mode", "structured"),
            "created_at": time.time(),
            "user_question": final_state.get("user_question", ""),
            "agent_outputs": agent_outputs,
            "metrics": final_state.get("metrics", {}),
            "final_answer": final_state.get("final_answer", ""),
        }
        self.records.append(record)
        self._save()

    def _save(self) -> None:
        """保存日志文件。"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": "chatlog-json-0.2",
            "updated_at": time.time(),
            "records": self.records,
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )