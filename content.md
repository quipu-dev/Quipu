# refactor: 全局品牌重塑 Axon -> Quipu

## 目标
将项目中的所有 `Axon` 相关命名，包括代码、配置、路径和测试数据，系统性地重命名为 `Quipu`，以完成项目的品牌重塑。

## 基本原理
为了实现彻底且安全的重命名，我们将使用强大的 shell 命令 (`find` 和 `sed`) 来递归地修改所有 Python (`.py`) 文件。这种方法可以精确控制替换范围，避免手动修改引入的遗漏和错误。

替换操作将分步、按特定性进行，首先处理最独特的大小写和前缀形式 (如 `AxonNode`, `.axon`)，最后处理通用的全小写形式 (`axon`)，以防止意外的替换。最后，清理掉遗留的空目录。

## 标签
#refactor #chore #rebranding

---

## Script

### Act 1: 在所有 Python 文件中执行品牌重命名

此操作将使用 `find` 命令定位所有 `.py` 文件，然后调用 `sed` 执行一系列精确的、大小写敏感的文本替换。

~~~~~act
run_command
~~~~~

~~~~~shell
find . -type f -name "*.py" -exec sed -i \
  -e 's/AxonNode/QuipuNode/g' \
  -e 's/AxonResult/QuipuResult/g' \
  -e 's/AxonUiApp/QuipuUiApp/g' \
  -e 's/Axon Bot/Quipu Bot/g' \
  -e 's/run_axon/run_quipu/g' \
  -e 's/\.axon/\.quipu/g' \
  -e 's/refs\/axon\/history/refs\/quipu\/history/g' \
  -e 's/axon_plugin_/quipu_plugin_/g' \
  -e 's/axon@test.com/quipu@test.com/g' \
  -e 's/Hello Axon/Hello Quipu/g' \
  -e 's/name="axon"/name="quipu"/g' \
  -e 's/axon/quipu/g' {} +
~~~~~

### Act 2: 移除过时的 axon 启动器

~~~~~act
run_command
~~~~~

~~~~~shell
rm -rf axon
~~~~~