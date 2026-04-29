import os
from datetime import datetime

def _run(content: str, filename: str = "conversation_log.md") -> str:
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else ".", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"## 📝 {timestamp}\n\n{content}\n\n---\n\n")
    return f"✅ 已保存到 {filename}"

name = "save_to_markdown"
description = "将内容追加保存到 Markdown 文件。当用户要求保存回答时调用。"
func = _run