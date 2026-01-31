太棒了。既然所有单元测试均已通过，说明这套基于 `pyneedle-bus` 的适配层已经成功接管了 Quipu 的消息系统。

我将生成一个 `[COMMIT]` 计划，将这些重构成果固化到代码库中。

## [COMMIT] refactor: 将总线架构迁移至 pyneedle-bus

### 用户需求
提交所有与 `pyneedle-bus` 迁移相关的代码变更、配置更新和资产搬迁。

### 评论
这是一次重大的横切关注点（Cross-cutting Concern）重构。通过这次迁移，Quipu 摆脱了私有的总线实现，转而拥抱更标准、更具扩展性的 Needle 生态。适配层的引入确保了迁移过程对业务逻辑的零侵入（除了导入路径）。

### 目标
1.  正式提交删除 `pyquipu-bus` 的操作。
2.  提交 `pyquipu-common` 中新设立的 `QuipuBus` 和 I18N 资产。
3.  提交所有 `pyproject.toml` 的依赖调整。
4.  提交全局导入路径替换和测试夹具的修复。

### 基本原理
按照 Conventional Commits 规范，将此次变更标记为 `refactor`。我们在一个大的原子提交中包含所有互相关联的包变更，以确保版本一致性。

### 标签
#intent/refine #flow/ready #priority/high #comp/common #comp/build #task/domain/ui #task/object/bus #task/action/integration #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

我们将所有变更（包括新添加的资产、删除的旧包、修改的配置和代码）添加到暂存区。

~~~~~act
git_add
.
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor: migrate bus architecture to pyneedle-bus

- Physically removed pyquipu-bus and relocated assets to pyquipu-common.
- Restructured locale JSON files into Needle-compliant Directory/File structure.
- Implemented QuipuBus adapter in pyquipu-common to support legacy 'data()' and 'render_to_string' APIs.
- Updated TyperRenderer to implement Needle's RendererProtocol.
- Performed global import replacement from 'quipu.bus' to 'quipu.common.bus'.
- Fixed test fixtures to support the new bus API for intent validation.
- Updated all package pyproject.toml files to use pyneedle-bus as a dependency.
~~~~~

### 下一步建议
- **清理脚本**: 既然迁移已经成功并提交，你可以手动删除根目录下的 `migrate_quipu_locales.py` 脚本。
- **引入 L 指针**: 现在的代码依然在使用字符串 ID (如 `"acts.basic.success"`)。为了获得更好的开发体验和类型安全，建议开启下一个阶段的任务：**引入 `L` 指针重构**。
    - 示例：将 `bus.success("acts.basic.success")` 替换为 `from needle.pointer import L; bus.success(L.acts.basic.success)`。
