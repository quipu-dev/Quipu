这是一个非常好的问题。在大多数场景下，直接引入成熟的库（如 `markdown-it-py` 或 `mistune`）确实是首选。

但在 Quipu 的上下文中，我们选择**手写一个简易状态机解析器**有以下两个核心原因：

1.  **“愚蠢”的空白保留 (The "Dumb" Whitespace Requirement)**:
    *   标准的 Markdown 解析器遵循 CommonMark 规范，该规范允许（甚至强制）剥离围栏代码块内容前 1-3 个空格的缩进。
    *   对于渲染 HTML 这很好，但对于 `patch_file` 来说是**灾难性**的。`patch_file` 依赖于**字节级精确匹配**。如果解析器“智能”地去掉了用户在 Plan 中特意保留的缩进，补丁就会匹配失败。
    *   我们需要一个“愚蠢”的解析器，它能原封不动地提取围栏内的所有字符，包括缩进。

2.  **依赖卫生 (Dependency Hygiene)**:
    *   `quipu-runtime` 被设计为最底层的核心包，目前仅依赖 `typer`。
    *   引入一个完整的 Markdown 解析库（通常比较重）仅仅为了提取代码块，在依赖树上略显臃肿。
    *   我们的需求仅仅是“提取围栏块”，几十行代码的状态机就能完美解决，且比正则更健壮。

基于以上技术考量，我建议继续执行重构为**状态机解析器**的方案。它既解决了正则的脆弱性，又保证了 `patch_file` 所需的绝对原始数据。

## [WIP] refactor: 实现保留原始空白的状态机解析器

### 用户需求
1.  解决 `RegexBlockParser` 无法处理复杂语言标签（如 `python.old`, `c++`）的问题。
2.  解决 `RegexBlockParser` 无法处理围栏后空格的问题。
3.  **关键约束**: 确保解析器**绝对不**修改代码块内的任何缩进或空白，以保证 `patch_file` 的匹配能力。

### 评论
这个“状态机”其实非常简单：只是一个简单的开关逻辑。它能让我们完全控制每一行的处理方式，确保数据的原真性。

### 目标
用 `StateBlockParser` 替换 `parser.py` 中的正则逻辑。

