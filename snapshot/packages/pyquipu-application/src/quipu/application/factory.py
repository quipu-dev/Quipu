import logging
from pathlib import Path

from quipu.engine.config import ConfigManager
from quipu.engine.git_storage import GitSnapshotStorage
from quipu.engine.memory_index import InMemoryGraphIndex
from quipu.engine.sqlite_db import DatabaseManager
from quipu.engine.sqlite_index import SQLiteGraphIndex
from quipu.engine.state_machine import Engine

from .utils import find_git_repository_root

logger = logging.getLogger(__name__)


def create_engine(work_dir: Path, lazy: bool = False, use_cache: bool = True) -> Engine:
    """实例化 Quipu 引擎堆栈。

    Args:
        work_dir: 操作的工作区目录。
        lazy: 如果为 True，则不立即加载完整的历史图谱 (不调用 align)。
        use_cache: 如果为 False，则关闭 SQLite 缓存，使用纯内存索引，
                  实现 0 IO 开销与零副作用，专为 CI/CD 瞬时执行设计。
    """
    project_root = find_git_repository_root(work_dir) or work_dir
    config = ConfigManager(project_root)

    # 1. 物理快照存储层：永远是 GitSnapshotStorage
    storage = GitSnapshotStorage(project_root)

    # 2. 检查配置覆盖 (如果用户显式配置了 storage.type = "memory" 或环境变量指定)
    config_storage_type = config.get("storage.type", "sqlite")
    if config_storage_type in ("memory", "none", "in_memory"):
        use_cache = False

    # 3. 逻辑索引层按需装配
    db_manager = None
    if use_cache:
        logger.debug("Engine factory: Using SQLiteGraphIndex (use_cache=True)")
        db_manager = DatabaseManager(project_root)
        db_manager.init_schema()
        index = SQLiteGraphIndex(db_manager)
    else:
        logger.debug("Engine factory: Using InMemoryGraphIndex (use_cache=False)")
        index = InMemoryGraphIndex()

    # 4. 组装并返回 Engine 门面
    engine = Engine(
        root_dir=project_root,
        storage=storage,
        index=index,
        db_manager=db_manager,
        use_cache=use_cache,
    )

    if not lazy:
        engine.align()

    return engine
