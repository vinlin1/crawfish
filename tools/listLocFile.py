import os
from pathlib import Path

def _run(directory: str = ".") -> str:
    """列出本地目录中的文件和子目录"""
    try:
        target_dir = Path(directory).expanduser().resolve()
    except Exception as e:
        return f"路径解析错误: {e}"

    if not target_dir.exists():
        return f"目录不存在: {target_dir}"
    if not target_dir.is_dir():
        return f"路径不是目录: {target_dir}"

    try:
        items = list(target_dir.iterdir())
        dirs = sorted([item for item in items if item.is_dir()], key=lambda x: x.name)
        files = sorted([item for item in items if item.is_file()], key=lambda x: x.name)
        result = [f"目录: {target_dir}\n"]
        result.append("\n📁 子目录:")
        for d in dirs:
            result.append(f"  📁 {d.name}/")
        result.append("\n📄 文件:")
        for f in files:
            size = f.stat().st_size
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            result.append(f"  📄 {f.name} ({size_str})")
        if not dirs and not files:
            result.append("  (空目录)")
        return "\n".join(result)
    except PermissionError:
        return f"权限不足，无法读取目录: {target_dir}"
    except Exception as e:
        return f"列出目录时出错: {e}"

name = "listLocFile"
description = "列出本地目录中的文件和子目录。输入目录路径（绝对或相对），默认列出当前目录。"
func = _run