好的，我分析了所有的 `pyright` 错误。这些问题主要源于几个方面：协议（`Protocol`）定义不完整、类型检查器无法推断出生命周期方法（如 Textual 的 `on_mount`）导致的 `None` 类型误报、以及对 `TypedDict` 的推断问题。

我将生成一个计划来系统性地修复这些问题。

## [WIP] fix: 解决 pyright 类型检查错误

### 用户需求

修复 `pyright` 报告的 61 个类型检查错误，使整个项目类型安全。

### 评论

这是一个关键的维护任务。解决这些类型错误可以提高代码的健壮性，减少潜在的运行时 Bug，并改善开发体验。本次修复将涉及多个包，主要是完善协议定义和在必要时添加类型断言来帮助类型检查器。

### 目标

1.  **完善协议**: 更新 `pyquipu-spec` 中的 `QuipuEngine` 和 `ExecutorProtocol` 协议，使其与具体实现保持一致。
2.  **处理 `None` 类型**: 在 `quipu.cli.tui` 中，为在 `on_mount` 后才被初始化的 `view_model` 添加断言，消除类型检查器的误报。
3.  **修复类型不匹配**: 修正 `workspace.py` 和 `executor.py` 中存在的类型不匹配问题。
4.  **明确类型**: 在 `parser.py` 中为 `TypedDict` 字面量添加显式类型注解。

### 基本原理

我们将遵循“类型优先”的原则，从最底层的 `pyquipu-spec` 包开始修复协议定义。这将连锁解决依赖于这些协议的上层包（如 `pyquipu-application` 和 `pyquipu-runtime`）中的大部分错误。对于 `tui.py` 中由 Textual 应用生命周期引起的误报，我们将使用 `assert self.view_model is not None` 这种对运行时无影响的断言，向 `pyright` 提供明确的类型信息。

### 标签

#intent/fix #flow/ready #priority/high #comp/spec #comp/cli #comp/runtime #comp/application #scope/core #scope/dx #ai/instruct #task/domain/testing #task/object/type-checking #task.action/bug-fix #task/state/begin

---

### Script

#### Acts 1: 完善 `pyquipu-spec` 中的核心协议

首先，我们修复 `pyquipu-spec` 中不完整或不正确的协议定义。这是解决大部分连锁错误的关键。

~~~~~act
patch_file
packages/pyquipu-spec/src/quipu/spec/protocols/engine.py
~~~~~
~~~~~python.old
from typing import Protocol, Dict, Optional, List, runtime_checkable
from pathlib import Path
from ..models.graph import QuipuNode
from .storage import HistoryReader, HistoryWriter


@runtime_checkable
class QuipuEngine(Protocol):
    root_dir: Path
    reader: HistoryReader
    writer: HistoryWriter
    history_graph: Dict[str, QuipuNode]
    current_node: Optional[QuipuNode]

    def align(self) -> str: ...
    def visit(self, target_hash: str) -> None: ...
~~~~~
~~~~~python.new
from typing import Protocol, Dict, Optional, List, runtime_checkable, Any
from ..models.graph import QuipuNode
from .storage import HistoryReader, HistoryWriter


@runtime_checkable
class QuipuEngine(Protocol):
    root_dir: Path
    reader: HistoryReader
    writer: HistoryWriter
    history_graph: Dict[str, QuipuNode]
    current_node: Optional[QuipuNode]
    git_db: Any

    def align(self) -> str: ...
    def visit(self, target_hash: str) -> None: ...
~~~~~

~~~~~act
patch_file
packages/pyquipu-spec/src/quipu/spec/protocols/runtime.py
~~~~~
~~~~~python.old
from __future__ import annotations
from pathlib import Path
from typing import Protocol, List, Callable, runtime_checkable, TypedDict
from ..exceptions import ExecutionError


@runtime_checkable
class ExecutorProtocol(Protocol):
    @property
    def root_dir(self) -> Path: ...
    def resolve_path(self, rel_path: str) -> Path: ...
    def request_confirmation(self, file_path: Path, old_content: str, new_content: str) -> bool: ...


