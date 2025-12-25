import re
from abc import ABC, abstractmethod
from typing import List, Optional

from pyquipu.interfaces.types import Statement


class BaseParser(ABC):
    """所有解析器的抽象基类"""

    @abstractmethod
    def parse(self, text: str) -> List[Statement]:
        """
        将文本解析为语句列表。
        必须由子类实现。
        """
        pass


class StateBlockParser(BaseParser):
    """
    基于状态机的解析器。
    逐行扫描文本，通过维护状态（在块内/在块外）来提取代码块。
    相比正则解析器，它对语言标签的格式限制更少，更健壮。
    """

    def __init__(self, fence_char: str):
        self.fence_char = fence_char

    def parse(self, text: str) -> List[Statement]:
        statements: List[Statement] = []
        current_statement: Optional[Statement] = None

        lines = text.splitlines(keepends=True)
        
        # 状态变量
        in_block = False
        current_fence = ""     # 记录开始时的围栏字符串，用于匹配结束
        current_lang = ""
        block_content: List[str] = []

        for line in lines:
            stripped_line = line.strip()
            
            if not in_block:
                # 检查是否是块的开始
                # 规则：以 fence_char 开头，至少 3 个字符
                if stripped_line.startswith(self.fence_char * 3):
                    # 确定围栏部分
                    # 我们需要分离 fence 和 language tag
                    # 例如: "~~~~ python.old" -> fence="~~~~", lang="python.old"
                    
                    # 简单的分离逻辑：取连续的 fence_char
                    fence_len = 0
                    for char in stripped_line:
                        if char == self.fence_char:
                            fence_len += 1
                        else:
                            break
                    
                    # 剩下的部分是语言标签
                    # 注意：我们要用原始行的切片，但 strip 后的版本比较容易处理逻辑
                    # 这里我们直接从 stripped_line 切
                    fence_str = stripped_line[:fence_len]
                    lang_str = stripped_line[fence_len:].strip()

                    # 进入块状态
                    in_block = True
                    current_fence = fence_str
                    current_lang = lang_str.lower()
                    block_content = []
                else:
                    # 普通文本行，忽略
                    pass

            else:
                # 在块内
                # 检查是否是结束围栏
                # 规则：必须是独立的一行，且去除首尾空格后与开始围栏完全一致
                # (这里我们采用严格匹配 current_fence，这是一种安全的策略)
                if stripped_line == current_fence:
                    # 块结束
                    in_block = False
                    
                    # 处理收集到的内容
                    # 1. 合并行
                    full_content = "".join(block_content)
                    
                    # 2. 去除末尾的一个换行符 (如果存在)，因为 splitlines(keepends=True) 保留了它
                    # 而通常代码块的内容不包含最后那个由闭合围栏造成的换行
                    if full_content.endswith("\n"):
                        full_content = full_content[:-1]

                    # 3. 根据语言标签分发
                    if current_lang == "act":
                        # 这是一个指令块，开始一个新的 Statement
                        action_name = full_content.strip()
                        # 创建新语句
                        new_stmt = {"act": action_name, "contexts": []}
                        statements.append(new_stmt)
                        current_statement = new_stmt
                    else:
                        # 这是一个上下文块
                        # 只有当已经有一个 active 的语句时才添加
                        if current_statement is not None:
                            current_statement["contexts"].append(full_content)
                        else:
                            # 孤立的上下文块，被忽略（或者可以记录警告）
                            pass
                    
                    # 重置块状态变量
                    current_fence = ""
                    current_lang = ""
                    block_content = []

                else:
                    # 是块的内容，累积
                    block_content.append(line)

        return statements


class BacktickParser(StateBlockParser):
    """标准 Markdown 解析器 (```) - 相当于 '绿幕'"""

    def __init__(self):
        super().__init__("`")


class TildeParser(StateBlockParser):
    """波浪号解析器 (~~~) - 相当于 '蓝幕'"""

    def __init__(self):
        super().__init__("~")


# --- 解析器注册表 ---

_PARSERS = {
    "backtick": BacktickParser,
    "tilde": TildeParser,
}


def get_parser(name: str) -> BaseParser:
    """工厂函数：根据名称获取解析器实例"""
    if name not in _PARSERS:
        raise ValueError(f"未知的解析器: {name}. 可用选项: {list(_PARSERS.keys())}")
    return _PARSERS[name]()


def list_parsers() -> List[str]:
    return list(_PARSERS.keys())


def detect_best_parser(text: str) -> str:
    """
    扫描文本，根据第一个出现的 act 块特征自动决定使用哪种解析器。
    策略：搜索第一个 ` ```act ` 或 ` ~~~act `，返回对应的解析器名称。
    支持变长围栏检测 (如 ` ````act `)。
    
    注：为了保持高效，这里仍然使用正则进行预扫描，
    但这个正则只负责检测“类型”，不负责解析内容，所以它是安全的。
    """
    # 匹配行首的 fence，后跟 act (忽略大小写)
    # group(1) 是 fence 字符
    # 注意：这里我们放宽了对 act 后面的匹配，允许空格等
    pattern = re.compile(r"^([`~]{3,})\s*act\b", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(text)

    if match:
        fence_str = match.group(1)
        # 检查 fence 由什么字符组成
        if fence_str.startswith("~"):
            return "tilde"
        # 默认为 backtick
        return "backtick"

    # 如果没找到明确的 act 块，默认返回 backtick
    return "backtick"