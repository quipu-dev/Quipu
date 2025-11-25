# feat(storage): implement qdps v1.0 phase 1 - interfaces & telemetry

## 目标
实现 Quipu 数据持久化协议 (QDPS) v1.0 的第一阶段：定义核心数据结构并实现运行时遥测数据的自动收集逻辑。这是实现“双 Blob 分离存储”架构的基础。

## 基本原理
为了实现元数据与内容的物理分离，我们需要：
1.  在接口层 (`quipu-interfaces`) 形式化定义 `QuipuMetadata` 及其子组件，确保各模块对数据结构有统一的认知。
2.  在引擎层 (`quipu-engine`) 实现 `telemetry` 模块，负责自动抓取环境指纹、生成源信息和执行耗时，实现“零用户摩擦”的元数据生成。

此阶段不涉及底层 Git 存储逻辑的修改，风险可控。

## 标签
#feat #storage #qdps #phase-1

---

## Script

### Act 1: 定义 QuipuMetadata 数据模型

在 `packages/quipu-interfaces/src/quipu/core/models.py` 中引入新的数据类，用于描述符合 QDPS v1.0 规范的元数据结构。同时更新 `QuipuNode` 以支持未来的分离存储。

~~~~~act
write_file packages/quipu-interfaces/src/quipu/core/models.py
~~~~~

~~~~~python
from __future__ import annotations
import dataclasses
from pathlib import Path
from typing import Optional, List, Literal, Dict
from datetime import datetime

@dataclasses.dataclass
class GeneratorInfo:
    """生成源信息：追踪是谁、用什么工具生成了这个节点"""
    id: str
    tool: str

@dataclasses.dataclass
class EnvInfo:
    """环境指纹：记录运行时的系统环境"""
    quipu: str
    python: str
    os: str

@dataclasses.dataclass
class ExecInfo:
    """执行遥测：记录客观执行数据"""
    start: float
    duration_ms: int

@dataclasses.dataclass
class QuipuMetadata:
    """
    QDPS v1.0 元数据结构 (metadata.yml)
    """
    meta_version: str
    type: Literal["plan", "capture"]
    generator: GeneratorInfo
    env: EnvInfo
    exec: ExecInfo

@dataclasses.dataclass
class QuipuNode:
    """
    表示 Axon 历史图谱中的一个节点。
    
    兼容性说明：
    - v1.0 (Legacy): 使用 filename, input_tree, output_tree 等扁平字段。
    - v2.0 (QDPS): 使用 metadata (QuipuMetadata) 和 content (str) 分离存储。
    
    在过渡期，Hydrator 负责将旧数据映射到这个模型，或填充默认的 metadata。
    """
    # 核心标识
    output_tree: str  # 节点的唯一标识 (对应 Git Commit Hash 或 Tree Hash，取决于上下文)
    
    # 物理/逻辑分离
    metadata: Optional[QuipuMetadata] = None
    content: str = ""
    
    # --- 旧字段 (保留以向后兼容 v1 逻辑，未来逐步废弃) ---
    input_tree: str = ""
    timestamp: datetime = dataclasses.field(default_factory=datetime.now)
    filename: Optional[Path] = None
    node_type: str = "unknown" # 对应 metadata.type
    parent: Optional[QuipuNode] = None
    children: List[QuipuNode] = dataclasses.field(default_factory=list)

    @property
    def short_hash(self) -> str:
        return self.output_tree[:7]

    @property
    def siblings(self) -> List[QuipuNode]:
        if not self.parent:
            return [self]
        return self.parent.children
~~~~~

### Act 2: 实现遥测收集器 (Telemetry)

在 `packages/quipu-engine/src/quipu/core/telemetry.py` 中实现 `MetadataFactory`，负责自动采集环境信息、处理生成者身份（支持环境变量注入），并提供计时工具。

~~~~~act
write_file packages/quipu-engine/src/quipu/core/telemetry.py
~~~~~

~~~~~python
import os
import time
import platform
import contextlib
from typing import Optional, Literal
from importlib.metadata import version, PackageNotFoundError

