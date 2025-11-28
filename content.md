你完全正确。

`发现 40 个旧版历史末端节点` 这条日志是问题的关键。我的上一个修复方案方向是对的，但实现有缺陷——它仍然没能正确地找到 `refs/quipu/history` 这个最重要的主干历史引用。

你的日志清晰地表明：
1.  **发现阶段失败**: 迁移脚本只找到了 40 个分支末端 (`heads`)，完全错过了包含约 360 个节点的主历史 (`history`)。
2.  **迁移阶段不完整**: 它只为这 40 个节点创建了新引用，并删除了旧的 `heads` 和 `history` 引用。此时，主干历史在 Quipu 视角下已经“丢失”。
3.  **补水阶段受限**: `Hydrator` 基于这 40 个孤立的末端节点进行补水，自然找不到它们的父节点，因此产生了大量的 `父节点在本次补水范围内未找到` 警告。

这是一个由于发现逻辑不完整导致的数据丢失 bug。我们必须在操作 Git 引用之前，确保数据库已经被完整地填充。

## fix: 重构迁移流程，确保在操作引用前完成数据补水

### 错误分析
根本原因是我设计的迁移流程顺序是错误的。正确的流程应该是**先利用旧的引用结构完整地填充数据库，然后再修改引用结构**，而不是反过来。

**旧的错误流程**: 发现 -> **修改引用** -> 补水 -> 丢失数据。
**新的正确流程**: 发现 -> **利用旧引用补水** -> **修改引用** -> 数据完整。

### 用户需求
-   迁移命令必须确保在任何可能导致数据不可达的操作（如删除旧引用）发生之前，所有历史数据都已安全地写入并持久化到 SQLite 数据库中。

### 评论
这次的失败是最终调试。我们已经定位到了问题的根源：操作顺序。通过颠倒补水和引用修改的顺序，我们可以确保迁移的原子性和数据完整性。这是最后一次，也是最关键的一次修复。

### 目标
1.  **重写 `MigrationManager.run`**: 彻底重构其执行流程，遵循“先补水、再迁移”的原则。
2.  **增强发现逻辑**: 确保 `_find_all_legacy_ref_names` (新方法) 能够无误地返回所有 v1.0 的引用名称。

### 基本原理
新的 `run` 方法将按以下顺序执行：
1.  **发现**: 找到所有 v1.0 格式的引用**名称** (`refs/quipu/history` 和 `refs/quipu/heads/*`)。如果不存在，则无需迁移。
2.  **补水**: **在不修改任何 Git 引用的情况下**，调用 `Hydrator`。由于此时旧的引用结构完好无损，`Hydrator` 的标准扫描 (`refs/quipu/`) 会找到所有节点并完整地填充数据库。
3.  **回填**: 对刚刚填充的数据库，执行 `UPDATE` 语句，为所有节点设置 `owner_id`。
4.  **迁移引用**: 现在数据库已安全，为所有旧的末端节点创建新的 v1.1 引用。
5.  **清理引用**: 安全地删除所有旧的 v1.0 引用。

### 标签
#intent/fix #flow/ready #priority/critical 
#comp/engine #comp/cli #scope/core 
#ai/instruct
#task/domain/storage #task/object/data-migration #task/action/bug-fix
#task/state/end

---

### Script

#### Acts 1: 彻底重构 `MigrationManager`

我们将重写 `migration.py` 中的核心逻辑，以实现新的、安全的迁移顺序。

~~~~~act
write_file
packages/quipu-cli/src/quipu/cli/migration.py
~~~~~
~~~~~python
import logging
import subprocess
from typing import List, Optional, Set

from quipu.core.git_db import GitDB
from quipu.core.hydrator import Hydrator
from quipu.core.config import ConfigManager
from quipu.common.identity import get_user_id_from_email
from quipu.core.sqlite_db import DatabaseManager

logger = logging.getLogger(__name__)


