# feat: 实现可插拔的摘要生成逻辑

## 用户需求
目前 `quipu-engine` 生成历史节点摘要 (Summary) 的逻辑是硬编码的，主要依赖简单的正则匹配 Markdown 标题或 `act` 块。
当用户通过插件添加自定义 Act 时，无法为其定义特定的摘要生成规则 (例如 `write_file` 应该显示 "Write: filename"，而 `git_commit` 应该显示 "Commit: message")。
用户希望能够为 Act 注册自定义的 Summarizer 函数，以便在历史记录 (`quipu log`) 中看到更语义化的描述。

## 评论
这是一个提升 DX (开发者体验) 和 UX (用户体验) 的重要功能。它将“如何解释一个操作”的权力下放给了 Act 的定义者 (`quipu-runtime`)，而不是耦合在存储层 (`quipu-engine`)。这也符合架构中 `Engine` 仅负责状态存储、`Runtime` 负责语义解释的分层原则。

## 目标
1.  在 `quipu-interfaces` 中定义 `Summarizer` 函数签名。
2.  更新 `quipu-runtime` 的 `Executor.register` 方法，支持传入可选的 `summarizer`。
3.  在核心 Acts (`basic`, `git`) 中实现并注册示例 Summarizer。
4.  更新 `quipu-cli` 的 `Controller`，在执行指令后，尝试调用 `Executor` 生成摘要，并将其传递给 `Engine`。
5.  更新 `quipu-engine`，使其 `HistoryWriter` 优先使用外部传入的摘要，仅在缺失时回退到默认解析逻辑。

## 基本原理
为了保持模块独立性，`Engine` 不应依赖 `Runtime` 的具体 Act 定义。因此，摘要的生成应当在 `CLI` 层协调：
1.  `CLI` 调用 `Runtime` 解析并获取 `Statement` 列表。
2.  `CLI` 询问 `Runtime` (Executor): "根据这个 Statement，你能生成一个摘要吗？"
3.  `Runtime` 查找对应 Act 的 Summarizer 并执行。
4.  `CLI` 将生成的摘要字符串作为参数传给 `Engine` 的 `create_plan_node`。

这种设计确保了 `Engine` 依然是无状态的底层存储，而语义逻辑保留在 `Runtime` 中。

## 标签
#comp/runtime #comp/engine #comp/cli #comp/interfaces #concept/history #scope/api

---

## Script

### Acts 1: 定义接口与更新 Executor

首先定义 Summarizer 的类型，并更新执行器的注册逻辑，使其能够存储和调用这些摘要生成器。

~~~~~act
write_file packages/quipu-interfaces/src/quipu/core/types.py
~~~~~

~~~~~python
from __future__ import annotations
from typing import TypedDict, List, Callable, Optional, Union
from pathlib import Path
from .exceptions import ExecutionError

# --- Forward declaration to avoid circular imports ---
class Executor: ...

class ActContext:
    """
    提供给插件函数的上下文 API。
    这是插件与执行器核心之间的稳定接口。
    """
    def __init__(self, executor: Executor):
        self._executor = executor

    @property
    def root_dir(self) -> Path:
        """获取当前工作区的根目录"""
        return self._executor.root_dir

    def resolve_path(self, rel_path: str) -> Path:
        """将相对路径安全地解析为工作区内的绝对路径"""
        return self._executor.resolve_path(rel_path)

    def request_confirmation(self, file_path: Path, old_content: str, new_content: str) -> bool:
        """生成 diff 并请求用户确认"""
        return self._executor.request_confirmation(file_path, old_content, new_content)

    def fail(self, message: str):
        """
        向执行器报告一个可恢复的错误并终止当前 act。
        这会抛出一个 ExecutionError。
        """
        raise ExecutionError(message)

# --- Type definitions for core components ---

# Act 函数签名定义: (context, args) -> None
ActFunction = Callable[[ActContext, List[str]], None]

# Summarizer 函数签名定义: (args, context_blocks) -> str
# 用于根据指令参数生成单行摘要
Summarizer = Callable[[List[str], List[str]], str]

