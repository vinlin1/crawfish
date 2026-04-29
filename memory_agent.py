#!/usr/bin/env python3
# memory_agent.py - 带对话记忆的 Agent

import os
from dotenv import load_dotenv
from datetime import datetime  # 添加这一行

load_dotenv()

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory

# ---------- 工具定义 ----------
@tool
def calculate(expression: str) -> str:
    """计算数学表达式，例如 '2+3*4'。"""
    try:
        result = eval(expression)
        return f"计算结果: {result}"
    except Exception as e:
        return f"表达式无效: {e}"

search = TavilySearchResults(max_results=2)
tools = [calculate, search]
#---------------save to  MD----------

@tool
def save_to_markdown(content: str, filename: str = "conversation_log.md") -> str:
    """
    将指定的内容追加保存到 Markdown 文件中。
    当用户要求“保存这个回答”、“写入文件”、“记录一下”时调用此工具。
    参数：
        content: 需要保存的文本内容（通常是之前的回答或总结）
        filename: 保存的文件名，默认为 conversation_log.md
    """
    # 确保目录存在（可选）
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else ".", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"## 📝 保存时间：{timestamp}\n\n")
        f.write(f"{content}\n\n")
        f.write("---\n\n")
    return f"✅ 内容已保存到 {filename}"

tools = [calculate, search, save_to_markdown]


# ---------- LLM (DeepSeek) ----------
llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("BASE_URL", "https://api.deepseek.com/v1"),
    temperature=0,
)

# ---------- Prompt 模板（包含历史消息占位符）----------
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个有用的助手，可以使用计算器和搜索引擎。请记住用户之前说过的话。"),
    MessagesPlaceholder(variable_name="chat_history"),  # 记忆会插入到这里
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

# ---------- 初始化记忆 ----------
memory = ConversationBufferMemory(
    memory_key="chat_history",   # 必须与 prompt 中的变量名一致
    return_messages=True         # 以消息列表形式返回，而非字符串
)

# ---------- 构建 Agent ----------
agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=memory,          # 注入记忆
    verbose=True,
    max_iterations=5,
)

# ---------- 交互式对话 ----------
if __name__ == "__main__":
    print("🤖 带记忆的 Agent 已启动 (输入 'exit' 退出)\n")
    while True:
        user_input = input("你: ")
        if user_input.lower() == "exit":
            break
        response = agent_executor.invoke({"input": user_input})
        print(f"助手: {response['output']}\n")
