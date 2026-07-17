"""纯文本对比模块：独立封装，不修改已有功能代码。

提供纯文本协作模式作为赛题要求的对比基线：
- Agent 间通过自然语言长文本直接透传全部协作信息
- 无结构化协议、无向量检索、无共享记忆
- 输出和对话记录不存储，仅作对比

公开 API：
- build_comparison(): 构建双模式对比数据
- print_comparison_report(): 打印对比报告
- print_text_result(): 打印纯文本模式结果
- TextModeRunner: 纯文本模式运行器
- build_text_model(): 构建无 JSON 约束的 LLM
"""

from comparison.comparator import build_comparison, print_comparison_report, print_text_result
from comparison.text_runner import TextModeRunner, build_text_model

__all__ = ["build_comparison", "print_comparison_report", "print_text_result", "TextModeRunner", "build_text_model"]