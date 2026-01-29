from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class QuipuResult:
    """Quipu 业务逻辑执行结果的标准容器"""

    success: bool
    exit_code: int
    message: str = ""
    data: Any = None
    error: Optional[Exception] = None
    msg_kwargs: Dict[str, Any] = field(default_factory=dict)
