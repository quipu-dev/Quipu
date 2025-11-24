# 💻 CLI 命令参考

Quipu 的命令行界面设计得简洁直观。所有命令的入口均为 `quipu`。

## `run` - 执行脚本

执行 Markdown 文件中的指令。

```bash
quipu run [FILE] [OPTIONS]
```

*   `FILE`: (可选) 要执行的 Markdown 文件路径。如果不提供且没有管道输入，默认寻找 `o.md`。
*   `--work-dir, -w`: 指定工作区根目录。默认为当前目录。
*   `--yolo, -y`: **You Only Look Once**。跳过所有交互式确认，直接执行。
*   `--parser, -p`: 指定解析器 (`auto`, `backtick`, `tilde`)。默认为 `auto`。
*   `--list-acts, -l`: 列出所有可用的 Act 指令。

**示例**:```bash
# 管道模式：将 LLM 的输出直接喂给 Quipu
llm "Refactor code" | quipu run -y
```

## `log` - 查看历史

以列表形式显示 Quipu 的操作历史。

```bash
quipu log [OPTIONS]
```

*   `--work-dir, -w`: 指定工作区。

输出将显示时间戳、节点类型（Plan/Capture）、Hash 前缀以及摘要。

## `checkout` - 时间旅行

将工作区重置到指定的历史状态。

```bash
quipu checkout <HASH_PREFIX> [OPTIONS]
```

*   `<HASH_PREFIX>`: 目标状态 Hash 的前几位（从 `log` 或 `ui` 命令获取）。
*   `--force, -f`: 强制重置，不询问确认。

**安全机制**: 如果当前工作区有未记录的修改，`checkout` 会在切换前自动创建一个 Capture 节点保存现场。

## `discard` - 丢弃变更

丢弃工作区中所有未被 Quipu 记录的变更，将文件恢复到上一个干净的历史状态。

```bash
quipu discard [OPTIONS]
```

*   `--force, -f`: 强制执行，不询问确认。

**使用场景**: 当一个 Plan 执行失败或被中途取消后，工作区可能会处于一个包含部分修改的“脏”状态。`discard` 命令提供了一个类似于 `git checkout .` 的功能，可以一键清理这些残留的修改，让你从一个已知的良好起点重新开始。

## `sync` - 远程同步

同步 Quipu 的隐形历史记录到远程 Git 仓库。

```bash
quipu sync [OPTIONS]
```

*   `--remote, -r`: 指定远程仓库名称（默认 `origin`）。

此命令通过 `git push/pull refs/quipu/history` 实现历史共享，让团队成员可以复现彼此的 AI 操作历史。

## `save` - 保存快照 (微提交)

创建一个当前工作区状态的轻量级快照。

```bash
quipu save "[MESSAGE]" [OPTIONS]
```

*   `[MESSAGE]`: (可选) 为这个快照添加一句描述，例如 "尝试修复 bug" 或 "重构前的状态"。
*   `--work-dir, -w`: 指定工作区。

**核心用途**:
`save` 命令填补了“编辑器撤销”和“Git 提交”之间的巨大空白。它允许你以极低的成本、极高的频率保存你的工作进度，而不会污染 Git 的主提交历史。你可以把它看作是一个拥有无限历史记录的“存盘点”。
---
## 🧭 导航命令

当历史记录出现分支时，这些命令允许你像在浏览器中前进/后退一样，在历史图谱中轻松穿梭，而无需手动复制哈希值。

| 命令 | 描述 | 示例 |
| :--- | :--- | :--- |
| `quipu undo` | 移动到当前节点的**父节点** (类似 Ctrl+Z)。 | `quipu undo -n 2` (向上移动2次) |
| `quipu redo` | 移动到当前节点的**子节点** (类似 Ctrl+Y)。 | `quipu redo` |
| `quipu prev` | 在兄弟分支间，切换到**上一个 (更旧的)** 分支。 | `quipu prev` |
| `quipu next` | 在兄弟分支间，切换到**下一个 (更新的)** 分支。 | `quipu next` |

## 📺 交互式界面

### `ui` - 启动 TUI 历史浏览器

提供一个全屏的、可视化的界面来浏览和操作历史图谱。

```bash
quipu ui
```

*   **视图**: 类似于 `git log --graph` 的垂直时间轴，清晰展示主干与分支。
*   **高亮**: 启动时自动高亮当前工作区所处的状态。
*   **操作**:
    *   使用 `↑` / `↓` 方向键选择节点。
    *   按 `Enter` 或 `c` 键检出 (checkout) 到选中节点。
    *   按 `h` 键切换显示/隐藏与当前分支无关的节点。
    *   按 `q` 键退出。

## `discard` - 丢弃变更

丢弃工作区中所有未被 Quipu 记录的变更，将文件恢复到上一个干净的历史状态。

```bash
quipu discard [OPTIONS]
```

*   `--force, -f`: 强制执行，不询问确认。

**使用场景**: 当一个 Plan 执行失败或被中途取消后，工作区可能会处于一个包含部分修改的“脏”状态。`discard` 命令提供了一个类似于 `git checkout .` 的功能，可以一键清理这些残留的修改，让你从一个已知的良好起点重新开始。

## `sync` - 远程同步

同步 Quipu 的隐形历史记录到远程 Git 仓库。

```bash
quipu sync [OPTIONS]
```

*   `--remote, -r`: 指定远程仓库名称（默认 `origin`）。

此命令通过 `git push/pull refs/quipu/history` 实现历史共享，让团队成员可以复现彼此的 AI 操作历史。

## `save` - 保存快照 (微提交)

创建一个当前工作区状态的轻量级快照。

```bash
quipu save "[MESSAGE]" [OPTIONS]
```

*   `[MESSAGE]`: (可选) 为这个快照添加一句描述，例如 "尝试修复 bug" 或 "重构前的状态"。
*   `--work-dir, -w`: 指定工作区。

**核心用途**:
`save` 命令填补了“编辑器撤销”和“Git 提交”之间的巨大空白。它允许你以极低的成本、极高的频率保存你的工作进度，而不会污染 Git 的主提交历史。你可以把它看作是一个拥有无限历史记录的“存盘点”。
---
## 🧭 导航命令

当历史记录出现分支时，这些命令允许你像在浏览器中前进/后退一样，在历史图谱中轻松穿梭，而无需手动复制哈希值。

| 命令 | 描述 | 示例 |
| :--- | :--- | :--- |
| `quipu undo` | 移动到当前节点的**父节点** (类似 Ctrl+Z)。 | `quipu undo -n 2` (向上移动2次) |
| `quipu redo` | 移动到当前节点的**子节点** (类似 Ctrl+Y)。 | `quipu redo` |
| `quipu prev` | 在兄弟分支间，切换到**上一个 (更旧的)** 分支。 | `quipu prev` |
| `quipu next` | 在兄弟分支间，切换到**下一个 (更新的)** 分支。 | `quipu next` |

## 📺 交互式界面

### `ui` - 启动 TUI 历史浏览器

提供一个全屏的、可视化的界面来浏览和操作历史图谱。

```bash
quipu ui
```

*   **操作**:
    *   使用 `↑` / `↓` 方向键选择节点。
    *   按 `Enter` 或 `c` 键检出 (checkout) 到选中节点。
    *   按 `q` 键退出。