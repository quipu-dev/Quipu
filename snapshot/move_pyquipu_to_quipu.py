from pathlib import Path
from stitcher.refactor.migration import MigrationSpec, Move, MoveDir


def upgrade(spec: MigrationSpec):
    # 基础路径定义
    base = Path(".").absolute()

    for prefix in base.glob('packages/pyquipu-*/src/'):
        spec.add(MoveDir(prefix / 'pyquipu', prefix / 'quipu'))
