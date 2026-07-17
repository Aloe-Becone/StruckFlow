"""对比编排器：先运行结构化模式，再运行纯文本模式，输出对比结果。

独立于主系统，不修改已有功能代码。
调用主系统的 MultiAgentSystem 运行结构化模式，
调用 TextModeRunner 运行纯文本模式，
然后生成对比报告。
"""

from typing import Any


def build_comparison(
    structured_result: dict[str, Any],
    text_result: dict[str, Any],
) -> dict[str, Any]:
    """构建结构化模式 vs 纯文本模式的对比数据。"""
    s_metrics = structured_result.get("metrics", {}).get("summary", {})
    t_metrics = text_result.get("metrics", {}).get("summary", {})

    s_tokens = s_metrics.get("token_usage", {})
    t_tokens = t_metrics.get("token_usage", {})

    s_total_tokens = s_tokens.get("total_tokens", 0)
    t_total_tokens = t_tokens.get("total_tokens", 0)
    token_saved = t_total_tokens - s_total_tokens
    token_saved_pct = (token_saved / t_total_tokens * 100) if t_total_tokens else 0

    s_prompt_tokens = s_tokens.get("prompt_tokens", 0)
    t_prompt_tokens = t_tokens.get("prompt_tokens", 0)
    prompt_saved = t_prompt_tokens - s_prompt_tokens
    prompt_saved_pct = (prompt_saved / t_prompt_tokens * 100) if t_prompt_tokens else 0

    s_precise_chars = s_metrics.get("precise_chars", 0)
    t_total_chars = t_metrics.get("total_chars", 0)
    char_saved = t_total_chars - s_precise_chars
    char_saved_pct = (char_saved / t_total_chars * 100) if t_total_chars else 0

    s_duration = s_metrics.get("total_duration_seconds", 0)
    t_duration = t_metrics.get("total_duration_seconds", 0)
    duration_diff = t_duration - s_duration

    s_messages = s_metrics.get("message_count", 0)
    t_messages = t_metrics.get("message_count", 0)

    return {
        # Token 对比
        "token": {
            "structured_total": s_total_tokens,
            "text_total": t_total_tokens,
            "saved": token_saved,
            "saved_pct": round(token_saved_pct, 1),
            "structured_prompt": s_prompt_tokens,
            "text_prompt": t_prompt_tokens,
            "prompt_saved": prompt_saved,
            "prompt_saved_pct": round(prompt_saved_pct, 1),
        },
        # 字符开销对比
        "chars": {
            "structured_precise_chars": s_precise_chars,
            "text_total_chars": t_total_chars,
            "saved": char_saved,
            "saved_pct": round(char_saved_pct, 1),
        },
        # 消息次数对比
        "messages": {
            "structured": s_messages,
            "text": t_messages,
        },
        # 耗时对比
        "duration": {
            "structured_seconds": s_duration,
            "text_seconds": t_duration,
            "diff_seconds": round(duration_diff, 2),
        },
        # 结构化模式独有指标
        "structured_only": {
            "semantic_transfers": s_metrics.get("semantic_transfers", 0),
            "semantic_bytes": s_metrics.get("semantic_bytes", 0),
            "control_decisions": s_metrics.get("control_decisions", 0),
            "memory_hits": s_metrics.get("memory_hits", 0),
            "memory_hit_rate": s_metrics.get("memory_hit_rate", 0),
        },
    }


