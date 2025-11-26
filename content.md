# fix: 修复 NameError 并统一测试代码块风格

## 用户需求
你在执行上一个计划后，`pytest` 在收集测试用例阶段因 `NameError: name 'Any' is not defined` 错误而中断。同时，你希望将测试文件中用于定义 plan 内容的 `~~~` 围栏全部统一为 ````。

## 评论
这是一个典型的依赖导入错误，很容易修复。统一测试文件中的代码块风格可以提高代码库的一致性，便于后续的自动化处理和阅读。将这两个任务合并在一次提交中是高效的。

## 目标
1.  在 `packages/quipu-engine/src/quipu/core/state_machine.py` 文件中添加对 `Any` 的导入，解决 `NameError`。
2.  修改 `tests/test_isolation.py`, `tests/test_root_invariance.py`, 和 `verify_sandbox.py` 三个文件，将其中定义的 plan 字符串中的 `~~~` 替换为 ````。

## 基本原理
1.  **修复 `NameError`**: Python 的类型提示需要在运行时能够找到对应的类型定义。通过 `from typing import Any` 即可解决此问题。
2.  **统一风格**: 使用 `replace` 指令，对目标文件中的特定多行字符串进行精确替换，以确保风格的统一。

## 标签
#intent/fix #intent/tune #flow/ready #priority/critical 
#comp/engine #comp/tests 
#scope/dx 
#ai/instruct 

---

## Script

### Acts 1: 修复 `NameError`

在 `state_machine.py` 中导入 `Any` 类型。

````act
replace packages/quipu-engine/src/quipu/core/state_machine.py
````
````python
from typing import Dict, Optional, List, Tuple
````
````python
from typing import Dict, Optional, List, Tuple, Any
````

### Acts 2: 统一测试文件中的指令块风格

将三个文件中使用 `~~~` 的 plan 定义字符串替换为使用 ````。

````act
replace tests/test_isolation.py
````
````python
        plan_content = """
~~~act
write_file result.txt
~~~
~~~content
isolation test
~~~
"""
````
````python
        plan_content = """
```act
write_file result.txt
```
```content
isolation test
```
"""
````

````act
replace tests/test_root_invariance.py
````
````python
    plan_content = """
~~~act
write_file
~~~
~~~path
result.txt
~~~
~~~content
Success from subdir
~~~
"""
````
````python
    plan_content = """
```act
write_file
```
```path
result.txt
```
```content
Success from subdir
```
"""
````

````act
replace verify_sandbox.py
````
````python
    plan_content = """
~~~act
write_file
~~~
~~~path
hello.txt
~~~
~~~content
Hello from Sandbox
~~~
"""
````
````python
    plan_content = """
```act
write_file
```
```path
hello.txt
```
```content
Hello from Sandbox
```
"""
````
