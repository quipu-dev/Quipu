# fix: 更新测试 Fixtures 以适配 Engine 构造函数

## 用户需求
在将 `Engine` 构造函数修改为需要一个 `db` 参数后，大量依赖旧构造函数的测试用例在启动时失败，并报告 `TypeError: Engine.__init__() missing 1 required positional argument: 'db'`。

## 评论
这是一个典型的重构后遗症。修改了核心类的构造函数签名，就必须同步更新所有实例化该类的地方。这个修复很简单，只需要在所有创建 `Engine` 实例的测试 fixtures 中，将 `GitDB` 实例作为 `db` 参数传递进去即可。

## 目标
1.  修改 `tests/test_engine.py` 中的 `engine_setup` fixture。
2.  修改 `tests/test_head_and_root.py` 中的 `engine_with_repo` fixture。
3.  修改 `tests/test_navigation.py` 中的 `nav_workspace` 和 `cli_workspace` fixtures。
4.  确保所有测试都能成功通过收集阶段。

## 基本原理
在每个受影响的 fixture 中，`GitDB` 实例已经被创建。我们只需要在调用 `Engine(...)` 时，通过关键字参数 `db=git_db` 将它传递给构造函数，就能满足新的接口要求。

## 标签
#intent/fix #flow/ready #priority/critical 
#comp/engine #comp/tests 
#scope/dx 
#ai/instruct 

---

## Script

### Acts 1: 修复 `test_engine.py`

````act
replace tests/test_engine.py
````
````python
    git_db = GitDB(repo_path)
    reader = GitObjectHistoryReader(git_db)
    writer = GitObjectHistoryWriter(git_db)
    engine = Engine(repo_path, reader=reader, writer=writer)

    return engine, repo_path
````
````python
    git_db = GitDB(repo_path)
    reader = GitObjectHistoryReader(git_db)
    writer = GitObjectHistoryWriter(git_db)
    engine = Engine(repo_path, db=git_db, reader=reader, writer=writer)

    return engine, repo_path
````

### Acts 2: 修复 `test_head_and_root.py`

````act
replace tests/test_head_and_root.py
````
````python
        git_db = GitDB(repo)
        reader = GitObjectHistoryReader(git_db)
        writer = GitObjectHistoryWriter(git_db)
        return Engine(repo, reader=reader, writer=writer)
````
````python
        git_db = GitDB(repo)
        reader = GitObjectHistoryReader(git_db)
        writer = GitObjectHistoryWriter(git_db)
        return Engine(repo, db=git_db, reader=reader, writer=writer)
````

### Acts 3: 修复 `test_navigation.py`

````act
replace tests/test_navigation.py
````
````python
    git_db = GitDB(repo_path)
    reader = GitObjectHistoryReader(git_db)
    writer = GitObjectHistoryWriter(git_db)
    engine = Engine(repo_path, reader=reader, writer=writer)
````
````python
    git_db = GitDB(repo_path)
    reader = GitObjectHistoryReader(git_db)
    writer = GitObjectHistoryWriter(git_db)
    engine = Engine(repo_path, db=git_db, reader=reader, writer=writer)
````

````act
replace tests/test_navigation.py
````
````python
        git_db = GitDB(ws)
        reader = GitObjectHistoryReader(git_db)
        writer = GitObjectHistoryWriter(git_db)
        engine = Engine(ws, reader=reader, writer=writer)
````
````python
        git_db = GitDB(ws)
        reader = GitObjectHistoryReader(git_db)
        writer = GitObjectHistoryWriter(git_db)
        engine = Engine(ws, db=git_db, reader=reader, writer=writer)
````