def print_comparison_report(comparison_result: dict[str, Any]) -> None:
    """打印对比报告到终端。"""
    comp = comparison_result["comparison"]
    structured = comparison_result["structured_result"]
    text_res = comparison_result["text_result"]

    print("\n" + "=" * 60)
    print("  结构化协议 vs 纯文本 对比报告")
    print("=" * 60)

    # ── 结果对比 ──
    print("\n── 最终答案对比 ──")
    print(f"[结构化] {structured['final_answer'][:120]}...")
    print(f"[纯文本] {text_res['final_answer'][:120]}...")

    # ── Token 对比 ──
    token = comp["token"]
    print("\n── Token 开销对比 ──")
    print(f"  结构化模式: prompt={token['structured_prompt']}, total={token['structured_total']}")
    print(f"  纯文本模式: prompt={token['text_prompt']}, total={token['text_total']}")
    if token["saved"] > 0:
        print(f"  ✦ Token 节省: {token['saved']} ({token['saved_pct']}%)")
    elif token["saved"] < 0:
        print(f"  ✦ Token 增加: {abs(token['saved'])} (结构化模式更耗 token)")
    else:
        print(f"  ✦ Token 开销相同")

    # ── 字符开销对比 ──
    chars = comp["chars"]
    print("\n── 字符开销对比 ──")
    print(f"  结构化模式 Precise 层: {chars['structured_precise_chars']} 字符")
    print(f"  纯文本模式全部通信: {chars['text_total_chars']} 字符")
    if chars["saved"] > 0:
        print(f"  ✦ 字符节省: {chars['saved']} ({chars['saved_pct']}%)")
    elif chars["saved"] < 0:
        print(f"  ✦ 字符增加: {abs(chars['saved'])}")
    else:
        print(f"  ✦ 字符开销相同")

    # ── 消息次数对比 ──
    msgs = comp["messages"]
    print("\n── 消息次数对比 ──")
    print(f"  结构化模式: {msgs['structured']} 次")
    print(f"  纯文本模式: {msgs['text']} 次")

    # ── 耗时对比 ──
    dur = comp["duration"]
    print("\n── 耗时对比 ──")
    print(f"  结构化模式: {dur['structured_seconds']:.2f} 秒")
    print(f"  纯文本模式: {dur['text_seconds']:.2f} 秒")
    if dur["diff_seconds"] > 0:
        print(f"  ✦ 结构化模式更快 {dur['diff_seconds']:.2f} 秒")
    elif dur["diff_seconds"] < 0:
        print(f"  ✦ 纯文本模式更快 {abs(dur['diff_seconds']):.2f} 秒")
    else:
        print(f"  ✦ 耗时相同")

    # ── 结构化模式独有指标 ──
    only = comp["structured_only"]
    print("\n── 结构化模式独有指标（纯文本模式不具备）──")
    print(f"  Semantic 层向量传递: {only['semantic_transfers']} 次, {only['semantic_bytes']} bytes")
    print(f"  Control 层路由决策: {only['control_decisions']} 次")
    print(f"  共享记忆命中: {only['memory_hits']} (命中率 {only['memory_hit_rate']})")

    print("\n" + "=" * 60)


def print_text_result(text_result: dict[str, Any]) -> None:
    """打印纯文本模式的 Agent 输出过程。"""
    print("\n========== 纯文本模式执行过程 ==========")
    for i, output in enumerate(text_result.get("agent_outputs", []), start=1):
        print(f"\n── Agent {i}: {output['agent']} ──")
        # 只打印前 200 字符避免过长
        content = output["output"]
        if len(content) > 200:
            print(content[:200] + "...")
        else:
            print(content)

    print("\n========== 纯文本模式最终输出 ==========")
    print(text_result.get("final_answer", "未生成答案。"))

    # 打印纯文本模式指标
    t_metrics = text_result.get("metrics", {}).get("summary", {})
    t_tokens = t_metrics.get("token_usage", {})
    print("\n========== 纯文本模式指标 ==========")
    print(f"模式: 纯文本协作")
    print(f"消息次数: {t_metrics.get('message_count', 0)}")
    print(f"字符开销: {t_metrics.get('total_chars', 0)}")
    print(
        f"Token 开销: "
        f"prompt={t_tokens.get('prompt_tokens', 0)}, "
        f"completion={t_tokens.get('completion_tokens', 0)}, "
        f"total={t_tokens.get('total_tokens', 0)}, "
        f"source={t_tokens.get('source', 'none')}"
    )
    print(f"总耗时: {t_metrics.get('total_duration_seconds', 0)} 秒")