## [WIP] refactor: 移除 pyquipu-bus 并更新依赖

### 用户需求
1.  物理删除 `packages/pyquipu-bus` 包。
2.  更新 `pyquipu-common` 的依赖，加入 `pyneedle-bus`。
3.  更新所有其他包（cli, engine, runtime, application, test-utils, root）的 `pyproject.toml`，移除对 `pyquipu-bus` 的依赖。

### 评论
这是一次破坏性的架构调整，正式废弃了旧的总线实现，转向 Needle 生态。操作涉及文件系统的删除和多个配置文件的修改，需要确保依赖关系的正确转移（即原先依赖 `pyquipu-bus` 的包现在应通过 `pyquipu-common` 获取总线能力）。

### 目标
1.  删除 `packages/pyquipu-bus` 目录。
2.  在 `packages/pyquipu-common/pyproject.toml` 中添加 `pyneedle-bus`。
3.  从其余 7 个 `pyproject.toml` 文件中清理 `pyquipu-bus` 相关条目。

### 基本原理
由于我们已经将资源文件和总线入口迁移到了 `pyquipu-common`，旧的包已无存在必要。清理依赖可以防止构建错误和混淆。`pyneedle-bus` 不需要作为 workspace member，而是作为外部依赖引入。

### 标签
#intent/refine #flow/ready #priority/high #comp/build #task/domain/ui #task/object/bus #task/action/cleanup #task/state/continue

---

### Script

#### Acts 1: 删除旧包

~~~~~act
run_command
~~~~~
~~~~~
rm -rf packages/pyquipu-bus
~~~~~

#### Acts 2: 更新 pyquipu-common 依赖

~~~~~act
patch_file
packages/pyquipu-common/pyproject.toml
~~~~~
~~~~~toml
dependencies = []
~~~~~
~~~~~toml
dependencies = [
    "pyneedle-bus ~= 0.1.4",
]
~~~~~

#### Acts 3: 更新各子包依赖 (移除 pyquipu-bus)

**pyquipu-runtime**
~~~~~act
patch_file
packages/pyquipu-runtime/pyproject.toml
~~~~~
~~~~~toml
dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-bus ~= 0.2.0",
    "typer >= 0.9.0"
]
~~~~~
~~~~~toml
dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-common ~= 0.1.1",
    "typer >= 0.9.0"
]
~~~~~
~~~~~act
patch_file
packages/pyquipu-runtime/pyproject.toml
~~~~~
~~~~~toml
[tool.uv.sources]
pyquipu-spec = { workspace = true }
pyquipu-common = { workspace = true }
pyquipu-bus = { workspace = true }
~~~~~
~~~~~toml
[tool.uv.sources]
pyquipu-spec = { workspace = true }
pyquipu-common = { workspace = true }
~~~~~

**pyquipu-engine**
~~~~~act
patch_file
packages/pyquipu-engine/pyproject.toml
~~~~~
~~~~~toml
dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-bus ~= 0.2.0",
    "pyyaml >= 6.0",
]
~~~~~
~~~~~toml
dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-common ~= 0.1.1",
    "pyyaml >= 6.0",
]
~~~~~
~~~~~act
patch_file
packages/pyquipu-engine/pyproject.toml
~~~~~
~~~~~toml
[tool.uv.sources]
pyquipu-spec = { workspace = true }
pyquipu-common = { workspace = true }
pyquipu-bus = { workspace = true }
~~~~~
~~~~~toml
[tool.uv.sources]
pyquipu-spec = { workspace = true }
pyquipu-common = { workspace = true }
~~~~~

