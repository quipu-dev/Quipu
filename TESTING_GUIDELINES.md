# 现代命令行系统（CLI）与复杂软件交互及测试规范

**文档版本**：v2.0  
**生效范围**：所有 CLI 驱动、引擎分层及包含物理环境副作用（文件、数据库、系统状态）的软件系统  
**核心宗旨**：**废弃对过程遥测（MessageBus/日志）的行为级 Mock，转向“状态副作用契约 + 纯核心结构化数据”的结果级验证。**

---

## 1. 核心哲学与第一性原理

### 1.1 结果（Outcome）vs 过程遥测（Telemetry）
软件系统的价值在于其对**现实世界产生的改变**或**输出的纯数据**。
* **业务成果（Business Outcome）**：状态发生了改变（文件被写入、数据库事务已提交、Git 树已更新），或者计算产出了确定性的数据。
* **过程遥测（Telemetry）**：在达成成果的过程中，向操作者发出的通知、进度条、日志或事件广播。

> **公理**：**遥测是为“人”或监控系统服务的伴生品，绝非系统业务契约的核心部分。测试若通过断言遥测消息来验证业务逻辑，本质上是在测试“系统是否宣称自己做了事”，而非“系统是否真的做了事”。**

### 1.2 系统输出的三维正交模型
一个健康的系统必须将其输出严格划分为互不干扰的三种渠道：

```
+-----------------------------------------------------------------+
|                       业务操作 / 命令触发                       |
+-----------------------------------------------------------------+
          |                               |                |
          v                               v                v
+-------------------+           +-------------------+   +--------------------+
|  1. 状态副作用    |           |  2. 数据管道      |   |  3. 诊断与反馈     |
| (Side Effects)    |           | (Data Payload)    |   | (Diagnostics/UI)   |
+-------------------+           +-------------------+   +--------------------+
| • 文件系统变更    |           | • stdout (管道)   |   | • stderr           |
| • 数据库持久化    |           | • JSON / 结构化流 |   | • 进度、高亮、图标 |
| • 外部服务状态    |           | • 机器可读核心输出|   | • 国际化反馈信息   |
+-------------------+           +-------------------+   +--------------------+
          |                               |                        |
          +---------------+---------------+                        |
                          |                                        |
                          v                                        v
               【自动化测试断言的唯一根据】               【仅在测试 UI 层时验证】
```

---

## 2. 架构分层与消息边界解耦准则

为消除业务逻辑与展示层强耦合（双轨制摩擦），系统必须遵循**“函数式核心，命令式外壳”（Functional Core, Imperative Shell）**的单向依赖原则：

### 2.1 基础设施与底层引擎层（Infrastructure / Core Engine）
* **绝对纯净**：严禁导入、注入或调用任何 UI 消息总线（MessageBus）、控制台输出工具（Rich/Typer/Click）或本地化 I18N 模块。
* **通信契约**：
  * **成功**：返回强类型的领域实体、数据模型或纯数据。
  * **失败**：直接抛出具体的、带有上下文数据的**结构化领域异常**（Domain Exception）。
  * **记录**：仅可使用标准库的底层 `logger.debug()` 记录调试诊断信息，禁止侵入用户业务认知。

### 2.2 应用编排与运行时层（Application / Runtime）
* **职责**：协调底层引擎与调度算法，执行原子操作集。
* **通信契约**：
  * 返回统一定义的执行结果对象（如 `Result[T]`），包含结构化指标（退出码、耗时、变更文件集等）。
  * 不承担将消息“翻译为好看的人类语言”的职责。

### 2.3 命令交互与展现层（CLI / Presentation Shell）
* **职责**：参数解析、异常捕获、格式化呈现、人机确认。
* **通信契约**：
  * 拥有使用 MessageBus / 终端渲染器的**唯一特权**。
  * 捕获业务层返回的数据或异常，转换为提供给终端用户的 UI 反馈（输出至 `stderr`）或机器数据（输出至 `stdout`）。

---

## 3. 测试黄金法则与反模式定义

### 3.1 验证 CLI / 系统命令的黄金三角法则
除专门测试“渲染器/国际化文案本身”的独立测试外，所有业务功能与集成测试**必须且仅能**通过以下三个正交维度进行断言：

