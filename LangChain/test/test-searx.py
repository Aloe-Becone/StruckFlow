#!/usr/bin/env python3
"""
SearXNG 搜索脚本 - 用户输入问题，返回精简后的 JSON 结果
"""

import sys
import json
from urllib.request import urlopen, Request
from urllib.parse import urlencode


def search_searxng(query: str, base_url: str = "http://localhost:8082") -> dict:
    """向 SearXNG 发起搜索请求，返回精简后的 JSON 数据"""
    params = urlencode({
        "q": query,
        "format": "json",
    })
    search_url = f"{base_url.rstrip('/')}/search?{params}"

    try:
        req = Request(search_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        response = urlopen(req, timeout=10)
        raw_data = response.read().decode("utf-8")
        data = json.loads(raw_data)

        # 精简：只保留核心有用字段
        simplified = {
            "query": data.get("query", ""),
            "total_results": len(data.get("results", [])),
            "results": [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("content", ""),
                    "source": r.get("engine", ""),
                    "published": r.get("publishedDate", None)
                }
                for r in data.get("results", [])
            ],
            "suggestions": data.get("suggestions", []),
            "unresponsive_engines": [
                {"engine": e[0], "reason": e[1]}
                for e in data.get("unresponsive_engines", [])
            ]
        }
        return simplified

    except Exception as e:
        return {
            "error": True,
            "message": f"搜索请求失败: {str(e)}"
        }


def main():
    print("=" * 58)
    print("  SearXNG 搜索工具 - 输入问题获取 JSON 结果")
    print("=" * 58)
    print("  输入 'quit' 或 'exit' 退出\n")

    while True:
        try:
            query = input("请输入搜索问题: ").strip()

            if not query:
                continue

            if query.lower() in ("quit", "exit", "q"):
                print("再见！")
                break

            print(f"\n正在搜索: \"{query}\" ...\n")

            result = search_searxng(query)

            if result.get("error"):
                print(f"[错误] {result['message']}")
            else:
                # 输出精简后的 JSON
                print(json.dumps(result, indent=2, ensure_ascii=False))

                # 输出简要统计
                print(f"\n--- 摘要 ---")
                print(f"查询词: {result['query']}")
                print(f"结果数: {result['total_results']}")
                if result['unresponsive_engines']:
                    for eng in result['unresponsive_engines']:
                        print(f"引擎异常: {eng['engine']} - {eng['reason']}")

            print("\n" + "-" * 45 + "\n")

        except KeyboardInterrupt:
            print("\n\n再见！")
            break
        except Exception as e:
            print(f"\n[意外错误] {e}\n")


if __name__ == "__main__":
    main()