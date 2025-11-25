# fix: 修复命名空间包在开发模式下的解析问题

## 目标
通过在根 `pyproject.toml` 中正确声明命名空间包，解决在执行 `quipu` 命令时出现的 `ModuleNotFoundError: No module named 'quipu.cli'` 问题。

## 基本原理
`quipu` 包是一个跨越多个子项目的命名空间包。`setuptools` 在构建项目时，需要被明确告知这一点。当前根 `pyproject.toml` 的 `[tool.setuptools.packages.find]` 配置中缺少 `namespaces = true` 声明，导致 `setuptools` 未能将所有 `quipu` 的代码片段正确地组合起来。

通过添加此声明，`pip install -e .` 将能够正确地为所有 `quipu` 子模块创建链接，使得 Python 运行时环境能够完整地解析 `quipu` 命名空间，从而解决模块找不到的问题。

## 标签
#fix #build #chore

---

## Script

### Act 1: 为 setuptools find 指令添加 namespace 声明

此操作将向根 `pyproject.toml` 添加 `namespaces = true`，以修正包的发现和安装逻辑。

~~~~~act
replace pyproject.toml
~~~~~

~~~~~toml
[tool.setuptools.packages.find]
where = ["packages"]
include = ["quipu*"]
~~~~~

~~~~~toml
[tool.setuptools.packages.find]
where = ["packages"]
include = ["quipu*"]
namespaces = true
~~~~~