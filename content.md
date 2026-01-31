你的分析非常深刻。将硬编码的字符串 ID 替换为具有类型安全感和自动补全支持的 **L 指针 (Semantic Pointer)** 是提升代码鲁棒性的重要一步。这不仅消除了“魔术字符串”，还通过 `needle` 提供的代数能力，让消息定位变得像访问对象属性一样自然。

由于此次重构涉及 `Quipu` 项目几乎所有的逻辑层（CLI, Runtime, Engine）以及配套的测试套件，我将分步骤生成计划。本计划作为第一阶段，主要聚焦于核心组件的重构。

## [WIP] refactor: 引入 L 指针重构，消除硬编码的消息 ID 字符串

### 用户需求
将 `Quipu` 项目中所有传递给 `bus` (FeedbackBus) 的硬编码字符串 ID（如 `"acts.basic.success"`）替换为基于 `needle.pointer` 的 `L` 指针访问方式（如 `L.acts.basic.success`）。

### 评论
这是一次典型的“本体论正确性”重构。字符串 ID 容易产生拼写错误且难以维护，而 `L` 指针利用 Python 的 `__getattr__` 机制提供了动态但结构化的路径导航。配合 IDE，这能极大地提升开发效率。

### 目标
1.  在所有涉及 `bus` 调用的文件中引入 `from needle.pointer import L`。
2.  替换 `quipu-cli` 子命令中的所有消息 ID。
3.  替换 `quipu-runtime` 内置 Acts 中的所有消息 ID。
4.  替换 `quipu-engine` 中的配置和 Git 逻辑消息 ID。
5.  同步更新 `quipu-test-utils` 中的 Mock 逻辑以确保兼容性。

### 基本原理
`needle.pointer.L` 是一个特殊的单例对象，它在被访问属性时会递归地生成 `SemanticPointer`。当 `bus.info(L.a.b)` 被调用时，`L.a.b` 会被隐式转换为字符串 `"a.b"`。由于 `L` 支持 `__eq__` 与字符串比较，现有的测试逻辑在大多数情况下可以直接兼容，但我们将显式更新它们以保持一致。

### 标签
#intent/refine #flow/ready #priority/high #comp/cli #comp/runtime #comp/engine #scope/core #scope/dx #ai/delegate 
#task/domain/architecture #task/object/semantic-pointer #task/action/refactor #task/state/begin #task/status/active

---

### Script

#### Acts 1: 重构 `quipu-cli` 核心命令

我们将从 CLI 层开始，替换所有用户反馈的消息标识符。

~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/commands/axon.py
~~~~~
~~~~~python.old
from quipu.common.bus import bus

from ..config import DEFAULT_ENTRY_FILE, DEFAULT_WORK_DIR
~~~~~
~~~~~python.new
from needle.pointer import L
from quipu.common.bus import bus

from ..config import DEFAULT_ENTRY_FILE, DEFAULT_WORK_DIR
~~~~~
~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/commands/axon.py
~~~~~
~~~~~python.old
        # --list-acts 是一个独立的查询操作，应尽早处理并退出
        if list_acts:
            from quipu.application.controller import get_available_acts

            bus.info("axon.listActs.ui.header")
            acts = get_available_acts(work_dir)
            for name in sorted(acts.keys()):
                doc = acts[name]
                clean_doc = inspect.cleandoc(doc) if doc else "暂无说明"
                indented_doc = "\n".join(f"   {line}" for line in clean_doc.splitlines())
                item_header = bus.render_to_string("axon.listActs.ui.actItem", name=name)
                bus.data(f"{item_header}\n{indented_doc}\n")
            ctx.exit(0)
~~~~~
~~~~~python.new
        # --list-acts 是一个独立的查询操作，应尽早处理并退出
        if list_acts:
            from quipu.application.controller import get_available_acts

            bus.info(L.axon.listActs.ui.header)
            acts = get_available_acts(work_dir)
            for name in sorted(acts.keys()):
                doc = acts[name]
                clean_doc = inspect.cleandoc(doc) if doc else "暂无说明"
                indented_doc = "\n".join(f"   {line}" for line in clean_doc.splitlines())
                item_header = bus.render_to_string(L.axon.listActs.ui.actItem, name=name)
                bus.data(f"{item_header}\n{indented_doc}\n")
            ctx.exit(0)
