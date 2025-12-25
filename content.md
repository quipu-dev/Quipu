太好了，测试全量通过标志着我们已经完成了一个高质量的重构周期。

我们不仅修复了 `patch_file` 的歧义风险，还通过引入状态机解析器，彻底解决了复杂语言标签（如 `python.old`）的识别问题。这显著提升了 Quipu 运行时的健壮性和可预测性。

我将生成最终的 `[COMMIT]` 计划，将这些改进正式提交。

## [COMMIT] refactor(runtime): 增强 patch 安全性并重构解析器为状态机

### 用户需求
将近期对 `patch_file` 的唯一性检查逻辑、状态机解析器的重构以及相关的测试套件更新合并并提交到版本控制系统中。

### 评论
这次重构解决了两个核心痛点：一是防止了静默错误修改（patch 歧义），二是极大地增强了指令解析的灵活性。采用状态机替代正则是一个明智的架构决定，它为未来支持更复杂的 Markdown 扩展奠定了基础。

### 目标
1.  提交对 `packages/quipu-runtime/src/pyquipu/acts/basic.py` 的修改（补丁唯一性检查）。
2.  提交对 `packages/quipu-runtime/src/pyquipu/runtime/parser.py` 的重构（状态机解析器）。
3.  提交对 `tests/runtime/conftest.py` 的配置优化（消除 pytest 警告）。
4.  提交新增的测试文件：
    *   `tests/runtime/acts/test_patch_ambiguity.py`
    *   `tests/runtime/test_parser_robustness.py`

### 基本原理
按照 TDD 流程，我们已经完成了“红-绿-重构”的完整循环。现在通过一个逻辑原子提交，将这些变更固化。提交信息将详细描述这些改进对系统稳定性的贡献。

### 标签
#intent/refine #flow/ready #priority/medium #comp/runtime #comp/tests #concept/parser #concept/executor #scope/core #ai/instruct #task/domain/runtime #task/object/patch-and-parser #task/action/refactor #task/state/end #task/status/completed

---
### Script

#### Acts 1: 提交代码变更

我们将所有涉及的修改添加到暂存区，并创建一个详尽的提交记录。

~~~~~act
git_add
packages/quipu-runtime/src/pyquipu/acts/basic.py
packages/quipu-runtime/src/pyquipu/runtime/parser.py
tests/runtime/conftest.py
tests/runtime/acts/test_patch_ambiguity.py
tests/runtime/test_parser_robustness.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(runtime): improve patch safety and rewrite parser as state machine

This commit introduces two major improvements to the quipu-runtime:

1. Patch Safety: The `patch_file` act now enforces uniqueness. It checks the number of occurrences of the target string before applying changes. If the content is missing or ambiguous (multiple matches), it fails with a descriptive error instead of silently modifying the first match.

2. Robust Parsing: Replaced the fragile `RegexBlockParser` with a line-based `StateBlockParser`. The new parser:
    - Supports arbitrary language tags, fixing issues with tags like 'python.old' or 'c++'.
    - Handles whitespace within fences according to CommonMark spirit.
    - Accurately preserves all internal indentation and whitespace, ensuring byte-perfect extraction for `patch_file` operations.

Additionally, added a comprehensive test suite covering patch ambiguity and parser edge cases, and cleaned up pytest configuration warnings.
~~~~~

### 下一步建议
- **代码审查**: 尽管测试已通过，但建议手动查看一下 `StateBlockParser` 的实现，确保它在处理极大文件时的性能符合预期。
- **扩展 Act**: 现在解析器已经可以识别任意语言标签，我们可以考虑在未来引入根据标签（如 `python` vs `shell`）进行语法检查的插件。
