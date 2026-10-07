import shutil
from pathlib import Path

import pytest
from quipu.acts.read import register as register_read_acts
from quipu.runtime.executor import ExecutionError, Executor
from quipu.spec.protocols.runtime import ActContext


class TestReadActs:
    @pytest.fixture(autouse=True)
    def setup_executor(self, executor: Executor):
        register_read_acts(executor)

    def test_search_python_fallback(self, executor: Executor, isolated_vault: Path, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda x: None)
        target_file = isolated_vault / "config.py"
        target_file.write_text('SECRET_KEY = "123456"', encoding="utf-8")
        (isolated_vault / "readme.md").write_text("Nothing here", encoding="utf-8")

        captured = []
        executor.data_handler = captured.append

        search_func, _, _ = executor._acts["search_files"]
        ctx = ActContext(executor)
        search_func(ctx, ["SECRET_KEY"])

        assert len(captured) == 1
        assert "config.py" in captured[0]
        assert 'SECRET_KEY = "123456"' in captured[0]

    @pytest.mark.skipif(not shutil.which("rg"), reason="Ripgrep (rg) 未安装，跳过集成测试")
    def test_search_with_ripgrep(self, executor: Executor, isolated_vault: Path):
        (isolated_vault / "main.rs").write_text('fn main() { println!("Hello Quipu"); }', encoding="utf-8")

        captured = []
        executor.data_handler = captured.append

        search_func, _, _ = executor._acts["search_files"]
        ctx = ActContext(executor)
        search_func(ctx, ["println!"])

        assert len(captured) == 1
        assert "main.rs" in captured[0]
        assert 'println!("Hello Quipu")' in captured[0]

    def test_search_scoped_path(self, executor: Executor, isolated_vault: Path, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda x: None)
        (isolated_vault / "target.txt").write_text("target_function", encoding="utf-8")
        src_dir = isolated_vault / "src"
        src_dir.mkdir()
        (src_dir / "inner.txt").write_text("target_function", encoding="utf-8")

        captured = []
        executor.data_handler = captured.append

        search_func, _, _ = executor._acts["search_files"]
        ctx = ActContext(executor)
        search_func(ctx, ["target_function", "--path", "src"])

        assert len(captured) == 1
        stdout = captured[0]
        assert str(Path("src") / "inner.txt") in stdout
        assert "target.txt" not in stdout

    def test_search_no_match(self, executor: Executor, isolated_vault: Path, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda x: None)
        (isolated_vault / "file.txt").write_text("some content", encoding="utf-8")

        captured = []
        executor.data_handler = captured.append

        search_func, _, _ = executor._acts["search_files"]
        ctx = ActContext(executor)
        search_func(ctx, ["non_existent_pattern"])

        assert len(captured) == 0

    def test_search_binary_file_resilience(self, executor: Executor, isolated_vault: Path, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda x: None)
        binary_file = isolated_vault / "data.bin"
        binary_file.write_bytes(b"\x80\x81\xff")
        search_func, _, _ = executor._acts["search_files"]
        ctx = ActContext(executor)
        try:
            search_func(ctx, ["pattern"])
        except Exception as e:
            pytest.fail(f"搜索过程因二进制文件崩溃: {e}")

    def test_search_args_error(self, executor: Executor):
        search_func, _, _ = executor._acts["search_files"]
        ctx = ActContext(executor)
        with pytest.raises(ExecutionError) as exc:
            search_func(ctx, ["pattern", "--unknown-flag"])
        assert "参数解析错误" in str(exc.value)

    def test_read_file_not_found(self, executor: Executor):
        func, _, _ = executor._acts["read_file"]
        ctx = ActContext(executor)
        with pytest.raises(ExecutionError, match="文件不存在"):
            func(ctx, ["ghost.txt"])

    def test_read_file_is_dir(self, executor: Executor, isolated_vault: Path):
        (isolated_vault / "subdir").mkdir()
        func, _, _ = executor._acts["read_file"]
        ctx = ActContext(executor)
        with pytest.raises(ExecutionError, match="这是一个目录"):
            func(ctx, ["subdir"])