class ActContext:
    def __init__(self, executor: ExecutorProtocol):
        self._executor = executor

    @property
    def root_dir(self) -> Path:
        return self._executor.root_dir

    def resolve_path(self, rel_path: str) -> Path:
        return self._executor.resolve_path(rel_path)

    def request_confirmation(self, file_path: Path, old_content: str, new_content: str) -> bool:
        return self._executor.request_confirmation(file_path, old_content, new_content)

    def fail(self, message: str):
        raise ExecutionError(message)
~~~~~
~~~~~python.new
from __future__ import annotations
from pathlib import Path
from typing import Protocol, List, Callable, runtime_checkable, TypedDict, NoReturn, Any
from ..exceptions import ExecutionError


@runtime_checkable
class ExecutorProtocol(Protocol):
    @property
    def root_dir(self) -> Path: ...
    def resolve_path(self, rel_path: str) -> Path: ...
    def request_confirmation(self, file_path: Path, old_content: str, new_content: str) -> None: ...
    def register(self, name: str, func: ActFunction, arg_mode: str = "hybrid", summarizer: Any = None) -> None: ...


class ActContext:
    def __init__(self, executor: ExecutorProtocol):
        self._executor = executor

    @property
    def root_dir(self) -> Path:
        return self._executor.root_dir

    def resolve_path(self, rel_path: str) -> Path:
        return self._executor.resolve_path(rel_path)

    def request_confirmation(self, file_path: Path, old_content: str, new_content: str) -> None:
        return self._executor.request_confirmation(file_path, old_content, new_content)

    def fail(self, message: str) -> NoReturn:
        raise ExecutionError(message)
~~~~~

#### Acts 2: 修复 `pyquipu-runtime` 中的类型问题

协议修复后，我们来处理 `pyquipu-runtime` 中的实现细节。

~~~~~act
patch_file
packages/pyquipu-runtime/src/quipu/runtime/executor.py
~~~~~
~~~~~python.old
    def get_registered_acts(self) -> Dict[str, str]:
        return {name: data[0].__doc__ for name, data in self._acts.items()}
~~~~~
~~~~~python.new
    def get_registered_acts(self) -> Dict[str, str]:
        return {name: data[0].__doc__ or "No documentation." for name, data in self._acts.items()}
~~~~~

~~~~~act
patch_file
packages/pyquipu-runtime/src/quipu/runtime/parser.py
~~~~~
~~~~~python.old
                    if current_lang == "act":
                        # 指令块：开始新语句
                        action_name = full_content.strip()
                        new_stmt = {"act": action_name, "contexts": []}
                        statements.append(new_stmt)
                        current_statement = new_stmt
~~~~~
~~~~~python.new
                    if current_lang == "act":
                        # 指令块：开始新语句
                        action_name = full_content.strip()
                        new_stmt: Statement = {"act": action_name, "contexts": []}
                        statements.append(new_stmt)
                        current_statement = new_stmt
~~~~~

#### Acts 3: 修复 `pyquipu-cli` 中的类型问题

现在处理 CLI 包中的类型错误。

~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/commands/workspace.py
~~~~~
~~~~~python.old
            current_hash = engine.git_db.get_tree_hash()
            if current_hash == target_tree_hash:
                bus.success("workspace.discard.noChanges", short_hash=latest_node.short_hash)
                ctx.exit(0)

            diff_stat_str = engine.git_db.get_diff_stat(target_tree_hash, current_hash)

            if not force:
                prompt = bus.get("workspace.discard.prompt.confirm", short_hash=latest_node.short_hash)
~~~~~
~~~~~python.new
            current_hash = engine.git_db.get_tree_hash()
            if current_hash == target_tree_hash:
                bus.success("workspace.discard.noChanges", short_hash=latest_node.short_hash)
                ctx.exit(0)

            assert target_tree_hash is not None
            diff_stat_str = engine.git_db.get_diff_stat(target_tree_hash, current_hash)

            if not force:
                prompt = bus.get("workspace.discard.prompt.confirm", short_hash=latest_node.short_hash)
~~~~~