class Statement(TypedDict):
    """表示解析后的单个操作语句"""
    act: str
    contexts: List[str]
~~~~~

~~~~~act
replace packages/quipu-runtime/src/quipu/core/executor.py
~~~~~

~~~~~python
    def __init__(self, root_dir: Path, yolo: bool = False):
        self.root_dir = root_dir.resolve()
        self.yolo = yolo
        self._acts: Dict[str, tuple[ActFunction, str]] = {}
        
        if not self.root_dir.exists():
~~~~~

~~~~~python
    def __init__(self, root_dir: Path, yolo: bool = False):
        self.root_dir = root_dir.resolve()
        self.yolo = yolo
        # Map: name -> (func, arg_mode, summarizer)
        self._acts: Dict[str, tuple[ActFunction, str, Any]] = {}
        
        if not self.root_dir.exists():
~~~~~

~~~~~act
replace packages/quipu-runtime/src/quipu/core/executor.py
~~~~~

~~~~~python
    def register(self, name: str, func: ActFunction, arg_mode: str = "hybrid"):
        """
        注册一个新的操作
        :param arg_mode: 参数解析模式
                         - "hybrid": (默认) 合并行内参数和块内容 (inline + blocks)
                         - "exclusive": 互斥模式。优先使用行内参数；若无行内参数，则使用块内容。绝不混合。
                         - "block_only": 仅使用块内容，强制忽略行内参数。
        """
        valid_modes = {"hybrid", "exclusive", "block_only"}
        if arg_mode not in valid_modes:
            raise ValueError(f"Invalid arg_mode: {arg_mode}. Must be one of {valid_modes}")
            
        self._acts[name] = (func, arg_mode)
        logger.debug(f"注册 Act: {name} (Mode: {arg_mode})")
~~~~~

~~~~~python
    def register(self, name: str, func: ActFunction, arg_mode: str = "hybrid", summarizer: Any = None):
        """
        注册一个新的操作
        :param arg_mode: 参数解析模式
                         - "hybrid": (默认) 合并行内参数和块内容 (inline + blocks)
                         - "exclusive": 互斥模式。优先使用行内参数；若无行内参数，则使用块内容。绝不混合。
                         - "block_only": 仅使用块内容，强制忽略行内参数。
        :param summarizer: 可选的 Summarizer 函数 (args, context_blocks) -> str
        """
        valid_modes = {"hybrid", "exclusive", "block_only"}
        if arg_mode not in valid_modes:
            raise ValueError(f"Invalid arg_mode: {arg_mode}. Must be one of {valid_modes}")
            
        self._acts[name] = (func, arg_mode, summarizer)
        logger.debug(f"注册 Act: {name} (Mode: {arg_mode})")
~~~~~

~~~~~act
replace packages/quipu-runtime/src/quipu/core/executor.py
~~~~~

~~~~~python
    def get_registered_acts(self) -> Dict[str, str]:
        """获取所有已注册的 Act 及其文档字符串"""
        return {name: data[0].__doc__ for name, data in self._acts.items()}
~~~~~

~~~~~python
    def get_registered_acts(self) -> Dict[str, str]:
        """获取所有已注册的 Act 及其文档字符串"""
        return {name: data[0].__doc__ for name, data in self._acts.items()}

    def summarize_statement(self, stmt: Statement) -> str | None:
        """
        尝试为给定的语句生成摘要。
        如果找不到 Act 或 Act 没有 summarizer，返回 None。
        """
        raw_act_line = stmt["act"]
        try:
            tokens = shlex.split(raw_act_line)
        except ValueError:
            return None
            
        if not tokens:
            return None
            
        act_name = tokens[0]
        inline_args = tokens[1:]
        contexts = stmt["contexts"]
        
        if act_name not in self._acts:
            return None
            
        _, _, summarizer = self._acts[act_name]
        
        if not summarizer:
            return None
            
        try:
            return summarizer(inline_args, contexts)
        except Exception as e:
            logger.warning(f"Summarizer for '{act_name}' failed: {e}")
            return None
