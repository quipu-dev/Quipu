class AIFSOpsError(Exception):
    """Quipu 生态系统的基础异常类"""
    pass


class ParseError(AIFSOpsError):
    """Markdown 或指令解析错误"""
    pass


class ExecutionError(AIFSOpsError):
    """Act 操作执行错误"""
    pass


class OperationCancelledError(ExecutionError):
    """当用户取消一个需要确认的操作时引发"""
    pass