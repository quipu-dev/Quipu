# refactor: 重构 Engine 以使用历史记录读写接口

## 用户需求
根据存储层改造计划，`Engine` 类需要被重构，以消除其对文件系统存储实现的直接依赖。它应该通过抽象的 `HistoryReader` 和 `HistoryWriter` 接口来执行所有历史记录的读写操作，并通过依赖注入的方式接收这些接口的具体实现。

## 评论
这是实现存储层解耦的核心步骤。通过应用依赖注入和面向接口编程，我们将 `Engine` 的业务流程控制（“做什么”）与存储的物理实现（“怎么做”）彻底分开。这不仅为未来切换到 Git 对象存储等新后端铺平了道路，还极大地提升了 `Engine` 模块的可测试性。

## 目标
1.  修改 `Engine` 类的构造函数 `__init__`，使其接受 `reader` 和 `writer` 对象作为参数。
2.  重构 `Engine.align()` 方法，使其使用 `self.reader` 来加载历史记录，而不是直接调用文件系统相关的函数。
3.  重构 `Engine.create_plan_node()` 和 `Engine.capture_drift()` 方法，将节点创建的持久化逻辑委托给 `self.writer`。
4.  清理 `history.py` 模块中因本次重构而变得多余的 `load_history_graph` 函数。

## 基本原理
本计划严格遵循“组合优于继承”和“依赖注入”的设计原则。`Engine` 类将不再关心历史记录是存储在 `.md` 文件中还是 Git 对象中；它只与 `HistoryReader` 和 `HistoryWriter` 这两个“契约”进行交互。具体的存储策略（`FileSystemHistoryReader` 等）将在更高层（未来将在 `quipu-cli` 的 `controller` 中）被实例化并“注入”到 `Engine` 中，从而实现了职责分离和高度的模块化。

## 标签
#comp/engine #concept/history #scope/core

---

## Script

### Acts 1: 重构 Engine 类以使用依赖注入

使用 `write_file` 完全覆盖 `state_machine.py` 文件，以引入新的接口依赖和重构后的方法逻辑。

~~~~~act
write_file
~~~~~

~~~~~path
packages/quipu-engine/src/quipu/core/state_machine.py
~~~~~

~~~~~python
import logging
import re
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from datetime import datetime

from .git_db import GitDB
from .config import ConfigManager
from quipu.core.models import QuipuNode
from quipu.core.storage import HistoryReader, HistoryWriter

logger = logging.getLogger(__name__)