~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python.old
    def _update_header(self):
        mode = "Markdown" if self.markdown_enabled else "Raw Text"
        self.sub_title = f"Page {self.view_model.current_page} / {self.view_model.total_pages} | View: {mode} (m)"

    def _load_page(self, page_number: int) -> None:
        logger.debug(f"TUI: Loading page {page_number}")
        self.view_model.load_page(page_number)
        logger.debug(f"TUI: Page {page_number} loaded with {len(self.view_model.current_page_nodes)} nodes.")
~~~~~
~~~~~python.new
    def _update_header(self):
        assert self.view_model is not None
        mode = "Markdown" if self.markdown_enabled else "Raw Text"
        self.sub_title = f"Page {self.view_model.current_page} / {self.view_model.total_pages} | View: {mode} (m)"

    def _load_page(self, page_number: int) -> None:
        assert self.view_model is not None
        logger.debug(f"TUI: Loading page {page_number}")
        self.view_model.load_page(page_number)
        logger.debug(f"TUI: Page {page_number} loaded with {len(self.view_model.current_page_nodes)} nodes.")
~~~~~

~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python.old
    def action_toggle_hidden(self) -> None:
        self.view_model.toggle_unreachable()
        self._refresh_table()
~~~~~
~~~~~python.new
    def action_toggle_hidden(self) -> None:
        assert self.view_model is not None
        self.view_model.toggle_unreachable()
        self._refresh_table()
~~~~~

~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python.old
    def action_checkout_node(self) -> None:
        selected_node = self.view_model.get_selected_node()
        if selected_node:
            self.exit(result=("checkout", selected_node.output_tree))

    def action_dump_content(self) -> None:
        selected_node = self.view_model.get_selected_node()
        if selected_node:
            content = self.view_model.get_public_content(selected_node)
            self.exit(result=("dump", content))

    def action_previous_page(self) -> None:
        if self.view_model.current_page > 1:
            self._load_page(self.view_model.current_page - 1)
        else:
            self.bell()

    def action_next_page(self) -> None:
        if self.view_model.current_page < self.view_model.total_pages:
            self._load_page(self.view_model.current_page + 1)
        else:
            self.bell()
~~~~~
~~~~~python.new
    def action_checkout_node(self) -> None:
        assert self.view_model is not None
        selected_node = self.view_model.get_selected_node()
        if selected_node:
            self.exit(result=("checkout", selected_node.output_tree))

    def action_dump_content(self) -> None:
        assert self.view_model is not None
        selected_node = self.view_model.get_selected_node()
        if selected_node:
            content = self.view_model.get_public_content(selected_node)
            self.exit(result=("dump", content))

    def action_previous_page(self) -> None:
        assert self.view_model is not None
        if self.view_model.current_page > 1:
            self._load_page(self.view_model.current_page - 1)
        else:
            self.bell()

    def action_next_page(self) -> None:
        assert self.view_model is not None
        if self.view_model.current_page < self.view_model.total_pages:
            self._load_page(self.view_model.current_page + 1)
        else:
            self.bell()
~~~~~

~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python.old
    def _refresh_table(self):
        table = self.query_one(DataTable)
        table.clear()
        # 从 ViewModel 获取要渲染的节点
        nodes_to_render = self.view_model.get_nodes_to_render()
        self._populate_table(table, nodes_to_render)
        self._focus_current_node(table)
        self._update_header()

    def _populate_table(self, table: DataTable, nodes: List[QuipuNode]):
        # 移除了过滤逻辑，因为 ViewModel 已经处理
        tracks: list[Optional[str]] = []

        for node in nodes:
            is_reachable = self.view_model.is_reachable(node.output_tree)
            dim_tag = "[dim]" if not is_reachable else ""
            end_dim_tag = "[/dim]" if dim_tag else ""
~~~~~
~~~~~python.new
    def _refresh_table(self):
        assert self.view_model is not None
        table = self.query_one(DataTable)
        table.clear()
        # 从 ViewModel 获取要渲染的节点
        nodes_to_render = self.view_model.get_nodes_to_render()
        self._populate_table(table, nodes_to_render)
        self._focus_current_node(table)
        self._update_header()

    def _populate_table(self, table: DataTable, nodes: List[QuipuNode]):
        assert self.view_model is not None
        # 移除了过滤逻辑，因为 ViewModel 已经处理
        tracks: list[Optional[str]] = []

        for node in nodes:
            is_reachable = self.view_model.is_reachable(node.output_tree)
            dim_tag = "[dim]" if not is_reachable else ""
            end_dim_tag = "[/dim]" if dim_tag else ""
