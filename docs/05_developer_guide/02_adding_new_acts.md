# 🔌 开发自定义 Act

Quipu 支持插件系统。你可以通过添加 `.py` 文件来扩展指令集。

## 插件加载路径

Quipu 按以下优先级顺序加载插件 (高优先级覆盖低优先级):

1.  **项目插件 (Project)**: `PROJECT_ROOT/.quipu/acts/`
    *   最高优先级。定义项目专属、应由团队共享的指令。Quipu 会从当前目录向上查找 `.git` 来确定项目根目录。
2.  **环境变量插件 (Env)**: `$AXON_EXTRA_ACTS_DIR`
    *   用于指定公司内部共享的插件库等。
3.  **用户全局插件 (User)**: `~/.quipu/acts/`
    *   最低优先级。用于存放您个人的、跨项目通用的自定义指令。

## 插件加载路径

Quipu 按以下优先级顺序加载插件 (高优先级覆盖低优先级):

1.  **项目插件 (Project)**: `PROJECT_ROOT/.quipu/acts/`
    *   最高优先级。定义项目专属、应由团队共享的指令。Quipu 会从当前目录向上查找 `.git` 来确定项目根目录。
2.  **环境变量插件 (Env)**: `$AXON_EXTRA_ACTS_DIR`
    *   用于指定公司内部共享的插件库等。
3.  **用户全局插件 (User)**: `~/.quipu/acts/`
    *   最低优先级。用于存放您个人的、跨项目通用的自定义指令。

## 编写规范

创建一个 Python 文件（例如 `my_plugin.py`），并实现 `register` 函数。

```python
import logging
from typing import List
from core.types import ActContext, Executor # Executor for register, ActContext for the act

logger = logging.getLogger(__name__)

def register(executor: Executor):
    """注册插件入口"""
    # 参数模式可选: "hybrid", "exclusive", "block_only"
    executor.register("my_hello", _my_hello, arg_mode="hybrid")

def _my_hello(ctx: ActContext, args: List[str]):
    """
    Act: my_hello
    Args: [name]
    说明: 一个简单的问候插件，演示新的 ActContext API。
    """
    if not args:
        name = "World"
    else:
        name = args[0]
        
    # 使用 logger 记录执行信息 (到 stderr)
    logger.info(f"Saying hello from project: {ctx.root_dir.name}")
    
    # 使用 print 输出结果数据 (到 stdout)
    print(f"Hello, {name}!")

    # 如果需要，可以这样安全地抛出错误
    # if name == "error":
    #     ctx.fail("Invalid name provided.")
```

## 测试插件

在 Markdown 中即可直接调用：

````markdown
~~~act
my_hello QuipuUser
~~~
````