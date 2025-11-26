# refactor: 调整 Plan 摘要生成逻辑，优先使用文档标题

## 用户需求
当前 `plan` 节点的历史摘要是从计划中的第一个 `act` 指令生成的。这通常不如计划文件本身的 Markdown 标题更能描述整个计划的意图。摘要逻辑应该优先使用这个人类编写的标题，以提高历史日志的可读性和信息价值。

## 评论
这是一个很合理的改进。它增强了 Quipu 计划的“文档属性”，使得通过 `quipu log` 或 `quipu ui` 查看历史时，能更快地理解每次变更的核心目的。

## 目标
修改摘要生成逻辑，使其遵循以下优先级顺序：
1.  **最高优先级**：使用 `plan` 内容中的 Markdown 标题 (`# ...`) 作为摘要。
2.  **次高优先级**：如果找不到标题，则回退到从第一个 `act` 指令生成的摘要。
3.  **最终回退**：如果以上都失败，则使用计划内容的第一行文本。

## 基本原理
将摘要生成的决策逻辑集中到 `quipu-cli` 的 `controller.py` 中。`controller` 能够访问原始 `plan` 内容（用于解析标题）和已解析的 `Statement` 对象（用于从 `act` 生成摘要），是实现此逻辑的最佳位置。

相应地，`quipu-engine` 中的 `writer` (`git_object_storage.py`) 将被简化。它将不再尝试解析 `act` 块，其对 `plan` 的摘要生成逻辑将简化为仅在 `controller` 未提供摘要时的最终回退。

## 标签
#intent/refine #flow/ready #priority/medium
#comp/cli #comp/engine #concept/history
#scope/core #scope/dx
#ai/instruct

---

## Script

### Acts 1: 调整 Controller 摘要逻辑

首先，我将修改 `controller.py` 以实现新的摘要生成优先级。这包括引入 `re` 模块来解析 Markdown 标题。

~~~~~act
replace
~~~~~
~~~~~path
packages/quipu-cli/src/quipu/cli/controller.py
~~~~~
~~~~~python
import logging
import sys
from pathlib import Path
~~~~~
~~~~~python
import logging
import re
import sys
from pathlib import Path
~~~~~

~~~~~act
replace
~~~~~
~~~~~path
packages/quipu-cli/src/quipu/cli/controller.py
~~~~~
~~~~~python
        # --- Phase 4: Recording (Plan Crystallization) ---
        smart_summary = None
        if statements:
            smart_summary = executor.summarize_statement(statements[0])

        output_tree_hash = self.engine.git_db.get_tree_hash()

        self.engine.create_plan_node(
            input_tree=input_tree_hash,
            output_tree=output_tree_hash,
            plan_content=content,
            summary_override=smart_summary,
        )
~~~~~
~~~~~python
        # --- Phase 4: Recording (Plan Crystallization) ---
        final_summary = None
        # 优先级 1: 从 Markdown 内容中提取 # 标题
        title_match = re.search(r"^\s*#{1,6}\s+(.*)", content, re.MULTILINE)
        if title_match:
            final_summary = title_match.group(1).strip()
        # 优先级 2: 从第一个 act 指令生成摘要
        elif statements:
            final_summary = executor.summarize_statement(statements[0])

        output_tree_hash = self.engine.git_db.get_tree_hash()

        self.engine.create_plan_node(
            input_tree=input_tree_hash,
            output_tree=output_tree_hash,
            plan_content=content,
            summary_override=final_summary,
        )
~~~~~

### Acts 2: 简化 Engine (Writer) 的回退逻辑

接下来，我将简化 `git_object_storage.py` 中的 `_generate_summary` 函数，移除其中多余且不健壮的 `act` 解析代码。

~~~~~act
replace
~~~~~
~~~~~path
packages/quipu-engine/src/quipu/core/git_object_storage.py
~~~~~
~~~~~python
        if node_type == "plan":
            # 优先从 act 块中提取摘要
            summary = ""
            in_act_block = False
            for line in content.strip().splitlines():
                clean_line = line.strip()
                if clean_line.startswith(("~~~act", "```act")):
                    in_act_block = True
                    continue

                if in_act_block:
                    if clean_line.startswith(("~~~", "```")):
                        break  # 块结束
                    if clean_line:
                        summary = clean_line
                        break  # 找到摘要

            if summary:
                return (summary[:75] + "...") if len(summary) > 75 else summary

            # 回退：尝试从 Markdown 的第一个标题中提取
            match = re.search(r"^\s*#{1,6}\s+(.*)", content, re.MULTILINE)
            if match:
                return match.group(1).strip()

            # Fallback to the first non-empty line
            first_line = next((line.strip() for line in content.strip().splitlines() if line.strip()), "Plan executed")
            return (first_line[:75] + "...") if len(first_line) > 75 else first_line
~~~~~
~~~~~python
        if node_type == "plan":
            # Controller 优先负责生成摘要。此处的逻辑仅作为当 controller 未提供摘要时的回退。
            # 优先级 1: 尝试从 Markdown 的第一个标题中提取
            match = re.search(r"^\s*#{1,6}\s+(.*)", content, re.MULTILINE)
            if match:
                return match.group(1).strip()

            # 最终回退: 使用内容的第一行
            first_line = next((line.strip() for line in content.strip().splitlines() if line.strip()), "Plan executed")
            return (first_line[:75] + "...") if len(first_line) > 75 else first_line
~~~~~