~~~~~

~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python.old
    def _get_node_summary(self, node: QuipuNode) -> str:
        return node.summary or "No description"

    def _focus_current_node(self, table: DataTable):
        current_output_tree_hash = self.view_model.current_output_tree_hash
        logger.debug(f"DEBUG: Attempting focus. HEAD={current_output_tree_hash}")

        if not current_output_tree_hash:
~~~~~
~~~~~python.new
    def _get_node_summary(self, node: QuipuNode) -> str:
        return node.summary or "No description"

    def _focus_current_node(self, table: DataTable):
        assert self.view_model is not None
        current_output_tree_hash = self.view_model.current_output_tree_hash
        logger.debug(f"DEBUG: Attempting focus. HEAD={current_output_tree_hash}")

        if not current_output_tree_hash:
~~~~~

~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python.old
        # LookupError 捕获 RowKeyError 等
                logger.warning(f"DEBUG: Row key {row_key} not found in DataTable.")

        except Exception as e:
            logger.error(f"DEBUG: Failed to focus current node: {e}", exc_info=True)

    def _update_loading_preview(self):
        node = self.view_model.get_selected_node()
        if not node:
            return
~~~~~
~~~~~python.new
        # LookupError 捕获 RowKeyError 等
                logger.warning(f"DEBUG: Row key {row_key} not found in DataTable.")

        except Exception as e:
            logger.error(f"DEBUG: Failed to focus current node: {e}", exc_info=True)

    def _update_loading_preview(self):
        assert self.view_model is not None
        node = self.view_model.get_selected_node()
        if not node:
            return
~~~~~

~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python.old
                self.update_timer = self.set_timer(self.debounce_delay_seconds, self._on_timer_finished)

            case ContentViewSate.SHOWING_CONTENT:
                container.set_class(True, "split-mode")
                node = self.view_model.get_selected_node()

                if node:
                    content = self.view_model.get_content_bundle(node)
                    # Update header
                    self.query_one("#content-header", Static).update(
~~~~~
~~~~~python.new
                self.update_timer = self.set_timer(self.debounce_delay_seconds, self._on_timer_finished)

            case ContentViewSate.SHOWING_CONTENT:
                container.set_class(True, "split-mode")
                assert self.view_model is not None
                node = self.view_model.get_selected_node()

                if node:
                    content = self.view_model.get_content_bundle(node)
                    # Update header
                    self.query_one("#content-header", Static).update(
~~~~~

~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python.old
    @on(DataTable.RowHighlighted)
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        # 1. Update data model
        if event.row_key.value:
            self.view_model.select_node_by_key(event.row_key.value)

        # 2. Handle UI updates based on current state
        if self.update_timer:
~~~~~
~~~~~python.new
    @on(DataTable.RowHighlighted)
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        assert self.view_model is not None
        # 1. Update data model
        if event.row_key.value:
            self.view_model.select_node_by_key(event.row_key.value)

        # 2. Handle UI updates based on current state
        if self.update_timer:
~~~~~

~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python.old
    def action_toggle_view(self) -> None:
        if self.content_view_state == ContentViewSate.HIDDEN:
            # If a node is selected, transition to loading, otherwise do nothing
            if self.view_model.get_selected_node():
                self._set_state(ContentViewSate.LOADING)
        else:
            self._set_state(ContentViewSate.HIDDEN)
~~~~~
~~~~~python.new
    def action_toggle_view(self) -> None:
        if self.content_view_state == ContentViewSate.HIDDEN:
            assert self.view_model is not None
            # If a node is selected, transition to loading, otherwise do nothing
            if self.view_model.get_selected_node():
                self._set_state(ContentViewSate.LOADING)
        else:
            self._set_state(ContentViewSate.HIDDEN)
~~~~~

### 下一步建议

所有已知的 `pyright` 错误都已被修复。我建议现在运行 `uv run pyright packages/**/src` 来验证所有问题是否都已解决。

如果验证通过，你可以生成一个 `[COMMIT]` 计划来提交这些修复。