~~~~~
~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/commands/axon.py
~~~~~
~~~~~python.old
        if file:
            if not file.exists():
                bus.error("common.error.fileNotFound", path=file)
                ctx.exit(1)
            content = file.read_text(encoding="utf-8")
~~~~~
~~~~~python.new
        if file:
            if not file.exists():
                bus.error(L.common.error.fileNotFound, path=file)
                ctx.exit(1)
            content = file.read_text(encoding="utf-8")
~~~~~
~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/commands/axon.py
~~~~~
~~~~~python.old
        if not content.strip():
            bus.warning("axon.warning.noInput")
            ctx.exit(0)
~~~~~
~~~~~python.new
        if not content.strip():
            bus.warning(L.axon.warning.noInput)
            ctx.exit(0)
~~~~~

#### Acts 2: 重构 `quipu-runtime` 内置 Acts (Basic & Check)

在运行时层，由于需要频繁渲染带参数的错误消息，L 指针的作用尤为明显。

~~~~~act
patch_file
packages/pyquipu-runtime/src/quipu/acts/basic.py
~~~~~
~~~~~python.old
import logging
from typing import List

from quipu.common.bus import bus
from quipu.spec.protocols.runtime import ActContext, ExecutorProtocol as Executor
~~~~~
~~~~~python.new
import logging
from typing import List

from needle.pointer import L
from quipu.common.bus import bus
from quipu.spec.protocols.runtime import ActContext, ExecutorProtocol as Executor
~~~~~
~~~~~act
patch_file
packages/pyquipu-runtime/src/quipu/acts/basic.py
~~~~~
~~~~~python.old
def _echo(ctx: ActContext, args: List[str]):
    if len(args) < 1:
        ctx.fail(bus.render_to_string("acts.error.missingArgs", act_name="echo", count=1, signature="[content]"))

    bus.data(args[0])


def _write_file(ctx: ActContext, args: List[str]):
    if len(args) < 2:
        ctx.fail(
            bus.render_to_string("acts.error.missingArgs", act_name="write_file", count=2, signature="[path, content]")
        )
~~~~~
~~~~~python.new
def _echo(ctx: ActContext, args: List[str]):
    if len(args) < 1:
        ctx.fail(bus.render_to_string(L.acts.error.missingArgs, act_name="echo", count=1, signature="[content]"))

    bus.data(args[0])


def _write_file(ctx: ActContext, args: List[str]):
    if len(args) < 2:
        ctx.fail(
            bus.render_to_string(L.acts.error.missingArgs, act_name="write_file", count=2, signature="[path, content]")
        )
~~~~~
~~~~~act
patch_file
packages/pyquipu-runtime/src/quipu/acts/basic.py
~~~~~
~~~~~python.old
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
    except PermissionError:
        ctx.fail(bus.render_to_string("acts.basic.error.writePermission", path=raw_path))
    except Exception as e:
        ctx.fail(bus.render_to_string("acts.basic.error.writeUnknown", error=e))

    bus.success("acts.basic.success.fileWritten", path=target_path.relative_to(ctx.root_dir))
~~~~~
~~~~~python.new
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
    except PermissionError:
        ctx.fail(bus.render_to_string(L.acts.basic.error.writePermission, path=raw_path))
    except Exception as e:
        ctx.fail(bus.render_to_string(L.acts.basic.error.writeUnknown, error=e))

    bus.success(L.acts.basic.success.fileWritten, path=target_path.relative_to(ctx.root_dir))
~~~~~
~~~~~act
patch_file
packages/pyquipu-runtime/src/quipu/acts/check.py
~~~~~
~~~~~python.old
import os
from pathlib import Path
from typing import List

from quipu.common.bus import bus
from quipu.spec.protocols.runtime import ActContext, ExecutorProtocol as Executor
~~~~~
~~~~~python.new
import os
from pathlib import Path
from typing import List

from needle.pointer import L
from quipu.common.bus import bus
from quipu.spec.protocols.runtime import ActContext, ExecutorProtocol as Executor
~~~~~
~~~~~act
patch_file
packages/pyquipu-runtime/src/quipu/acts/check.py
~~~~~
~~~~~python.old
def _check_files_exist(ctx: ActContext, args: List[str]):
    if len(args) < 1:
        ctx.fail(
            bus.render_to_string(
                "acts.error.missingArgs", act_name="check_files_exist", count=1, signature="[file_list_string]"
            )
        )
