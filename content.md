# fix: 修复因 Summarizer 引入导致的测试解包错误

## 用户需求
在引入可插拔 Summarizer 后，`Executor._acts` 的存储结构从 `(func, mode)` 变成了 `(func, mode, summarizer)`。
现有的单元测试代码中，大量使用了 `func, _ = executor._acts[...]` 这种解包方式，导致 `ValueError: too many values to unpack`。
同时，部分集成测试依赖于旧的摘要格式 (直接使用 Act 文本)，现在因为有了 Summarizer，摘要变成了更语义化的格式 (如 "Write: a.txt")，导致断言失败。
需要修复这些测试以适应新的架构。

## 评论
这是重构后的标准清理工作。虽然破坏了测试，但新的摘要机制本身工作正常（从断言失败的 message 中可以看到生成了新的摘要）。

## 目标
1.  修正所有测试文件中对 `executor._acts` 的错误解包。
2.  更新集成测试中的断言，使其匹配新的摘要格式。

## 基本原理
将 `func, _ = ...` 替换为 `func, *args = ...` 或 `func, _, _ = ...` 以兼容 3 元组。
更新字符串断言以匹配 `_summarize_write` 等函数生成的格式。

## 标签
#comp/tests #scope/dx #fix

---

## Script

### Acts 1: 修复 test_check.py

~~~~~act
replace tests/test_check.py
~~~~~

~~~~~python
    def test_check_files_exist_success(self, executor: Executor, isolated_vault: Path):
        (isolated_vault / "config.json").touch()
        (isolated_vault / "src").mkdir()
        (isolated_vault / "src/main.py").touch()
        
        file_list = "config.json\nsrc/main.py"
        func, _ = executor._acts['check_files_exist']
        ctx = ActContext(executor)
        func(ctx, [file_list]) # No exception should be raised

    def test_check_files_exist_fail(self, executor: Executor, isolated_vault: Path):
        (isolated_vault / "exists.txt").touch()
        file_list = "exists.txt\nmissing.txt"
        
        with pytest.raises(ExecutionError) as excinfo:
            func, _ = executor._acts['check_files_exist']
            ctx = ActContext(executor)
            func(ctx, [file_list])
        
        msg = str(excinfo.value)
        assert "missing.txt" in msg
        assert "exists.txt" not in msg

    def test_check_cwd_match_success(self, executor: Executor, isolated_vault: Path):
        real_path = str(isolated_vault.resolve())
        func, _ = executor._acts['check_cwd_match']
        ctx = ActContext(executor)
        func(ctx, [real_path]) # No exception should be raised

    def test_check_cwd_match_fail(self, executor: Executor):
        wrong_path = "/this/path/does/not/exist"
        
        with pytest.raises(ExecutionError) as excinfo:
            func, _ = executor._acts['check_cwd_match']
            ctx = ActContext(executor)
            func(ctx, [wrong_path])
~~~~~

~~~~~python
    def test_check_files_exist_success(self, executor: Executor, isolated_vault: Path):
        (isolated_vault / "config.json").touch()
        (isolated_vault / "src").mkdir()
        (isolated_vault / "src/main.py").touch()
        
        file_list = "config.json\nsrc/main.py"
        func, _, _ = executor._acts['check_files_exist']
        ctx = ActContext(executor)
        func(ctx, [file_list]) # No exception should be raised

    def test_check_files_exist_fail(self, executor: Executor, isolated_vault: Path):
        (isolated_vault / "exists.txt").touch()
        file_list = "exists.txt\nmissing.txt"
        
        with pytest.raises(ExecutionError) as excinfo:
            func, _, _ = executor._acts['check_files_exist']
            ctx = ActContext(executor)
            func(ctx, [file_list])
        
        msg = str(excinfo.value)
        assert "missing.txt" in msg
        assert "exists.txt" not in msg

    def test_check_cwd_match_success(self, executor: Executor, isolated_vault: Path):
        real_path = str(isolated_vault.resolve())
        func, _, _ = executor._acts['check_cwd_match']
        ctx = ActContext(executor)
        func(ctx, [real_path]) # No exception should be raised

    def test_check_cwd_match_fail(self, executor: Executor):
        wrong_path = "/this/path/does/not/exist"
        
        with pytest.raises(ExecutionError) as excinfo:
            func, _, _ = executor._acts['check_cwd_match']
            ctx = ActContext(executor)
            func(ctx, [wrong_path])
