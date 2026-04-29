import os
from tavily import TavilyClient

# 从环境变量读取 API Key
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
client = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None

def _run(query: str, max_results: int = 5) -> str:
    """
    搜索最新新闻。
    输入关键词，返回新闻标题、摘要和链接。
    """
    if not client:
        return "Tavily API Key 未配置，请在 .env 中设置 TAVILY_API_KEY"
    try:
        response = client.search(query, max_results=max_results, topic="news")
        results = response.get("results", [])
        if not results:
            return f"未找到关于 '{query}' 的新闻。"
        formatted = []
        for idx, item in enumerate(results, 1):
            title = item.get("title", "无标题")
            content = item.get("content", "无内容")
            url = item.get("url", "#")
            formatted.append(f"**{idx}. {title}**\n{content}\n[阅读全文]({url})\n")
        return "\n".join(formatted)
    except Exception as e:
        return f"新闻搜索出错: {str(e)}"

name = "news_search"
description = "搜索互联网上的最新新闻。输入关键词，返回相关新闻摘要。"
func = _run