from typing import Any

import typer


class TyperRenderer:
    """适配 Needle 的 RendererProtocol，并支持 Quipu 特有的 data() 输出。"""

    def render(self, message_text: str, level: str = "info", **kwargs: Any) -> None:
        """实现 Needle 的标准渲染接口。"""
        color = None
        err = True  # 严格输出至 stderr (反馈信息与遥测)

        if level == "success":
            color = typer.colors.GREEN
        elif level == "warning":
            color = typer.colors.YELLOW
        elif level == "error":
            color = typer.colors.RED
        elif level == "info":
            color = typer.colors.BLUE
        elif level == "debug":
            pass

        typer.secho(message_text, fg=color, err=err)

    def data(self, data_string: str) -> None:
        """Quipu 特有接口：输出原始数据到 stdout。"""
        # 向后兼容过渡，上层命令已全面迁移至原生 stdout
        typer.echo(data_string, err=False)
