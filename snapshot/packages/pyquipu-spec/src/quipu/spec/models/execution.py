from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List, TypedDict


@dataclass
class QuipuResult:
    """Quipu 业务逻辑执行结果的标准容器"""

    success: bool
    exit_code: int
    message: str = ""
    data: Any = None
    error: Optional[Exception] = None
    msg_kwargs: Dict[str, Any] = field(default_factory=dict)


class Statement(TypedDict):
    """表示解析后的单个操作语句"""

    act: str
    contexts: List[str]
