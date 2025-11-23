
## [2025-11-21 22:47:52]
Implementation Logic:
1.  **Refactored `plugin_loader.py`**: Switched from `import_module` to `spec_from_file_location`. This is crucial because `import_module` relies on Python's `sys.path`. If we have multiple folders named `.axon/acts` in different locations (Home, Project), Python would treat them as the same package namespace or fail to distinguish them. Loading by file path isolates each plugin file as a unique module in memory.
2.  **Enhanced `main.py`**: Added `_find_project_root` to detect Git boundaries. Added `_load_extra_plugins` to build a list of plugin paths.
3.  **Loading Order**: The order `Home -> Env -> Project -> Local` ensures that a script in your current folder can override a project-wide script, and a project script can override a global user script. This follows the standard "Cascading Configuration" pattern (like CSS or Git config).

## [2025-11-23 16:34:39]
开始执行阶段 3：用户体验与核心功能。

首要任务是实现 `axon log` 命令。
1.  **目标**: 提供一个简单的方式来查看 `.axon/history` 目录中记录的所有操作节点。
2.  **实现路径**:
    *   在 `main.py` 中使用 Typer 添加一个新的 `log` 命令。
    *   该命令将调用 `core.history.load_history_graph` 来加载所有历史节点。
    *   将加载的节点按时间戳降序排列。
    *   以清晰、格式化的方式将节点信息（时间戳、类型、哈希、内容摘要）打印到终端。
3.  **收尾**: 修改 `TODO.md`，将 `axon log` 相关的任务标记为已完成。
