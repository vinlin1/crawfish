# agent_session.py
import os
import importlib.util
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import StructuredTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory

# 全局变量：保存当前 Agent 实例和工具列表
_current_executor = None
_current_tools = []
_current_memory = None

def load_tools_from_dir(tools_dir="tools"):
    """动态加载所有插件，返回工具列表和加载信息"""
    tools = []
    tools_path = Path(tools_dir)
    if not tools_path.exists():
        return tools, []
    load_log = []
    for py_file in tools_path.glob("*.py"):
        if py_file.name.startswith("__"):
            continue
        module_name = py_file.stem
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
            if hasattr(module, "name") and hasattr(module, "description") and hasattr(module, "func"):
                tool = StructuredTool.from_function(
                    func=module.func,
                    name=module.name,
                    description=module.description
                )
                tools.append(tool)
                load_log.append(f"✅ {module.name}")
            else:
                load_log.append(f"⚠️ {py_file.name}: 缺少 name/description/func")
        except Exception as e:
            load_log.append(f"❌ {py_file.name}: {str(e)}")
    return tools, load_log

def create_agent(tools):
    """根据工具列表创建新的 AgentExecutor"""
    global _current_memory, _current_executor
    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("BASE_URL", "https://api.deepseek.com/v1"),
        temperature=0,
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个有用的助手，可以使用多种工具。当用户要求保存内容时，请调用 save_to_markdown 工具。"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])
    # 每次重新创建 Agent 时，保留记忆（如果需要重置记忆可以新建）
    if _current_memory is None:
        _current_memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    agent = create_openai_tools_agent(llm, tools, prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        memory=_current_memory,
        verbose=False,   # Web 下关闭 verbose，避免输出混乱
        max_iterations=5,
        handle_parsing_errors=True
    )
    _current_executor = executor
    return executor

def reload_agent():
    """重新加载所有插件并重建 Agent"""
    global _current_tools, _current_executor
    _current_tools, load_log = load_tools_from_dir("tools")
    _current_executor = create_agent(_current_tools)
    return load_log

def get_current_tools():
    """获取当前已加载的工具列表（名称+描述）"""
    if _current_executor is None:
        reload_agent()
    return [{"name": t.name, "description": t.description} for t in _current_tools]

def invoke_agent(user_input: str):
    """调用 Agent 并返回回答"""
    if _current_executor is None:
        reload_agent()
    response = _current_executor.invoke({"input": user_input})
    return response["output"]

def reset_memory():
    """重置对话记忆"""
    global _current_memory
    _current_memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    if _current_executor:
        _current_executor.memory = _current_memory
    return "记忆已重置"

def test_tool(tool_name: str, args: dict):
    """单独测试一个工具（不经过 Agent）"""
    for tool in _current_tools:
        if tool.name == tool_name:
            try:
                # 根据工具的函数签名调用
                result = tool.func(**args)
                return {"success": True, "result": str(result)}
            except Exception as e:
                return {"success": False, "error": str(e)}
    return {"success": False, "error": f"工具 '{tool_name}' 未找到"}

def save_plugin_file(filename: str, content: str):
    """保存插件文件到 tools/ 目录（覆盖）"""
    tools_dir = Path("tools")
    tools_dir.mkdir(exist_ok=True)
    filepath = tools_dir / filename
    if not filename.endswith(".py"):
        filename += ".py"
    filepath.write_text(content, encoding="utf-8")
    return str(filepath)

def delete_plugin_file(filename: str):
    """删除插件文件"""
    filepath = Path("tools") / filename
    if filepath.exists() and filename.endswith(".py"):
        filepath.unlink()
        return True
    return False

def list_plugin_files():
    """列出 tools/ 下的所有 .py 文件"""
    tools_dir = Path("tools")
    if not tools_dir.exists():
        return []
    return [f.name for f in tools_dir.glob("*.py") if not f.name.startswith("__")]

def get_plugin_content(filename: str):
    """读取插件文件内容"""
    filepath = Path("tools") / filename
    if filepath.exists():
        return filepath.read_text(encoding="utf-8")
    return None

# 启动时自动加载一次
reload_agent()