~~~~~

### Acts 2: 修复 test_ops.py

~~~~~act
replace tests/test_ops.py
~~~~~

~~~~~python
    def test_write_file(self, executor: Executor, isolated_vault: Path):
        contexts = ["docs/readme.md", "# Hello"]
        write_func, _ = executor._acts['write_file']
        ctx = ActContext(executor)
        write_func(ctx, contexts)
        
        expected_file = isolated_vault / "docs/readme.md"
        assert expected_file.exists()
        assert expected_file.read_text(encoding='utf-8') == "# Hello"

    def test_replace_text(self, executor: Executor, isolated_vault: Path):
        f = isolated_vault / "main.py"
        f.write_text('print("Hello World")', encoding='utf-8')
        
        replace_func, _ = executor._acts['replace']
        ctx = ActContext(executor)
        replace_func(ctx, ["main.py", 'print("Hello World")', 'print("Hello AI")'])
        
        assert f.read_text(encoding='utf-8') == 'print("Hello AI")'

    def test_replace_fail_not_found(self, executor: Executor, isolated_vault: Path):
        f = isolated_vault / "wrong.txt"
        f.write_text("AAA", encoding='utf-8')
        
        replace_func, _ = executor._acts['replace']
        ctx = ActContext(executor)
        
        with pytest.raises(ExecutionError) as excinfo:
            replace_func(ctx, ["wrong.txt", "BBB", "CCC"])
        
        assert "未找到指定的旧文本" in str(excinfo.value)

    def test_append_file(self, executor: Executor, isolated_vault: Path):
        f = isolated_vault / "log.txt"
        f.write_text("Line 1\n", encoding='utf-8')
        
        append_func, _ = executor._acts['append_file']
        ctx = ActContext(executor)
        append_func(ctx, ["log.txt", "Line 2"])
        
        assert f.read_text(encoding='utf-8') == "Line 1\nLine 2"

    def test_append_fail_not_found(self, executor: Executor):
        append_func, _ = executor._acts['append_file']
        ctx = ActContext(executor)
        
        with pytest.raises(ExecutionError) as excinfo:
            append_func(ctx, ["ghost.txt", "content"])
~~~~~

~~~~~python
    def test_write_file(self, executor: Executor, isolated_vault: Path):
        contexts = ["docs/readme.md", "# Hello"]
        write_func, _, _ = executor._acts['write_file']
        ctx = ActContext(executor)
        write_func(ctx, contexts)
        
        expected_file = isolated_vault / "docs/readme.md"
        assert expected_file.exists()
        assert expected_file.read_text(encoding='utf-8') == "# Hello"

    def test_replace_text(self, executor: Executor, isolated_vault: Path):
        f = isolated_vault / "main.py"
        f.write_text('print("Hello World")', encoding='utf-8')
        
        replace_func, _, _ = executor._acts['replace']
        ctx = ActContext(executor)
        replace_func(ctx, ["main.py", 'print("Hello World")', 'print("Hello AI")'])
        
        assert f.read_text(encoding='utf-8') == 'print("Hello AI")'

    def test_replace_fail_not_found(self, executor: Executor, isolated_vault: Path):
        f = isolated_vault / "wrong.txt"
        f.write_text("AAA", encoding='utf-8')
        
        replace_func, _, _ = executor._acts['replace']
        ctx = ActContext(executor)
        
        with pytest.raises(ExecutionError) as excinfo:
            replace_func(ctx, ["wrong.txt", "BBB", "CCC"])
        
        assert "未找到指定的旧文本" in str(excinfo.value)

    def test_append_file(self, executor: Executor, isolated_vault: Path):
        f = isolated_vault / "log.txt"
        f.write_text("Line 1\n", encoding='utf-8')
        
        append_func, _, _ = executor._acts['append_file']
        ctx = ActContext(executor)
        append_func(ctx, ["log.txt", "Line 2"])
        
        assert f.read_text(encoding='utf-8') == "Line 1\nLine 2"

    def test_append_fail_not_found(self, executor: Executor):
        append_func, _, _ = executor._acts['append_file']
        ctx = ActContext(executor)
        
        with pytest.raises(ExecutionError) as excinfo:
            append_func(ctx, ["ghost.txt", "content"])