class Engine:
    """
    Axon 状态引擎。
    负责协调 Git 物理状态和 Axon 逻辑图谱。
    """

    def _sync_persistent_ignores(self):
        """将 config.yml 中的持久化忽略规则同步到 .git/info/exclude。"""
        try:
            config = ConfigManager(self.root_dir)
            patterns = config.get("sync.persistent_ignores", [])
            if not patterns:
                return

            exclude_file = self.root_dir / ".git" / "info" / "exclude"
            exclude_file.parent.mkdir(exist_ok=True)

            header = "# --- Managed by Quipu ---"
            footer = "# --- End Managed by Quipu ---"

            content = ""
            if exclude_file.exists():
                content = exclude_file.read_text("utf-8")

            managed_block_pattern = re.compile(rf"{re.escape(header)}.*{re.escape(footer)}", re.DOTALL)

            new_block = f"{header}\n" + "\n".join(patterns) + f"\n{footer}"

            new_content, count = managed_block_pattern.subn(new_block, content)
            if count == 0:
                if content and not content.endswith("\n"):
                    content += "\n"
                new_content = content + "\n" + new_block + "\n"

            if new_content != content:
                exclude_file.write_text(new_content, "utf-8")
                logger.debug("✅ .git/info/exclude 已更新。")

        except Exception as e:
            logger.warning(f"⚠️  无法同步持久化忽略规则: {e}")

    def __init__(self, root_dir: Path, reader: HistoryReader, writer: HistoryWriter):
        self.root_dir = root_dir.resolve()
        self.quipu_dir = self.root_dir / ".quipu"
        self.history_dir = self.quipu_dir / "history"
        self.head_file = self.quipu_dir / "HEAD"

        self.nav_log_file = self.quipu_dir / "nav_log"
        self.nav_ptr_file = self.quipu_dir / "nav_ptr"

        self.history_dir.mkdir(parents=True, exist_ok=True)

        quipu_gitignore = self.quipu_dir / ".gitignore"
        if not quipu_gitignore.exists():
            try:
                quipu_gitignore.write_text("*\n", encoding="utf-8")
            except Exception as e:
                logger.warning(f"无法创建隔离文件 {quipu_gitignore}: {e}")

        self.git_db = GitDB(self.root_dir)
        self.reader = reader
        self.writer = writer
        self.history_graph: Dict[str, QuipuNode] = {}
        self.current_node: Optional[QuipuNode] = None

        self._sync_persistent_ignores()

    def _read_head(self) -> Optional[str]:
        if self.head_file.exists():
            return self.head_file.read_text(encoding="utf-8").strip()
        return None

    def _write_head(self, tree_hash: str):
        try:
            self.head_file.write_text(tree_hash, encoding="utf-8")
        except Exception as e:
            logger.warning(f"⚠️  无法更新 HEAD 指针: {e}")

    def _read_nav(self) -> Tuple[List[str], int]:
        log = []
        ptr = -1
        if self.nav_log_file.exists():
            try:
                content = self.nav_log_file.read_text(encoding="utf-8").strip()
                if content:
                    log = content.splitlines()
            except Exception: pass
        if self.nav_ptr_file.exists():
            try:
                ptr = int(self.nav_ptr_file.read_text(encoding="utf-8").strip())
            except Exception: pass
        if not log:
            ptr = -1
        elif ptr < 0:
            ptr = 0
        elif ptr >= len(log):
            ptr = len(log) - 1
        return log, ptr

    def _write_nav(self, log: List[str], ptr: int):
        try:
            self.nav_log_file.write_text("\n".join(log), encoding="utf-8")
            self.nav_ptr_file.write_text(str(ptr), encoding="utf-8")
        except Exception as e:
            logger.warning(f"⚠️  无法更新导航历史: {e}")

    def _append_nav(self, tree_hash: str):
        log, ptr = self._read_nav()
        if not log:
            current_head = self._read_head()
            if current_head and current_head != tree_hash:
                log.append(current_head)
                ptr = 0
        if ptr < len(log) - 1:
            log = log[:ptr + 1]
        if log and log[-1] == tree_hash:
            ptr = len(log) - 1
            self._write_nav(log, ptr)
            return
        log.append(tree_hash)
        ptr = len(log) - 1
        MAX_LOG_SIZE = 100
        if len(log) > MAX_LOG_SIZE:
            log = log[-MAX_LOG_SIZE:]
            ptr = len(log) - 1
        self._write_nav(log, ptr)

    def visit(self, target_hash: str):
        self.checkout(target_hash)
        self._append_nav(target_hash)

    def back(self) -> Optional[str]:
        log, ptr = self._read_nav()
        if ptr > 0:
            new_ptr = ptr - 1
            target_hash = log[new_ptr]
            logger.info(f"🔙 Back to: {target_hash[:7]} (History: {new_ptr + 1}/{len(log)})")
            self.checkout(target_hash)
            self._write_nav(log, new_ptr)
            return target_hash
        return None

    def forward(self) -> Optional[str]:
        log, ptr = self._read_nav()
        if ptr < len(log) - 1:
            new_ptr = ptr + 1
            target_hash = log[new_ptr]
            logger.info(f"🔜 Forward to: {target_hash[:7]} (History: {new_ptr + 1}/{len(log)})")
            self.checkout(target_hash)
            self._write_nav(log, new_ptr)
            return target_hash
        return None

    def align(self) -> str:
        all_nodes = self.reader.load_all_nodes()
        final_graph: Dict[str, QuipuNode] = {}
        for node in all_nodes:
            if node.output_tree not in final_graph or \
               node.timestamp > final_graph[node.output_tree].timestamp:
                final_graph[node.output_tree] = node
        self.history_graph = final_graph
        if all_nodes:
            logger.info(f"从存储中加载了 {len(all_nodes)} 个历史事件，形成 {len(final_graph)} 个唯一状态节点。")

        current_hash = self.git_db.get_tree_hash()
        EMPTY_TREE_HASH = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        if current_hash == EMPTY_TREE_HASH and not self.history_graph:
            logger.info("✅ 状态对齐：检测到创世状态 (空仓库)。")
            self.current_node = None
            return "CLEAN"

        if current_hash in self.history_graph:
            self.current_node = self.history_graph[current_hash]
            logger.info(f"✅ 状态对齐：当前工作区匹配节点 {self.current_node.short_hash}")
            self._write_head(current_hash)
            return "CLEAN"

        logger.warning(f"⚠️  状态漂移：当前 Tree Hash {current_hash[:7]} 未在历史中找到。")
        if not self.history_graph:
            return "ORPHAN"
        return "DIRTY"

    def capture_drift(self, current_hash: str, message: Optional[str] = None) -> QuipuNode:
        log_message = f"📸 正在捕获工作区漂移 (Message: {message})" if message else "📸 正在捕获工作区漂移"
        logger.info(f"{log_message}，新状态 Hash: {current_hash[:7]}")

        genesis_hash = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        input_hash = genesis_hash
        head_hash = self._read_head()
        if head_hash and head_hash in self.history_graph:
            input_hash = head_hash
        elif self.history_graph:
            last_node = max(self.history_graph.values(), key=lambda node: node.timestamp)
            input_hash = last_node.output_tree
            logger.warning(f"⚠️  丢失 HEAD 指针，自动回退到最新历史节点: {input_hash[:7]}")

        diff_summary = self.git_db.get_diff_stat(input_hash, current_hash)
        user_message_section = f"### 💬 备注:\n{message}\n\n" if message else ""
        body = (
            f"# 📸 Snapshot Capture\n\n"
            f"{user_message_section}"
            f"检测到工作区发生变更。\n\n"
            f"### 📝 变更文件摘要:\n```\n{diff_summary}\n```"
        )

        new_node = self.writer.create_node(
            node_type="capture",
            input_tree=input_hash,
            output_tree=current_hash,
            content=body,
            message=message
        )

        last_commit_hash = None
        res = self.git_db._run(["rev-parse", "refs/quipu/history"], check=False)
        if res.returncode == 0:
            last_commit_hash = res.stdout.strip()
        commit_msg = f"Axon Save: {message}" if message else f"Axon Capture: {current_hash[:7]}"
        parents = [last_commit_hash] if last_commit_hash else []
        new_commit_hash = self.git_db.create_anchor_commit(current_hash, commit_msg, parent_commits=parents)
        self.git_db.update_ref("refs/quipu/history", new_commit_hash)

        self.history_graph[current_hash] = new_node
        self.current_node = new_node
        self._write_head(current_hash)
        self._append_nav(current_hash)

        logger.info(f"✅ 捕获完成，新节点已创建: {new_node.filename.name}")
        return new_node

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

        parent_commit = None
        try:
            res = self.git_db._run(["rev-parse", "refs/quipu/history"], check=False)
            if res.returncode == 0:
                parent_commit = res.stdout.strip()
        except Exception: pass
        commit_msg = f"Axon Plan: {output_tree[:7]}"
        parents = [parent_commit] if parent_commit else []
        new_commit_hash = self.git_db.create_anchor_commit(output_tree, commit_msg, parent_commits=parents)
        self.git_db.update_ref("refs/quipu/history", new_commit_hash)

        self.history_graph[output_tree] = new_node
        self.current_node = new_node
        self._write_head(output_tree)
        self._append_nav(output_tree)

        logger.info(f"✅ Plan 已归档: {new_node.filename.name}")
        return new_node

    def checkout(self, target_hash: str):
        self.git_db.checkout_tree(target_hash)
        self._write_head(target_hash)
        if target_hash in self.history_graph:
            self.current_node = self.history_graph[target_hash]
        logger.info(f"🔄 状态已切换至: {target_hash[:7]}")
