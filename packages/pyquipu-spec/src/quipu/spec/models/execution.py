from dataclasses import dataclass
from typing import Any


@dataclass
class QuipuResult:
    """Quipu 业务逻辑执行结果的标准容器"""

    success: bool
    exit_code: int
    message: str = ""
    data: Any = None
    error: Exception | None = None
