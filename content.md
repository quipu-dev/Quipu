Excellent. The script has confirmed that all critical errors (missing and duplicate keys) have been resolved.

Now, we are left with the "Unused keys" warning. Your instinct to "add these strings" is understandable, but let's analyze the situation more closely. The script is telling us that these keys are defined in our JSON files but it couldn't find them being used in the code.

However, as I mentioned previously, this is very likely a **false positive**. Our static analysis script is simple and has limitations.

The script reports these keys as "unused" because it can only detect direct, literal string usage like `bus.success("my.key.id")`. It cannot trace keys that are passed through variables or returned from functions.

A very common pattern in our codebase is for application logic to return a `QuipuResult` object, which contains the message ID:
```python
# In pyquipu/application/controller.py
return QuipuResult(success=True, exit_code=0, message="run.success")
```
Then, the CLI entry point (`run.py`) takes this result and passes the message ID to the bus:
```python
# In pyquipu/cli/commands/run.py
result = run_quipu(...)
if result.message:
    bus.success(result.message, **kwargs) # <-- The script cannot see this link!
```
The script sees `bus.success(result.message)` and doesn't know that `result.message` contains the string `"run.success"`. Therefore, it incorrectly flags `"run.success"` as unused.

The correct solution is not to modify the application code, but to **make our analysis script smarter**.

## [WIP] chore: Improve localization script to reduce false positives

### 用户需求

The user wants to resolve the "Unused keys" warnings reported by the `check_locales.py` script. The goal is to have a clean, error-free output from the analysis tool.

### 评论

Fixing this is a significant improvement to our developer experience (DX). A noisy tool with many false positives is quickly ignored. By making the script more intelligent and context-aware, we increase its reliability and ensure that when it does report a warning, it's a legitimate issue that needs attention.

### 目标

1.  Modify `scripts/check_locales.py` to be more intelligent.
2.  Extend the `CodeVisitor` class to also find keys used in `QuipuResult(message="...")` constructor calls.
3.  This will correctly identify many of the flagged keys as "used," dramatically reducing the number of false positives.

### 基本原理

We will enhance our `ast.NodeVisitor` to recognize project-specific patterns. By teaching the script to look for the `QuipuResult` constructor and extract the string literal from its `message` keyword argument, we make the static analysis more powerful and accurate for our specific codebase. This is a pragmatic way to improve the tool's effectiveness.

### 标签

#intent/tooling #flow/ready #priority/medium #comp/build #scope/dx #ai/brainstorm #task/domain/testing #task/object/localization-checker #task/action/refine #task/state/continue

---

### Script

#### Acts 1: 增强脚本的键提取逻辑

我们将修改 `check_locales.py` 中的 `CodeVisitor`，使其能够识别 `QuipuResult` 中的 `message` 参数，从而更准确地追踪被使用的本地化键。

~~~~~act
patch_file
scripts/check_locales.py
~~~~~
~~~~~
    def visit_Call(self, node: ast.Call):
        # We are looking for calls of the form: bus.method("key", ...)
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "bus"
            and node.func.attr in BUS_METHODS
        ):
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                key = node.args[0].value
                self.keys.add(key)

        self.generic_visit(node)
~~~~~
~~~~~
    def visit_Call(self, node: ast.Call):
        # Pattern 1: bus.method("key.id", ...)
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "bus"
            and node.func.attr in BUS_METHODS
        ):
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                key = node.args[0].value
                self.keys.add(key)

        # Pattern 2: QuipuResult(message="key.id", ...)
        elif isinstance(node.func, ast.Name) and node.func.id == "QuipuResult":
            for keyword in node.keywords:
                if keyword.arg == "message" and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
                    key = keyword.value.value
                    self.keys.add(key)
                    break # Found it, no need to check other keywords

        self.generic_visit(node)
~~~~~

### 下一步建议

现在脚本已经变得更加智能了。

1.  **再次运行检查脚本**: 请再次执行 `python scripts/check_locales.py`。这次的输出应该会大大减少 "Unused keys" 的数量。
2.  **评估剩余项**: 审查更新后的、更短的未使用键列表。如果还有剩余的，它们现在更有可能是真正未使用的键，我们可以安全地进行清理。
3.  **提交变更**: 一旦脚本报告完全干净（或我们处理了所有剩余的真实问题），我们就可以创建一个 `[COMMIT]` 计划来提交所有这些改进。