~~~~~

### Acts 3: 修复 test_read.py

~~~~~act
replace tests/test_read.py
~~~~~

~~~~~python
    def test_search_python_fallback(self, executor: Executor, isolated_vault: Path, caplog, capsys, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda x: None)
        target_file = isolated_vault / "config.py"
        target_file.write_text('SECRET_KEY = "123456"', encoding='utf-8')
        (isolated_vault / "readme.md").write_text("Nothing here", encoding='utf-8')

        caplog.set_level(logging.INFO)
        search_func, _ = executor._acts['search_files']
        ctx = ActContext(executor)
        search_func(ctx, ["SECRET_KEY"])

        assert "Using Python native search" in caplog.text
        captured = capsys.readouterr()
        assert "config.py" in captured.out
        assert 'SECRET_KEY = "123456"' in captured.out

    @pytest.mark.skipif(not shutil.which("rg"), reason="Ripgrep (rg) 未安装，跳过集成测试")
    def test_search_with_ripgrep(self, executor: Executor, isolated_vault: Path, caplog, capsys):
        (isolated_vault / "main.rs").write_text('fn main() { println!("Hello Quipu"); }', encoding='utf-8')

        caplog.set_level(logging.INFO)
        search_func, _ = executor._acts['search_files']
        ctx = ActContext(executor)
        search_func(ctx, ['println!'])

        assert "Using 'rg' (ripgrep)" in caplog.text
        captured = capsys.readouterr()
        assert "main.rs" in captured.out
        assert 'println!("Hello Quipu")' in captured.out

    def test_search_scoped_path(self, executor: Executor, isolated_vault: Path, caplog, capsys, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda x: None)
        (isolated_vault / "target.txt").write_text("target_function", encoding='utf-8')
        src_dir = isolated_vault / "src"
        src_dir.mkdir()
        (src_dir / "inner.txt").write_text("target_function", encoding='utf-8')

        caplog.set_level(logging.INFO)
        search_func, _ = executor._acts['search_files']
        ctx = ActContext(executor)
        search_func(ctx, ["target_function", "--path", "src"])

        captured = capsys.readouterr()
        stdout = captured.out
        
        # After the fix, the path should be relative to the root
        assert str(Path("src") / "inner.txt") in stdout
        assert str(isolated_vault / "target.txt") not in stdout
        assert "target.txt:1:target_function" not in stdout

    def test_search_no_match(self, executor: Executor, isolated_vault: Path, caplog, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda x: None)
        (isolated_vault / "file.txt").write_text("some content", encoding='utf-8')
        caplog.set_level(logging.INFO)
        search_func, _ = executor._acts['search_files']
        ctx = ActContext(executor)
        search_func(ctx, ["non_existent_pattern"])
        assert "No matches found" in caplog.text

    def test_search_binary_file_resilience(self, executor: Executor, isolated_vault: Path, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda x: None)
        binary_file = isolated_vault / "data.bin"
        binary_file.write_bytes(b'\x80\x81\xff')
        search_func, _ = executor._acts['search_files']
        ctx = ActContext(executor)
        try:
            search_func(ctx, ["pattern"])
        except Exception as e:
            pytest.fail(f"搜索过程因二进制文件崩溃: {e}")

    def test_search_args_error(self, executor: Executor):
        search_func, _ = executor._acts['search_files']
        ctx = ActContext(executor)
        with pytest.raises(ExecutionError) as exc:
            search_func(ctx, ["pattern", "--unknown-flag"])
~~~~~

