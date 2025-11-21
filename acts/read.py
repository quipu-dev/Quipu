import os
from pathlib import Path
from typing import List
import logging
from core.executor import Executor, ExecutionError

logger = logging.getLogger(__name__)

def register_read_acts(executor: Executor):
    """注册读取与检索操作"""
    executor.register("read_file", _read_file)
    executor.register("list_files", _list_files)

def _read_file(executor: Executor, args: List[str]):
    """
    Act: read_file
    Args: [path]
    说明: 读取并打印文件内容到日志（stdout）。
    """
    if len(args) < 1:
        raise ExecutionError("read_file 需要至少一个参数: [path]")
    
    raw_path = args[0]
    target_path = executor.resolve_path(raw_path)
    
    if not target_path.exists():
        raise ExecutionError(f"文件不存在: {raw_path}")
    
    if target_path.is_dir():
        raise ExecutionError(f"这是一个目录，请使用 list_files: {raw_path}")

    try:
        content = target_path.read_text(encoding='utf-8')
        # 打印文件内容，带上简单的边框方便阅读
        logger.info(f"\n📖 [Read] {target_path.name}:\n{'-'*40}\n{content}\n{'-'*40}")
    except UnicodeDecodeError:
        logger.error(f"❌ [Read] 无法读取二进制文件或非 UTF-8 文件: {raw_path}")
    except Exception as e:
        raise ExecutionError(f"读取文件失败: {e}")

def _list_files(executor: Executor, args: List[str]):
    """
    Act: list_files
    Args: [path (optional, default=.)]
    说明: 列出目录下的文件结构（类似于 tree 命令）。
    """
    target_dir = executor.root_dir
    if args:
        target_dir = executor.resolve_path(args[0])
    
    if not target_dir.exists() or not target_dir.is_dir():
        raise ExecutionError(f"目录不存在: {target_dir}")

    logger.info(f"📂 [List] Directory: {target_dir}")
    
    # 简单的递归遍历，限制深度防止刷屏
    limit_depth = 3
    output_lines = []
    
    # 计算基准深度的层级数
    base_level = len(target_dir.parts)

    for root, dirs, files in os.walk(target_dir):
        # 排除隐藏目录
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        files = [f for f in files if not f.startswith('.')]
        
        root_path = Path(root)
        level = len(root_path.parts) - base_level
        
        if level >= limit_depth:
            del dirs[:] # 停止向下递归
            continue
            
        indent = "  " * level
        output_lines.append(f"{indent}📁 {root_path.name}/")
        for f in files:
            output_lines.append(f"{indent}  📄 {f}")

    print("\n".join(output_lines))