1. **退出码（Exit Code）**：
   * `0`：操作成功且达成预期。
   * `1`：运行时/系统错误。
   * `2`：操作被主动取消（用户输入 n，或遇到安全阻断）。
2. **环境副作用（Persistent Side Effects）**：
   * 目标文件是否被创建/修改？哈希值或内容是否完全匹配？
   * 数据库中的记录行数、外键关系是否正确更新？
   * Git / 外部版本系统的引用指针（Refs）、快照树是否确实发生移动？
3. **结构化数据载荷（Structured Payload）**：
   * 当命令属于查询/导出类命令（Query/Export），且支持机器可读输出（如 `--json`）时，直接解析 `result.stdout` 并断言 JSON 数据结构。

---

### 3.2 严厉禁止的测试反模式

#### ❌ 反模式 1：遥测注入断言（The Telemetry Mocking Trap）
* **错误定义**：在测试前通过 `monkeypatch` 或 `MagicMock` 截获消息总线（MessageBus），并以 `mock_bus.success.assert_called_with(...)` 作为验证功能成功的唯一或主要手段。
* **致命缺陷**：
  * **假阳性（False Positive）**：若底层文件并未写盘，但代码漏写了错误处理依然触发了 `bus.success`，测试仍旧通过。
  * **实现细节耦合**：重构优化、调整文案、增加/合并消息批次会导致大面积测试雪崩，抑制重构勇气。

#### ❌ 反模式 2：双轨制负担（Dual-Track Liability）
* **错误定义**：业务逻辑写完后，必须为了“让测试能断言”而强行在业务流中穿插独特的、细碎的 `EventId` 或 `MessageTag`。
* **致命缺陷**：开发者需要同时维护“真实的程序行为”与“专供测试监控的消息系统”，摩擦成本翻倍。

#### ❌ 反模式 3：污染标准输出流（Polluted stdout）
* **错误定义**：将装饰性文本、警告信息、进度提示未经区分直接输出到 `stdout`，导致测试不得不使用模糊正则表达式（如 `assert "Done" in result.stdout`）在输出垃圾中检索关键信息。

---

## 4. 规范代码范式对比

### 场景：执行“工作区无变更时，保存操作应静默或跳过”

#### ❌ 错误范式（脆弱的遥测拦截）

**实现代码：**
```python
# 业务代码与 UI 强耦合
def save_command(work_dir: Path):
    if is_workspace_clean(work_dir):
        # 强行广播一条特定消息供测试拦截
        bus.success(EventID.WORKSPACE_NO_CHANGES)
        return
    commit_drift(work_dir)
```

**测试代码：**
```python
def test_save_clean_workspace(runner, mock_workspace, monkeypatch):
    mock_bus = MagicMock()
    # 侵入式 Mock 消息组件
    monkeypatch.setattr("system.cli.bus", mock_bus)

    result = runner.invoke(app, ["save"])

    assert result.exit_code == 0
    # 脆弱断言：仅仅验证了代码发了一封电报，无法证明底层真实持久化状态！
    mock_bus.success.assert_called_once_with("workspace.save.noChanges")
```

---

#### ✅ 标准范式（黑盒状态断言 + 纯核心验证）

**实现代码：**
```python
# 核心业务层：返回确定性状态，不依赖任何展示组件
class WorkspaceManager:
    def save(self, work_dir: Path) -> SaveResult:
        if self.is_clean(work_dir):
            return SaveResult(changed=False, snapshot_id=self.get_current_head(work_dir))

        new_snapshot = self.commit(work_dir)
        return SaveResult(changed=True, snapshot_id=new_snapshot)


# CLI 适配层：仅负责消费业务结果，并将遥测发往 stderr
@app.command()
def save(work_dir: Path = "."):
    manager = WorkspaceManager()
    result = manager.save(work_dir)

    if not result.changed:
        # 人类友好的提示统统流向 stderr，不影响管道
        console.print_warning("No changes detected.", err=True)
        raise typer.Exit(code=0)

    console.print_success(f"Saved: {result.snapshot_id}", err=True)
```

