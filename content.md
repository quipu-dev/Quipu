# fix: 修复 `ModuleNotFoundError`

## 错误分析
测试框架在收集测试文件 `tests/test_view_model.py` 时失败，报告 `ModuleNotFoundError: No module named 'quipu.cli.view_model'`。

这个错误的原因是 Python 的导入系统无法找到我们刚刚创建的 `view_model.py` 文件。尽管 `quipu/cli` 目录下已经存在其他模块，但在某些情况下（尤其是在添加新文件到已安装的 editable 包时），Python 需要明确的信号来识别一个目录是“包”。最稳定和明确的方式是添加一个 `__init__.py` 文件。

## 用户需求
解决模块导入错误，使测试能够正常运行。

## 评论
这是一个常见的环境和路径问题。通过添加空的 `__init__.py` 文件，我们将 `quipu` 和 `quipu.cli` 显式地声明为常规包 (Regular Packages)，而不是依赖隐式的命名空间包 (Namespace Packages) 行为。这使得包的结构更加健壮，更容易被包括 `pytest` 在内的各种工具正确发现。

## 目标
1.  在 `src/quipu/` 目录下创建一个空的 `__init__.py` 文件。
2.  在 `src/quipu/cli/` 目录下创建一个空的 `__init__.py` 文件。

## 基本原理
`__init__.py` 文件是 Python 用来标识一个目录为包的特殊文件。即使文件是空的，它的存在也足以让 Python 的导入机制正确地扫描并索引该目录下的所有模块。通过添加这两个文件，`from quipu.cli.view_model import GraphViewModel` 这条导入语句现在可以被正确解析了。

## 标签
#intent/fix #flow/ready #priority/critical
#comp/cli #comp/build #scope/dx
#ai/instruct
#task/domain/ui #task/object/performance #task/action/bug-fix
#task/state/continue #task/status/active

---

## Script

### Acts 1: 创建 `__init__.py` 文件以确保包的可发现性

我们创建两个空的 `__init__.py` 文件来显式定义包结构，解决模块未找到的错误。

~~~~~act
write_file src/quipu/__init__.py
~~~~~
~~~~~python

~~~~~

~~~~~act
write_file src/quipu/cli/__init__.py
~~~~~
~~~~~python

~~~~~
