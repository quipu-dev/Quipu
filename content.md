好的，测试通过意味着我们的幂等性 CD 架构的基础设施已经就绪。

现在，我将按照 CD v2.0 规范的要求，更新门户包 `packages/pyquipu` 中的 README 文件。为了确保在 PyPI 页面上能够正确跳转，我们将所有语言切换链接替换为指向 GitHub `main` 分支的绝对 URL。

## [WIP] docs: 修正门户包 README 中的语言链接为绝对路径

### 用户需求
按照“基于主分支的幂等性持续交付 (Main-Branch Idempotent CD) v2.0”规范，将 `packages/pyquipu/README.md` 和 `packages/pyquipu/README.zh-CN.md` 中的语言切换链接修改为指向 GitHub 的绝对 URL，严禁使用相对路径。

### 评论
这是一项必要的操作。由于 PyPI 不会托管除主 README 以外的辅助 Markdown 文件，使用相对路径会导致 PyPI 页面上的语言切换链接失效（404）。使用指向 GitHub 源码仓库的绝对 URL 是 Monorepo 分发包的最佳实践。

### 目标
1.  在 `packages/pyquipu/README.md` 中添加/更新指向 GitHub 的中文版绝对链接。
2.  在 `packages/pyquipu/README.zh-CN.md` 中添加/更新指向 GitHub 的英文版绝对链接。

### 基本原理
遵循“真理单一来源 (SSoT)”原则，README 虽然存在于多个位置，但在分发单元（PyPI 包）中，它必须具备自包含的、确定性的外部引用能力。

### 标签
#intent/tune #flow/ready #priority/low
#comp/docs #scope/ux #dx
#ai/instruct
#task/domain/docs #task/object/pypi-facade #task/action/refactor
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 更新英文 README 的语言链接

我们将语言切换链接插入到标题下方，并使用绝对路径。

~~~~~act
patch_file
packages/pyquipu/README.md
~~~~~
~~~~~markdown.old
# Quipu: "Process Archaeology" for the AI Era

**Quipu is not a version control system. It is a "thought-to-reality" transcriber designed for AI, not humans, to record all its operations—successes and failures alike.**
~~~~~
~~~~~markdown.new
# Quipu: "Process Archaeology" for the AI Era

English | [中文](https://github.com/quipu-dev/pyquipu/blob/main/packages/pyquipu/README.zh-CN.md)

**Quipu is not a version control system. It is a "thought-to-reality" transcriber designed for AI, not humans, to record all its operations—successes and failures alike.**
~~~~~

#### Acts 2: 更新中文 README 的语言链接

同步更新中文版，使其链接回 GitHub 上的英文主页。

~~~~~act
patch_file
packages/pyquipu/README.zh-CN.md
~~~~~
~~~~~markdown.old
# Quipu: 面向 AI 时代的“过程考古学”

**Quipu 不是一个版本控制系统。它是一个为 AI 而非人类设计的、旨在记录其所有成功与失败操作的“思维-现实”转录机。**
~~~~~
~~~~~markdown.new
# Quipu: 面向 AI 时代的“过程考古学”

[English](https://github.com/quipu-dev/pyquipu/blob/main/packages/pyquipu/README.md) | 中文

**Quipu 不是一个版本控制系统。它是一个为 AI 而非人类设计的、旨在记录其所有成功与失败操作的“思维-现实”转录机。**
~~~~~

### 下一步建议
- **合并至 Main**: 确认修改无误后，将此变更合并至 `main` 分支。
- **触发 CD**: 合并后，由于我们之前配置的 `cd.yml` 监测到门户包的版本可能未在 PyPI 发布（或版本号未变），你可以考虑将 `packages/pyquipu/pyproject.toml` 中的版本号提升（例如 `0.1.1`）来触发第一次真实的幂等发布测试。
