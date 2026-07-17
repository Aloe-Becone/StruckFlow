from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class ConversationSession:
    """一次可导入的会话，绑定同一时间戳下的记忆文件和对话日志。"""

    index: int
    timestamp: str
    memory_path: Path
    chat_path: Path
    updated_at: float

    @property
    def name(self) -> str:
        """展示给 CLI 用户的会话名称。"""
        return self.timestamp


class MemorySessionManager:
    """管理历史记忆会话，支持新建和恢复跨任务上下文。"""

    def __init__(self, memory_dir: Path, chat_dir: Path) -> None:
        self.memory_dir = memory_dir
        self.chat_dir = chat_dir

    def list_sessions(self) -> list[ConversationSession]:
        """按最近更新时间倒序列出可导入的记忆会话。"""
        if not self.memory_dir.exists():
            return []
        files = sorted(
            self.memory_dir.glob("mem-*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        return [
            self._session_from_memory_path(index, path)
            for index, path in enumerate(files, start=1)
        ]

    def new_session(self) -> ConversationSession:
        """创建新的记忆/日志路径；文件在首次写入时落盘。"""
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.chat_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return ConversationSession(
            index=0,
            timestamp=timestamp,
            memory_path=self.memory_dir / f"mem-{timestamp}.json",
            chat_path=self.chat_dir / f"chat-{timestamp}.json",
            updated_at=0,
        )

    def _session_from_memory_path(self, index: int, path: Path) -> ConversationSession:
        """根据记忆文件名推导同时间戳的对话日志路径。"""
        timestamp = path.stem.removeprefix("mem-")
        return ConversationSession(
            index=index,
            timestamp=timestamp,
            memory_path=path,
            chat_path=self.chat_dir / f"chat-{timestamp}.json",
            updated_at=path.stat().st_mtime,
        )
