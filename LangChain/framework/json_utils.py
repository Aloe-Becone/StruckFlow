import json
from typing import Any


def compact_json(data: Any) -> str:
    """输出无多余空白的 JSON，用于减少协议消息 token/字符开销。"""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def pretty_json(data: Any) -> str:
    """输出便于人工阅读的 JSON，用于 CLI 展示和调试。"""
    return json.dumps(data, ensure_ascii=False, indent=2)


def safe_json_loads(text: str) -> dict[str, Any]:
    """尽力解析模型输出的 JSON，失败时保留错误信息和原始内容。"""
    text = (text or "").strip()
    if not text:
        return {
            "parse_error": "模型返回空内容。",
            "raw": text,
        }
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {"value": data}
    except json.JSONDecodeError:
        extracted = extract_json_object(text)
        if extracted:
            try:
                data = json.loads(extracted)
                return data if isinstance(data, dict) else {"value": data}
            except json.JSONDecodeError:
                pass
        return {
            "parse_error": "模型没有返回合法 JSON，已保留原始内容。",
            "raw": text,
        }


def extract_json_object(text: str) -> str | None:
    """从包含 Markdown 或额外解释的模型输出中提取首个 JSON 对象。"""
    fenced_start = text.find("```json")
    if fenced_start != -1:
        body_start = text.find("\n", fenced_start)
        body_end = text.find("```", body_start + 1)
        if body_start != -1 and body_end != -1:
            return text[body_start:body_end].strip()

    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None
