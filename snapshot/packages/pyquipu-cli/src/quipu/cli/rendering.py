from typing import Any

import typer


class TyperRenderer:
    def render(self, message: str, level: str = "info", **kwargs: Any) -> None:
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
        typer.echo(data_string, err=False)