~~~~~

~~~~~act
replace packages/quipu-runtime/src/quipu/core/executor.py
~~~~~

~~~~~python
            if act_name not in self._acts:
                logger.warning(f"Skipping unknown operation [{i+1}/{len(statements)}]: {act_name}")
                continue

            func, arg_mode = self._acts[act_name]

            final_args = []
~~~~~

~~~~~python
            if act_name not in self._acts:
                logger.warning(f"Skipping unknown operation [{i+1}/{len(statements)}]: {act_name}")
                continue

            func, arg_mode, _ = self._acts[act_name]

            final_args = []
~~~~~

### Acts 2: 为核心 Acts 添加 Summarizer

现在更新 `basic.py` 和 `git.py`，为 `write_file`, `replace`, `git_commit` 等常用操作添加摘要生成逻辑。

~~~~~act
replace packages/quipu-runtime/src/quipu/acts/basic.py
~~~~~

~~~~~python
def register(executor: Executor):
    """注册基础文件系统操作"""
    executor.register("write_file", _write_file, arg_mode="hybrid")
    executor.register("replace", _replace, arg_mode="hybrid")
    executor.register("append_file", _append_file, arg_mode="hybrid")
    executor.register("end", _end, arg_mode="hybrid")
    executor.register("echo", _echo, arg_mode="hybrid")
~~~~~

~~~~~python
def register(executor: Executor):
    """注册基础文件系统操作"""
    executor.register("write_file", _write_file, arg_mode="hybrid", summarizer=_summarize_write)
    executor.register("replace", _replace, arg_mode="hybrid", summarizer=_summarize_replace)
    executor.register("append_file", _append_file, arg_mode="hybrid", summarizer=_summarize_append)
    executor.register("end", _end, arg_mode="hybrid")
    executor.register("echo", _echo, arg_mode="hybrid")

def _summarize_write(args: List[str], contexts: List[str]) -> str:
    path = args[0] if args else (contexts[0] if contexts else "???")
    return f"Write: {path}"

def _summarize_replace(args: List[str], contexts: List[str]) -> str:
    path = args[0] if args else (contexts[0] if contexts else "???")
    return f"Replace in: {path}"

def _summarize_append(args: List[str], contexts: List[str]) -> str:
    path = args[0] if args else (contexts[0] if contexts else "???")
    return f"Append to: {path}"
~~~~~

~~~~~act
replace packages/quipu-runtime/src/quipu/acts/git.py
~~~~~

~~~~~python
def register(executor: Executor):
    """注册 Git 相关操作"""
    executor.register("git_init", _git_init, arg_mode="exclusive")
    executor.register("git_add", _git_add, arg_mode="exclusive")
    executor.register("git_commit", _git_commit, arg_mode="block_only")
    executor.register("git_status", _git_status, arg_mode="exclusive")
~~~~~

~~~~~python
def register(executor: Executor):
    """注册 Git 相关操作"""
    executor.register("git_init", _git_init, arg_mode="exclusive")
    executor.register("git_add", _git_add, arg_mode="exclusive")
    executor.register("git_commit", _git_commit, arg_mode="block_only", summarizer=_summarize_commit)
    executor.register("git_status", _git_status, arg_mode="exclusive")

def _summarize_commit(args: List[str], contexts: List[str]) -> str:
    msg = contexts[0] if contexts else "No message"
    # Keep it short
    summary = (msg[:50] + '...') if len(msg) > 50 else msg
    return f"Git Commit: {summary}"
~~~~~

### Acts 3: 更新 Engine 层以支持外部摘要

更新 `GitObjectHistoryWriter`，允许通过 `kwargs` 传入 `summary_override`，并在生成摘要时优先使用它。同时更新 `Engine.create_plan_node` 接口以传递此参数。

~~~~~act
replace packages/quipu-engine/src/quipu/core/git_object_storage.py
~~~~~