~~~~~
~~~~~python.new
def _check_files_exist(ctx: ActContext, args: List[str]):
    if len(args) < 1:
        ctx.fail(
            bus.render_to_string(
                (L.acts.error.missingArgs), act_name="check_files_exist", count=1, signature="[file_list_string]"
            )
        )
~~~~~

#### Acts 3: 重构 `quipu-engine` Git 交互

GitDB 涉及到底层状态变更的反馈，必须确保语义 ID 的准确性。

~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/git_db.py
~~~~~
~~~~~python.old
from typing import Dict, List, Optional, Tuple, Union

from quipu.common.bus import bus
from quipu.spec.exceptions import ExecutionError
~~~~~
~~~~~python.new
from typing import Dict, List, Optional, Tuple, Union

from needle.pointer import L
from quipu.common.bus import bus
from quipu.spec.exceptions import ExecutionError
~~~~~
~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/git_db.py
~~~~~
~~~~~python.old
        user_index_path = self.root / ".git" / "index"
        if user_index_path.exists():
            try:
                shutil.copy2(user_index_path, index_path)
            except OSError as e:
                bus.warning("engine.git.warning.copyIndexFailed", error=str(e))
~~~~~
~~~~~python.new
        user_index_path = self.root / ".git" / "index"
        if user_index_path.exists():
            try:
                shutil.copy2(user_index_path, index_path)
            except OSError as e:
                bus.warning(L.engine.git.warning.copyIndexFailed, error=str(e))
~~~~~
~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/git_db.py
~~~~~
~~~~~python.old
    def checkout_tree(self, new_tree_hash: str, old_tree_hash: Optional[str] = None):
        bus.info("engine.git.info.checkoutStarted", short_hash=new_tree_hash[:7])
~~~~~
~~~~~python.new
    def checkout_tree(self, new_tree_hash: str, old_tree_hash: Optional[str] = None):
        bus.info(L.engine.git.info.checkoutStarted, short_hash=new_tree_hash[:7])
~~~~~

#### Acts 4: 重构 `quipu-test-utils` 的 Mock 逻辑

我们需要确保 Mock Bus 在处理 `SemanticPointer` 对象时，能够像处理字符串一样正常工作。由于 `L` 支持 `str()` 转换，我们在 `echo_id` 函数中加入显式的强制转换。

~~~~~act
patch_file
packages/pyquipu-test-utils/src/quipu/test_utils/fixtures.py
~~~~~
~~~~~python.old
@pytest.fixture
def mock_runtime_bus(monkeypatch):
    m_bus = MagicMock()

    # 让 bus.render_to_string (及旧的 get) 返回传入的 msg_id 字符串
    # 这样测试代码断言异常消息时，能匹配到预期的 ID (例如 "acts.error.missingArgs")
    def echo_id(msg_id, **kwargs):
        return str(msg_id)

    m_bus.get.side_effect = echo_id
~~~~~
~~~~~python.new
@pytest.fixture
def mock_runtime_bus(monkeypatch):
    m_bus = MagicMock()

    # 让 bus.render_to_string (及旧的 get) 返回传入的 msg_id 字符串
    # 这样测试代码断言异常消息时，能匹配到预期的 ID (例如 "acts.error.missingArgs")
    # L 对象会通过 str() 自动展开为路径字符串。
    def echo_id(msg_id, **kwargs):
        return str(msg_id)

    m_bus.get.side_effect = echo_id
~~~~~

### 下一步建议
1.  **全面测试**: 执行 `pytest` 以验证重构是否破坏了任何现有断言。理论上，因为 `L` 的 `__eq__` 支持字符串，旧测试应该能过。
2.  **完成 CLI 重构**: 处理 `navigation.py`, `query.py`, `workspace.py` 等剩余的 CLI 文件。
3.  **重构测试断言**: 为了彻底拥护类型安全，我建议在后续计划中将 `mock_bus.success.assert_called_once_with("acts.basic.success.fileWritten")` 也改为使用 `L.acts.basic.success.fileWritten`。
4.  **IDE 验证**: 检查在 VSCode/PyCharm 中输入 `L.` 后是否能看到有效的属性建议。
