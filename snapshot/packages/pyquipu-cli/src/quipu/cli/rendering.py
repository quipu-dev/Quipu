from typing import Any

import typer


class TyperRenderer:
    """
    适配 Needle 的 RendererProtocol，并支持 Quipu 特有的 data() 输出。
    """

    def render(self, message: str, level: str = "info", **kwargs: Any) -> None:
        """
        实现 Needle 的标准渲染接口。
        """
        color = None
        err = True  # 默认输出到 stderr (反馈信息)

        if level == "success":
            color = typer.colors.GREEN
        elif level == "warning":
            color = typer.colors.YELLOW
        elif level == "error":
            color = typer.colors.RED
        elif level == "info":
            color = typer.colors.BLUE
        elif level == "debug":
            # Debug 可以在配置中关闭，或者输出为灰色
            # 这里简单处理，视为无色或灰色
            pass

        # Typer 的 secho 处理颜色和 stderr 输出
        typer.secho(message, fg=color, err=err)

    def data(self, data_string: str) -> None:
        """
        Quipu 特有接口：输出原始数据到 stdout。
        """
        typer.echo(data_string, err=False)