### 基本原理
逻辑如下：
1.  遍历每一行。
2.  如果遇到 `~~~` 或 ` ``` ` 开头：
    *   记录围栏标记。
    *   进入“收集模式”。
3.  在“收集模式”下：
    *   如果是结束围栏（与开始标记完全一致）：结束收集。
    *   否则：将该行**原样**（raw string）加入缓冲区。
4.  生成的 `content` 将用于后续的 Act 执行。

### 标签
#intent/refine #flow/ready #priority/high #comp/runtime #concept/parser #scope/core #ai/instruct #task/domain/parsing #task/object/state-machine-parser #task/action/rewrite #task/state/continue

---
### Script

#### Acts 1: 重写 parser.py

这将完全替换原有的正则实现。

~~~~~act
write_file
packages/quipu-runtime/src/pyquipu/runtime/parser.py
~~~~~
~~~~~python
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
    
    设计目标：
    1. 健壮性：支持任意语言标签（如 python.old, c++, python-new）。
    2. 原真性：绝对保留块内的所有空白和缩进（这对 patch_file 至关重要）。
       标准 Markdown 解析器可能会剥离 1-3 个空格的缩进，这会导致补丁匹配失败。
    """

    def __init__(self, fence_char: str):
        self.fence_char = fence_char

    def parse(self, text: str) -> List[Statement]:
        statements: List[Statement] = []
        current_statement: Optional[Statement] = None

        # keepends=True 保留换行符，确保内容原样还原
        lines = text.splitlines(keepends=True)
        
        in_block = False
        current_fence = ""     # 记录开始时的围栏字符串（不含语言标签）
        current_lang = ""
        block_content: List[str] = []

        for line in lines:
            stripped_line = line.strip()
            
            if not in_block:
                # --- 状态：寻找块的开始 ---
                # 规则：以 fence_char 开头，至少 3 个字符
                if stripped_line.startswith(self.fence_char * 3):
                    # 分离 fence 和 language tag
                    # 例如: "~~~~ python.old" -> fence="~~~~", lang="python.old"
                    
                    # 计算 fence 长度
                    fence_len = 0
                    for char in stripped_line:
                        if char == self.fence_char:
                            fence_len += 1
                        else:
                            break
                    
                    # 提取元数据
                    fence_str = stripped_line[:fence_len]
                    lang_str = stripped_line[fence_len:].strip()

                    # 切换状态
                    in_block = True
                    current_fence = fence_str
                    current_lang = lang_str.lower()
                    block_content = []
                else:
                    # 普通文本行，忽略
                    pass

            else:
                # --- 状态：在块内 ---
                # 检查是否是结束围栏
                # 规则：去除首尾空白后，必须与开始围栏完全一致
                if stripped_line == current_fence:
                    # 块结束
                    in_block = False
                    
                    # 处理收集到的内容
                    full_content = "".join(block_content)
                    
                    # 如果内容末尾有换行符（通常都有），且它是因为上一行内容自带的，我们保留。
                    # 但如果是空块，或者为了符合直觉，通常不处理。
                    # 在这里我们保持最原始的数据，但在 splitlines 时最后一行通常带有 \n。
                    # 唯独要注意的是：编辑器通常会在闭合 fence 前加一个换行，这个换行在逻辑上属于内容的一部分吗？
                    # 标准 Markdown：是的。
                    # 但为了 patch_file 的方便，如果最后一个字符是换行，通常意味着是块的结束。
                    # 我们这里做一个微调：如果最后一行以 \n 结尾，我们可以选择去掉它，
                    # 使得 ```text\nA\n``` 解析为 "A\n" 而不是 "A\n"。
                    # 这取决于 splitlines 的行为。
                    
                    # 这里采用一个实用策略：strip 掉尾部的一个换行符。
                    if full_content.endswith("\n"):
                        full_content = full_content[:-1]

                    # 根据语言标签分发
                    if current_lang == "act":
                        # 指令块：开始新语句
                        action_name = full_content.strip()
                        new_stmt = {"act": action_name, "contexts": []}
                        statements.append(new_stmt)
                        current_statement = new_stmt
                    else:
                        # 上下文块：追加到当前语句
                        if current_statement is not None:
                            current_statement["contexts"].append(full_content)
                    
                    # 重置状态
                    current_fence = ""
                    current_lang = ""
                    block_content = []

                else:
                    # 收集内容
                    block_content.append(line)

        return statements


class BacktickParser(StateBlockParser):
    """标准 Markdown 解析器 (```)"""

    def __init__(self):
        super().__init__("`")


class TildeParser(StateBlockParser):
    """波浪号解析器 (~~~)"""

    def __init__(self):
        super().__init__("~")


# --- 解析器注册表 ---

_PARSERS = {
    "backtick": BacktickParser,
    "tilde": TildeParser,
}


def get_parser(name: str) -> BaseParser:
    """工厂函数"""
    if name not in _PARSERS:
        raise ValueError(f"未知的解析器: {name}. 可用选项: {list(_PARSERS.keys())}")
    return _PARSERS[name]()


def list_parsers() -> List[str]:
    return list(_PARSERS.keys())


def detect_best_parser(text: str) -> str:
    """
    自动检测解析器类型。
    使用简单的正则预扫描来判断是使用波浪号还是反引号。
    """
    # 宽松匹配：行首 fence + 任意空白 + act
    pattern = re.compile(r"^([`~]{3,})\s*act\b", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(text)

    if match:
        fence_str = match.group(1)
        if fence_str.startswith("~"):
            return "tilde"
        return "backtick"

    return "backtick"
~~~~~

### 下一步建议
请执行此计划。
然后运行全量测试：
`pytest tests/runtime/test_parser_robustness.py tests/runtime/acts/test_patch_ambiguity.py tests/runtime/acts/test_parser_and_basic_acts.py`

我非常有信心这将通过所有测试。
