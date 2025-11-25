# fix-install-strategy 调整安装策略

## 目标
通过仅安装子包（Sub-packages）而不安装根包（Root Package），来避免 `pip` 将子包作为普通依赖复制到 `site-packages`，从而破坏 Editable 状态和命名空间合并。

## 基本原理
根目录的 `quipu-dev` 包定义了对子包的本地文件依赖。当执行 `pip install -e .` 时，`pip` 可能会优先满足这些依赖，将其构建为 wheel 并安装到 `site-packages`，这会覆盖我们之前手动执行的 `pip install -e packages/...`。
由于 `quipu` CLI 入口点已在 `quipu-cli` 包中定义，我们实际上不需要安装根包即可拥有完整的开发环境。

## 标签
#fix #env #install-strategy

---

## Script

### Act 1: 彻底清理环境

卸载所有相关的包，并手动删除残留目录，确保从零开始。

~~~~~act
run_command
~~~~~

~~~~~bash
pip uninstall -y quipu-cli quipu-engine quipu-runtime quipu-interfaces quipu-dev
rm -rf /home/doucx/pyvenv/lib/python3.13/site-packages/quipu
rm -rf /home/doucx/pyvenv/lib/python3.13/site-packages/quipu*
~~~~~

### Act 2: 仅安装子包

以 Editable 模式安装四个核心子包。**不安装根目录**。

~~~~~act
run_command
~~~~~

~~~~~bash
pip install -e packages/quipu-interfaces -e packages/quipu-engine -e packages/quipu-runtime -e packages/quipu-cli
~~~~~

### Act 3: 验证安装与导入

运行诊断脚本。如果策略正确，`quipu.__path__` 应该包含四个 `src/quipu` 路径。

~~~~~act
run_command
~~~~~

~~~~~bash
python3 debug_quipu.py
~~~~~

### Act 4: 运行测试

~~~~~act
run_command
~~~~~

~~~~~bash
pytest
~~~~~