~~~~~python
    def test_search_python_fallback(self, executor: Executor, isolated_vault: Path, caplog, capsys, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda x: None)
        target_file = isolated_vault / "config.py"
        target_file.write_text('SECRET_KEY = "123456"', encoding='utf-8')
        (isolated_vault / "readme.md").write_text("Nothing here", encoding='utf-8')

        caplog.set_level(logging.INFO)
        search_func, _, _ = executor._acts['search_files']
        ctx = ActContext(executor)
        search_func(ctx, ["SECRET_KEY"])

        assert "Using Python native search" in caplog.text
        captured = capsys.readouterr()
        assert "config.py" in captured.out
        assert 'SECRET_KEY = "123456"' in captured.out

    @pytest.mark.skipif(not shutil.which("rg"), reason="Ripgrep (rg) 未安装，跳过集成测试")
    def test_search_with_ripgrep(self, executor: Executor, isolated_vault: Path, caplog, capsys):
        (isolated_vault / "main.rs").write_text('fn main() { println!("Hello Quipu"); }', encoding='utf-8')

        caplog.set_level(logging.INFO)
        search_func, _, _ = executor._acts['search_files']
        ctx = ActContext(executor)
        search_func(ctx, ['println!'])

        assert "Using 'rg' (ripgrep)" in caplog.text
        captured = capsys.readouterr()
        assert "main.rs" in captured.out
        assert 'println!("Hello Quipu")' in captured.out

    def test_search_scoped_path(self, executor: Executor, isolated_vault: Path, caplog, capsys, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda x: None)
        (isolated_vault / "target.txt").write_text("target_function", encoding='utf-8')
        src_dir = isolated_vault / "src"
        src_dir.mkdir()
        (src_dir / "inner.txt").write_text("target_function", encoding='utf-8')

        caplog.set_level(logging.INFO)
        search_func, _, _ = executor._acts['search_files']
        ctx = ActContext(executor)
        search_func(ctx, ["target_function", "--path", "src"])

        captured = capsys.readouterr()
        stdout = captured.out
        
        # After the fix, the path should be relative to the root
        assert str(Path("src") / "inner.txt") in stdout
        assert str(isolated_vault / "target.txt") not in stdout
        assert "target.txt:1:target_function" not in stdout

    def test_search_no_match(self, executor: Executor, isolated_vault: Path, caplog, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda x: None)
        (isolated_vault / "file.txt").write_text("some content", encoding='utf-8')
        caplog.set_level(logging.INFO)
        search_func, _, _ = executor._acts['search_files']
        ctx = ActContext(executor)
        search_func(ctx, ["non_existent_pattern"])
        assert "No matches found" in caplog.text

    def test_search_binary_file_resilience(self, executor: Executor, isolated_vault: Path, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda x: None)
        binary_file = isolated_vault / "data.bin"
        binary_file.write_bytes(b'\x80\x81\xff')
        search_func, _, _ = executor._acts['search_files']
        ctx = ActContext(executor)
        try:
            search_func(ctx, ["pattern"])
        except Exception as e:
            pytest.fail(f"搜索过程因二进制文件崩溃: {e}")

    def test_search_args_error(self, executor: Executor):
        search_func, _, _ = executor._acts['search_files']
        ctx = ActContext(executor)
        with pytest.raises(ExecutionError) as exc:
            search_func(ctx, ["pattern", "--unknown-flag"])
~~~~~

### Acts 4: 修复 test_git.py

~~~~~act
replace tests/test_git.py
~~~~~

~~~~~python
    @pytest.fixture(autouse=True)
    def setup_git_env(self, executor: Executor, isolated_vault: Path):
        """为测试环境自动注册 Git Acts 并进行 git init"""
        register_git_acts(executor)
        
        # 执行初始化
        func, _ = executor._acts['git_init']
        func(executor, [])
        
        # 配置测试用的 user，防止 CI/Test 环境报错
        subprocess.run(["git", "config", "user.email", "quipu@test.com"], cwd=isolated_vault, check=True)
        subprocess.run(["git", "config", "user.name", "Quipu Bot"], cwd=isolated_vault, check=True)

    def test_git_workflow(self, executor: Executor, isolated_vault: Path):
        # 1. 创建文件
        target_file = isolated_vault / "README.md"
        target_file.write_text("# Test Repo", encoding="utf-8")
        
        # 2. Git Add
        git_add, _ = executor._acts['git_add']
        git_add(executor, ["README.md"])
        
        # 验证状态 (porcelain 输出 ?? 代表未追踪，A 代表已添加)
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=isolated_vault, text=True)
        assert "A  README.md" in status
        
        # 3. Git Commit
        git_commit, _ = executor._acts['git_commit']
        git_commit(executor, ["Initial commit"])
        
        # 验证提交日志
        log = subprocess.check_output(["git", "log", "--oneline"], cwd=isolated_vault, text=True)
        assert "Initial commit" in log

    # This test is obsolete after redirecting git_status output to stdout
    # and has been removed. The behavior is now correctly tested by
    # test_git_status_output_stream.

    def test_git_init_idempotent(self, executor: Executor, caplog):
        # setup_git_env 已经 init 过了，再次 init 应该提示跳过
        import logging
        caplog.set_level(logging.INFO)
        
        func, _ = executor._acts['git_init']
        func(executor, [])
        assert "Git 仓库已存在" in caplog.text