**pyquipu-application**
~~~~~act
patch_file
packages/pyquipu-application/pyproject.toml
~~~~~
~~~~~toml
dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-engine ~= 0.2.1",
    "pyquipu-runtime ~= 0.2.1",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-bus ~= 0.2.0",
]
~~~~~
~~~~~toml
dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-engine ~= 0.2.1",
    "pyquipu-runtime ~= 0.2.1",
    "pyquipu-common ~= 0.1.1",
]
~~~~~
~~~~~act
patch_file
packages/pyquipu-application/pyproject.toml
~~~~~
~~~~~toml
pyquipu-runtime = { workspace = true }
pyquipu-common = { workspace = true }
pyquipu-bus = { workspace = true }
~~~~~
~~~~~toml
pyquipu-runtime = { workspace = true }
pyquipu-common = { workspace = true }
~~~~~

**pyquipu-cli**
~~~~~act
patch_file
packages/pyquipu-cli/pyproject.toml
~~~~~
~~~~~toml
dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-engine ~= 0.2.1",
    "pyquipu-runtime ~= 0.2.1",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-application ~= 0.2.1",
    "pyquipu-bus ~= 0.2.0",
    "typer >= 0.9.0",
    "textual >= 0.58.0",
]
~~~~~
~~~~~toml
dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-engine ~= 0.2.1",
    "pyquipu-runtime ~= 0.2.1",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-application ~= 0.2.1",
    "typer >= 0.9.0",
    "textual >= 0.58.0",
]
~~~~~
~~~~~act
patch_file
packages/pyquipu-cli/pyproject.toml
~~~~~
~~~~~toml
pyquipu-application = { workspace = true }
pyquipu-bus = { workspace = true }
~~~~~
~~~~~toml
pyquipu-application = { workspace = true }
~~~~~

**pyquipu-test-utils**
这里我们同时添加 `pyneedle-bus`，因为测试工具通常需要直接与总线类型交互（例如 Mock）。

~~~~~act
patch_file
packages/pyquipu-test-utils/pyproject.toml
~~~~~
~~~~~toml
dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-engine ~= 0.2.1",
    "pyquipu-bus ~= 0.2.0",
    "typer"
]
~~~~~
~~~~~toml
dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-engine ~= 0.2.1",
    "pyneedle-bus ~= 0.1.4",
    "typer"
]
~~~~~
~~~~~act
patch_file
packages/pyquipu-test-utils/pyproject.toml
~~~~~
~~~~~toml
[tool.uv.sources]
pyquipu-spec = { workspace = true }
pyquipu-engine = { workspace = true }
pyquipu-bus = { workspace = true }
~~~~~
~~~~~toml
[tool.uv.sources]
pyquipu-spec = { workspace = true }
pyquipu-engine = { workspace = true }
~~~~~

**pyquipu (meta)**
~~~~~act
patch_file
packages/pyquipu/pyproject.toml
~~~~~
~~~~~toml
dependencies = [
    "pyquipu-application ~= 0.2.1",
    "pyquipu-bus ~= 0.2.0",
    "pyquipu-cli ~= 0.2.1",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-engine ~= 0.2.1",
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-runtime ~= 0.2.1",
]
~~~~~
~~~~~toml
dependencies = [
    "pyquipu-application ~= 0.2.1",
    "pyquipu-cli ~= 0.2.1",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-engine ~= 0.2.1",
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-runtime ~= 0.2.1",
]
~~~~~

#### Acts 4: 更新根目录配置

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml
pyquipu-application = { workspace = true }
pyquipu-bus = { workspace = true }
pyquipu-cli = { workspace = true }
~~~~~
~~~~~toml
pyquipu-application = { workspace = true }
pyquipu-cli = { workspace = true }
~~~~~

### 下一步建议
依赖关系已经清理完毕。下一步是代码层面的重构：全局搜索代码库，将所有 `from quipu.bus import bus` 替换为 `from quipu.common.bus import bus`。同时，由于 `pyneedle-bus` 的 `bus` 对象 API 与旧的 `MessageBus` 有所不同（主要是 `get` 方法变为了 `render_to_string`，以及支持 `L` 指针），我们需要修复相应的调用点。
