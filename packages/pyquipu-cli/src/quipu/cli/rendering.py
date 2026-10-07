from typing import Any

import typer


class TyperRenderer:
    def render(self, message_text: str, level: str = "info", **kwargs: Any) -> None:
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
        # 向后兼容过渡，上层命令已全面迁移至原生 stdout
        typer.echo(data_string, err=False)
