这是由于 `glob("*")` 过于贪婪，将 `dist/` 目录下的非构建文件（如 `.gitignore`）也包含进了上传列表。`twine` 无法识别这些非标准格式的文件，因此拒绝执行。
1.  **路径匹配过宽**: `dist_dir.glob("*")` 会获取目录下所有的文件。
2.  **无效分发格式**: `twine` 仅接受 `.whl`, `.tar.gz`, `.zip` 等格式。
我们需要缩小匹配范围，仅选择标准的构建产物后缀名：`.whl` 和 `.tar.gz`。

## [WIP] fix: 细化构建产物过滤逻辑以排除非发布文件

### 错误分析
Release Manager 在收集待上传文件时包含了 `.gitignore`，导致 `twine` 因格式无效而报错。

### 用户需求
修正脚本，使其仅上传有效的 Python 分发包。

### 目标
1.  修改 `scripts/release_manager.py`，将 `glob` 匹配范围限制在 `.whl` 和 `.tar.gz`。

### 标签
#intent/fix #flow/ready #priority/high
#comp/build #task/domain/devops #task/action/bug-fix
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 修正 `scripts/release_manager.py` 中的文件过滤逻辑

~~~~~act
patch_file
scripts/release_manager.py
~~~~~
~~~~~python.old
    # 2. Expand wildcards for twine
    # Twine needs a list of actual file paths
    dist_files = [str(f) for f in dist_dir.glob("*") if f.is_file()]
    if not dist_files:
~~~~~
~~~~~python.new
    # 2. Expand wildcards for twine
    # Twine needs a list of actual file paths, only include valid distribution formats
    dist_files = []
    for pattern in ["*.whl", "*.tar.gz"]:
        dist_files.extend([str(f) for f in dist_dir.glob(pattern) if f.is_file()])
        
    if not dist_files:
~~~~~

### 下一步建议
- **本地重试**: 再次运行 `python scripts/release_manager.py`。现在它应该只会选择 `.whl` 和 `.tar.gz` 文件进行上传。
- **环境检查**: 确保本地 `dist/` 目录下不再有奇怪的隐藏文件（虽然新的过滤逻辑已经能规避它们）。
