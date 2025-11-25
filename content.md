~~~~~act
replace
~~~~~
~~~~~path
main.py
~~~~~
~~~old
app = typer.Typer(add_completion=False, name="axon")
~~~
~~~new
app = typer.Typer(
    add_completion=False, 
    name="axon",
    pretty_exceptions_enable=False  # 禁用 rich 美化异常，这是启动加速的关键
)
~~~

~~~~~act
end
~~~~~