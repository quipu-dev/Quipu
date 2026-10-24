import subprocess
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer
from quipu.application.utils import find_git_repository_root
from quipu.common.identity import get_user_id_from_email
from quipu.engine.config import ConfigManager
from quipu.engine.git_db import GitDB

from ..config import DEFAULT_WORK_DIR
from ..logger_config import setup_logging
from .helpers import engine_context


class SyncMode(str, Enum):
    BIDIRECTIONAL = "bidirectional"
    PUSH_FORCE = "push-force"
    PUSH_ONLY = "push-only"
    PULL_PRUNE = "pull-prune"
    PULL_ONLY = "pull-only"


def register(app: typer.Typer):
    @app.command(help="与远程 Git 仓库同步 Quipu 历史记录。")
    def sync(
        ctx: typer.Context,
        work_dir: Annotated[
            Path,
            typer.Option(
                "--work-dir", "-w", help="操作执行的根目录（工作区）", file_okay=False, dir_okay=True, resolve_path=True
            ),
        ] = DEFAULT_WORK_DIR,
        remote_option: Annotated[
            str | None, typer.Option("--remote", "-r", help="Git 远程仓库的名称 (覆盖配置文件)。")
        ] = None,
        mode: Annotated[
            SyncMode,
            typer.Option(
                "--mode",
                "-m",
                help="同步模式: 'bidirectional' (默认), 'push-force', 'push-only', 'pull-prune', 'pull-only'",
                case_sensitive=False,
            ),
        ] = SyncMode.BIDIRECTIONAL,
    ):
        setup_logging()
        sync_dir = find_git_repository_root(work_dir) or work_dir
        config = ConfigManager(sync_dir)
        remote = remote_option or config.get("sync.remote_name", "origin")

        final_user_id = config.get("sync.user_id")
        if not final_user_id:
            typer.secho("🤝 首次使用 sync 功能，正在自动配置用户身份...", fg=typer.colors.BLUE, err=True)
            try:
                result = subprocess.run(
                    ["git", "config", "user.email"], cwd=sync_dir, capture_output=True, text=True, check=True
                )
                email = result.stdout.strip()
                if not email:
                    raise ValueError("Git user.email is empty.")

                final_user_id = get_user_id_from_email(email)
                config.set("sync.user_id", final_user_id)
                config.save()
                typer.secho(
                    f"✅ 已根据你的 Git 邮箱 '{email}' 生成并保存用户 ID: {final_user_id}",
                    fg=typer.colors.GREEN,
                    err=True,
                )

            except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
                typer.secho("❌ 错误：无法获取你的 Git 用户邮箱。", fg=typer.colors.RED, err=True)
                typer.secho(
                    '💡 请先运行以下命令进行设置:\n  git config --global user.email "you@example.com"',
                    fg=typer.colors.YELLOW,
                    err=True,
                )
                ctx.exit(1)

        try:
            git_db = GitDB(sync_dir)
            subscriptions = config.get("sync.subscriptions", [])
            target_ids_to_fetch = set(subscriptions)
            target_ids_to_fetch.add(final_user_id)

            typer.secho(f"⚙️  模式: {mode.value}", fg=typer.colors.BLUE, err=True)

            # --- Operation Dispatch based on Mode ---
            match mode:
                case SyncMode.BIDIRECTIONAL:
                    typer.secho("⬇️  正在拉取...", fg=typer.colors.BLUE, err=True)
                    for target_id in sorted(target_ids_to_fetch):
                        git_db.fetch_quipu_refs(remote, target_id)
                    typer.secho("🤝 正在调和...", fg=typer.colors.BLUE, err=True)
                    git_db.reconcile_local_with_remote(remote, final_user_id)
                    typer.secho("⬆️  正在推送...", fg=typer.colors.BLUE, err=True)
                    git_db.push_quipu_refs(remote, final_user_id)
                    typer.secho("\n✅ Quipu 双向同步完成。", fg=typer.colors.GREEN, err=True)

                case SyncMode.PULL_ONLY:
                    typer.secho("⬇️  正在拉取...", fg=typer.colors.BLUE, err=True)
                    for target_id in sorted(target_ids_to_fetch):
                        git_db.fetch_quipu_refs(remote, target_id)
                    typer.secho("🤝 正在调和...", fg=typer.colors.BLUE, err=True)
                    git_db.reconcile_local_with_remote(remote, final_user_id)
                    typer.secho("\n✅ Quipu 拉取同步完成。", fg=typer.colors.GREEN, err=True)

                case SyncMode.PULL_PRUNE:
                    typer.secho("⬇️  正在拉取 (带修剪)...", fg=typer.colors.BLUE, err=True)
                    for target_id in sorted(target_ids_to_fetch):
                        git_db.fetch_quipu_refs(remote, target_id)
                    typer.secho("🤝 正在调和...", fg=typer.colors.BLUE, err=True)
                    git_db.reconcile_local_with_remote(remote, final_user_id)
                    typer.secho("🗑️  正在修剪本地...", fg=typer.colors.BLUE, err=True)
                    git_db.prune_local_from_remote(remote, final_user_id)
                    typer.secho("\n✅ Quipu 拉取同步 (带修剪) 完成。", fg=typer.colors.GREEN, err=True)

                case SyncMode.PUSH_ONLY:
                    typer.secho("⬆️  正在推送...", fg=typer.colors.BLUE, err=True)
                    git_db.push_quipu_refs(remote, final_user_id, force=False)
                    typer.secho("\n✅ Quipu 推送同步完成。", fg=typer.colors.GREEN, err=True)

                case SyncMode.PUSH_FORCE:
                    typer.secho("⬆️  正在强制推送...", fg=typer.colors.BLUE, err=True)
                    git_db.push_quipu_refs(remote, final_user_id, force=True)
                    typer.secho("\n✅ Quipu 强制推送完成。", fg=typer.colors.GREEN, err=True)

            # --- 自动数据补水 ---
            # 确保远程拉取的引用立即被 SQLite 索引
            typer.secho("💧 正在执行增量数据补水...", fg=typer.colors.BLUE, err=True)
            try:
                with engine_context(work_dir):
                    pass
                typer.secho("✅ 数据同步完成。", fg=typer.colors.GREEN, err=True)
            except Exception as e:
                typer.secho(f"❌ 数据同步失败: {e}", fg=typer.colors.YELLOW, err=True)

        except RuntimeError as e:
            typer.secho(f"\n❌ 同步操作失败: {e}", fg=typer.colors.RED, err=True)
            ctx.exit(1)
