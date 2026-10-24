import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def find_git_repository_root(start_path: Path) -> Path | None:
    """向上递归查找包含 .git 的目录作为项目根目录"""
    try:
        current = start_path.resolve()
        for parent in [current] + list(current.parents):
            if (parent / ".git").exists():
                return parent
    except Exception:
        pass
    return None
