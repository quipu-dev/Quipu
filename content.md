好的，我将创建一个计划来为 `ConfigManager` 添加单元测试。

## test: 为 ConfigManager 增加单元测试

### 用户需求
为 `quipu-engine` 包中的 `ConfigManager` 类添加全面的单元测试，以验证其读取、写入和回退到默认值的逻辑是否正确。

### 评论
为 `ConfigManager` 补充单元测试是确保配置系统健壮性的重要步骤。这可以保证未来的重构不会意外破坏配置的加载、保存或嵌套设置功能，从而提高整个引擎的可靠性。

### 目标
1.  在 `tests/engine/` 目录下创建一个新的测试文件 `test_config.py`。
2.  编写测试用例，覆盖以下场景：
    *   当配置文件不存在时，能够正确返回默认值。
    *   能够正确加载已存在的 YAML 配置文件并读取其中的值。
    *   `set()` 方法能够正确设置顶层和嵌套键的值。
    *   `save()` 方法能够将内存中的配置正确地持久化到 YAML 文件。
    *   一次完整的“写入-保存-重新加载-读取”流程是正确的。

### 基本原理
我们将使用 `pytest` 的 `tmp_path` fixture 来创建一个临时的测试目录。这样可以确保测试在隔离的环境中进行，不会影响项目或本地的实际配置文件，并且在测试结束后会自动清理。通过在临时目录中创建、修改和读取 `config.yml`，我们可以精确地验证 `ConfigManager` 的所有 I/O 行为。

### 标签
#intent/tooling #flow/ready #priority/high 
#comp/engine #comp/tests
#concept/config 
#scope/dx 
#ai/instruct
#task/domain/testing #task/object/config-manager #task/action/unit-test #task/state/continue

---

### Script

#### Acts 1: 创建测试文件 `test_config.py`

我们将在 `tests/engine/` 目录下创建新的测试文件，并编写完整的测试用例。

~~~~~act
write_file
tests/engine/test_config.py
~~~~~
~~~~~python
import yaml
from pathlib import Path
from quipu.core.config import ConfigManager, DEFAULTS


def test_config_defaults_when_no_file_exists(tmp_path: Path):
    """
    测试：当配置文件不存在时，ConfigManager 应能正确返回默认值。
    """
    work_dir = tmp_path
    cm = ConfigManager(work_dir)

    # 验证 .quipu 目录被创建
    assert (work_dir / ".quipu").exists()

    # 测试获取默认值
    assert cm.get("storage.type") == "git_object"
    assert cm.get("sync.remote_name") == "origin"
    assert cm.get("sync.user_id") is None
    assert cm.get("non_existent_key", "fallback") == "fallback"


def test_config_loading_from_existing_file(tmp_path: Path):
    """
    测试：ConfigManager 能否正确加载并覆盖默认值。
    """
    work_dir = tmp_path
    config_dir = work_dir / ".quipu"
    config_dir.mkdir()
    config_file = config_dir / "config.yml"
    user_config = {
        "storage": {"type": "sqlite"},
        "sync": {"remote_name": "upstream", "user_id": "test-user"},
    }
    with open(config_file, "w") as f:
        yaml.dump(user_config, f)

    cm = ConfigManager(work_dir)

    # 测试用户自定义值
    assert cm.get("storage.type") == "sqlite"
    assert cm.get("sync.remote_name") == "upstream"
    assert cm.get("sync.user_id") == "test-user"

    # 测试未被覆盖的默认值
    assert isinstance(cm.get("sync.persistent_ignores"), list)


def test_config_set_and_save_simple_key(tmp_path: Path):
    """
    测试：设置顶层键并保存。
    """
    work_dir = tmp_path
    cm = ConfigManager(work_dir)

    cm.set("sync.user_id", "new-user-id")
    cm.save()

    # 验证文件是否被写入
    config_file = work_dir / ".quipu" / "config.yml"
    assert config_file.exists()

    with open(config_file, "r") as f:
        data = yaml.safe_load(f)

    assert data["sync"]["user_id"] == "new-user-id"


def test_config_set_and_save_nested_key(tmp_path: Path):
    """
    测试：设置一个不存在的嵌套键，并验证中间路径是否被创建。
    """
    work_dir = tmp_path
    cm = ConfigManager(work_dir)

    cm.set("new_feature.enabled", True)
    cm.set("new_feature.credentials.user", "test")
    cm.save()

    # 重新加载并验证
    cm_reloaded = ConfigManager(work_dir)
    assert cm_reloaded.get("new_feature.enabled") is True
    assert cm_reloaded.get("new_feature.credentials.user") == "test"

    # 直接读取文件验证结构
    with open(cm.config_path, "r") as f:
        data = yaml.safe_load(f)
    assert data["new_feature"]["credentials"]["user"] == "test"


def test_config_e2e_workflow(tmp_path: Path):
    """
    测试一个完整的端到端流程：加载 -> 修改 -> 保存 -> 重新加载 -> 验证。
    """
    # 1. 初始状态：创建一个带有一些自定义值的配置文件
    work_dir = tmp_path
    config_dir = work_dir / ".quipu"
    config_dir.mkdir()
    config_file = config_dir / "config.yml"
    initial_config = {"storage": {"type": "sqlite"}}
    with open(config_file, "w") as f:
        yaml.dump(initial_config, f)

    # 2. 加载并修改
    cm1 = ConfigManager(work_dir)
    assert cm1.get("storage.type") == "sqlite"
    assert cm1.get("sync.remote_name") == "origin"  # 来自默认值

    cm1.set("storage.type", "git_object")  # 修改现有值
    cm1.set("sync.user_id", "final-user")   # 添加新值
    cm1.save()

    # 3. 重新加载并验证
    cm2 = ConfigManager(work_dir)
    assert cm2.get("storage.type") == "git_object"
    assert cm2.get("sync.user_id") == "final-user"
    assert cm2.get("sync.remote_name") == "origin"  # 默认值依然存在
~~~~~

### 下一步建议
`ConfigManager` 的核心逻辑现在已经有了测试覆盖。我们可以继续推进 `Quipu Sync` 功能的开发。下一步是执行任务列表中的 **阶段 2：Git 底层接口扩展 (`quipu-engine`)**，从任务 2.1 开始，为 `GitDB` 定义新的 Ref 路径常量。