**测试代码：**
```python
def test_save_clean_workspace(runner, setup_clean_workspace):
    """验证工作区干净时的系统表现：
    1. 退出码为 0
    2. 物理存储层未产生任何多余快照（副作用验证）
    """
    ws = setup_clean_workspace
    initial_snapshots_count = len(list_snapshots(ws))
    initial_head = read_head_pointer(ws)

    # 真实执行 CLI，不 Mock 任何内部总线
    result = runner.invoke(app, ["save", "-w", str(ws)])

    # 1. 验证退出码契约
    assert result.exit_code == 0

    # 2. 验证物理真实状态（绝无垃圾提交，指针不漂移）
    assert len(list_snapshots(ws)) == initial_snapshots_count
    assert read_head_pointer(ws) == initial_head
```

---

### 场景：查询类命令（Query Command）

#### ✅ 标准范式（机器可读数据流）

**测试代码：**
```python
def test_log_query_returns_valid_chronological_records(runner, setup_populated_workspace):
    """测试查询命令：直接断言结构化输出契约（stdout），而非拦截日志。"""
    ws = setup_populated_workspace

    result = runner.invoke(app, ["log", "--json", "-w", str(ws)])

    assert result.exit_code == 0

    # 直接断言 stdout 中的机器消费契约
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert len(data) == 3
    # 严格验证数据排序契约：时间倒序
    assert data[0]["timestamp"] > data[1]["timestamp"]
```

---

## 5. 测试金字塔与分类执行准则

| 测试层级 | 测试目标 | 依赖/环境 | 核心断言手法 | 严禁行为 |
| :--- | :--- | :--- | :--- | :--- |
| **单元测试 (Unit)** | 算法、解析器、核心模型、状态机转换逻辑 | 纯内存、本地临时目录 | `assert result == ExpectedData`<br>`pytest.raises(CustomException)` | 严禁启动子进程；严禁引入任何展示层组件；严禁 Mock Bus |
| **集成测试 (Integration)** | 基础设施抽象（Git Plumbing、SQLite 存储、文件系统 I/O） | 真实文件系统临时沙箱 (`tmp_path`) | 文件内容哈希、SQLite 数据行比对、底层状态校验 | 严禁断言“控制台输出了什么”；严禁全局环境变量污染 |
| **端到端测试 (E2E / CLI)** | CLI 入口参数、全局配置级联、人机中断链路 | 完整的沙箱工作区 + CLI Runner | 1. `result.exit_code`<br>2. 真实磁盘持久化文件状态<br>3. `json.loads(result.stdout)` | **严禁截获并断言 `mock_bus.assert_called_with()`**；除错误中断测试外，尽量避免断言具体的纯人类文本 |

---

## 6. 特殊场景处置细则

### 6.1 人机交互确认测试（Prompt / Confirmation）
* **原则**：测试应当验证“拒绝时是否**安全终止且未造成副作用**”，以及“接受时是否**完整执行了副作用**”。
* **模式**：
  ```python
  def test_destructive_action_aborts_on_user_rejection(runner, dirty_workspace):
      # 模拟用户在交互终端输入 'n'
      result = runner.invoke(app, ["discard", "-w", str(dirty_workspace)], input="n\n")

      # 契约断言：操作取消（Exit Code 2 或 1，取决于系统定义）
      assert result.exit_code != 0
      # 物理断言：脏数据必须完好无损，绝对没有被物理丢弃
      assert (dirty_workspace / "wip.txt").read_text() == "dirty_content"
  ```

### 6.2 异常与错误测试（Error Handling）
* 当测试一个异常分支时（例如缺少参数、权限不足、目标文件不存在）：
  1. 断言 `result.exit_code != 0`。
  2. （可选）断言物理状态没有被部分执行（事务完整性）。
  3. **至多**检查错误日志中是否包含高辨识度的根因关键词（如 `not found` 或自定义异常码 `ERR_404`），**绝对不要断言整个错误文案的标点符号或格式排版**。

---

## 7. 结语

软件的可维护性取决于**核心逻辑与外部世界（用户/终端/网络）的解耦程度**。

* **消息总线（MessageBus）属于外壳**：它是一个单向的、向外辐射的“麦克风”，用来把状态变化广播给终端人类。
* **业务状态属于核心**：无论有没有麦克风、麦克风是开是关，文件写入了就是写入了，快照生成了就是生成了。

**测试应该去检查土地上的庄稼有没有长出来，而不是去监听广播电台有没有宣布丰收。**