~~~~~

~~~~~python
    @pytest.fixture(autouse=True)
    def setup_git_env(self, executor: Executor, isolated_vault: Path):
        """为测试环境自动注册 Git Acts 并进行 git init"""
        register_git_acts(executor)
        
        # 执行初始化
        func, _, _ = executor._acts['git_init']
        func(executor, [])
        
        # 配置测试用的 user，防止 CI/Test 环境报错
        subprocess.run(["git", "config", "user.email", "quipu@test.com"], cwd=isolated_vault, check=True)
        subprocess.run(["git", "config", "user.name", "Quipu Bot"], cwd=isolated_vault, check=True)

    def test_git_workflow(self, executor: Executor, isolated_vault: Path):
        # 1. 创建文件
        target_file = isolated_vault / "README.md"
        target_file.write_text("# Test Repo", encoding="utf-8")
        
        # 2. Git Add
        git_add, _, _ = executor._acts['git_add']
        git_add(executor, ["README.md"])
        
        # 验证状态 (porcelain 输出 ?? 代表未追踪，A 代表已添加)
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=isolated_vault, text=True)
        assert "A  README.md" in status
        
        # 3. Git Commit
        git_commit, _, _ = executor._acts['git_commit']
        git_commit(executor, ["Initial commit"])
        
        # 验证提交日志
        log = subprocess.check_output(["git", "log", "--oneline"], cwd=isolated_vault, text=True)
        assert "Initial commit" in log

    # This test is obsolete after redirecting git_status output to stdout
    # and has been removed. The behavior is now correctly tested by
    # test_git_status_output_stream.

    def test_git_init_idempotent(self, executor: Executor, caplog):
        # setup_git_env 已经 init 过了，再次 init 应该提示跳过
        import logging
        caplog.set_level(logging.INFO)
        
        func, _, _ = executor._acts['git_init']
        func(executor, [])
        assert "Git 仓库已存在" in caplog.text
~~~~~

### Acts 5: 修复 test_storage_integration.py 中的断言

~~~~~act
replace tests/test_storage_integration.py
~~~~~

~~~~~python
        # 3. Use `log` to check history
        res_log = runner.invoke(app, ["log", "-w", str(git_workspace)])
        assert res_log.exit_code == 0
        assert "add b.txt" in res_log.stderr  # Summary of the save message
        assert "write_file a.txt" in res_log.stderr # Summary of the plan
        
        # 4. Use `find` and `checkout` to go back to state A
~~~~~

~~~~~python
        # 3. Use `log` to check history
        res_log = runner.invoke(app, ["log", "-w", str(git_workspace)])
        assert res_log.exit_code == 0
        assert "add b.txt" in res_log.stderr  # Summary of the save message
        assert "Write: a.txt" in res_log.stderr # Summary of the plan (Updated format)
        
        # 4. Use `find` and `checkout` to go back to state A
~~~~~

~~~~~act
replace tests/test_storage_integration.py
~~~~~

~~~~~python
    def test_find_cli_by_type(self, runner, populated_workspace):
        result = runner.invoke(app, ["find", "--type", "plan", "-w", str(populated_workspace)])
        assert result.exit_code == 0
        assert "[PLAN]" in result.stderr
        assert "[CAPTURE]" not in result.stderr
        assert "write_file a.txt" in result.stderr

    def test_find_cli_by_summary(self, runner, populated_workspace):
~~~~~

~~~~~python
    def test_find_cli_by_type(self, runner, populated_workspace):
        result = runner.invoke(app, ["find", "--type", "plan", "-w", str(populated_workspace)])
        assert result.exit_code == 0
        assert "[PLAN]" in result.stderr
        assert "[CAPTURE]" not in result.stderr
        assert "Write: a.txt" in result.stderr

    def test_find_cli_by_summary(self, runner, populated_workspace):
~~~~~