~~~~~python
    def _generate_summary(
        self,
        node_type: str,
        content: str,
        input_tree: str,
        output_tree: str,
        **kwargs: Any,
    ) -> str:
        """根据节点类型生成单行摘要。"""
        if node_type == "plan":
            # 优先从 act 块中提取摘要
            summary = ""
            in_act_block = False
~~~~~

~~~~~python
    def _generate_summary(
        self,
        node_type: str,
        content: str,
        input_tree: str,
        output_tree: str,
        **kwargs: Any,
    ) -> str:
        """根据节点类型生成单行摘要。"""
        # 1. 如果传入了显式的摘要，直接使用
        if kwargs.get("summary_override"):
            return kwargs["summary_override"]

        if node_type == "plan":
            # 优先从 act 块中提取摘要
            summary = ""
            in_act_block = False
~~~~~

~~~~~act
replace packages/quipu-engine/src/quipu/core/state_machine.py
~~~~~

~~~~~python
    def create_plan_node(self, input_tree: str, output_tree: str, plan_content: str) -> QuipuNode:
        if input_tree == output_tree:
            logger.info(f"📝 记录幂等操作节点 (Idempotent Node): {output_tree[:7]}")
        else:
            logger.info(f"📝 正在记录 Plan 节点: {input_tree[:7]} -> {output_tree[:7]}")

        new_node = self.writer.create_node(
            node_type="plan",
            input_tree=input_tree,
            output_tree=output_tree,
            content=plan_content
        )

        self.history_graph[output_tree] = new_node
~~~~~

~~~~~python
    def create_plan_node(
        self, 
        input_tree: str, 
        output_tree: str, 
        plan_content: str,
        summary_override: Optional[str] = None
    ) -> QuipuNode:
        if input_tree == output_tree:
            logger.info(f"📝 记录幂等操作节点 (Idempotent Node): {output_tree[:7]}")
        else:
            logger.info(f"📝 正在记录 Plan 节点: {input_tree[:7]} -> {output_tree[:7]}")

        new_node = self.writer.create_node(
            node_type="plan",
            input_tree=input_tree,
            output_tree=output_tree,
            content=plan_content,
            summary_override=summary_override
        )

        self.history_graph[output_tree] = new_node
~~~~~

### Acts 4: 更新 Controller 层进行协调

最后，在 `quipu-cli/controller.py` 中，使用 Executor 计算摘要，并将其传递给 Engine。

~~~~~act
replace packages/quipu-cli/src/quipu/cli/controller.py
~~~~~

~~~~~python
        # 3.3 Execute
        executor.execute(statements)

        # --- Phase 4: Recording (Plan Crystallization) ---
        
        # 执行成功后，计算新的状态
        output_tree_hash = engine.git_db.get_tree_hash()
        
        # 如果状态发生了变化，或者我们想记录即使无变化的 Plan（通常记录一下比较好）
        # 这里我们调用 Engine 的 create_plan_node 方法
        engine.create_plan_node(
            input_tree=input_tree_hash,
            output_tree=output_tree_hash,
            plan_content=content
        )

        return QuipuResult(success=True, exit_code=0, message="✨ 执行成功")
~~~~~

~~~~~python
        # 3.3 Execute
        executor.execute(statements)

        # --- Phase 4: Recording (Plan Crystallization) ---
        
        # 尝试生成智能摘要 (使用第一个指令)
        smart_summary = None
        if statements:
            smart_summary = executor.summarize_statement(statements[0])

        # 执行成功后，计算新的状态
        output_tree_hash = engine.git_db.get_tree_hash()
        
        # 如果状态发生了变化，或者我们想记录即使无变化的 Plan（通常记录一下比较好）
        # 这里我们调用 Engine 的 create_plan_node 方法
        engine.create_plan_node(
            input_tree=input_tree_hash,
            output_tree=output_tree_hash,
            plan_content=content,
            summary_override=smart_summary
        )

        return QuipuResult(success=True, exit_code=0, message="✨ 执行成功")
~~~~~
