#!/usr/bin/env python3
# multi_tool_agent.py
# 适用于 langchain 0.3.0，使用 create_openai_tools_agent

import os
from dotenv import load_dotenv
load_dotenv()  # 加载 .env 中的 DEEPSEEK_API_KEY, BASE_URL, TAVILY_API_KEY

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate

# ---------- 1. 定义工具 ----------
@tool
def calculate(expression: str) -> str:
    """计算数学表达式，例如 '2+3*4' 或 '(10-5)/2'。"""
    try:
        # 注意：eval 在安全环境下可以使用，生产环境建议用 numexpr 或受限 eval
        result = eval(expression)
        return f"计算结果: {result}"
    except Exception as e:
        return f"表达式无效: {e}"

# 初始化 Tavily 搜索工具（需要 TAVILY_API_KEY）
# 如果未设置 API Key 或不想用网络搜索，可以将下面的 search 替换为 mock_search
try:
    search = TavilySearchResults(max_results=2)
    # 测试一下是否有 key（可选）
    if not os.getenv("TAVILY_API_KEY"):
        print("⚠️ 未设置 TAVILY_API_KEY，搜索工具将不可用，使用模拟搜索代替。")
        @tool
        def mock_search(query: str) -> str:
            """模拟搜索引擎，返回固定结果（用于测试）。"""
            return "关于 '{}' 的模拟结果：2024年诺贝尔物理学奖得主是约翰·霍普菲尔德和杰弗里·辛顿。".format(query)
        search = mock_search
except Exception:
    # 如果导入失败或没有 key，使用模拟搜索
    @tool
    def mock_search(query: str) -> str:
        """模拟搜索引擎，返回固定结果。"""
        return "模拟搜索结果：2024年诺贝尔物理学奖得主是约翰·霍普菲尔德和杰弗里·辛顿。"
    search = mock_search

tools = [calculate, search]

# ---------- 2. 初始化 LLM (DeepSeek) ----------
llm = ChatOpenAI(
    model="deepseek-chat",                     # 或 "deepseek-v4-flash"
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("BASE_URL", "https://api.deepseek.com/v1"),
    temperature=0,
)

# ---------- 3. 创建 Prompt 模板 ----------
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个有用的助手，可以使用计算器和搜索引擎来回答问题。请按需调用工具。"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}")   # 用于存放中间步骤
])

# ---------- 4. 构建 Agent ----------
agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,              # 打印思考链路
    max_iterations=5,          # 防止无限循环
    early_stopping_method="generate"
)

# ---------- 5. 执行测试 ----------
if __name__ == "__main__":
    question = "请帮我查一下2024年诺贝尔物理学奖得主，然后计算一下如果他们出生于1960年，现在多少岁？"
    print(f"问题: {question}\n")
    result = agent_executor.invoke({"input": question})
    print("\n最终答案:\n", result["output"])
