from pathlib import Path

import pytest
from quipu.acts.refactor import register as register_refactor_acts
from quipu.spec.exceptions import ExecutionError
from quipu.spec.protocols.runtime import ActContext
from quipu.runtime.executor import Executor
from needle.pointer import L


class TestRefactorActs:
    @pytest.fixture(autouse=True)
    def setup_executor(self, executor: Executor):
        register_refactor_acts(executor)

    def test_move_file_success(self, executor: Executor, isolated_vault: Path, mock_runtime_bus):
        src = isolated_vault / L.old.txt
        src.write_text("content")
        dest = isolated_vault / L.new.txt

        func, _, _ = executor._acts["move_file"]
        ctx = ActContext(executor)
        func(ctx, [L.old.txt, L.new.txt])

        assert not src.exists()
        assert dest.exists()
        assert dest.read_text() == "content"
        mock_runtime_bus.success.assert_called_with(
            L.acts.refactor.success.moved, source=L.old.txt, destination=L.new.txt
        )

    def test_move_file_src_not_found(self, executor: Executor):
        func, _, _ = executor._acts["move_file"]
        ctx = ActContext(executor)
        with pytest.raises(ExecutionError, match=L.acts.refactor.error.srcNotFound):
            func(ctx, [L.missing.txt, L.dest.txt])

    def test_move_file_permission_error(self, executor: Executor, isolated_vault: Path, monkeypatch):
        src = isolated_vault / L.locked.txt
        src.touch()
        import shutil

        def mock_move(*args):
            raise PermissionError("Access denied")

        monkeypatch.setattr(shutil, "move", mock_move)

        func, _, _ = executor._acts["move_file"]
        ctx = ActContext(executor)
        with pytest.raises(ExecutionError, match=L.acts.refactor.error.movePermission):
            func(ctx, [L.locked.txt, L.dest.txt])

    def test_delete_file_success(self, executor: Executor, isolated_vault: Path, mock_runtime_bus):
        target = isolated_vault / L.trash.txt
        target.touch()

        func, _, _ = executor._acts["delete_file"]
        ctx = ActContext(executor)
        func(ctx, [L.trash.txt])

        assert not target.exists()
        mock_runtime_bus.success.assert_called_with(L.acts.refactor.success.deleted, path=L.trash.txt)

    def test_delete_dir_success(self, executor: Executor, isolated_vault: Path, mock_runtime_bus):
        target_dir = isolated_vault / "trash_dir"
        target_dir.mkdir()
        (target_dir / L.file.txt).touch()

        func, _, _ = executor._acts["delete_file"]
        ctx = ActContext(executor)
        func(ctx, ["trash_dir"])

        assert not target_dir.exists()
        mock_runtime_bus.success.assert_called_with(L.acts.refactor.success.deleted, path="trash_dir")

    def test_delete_skipped(self, executor: Executor, mock_runtime_bus):
        func, _, _ = executor._acts["delete_file"]
        ctx = ActContext(executor)
        func(ctx, [L.non_existent.txt])

        mock_runtime_bus.warning.assert_called_with(L.acts.refactor.warning.deleteSkipped, path=L.non_existent.txt)