from quipu.core.models import QuipuMetadata, GeneratorInfo, EnvInfo, ExecInfo

class MetadataFactory:
    """
    负责构建 QuipuMetadata 对象。
    自动收集环境信息、生成者身份和执行时间。
    """
    
    def __init__(self):
        self._start_time: float = 0.0
        self._duration_ms: int = 0

    @contextlib.contextmanager
    def stopwatch(self):
        """
        计时上下文管理器。
        用法:
            factory = MetadataFactory()
            with factory.stopwatch():
                ... execute task ...
            metadata = factory.create("plan")
        """
        self._start_time = time.time()
        try:
            yield
        finally:
            end_time = time.time()
            self._duration_ms = int((end_time - self._start_time) * 1000)

    def _get_env_info(self) -> EnvInfo:
        try:
            # 尝试获取安装后的版本，如果未安装（开发模式）可能抛出异常或返回不准确的值
            # 这里简单处理：如果找不到，标记为 dev
            q_version = version("quipu-engine")
        except PackageNotFoundError:
            q_version = "dev"
            
        return EnvInfo(
            quipu=q_version,
            python=platform.python_version(),
            os=platform.system().lower()
        )

    def _get_generator_info(self) -> GeneratorInfo:
        """
        支持通过环境变量注入生成者信息，适配 AI Agent 或 CI 环境。
        """
        return GeneratorInfo(
            id=os.getenv("QUIPU_GENERATOR_ID", "manual"),
            tool=os.getenv("QUIPU_TOOL", "quipu-cli")
        )

    def create(self, node_type: Literal["plan", "capture"]) -> QuipuMetadata:
        """
        构建并返回元数据快照。
        必须在 stopwatch() 之后调用以获取准确的执行时间。
        """
        # 如果未调用 stopwatch，默认使用当前时间，耗时 0
        start = self._start_time if self._start_time > 0 else time.time()
        
        return QuipuMetadata(
            meta_version="1.0",
            type=node_type,
            generator=self._get_generator_info(),
            env=self._get_env_info(),
            exec=ExecInfo(
                start=start,
                duration_ms=self._duration_ms
            )
        )
~~~~~

### Act 3: 添加遥测单元测试

创建 `tests/test_telemetry.py`，验证元数据工厂的各项功能，特别是环境变量注入和计时器逻辑。

~~~~~act
write_file tests/test_telemetry.py
~~~~~

~~~~~python
import os
import time
import pytest
from unittest.mock import patch
from quipu.core.telemetry import MetadataFactory

class TestTelemetry:
    
    def test_env_capture(self):
        factory = MetadataFactory()
        meta = factory.create("plan")
        
        assert meta.meta_version == "1.0"
        assert meta.env.python  # Should not be empty
        assert meta.env.os      # Should not be empty
        # In dev environment, version might be 'dev' or actual version
        assert meta.env.quipu

    def test_generator_injection(self):
        """验证环境变量注入是否生效"""
        with patch.dict(os.environ, {"QUIPU_GENERATOR_ID": "gpt-5", "QUIPU_TOOL": "agent-x"}):
            factory = MetadataFactory()
            meta = factory.create("capture")
            
            assert meta.generator.id == "gpt-5"
            assert meta.generator.tool == "agent-x"

    def test_default_generator(self):
        """验证默认生成者信息"""
        # Ensure env vars are cleared for this test
        with patch.dict(os.environ, {}, clear=True):
            factory = MetadataFactory()
            meta = factory.create("plan")
            
            assert meta.generator.id == "manual"
            assert meta.generator.tool == "quipu-cli"

    def test_stopwatch_timing(self):
        factory = MetadataFactory()
        
        with factory.stopwatch():
            time.sleep(0.1)
            
        meta = factory.create("plan")
        
        # 允许少量误差，但应接近 100ms
        assert meta.exec.duration_ms >= 100
        assert meta.exec.start > 0

    def test_create_types(self):
        factory = MetadataFactory()
        meta_plan = factory.create("plan")
        assert meta_plan.type == "plan"
        
        meta_capture = factory.create("capture")
        assert meta_capture.type == "capture"
~~~~~