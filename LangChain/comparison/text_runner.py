"""纯文本模式运行器：独立于主系统工作流。

核心设计：
- Agent 间通过自然语言长文本直接透传全部协作信息
- 每个 Agent 收到之前所有 Agent 的完整自然语言输出拼接
- 无结构化协议、无向量检索、无共享记忆
- LLM 自己决定下一步路由（从输出中解析 next_agent）
- 输出和对话记录不存储，仅作对比

与主系统 workflow.py 的区别：
- 不使用 SemanticObject 三层协议
- 不使用 JsonMemoryStore 共享记忆
- 不使用 QwenEmbeddingService 向量
- 不使用 Control 层系统路由
- 不使用 Precise 层最小字段过滤
- 不写入对话日志和记忆文件
- 不强制 JSON 输出格式（自然语言输出）
"""

import re
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .text_metrics import (
    finalize_text_metrics,
    new_text_metrics,
    record_text_turn,
    text_normalize_usage,
)
from .text_prompts import (
    TEXT_AGENT_SEQUENCE,
    TEXT_NEXT_AGENT_MAP,
    TEXT_ROLE_PROMPTS,
    TextAgentName,
)
from ..framework.config import Settings


def build_text_model(settings: Settings) -> ChatOpenAI:
    """构建纯文本模式的 LLM：不强制 JSON 输出格式。

    与主系统 build_chat_model 的区别：移除 response_format 约束，
    因为纯文本模式输出自然语言而非 JSON。
    """
    return ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=settings.openai_temperature,
    )


class TextModeRunner:
    """纯文本协作模式运行器。

    使用与主系统相同的模型配置，但通信方式为自然语言长文本透传。
    不使用任何结构化协议、向量检索、共享记忆。
    """

    def __init__(self, llm: ChatOpenAI) -> None:
        self.llm = llm
        self.max_steps = 6

    def run(self, question: str) -> dict[str, Any]:
        """执行纯文本模式协作，返回结果和指标。

        Args:
            question: 用户问题

        Returns:
            {
                "final_answer": str,
                "agent_outputs": [{"agent": str, "output": str}],
                "metrics": dict,
            }
        """
        metrics = new_text_metrics()
        agent_outputs: list[dict[str, str]] = []
        conversation_history = f"用户问题：{question}\n"

        # 第一个 Agent 固定为任务分配
        current_agent: TextAgentName = "任务分配"

        for step in range(self.max_steps):
            # 构建纯文本输入：系统提示 + 全部历史输出
            system_prompt = TEXT_ROLE_PROMPTS[current_agent]
            human_text = self._build_human_input(current_agent, conversation_history)

            # 调用 LLM
            started_at = time.perf_counter()
            response = self.llm.invoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=human_text),
                ]
            )
            duration_seconds = time.perf_counter() - started_at

            content = response.content if isinstance(response.content, str) else str(response.content)
            prompt_text = human_text
            completion_text = content

            # 记录指标
            usage = text_normalize_usage(response, prompt_text, completion_text)
            record_text_turn(
                metrics,
                agent=current_agent,
                prompt_text=prompt_text,
                completion_text=completion_text,
                token_usage=usage,
                duration_seconds=duration_seconds,
            )

            # 记录 Agent 输出
            agent_outputs.append({"agent": current_agent, "output": content})

            # 更新对话历史：拼接当前 Agent 的完整输出
            conversation_history += f"\n--- {current_agent} 的输出 ---\n{content}\n"

            # 解析路由：从 LLM 输出中提取 next_agent
            next_agent = self._parse_next_agent(content)

            # 提取最终答案
            if next_agent == "END" or current_agent == "总结验证":
                break

            # 路由到下一个 Agent
            mapped = TEXT_NEXT_AGENT_MAP.get(next_agent)
            if mapped and mapped != "END":
                current_agent = mapped  # type: ignore[assignment]
            else:
                # 解析失败或到达终点，按固定顺序推进
                idx = TEXT_AGENT_SEQUENCE.index(current_agent)
                if idx + 1 < len(TEXT_AGENT_SEQUENCE):
                    current_agent = TEXT_AGENT_SEQUENCE[idx + 1]
                else:
                    break

        # 提取最终答案
        final_answer = self._extract_final_answer(agent_outputs)

        finalize_text_metrics(metrics)

        return {
            "final_answer": final_answer,
            "agent_outputs": agent_outputs,
            "metrics": metrics,
        }

    def _build_human_input(self, current_agent: TextAgentName, history: str) -> str:
        """构建纯文本模式的 Human 输入。

        任务分配 Agent 只收到用户问题；
        其他 Agent 收到用户问题 + 之前所有 Agent 的完整输出。
        """
        if current_agent == "任务分配":
            return history
        return history

    def _parse_next_agent(self, output: str) -> str:
        """从 LLM 输出中解析 next_agent 路由字段。"""
        # 匹配 "next_agent: XXX" 或 "next_agent：XXX"
        match = re.search(r"next_agent\s*[:：]\s*(\S+)", output, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_final_answer(self, agent_outputs: list[dict[str, str]]) -> str:
        """从 Agent 输出中提取最终答案。"""
        # 优先从总结验证 Agent 提取
        for output in reversed(agent_outputs):
            if output["agent"] == "总结验证":
                content = output["output"]
                # 尝试提取 "最终答案：" 后的内容
                match = re.search(
                    r"最终答案\s*[:：]\s*(.+)",
                    content,
                    re.DOTALL | re.IGNORECASE,
                )
                if match:
                    return match.group(1).strip()
                # 没有标记则返回最后一段
                return content.strip()

        # 兜底：从任务执行 Agent 提取草稿
        for output in reversed(agent_outputs):
            if output["agent"] == "任务执行":
                content = output["output"]
                match = re.search(
                    r"草稿\s*[:：]\s*(.+)",
                    content,
                    re.DOTALL | re.IGNORECASE,
                )
                if match:
                    return match.group(1).strip()

        # 最后兜底：返回最后一个 Agent 的输出
        if agent_outputs:
            return agent_outputs[-1]["output"].strip()
        return "未生成答案。"