~~~~~

### Acts 2: 清理 `history.py` 模块

移除 `load_history_graph` 函数，因为它现在的功能已经内化到 `Engine.align` 方法中。`load_all_history_nodes` 函数被保留，作为 `FileSystemHistoryReader` 的实现基础。

~~~~~act
write_file
~~~~~

~~~~~path
packages/quipu-engine/src/quipu/core/history.py
~~~~~

~~~~~python
import logging
import re
from pathlib import Path
from typing import Dict, Optional, List
import yaml
from quipu.core.models import QuipuNode
from datetime import datetime

logger = logging.getLogger(__name__)

FILENAME_PATTERN = re.compile(
    r"([0-9a-f]{40}|_{40})_([0-9a-f]{40})_(\d{14})\.md"
)

def _parse_frontmatter(text: str) -> tuple[Dict, str]:
    if not text.startswith("---"): return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3: return {}, text
    _, frontmatter_str, content = parts
    try:
        meta = yaml.safe_load(frontmatter_str) or {}
        return meta, content.strip()
    except yaml.YAMLError:
        return {}, text

def load_all_history_nodes(history_dir: Path) -> List[QuipuNode]:
    """
    (For UI & Graphing)
    加载所有历史事件，构建完整的父子关系图，并返回所有节点的列表。
    """
    if not history_dir.exists(): return []

    all_nodes: List[QuipuNode] = []
    nodes_by_output: Dict[str, List[QuipuNode]] = {}

    for file_path in history_dir.glob("*.md"):
        match = FILENAME_PATTERN.match(file_path.name)
        if not match:
            logger.warning(f"跳过格式不匹配的历史文件: {file_path.name}")
            continue
        
        input_hash, output_hash, ts_str = match.groups()
        try:
            full_content = file_path.read_text("utf-8")
            meta, body_content = _parse_frontmatter(full_content)
            
            node = QuipuNode(
                input_tree=input_hash, output_tree=output_hash,
                timestamp=datetime.strptime(ts_str, "%Y%m%d%H%M%S"),
                filename=file_path, node_type=meta.get("type", "unknown"),
                content=body_content
            )
            all_nodes.append(node)
            nodes_by_output.setdefault(output_hash, []).append(node)
        except Exception as e:
            logger.error(f"加载历史节点失败 {file_path.name}: {e}")

    # 对每个 output_hash 对应的节点列表按时间戳排序
    # 这是构建父子关系所必需的，确保子节点总能找到时间上在其之前的父节点
    for nodes in nodes_by_output.values():
        nodes.sort(key=lambda n: n.timestamp)

    # 构建父子关系
    for node in all_nodes:
        # 寻找潜在的父节点 (其 output_tree 是当前节点的 input_tree)
        potential_parents = nodes_by_output.get(node.input_tree, [])
        # 过滤出时间戳在当前节点之前的父节点
        valid_parents = [p for p in potential_parents if p.timestamp < node.timestamp]
        if valid_parents:
            # 选择时间戳最新的那个作为父节点
            parent_node = max(valid_parents, key=lambda p: p.timestamp)
            node.parent = parent_node
            parent_node.children.append(node)

    # 对每个节点的子节点列表按时间戳排序
    for node in all_nodes:
        node.children.sort(key=lambda n: n.timestamp)
        
    return all_nodes
~~~~~