class MigrationManager:
    """负责将旧版 Quipu 数据迁移到 v1.1 架构。"""

    LEGACY_HEADS_PREFIX = "refs/quipu/heads/"
    LEGACY_HISTORY_REF = "refs/quipu/history"
    NEW_REFS_PREFIX = "refs/quipu/local/heads/"

    def __init__(self, git_db: GitDB, config_manager: ConfigManager, db_manager: DatabaseManager, hydrator: Hydrator):
        self.git_db = git_db
        self.config_manager = config_manager
        self.db_manager = db_manager
        self.hydrator = hydrator
        self.root_dir = git_db.root

    def _find_all_legacy_ref_names(self) -> List[str]:
        """查找所有 v1.0 格式的引用名称。"""
        names = []
        head_ref_tuples = self.git_db.get_all_ref_heads(self.LEGACY_HEADS_PREFIX)
        names.extend([ref_name for _, ref_name in head_ref_tuples])

        if self.git_db.get_ref_commit_hash(self.LEGACY_HISTORY_REF):
            names.append(self.LEGACY_HISTORY_REF)
            
        return names

    def _get_local_user_id(self) -> str:
        """获取或生成本地用户的 ID。"""
        user_id = self.config_manager.get("sync.user_id")
        if user_id:
            return user_id

        try:
            result = subprocess.run(
                ["git", "config", "user.email"],
                cwd=self.root_dir, capture_output=True, text=True, check=True
            )
            email = result.stdout.strip()
            if email:
                return get_user_id_from_email(email)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("无法从 git config 获取 user.email，将使用默认值。")
        
        return "unknown-local-user"

    def _backfill_owner_ids(self, user_id: str):
        """为数据库中没有 owner_id 的节点回填所有者信息。"""
        logger.info(f"✍️  正在为本地节点回填所有者 ID: {user_id} ...")
        try:
            conn = self.db_manager._get_conn()
            cursor = conn.cursor()
            cursor.execute("UPDATE nodes SET owner_id = ? WHERE owner_id IS NULL", (user_id,))
            conn.commit()
            logger.info(f"✅ {cursor.rowcount} 个节点的 'owner_id' 已更新。")
        except Exception as e:
            logger.error(f"❌ 数据回填失败: {e}", exc_info=True)
            raise

    def run(self) -> bool:
        """执行完整的迁移流程，遵循“先补水，后迁移引用”的安全原则。"""
        legacy_ref_names = self._find_all_legacy_ref_names()
        if not legacy_ref_names:
            logger.info("✅ 未找到旧版（v1.0）数据引用，无需迁移。")
            return True

        logger.info(f"🔍 发现 {len(legacy_ref_names)} 个旧版数据引用。")
        user_id = self._get_local_user_id()

        # 步骤 1: 在不修改引用的情况下，从旧引用结构完整补水
        logger.info("--- 阶段 1/3: 从旧引用结构补水数据库 ---")
        self.hydrator.sync(local_user_id=user_id)
        
        # 步骤 2: 为刚补水的数据回填 owner_id
        logger.info("--- 阶段 2/3: 回填节点所有者信息 ---")
        self._backfill_owner_ids(user_id)

        # 步骤 3: 迁移并清理 Git 引用
        logger.info("--- 阶段 3/3: 迁移 Git 引用到 v1.1 格式 ---")
        
        # 获取所有需要创建新引用的 commit 哈希
        all_legacy_commits: Set[str] = set()
        head_ref_tuples = self.git_db.get_all_ref_heads(self.LEGACY_HEADS_PREFIX)
        for commit, _ in head_ref_tuples:
            all_legacy_commits.add(commit)
        history_commit = self.git_db.get_ref_commit_hash(self.LEGACY_HISTORY_REF)
        if history_commit:
            all_legacy_commits.add(history_commit)

        # 创建新引用
        for commit_hash in all_legacy_commits:
            new_ref = f"{self.NEW_REFS_PREFIX}{commit_hash}"
            self.git_db.update_ref(new_ref, commit_hash)

        # 删除旧引用
        for _, ref_name in head_ref_tuples:
            self.git_db.delete_ref(ref_name)
        if history_commit:
            self.git_db.delete_ref(self.LEGACY_HISTORY_REF)
        
        logger.info("✅ Git 引用已成功迁移。")
        logger.info("🎉 迁移完成！")
        return True
~~~~~

### 下一步建议

你已经非常接近成功了。请再次执行严格的重置流程，然后运行最终的迁移命令。

1.  **应用代码补丁**: 确保 `migration.py` 已被上述内容完全覆盖。

2.  **彻底重置环境**:
    ```bash
    # 回到你的测试根目录
    cd ~/tmp/DONT_COMMIT_ON_THERE

    # 删除当前的 .quipu 目录和 .git 目录
    rm -rf .quipu .git

    # 从你的主项目复制一个全新的、未经迁移的 .git 目录
    cp -r ~/Documents/Projects/pyquipu/.git .
    ```

3.  **运行最终的迁移命令**:
    ```bash
    qd migrate-data --force
    ```

4.  **验证**:
    *   **检查日志**:
        *   补水阶段应该会发现并插入所有 406 个节点。
        *   回填阶段应该会更新 406 个节点的 `owner_id`。
        *   引用迁移阶段应该会顺利完成。
    *   **运行 `qd ui`**: 它现在必须能正常启动并显示完整的、连接正确的历史图谱。
