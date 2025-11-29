好的。遵照你的指示，我将对 Quipu 的日志记录和错误处理进行增强。日志级别现在将可以通过 `QUIPU_LOG_LEVEL` 环境变量进行配置，并且我会在关键路径和错误处理块中添加更详细的日志记录，包括在捕获到未预期异常时记录完整的堆栈跟踪。

## [WIP] chore: 增强日志与错误处理

### 错误分析
当前 Quipu 的 CLI 实现中存在几个可以改进的点：
1.  **日志级别环境变量通用**: 日志级别配置虽然从环境变量读取，但变量名 `LOG_LEVEL` 过于通用，容易与其他工具冲突。
2.  **错误处理信息不足**: 多个命令中使用了 `except Exception` 来捕获所有错误，虽然能防止程序崩溃，但没有记录下完整的错误堆栈信息 (`traceback`)，这使得调试问题变得困难。
3.  **关键路径日志缺失**: 在一些关键执行路径（如选择存储后端、命令调用入口）缺少日志，使得追踪程序行为不够直观。

### 用户需求
1.  使日志记录级别可以通过一个项目专有的环境变量进行调整。
2.  在现有的 `except Exception` 块中增加详细的日志记录（包含堆栈跟踪），并在可能的情况下使用更具体的异常捕获。

### 评论
这是一个非常基础且重要的工程实践改进。增强日志和错误处理能力是提升系统健壮性、可维护性和可观测性的基石。特别是对于一个命令行工具，清晰的错误信息和可配置的日志级别对于用户排查问题至关重要。

### 目标
1.  将日志级别的环境变量重命名为 `QUIPU_LOG_LEVEL` 以避免冲突。
2.  在所有捕获通用 `Exception` 的地方，使用 `logger.error(..., exc_info=True)` 来记录完整的堆栈跟踪。
3.  在几个关键命令的入口处增加 `DEBUG` 级别的日志，记录调用参数。
4.  在引擎工厂函数中增加日志，明确指出当前使用的存储后端。
5.  在部分可以预测错误类型的地方，使用更具体的异常类进行捕获。

### 基本原理
通过遵循这些目标，我们可以系统性地提升应用的可靠性。使用 `exc_info=True` 是 Python `logging` 模块的标准实践，它能在不改变异常处理流程的同时，将宝贵的调试信息记录到日志中。将环境变量专有化可以避免与其他 Python 应用或库产生意外的相互作用。在命令入口添加参数日志，则使得通过 `DEBUG` 日志复现用户报告的问题变得简单直接。

### 标签
#intent/refine #flow/ready #priority/medium #comp/cli #concept/state #scope/dx #ai/instruct #task/domain/cli #task/object/logging-error-handling #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 更新日志配置与引擎工厂

我们将首先更新配置，使日志级别可通过 `QUIPU_LOG_LEVEL` 控制，并在引擎工厂中添加日志记录。

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/config.py
~~~~~
~~~~~python
# 日志级别
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
~~~~~
~~~~~python
# 日志级别
# 使用项目特定的环境变量 QUIPU_LOG_LEVEL，并确保其值为大写
LOG_LEVEL: str = os.getenv("QUIPU_LOG_LEVEL", "INFO").upper()
~~~~~

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/factory.py
~~~~~
~~~~~python
    storage_type = config.get("storage.type", "git_object")
    git_db = GitDB(project_root)
~~~~~
~~~~~python
    storage_type = config.get("storage.type", "git_object")
    logger.debug(f"Engine factory configured with storage type: '{storage_type}'")
    git_db = GitDB(project_root)
~~~~~

#### Acts 2: 增强 Axon 命令的日志与错误处理

为 `axon` 命令添加入口日志，并细化其异常捕获。

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/commands/axon.py
~~~~~
~~~~~python
        """
        Axon: 无状态的 Markdown 任务执行器 (不记录历史)。
        """
        setup_logging()

        # 1. 配置执行器的 UI 确认回调
~~~~~
~~~~~python
        """
        Axon: 无状态的 Markdown 任务执行器 (不记录历史)。
        """
        setup_logging()
        logger.debug(f"axon started with file={file}, work_dir={work_dir}, parser={parser_name}, yolo={yolo}")

        # 1. 配置执行器的 UI 确认回调
~~~~~

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/commands/axon.py
~~~~~
~~~~~python
        except ExecutionError as e:
            typer.secho(f"\n❌ 执行失败: {e}", fg=typer.colors.RED, err=True)
            ctx.exit(1)
        except Exception as e:
            logger.error(f"系统错误: {e}", exc_info=True)
            typer.secho(f"\n❌ 系统错误: {e}", fg=typer.colors.RED, err=True)
            ctx.exit(1)
~~~~~
~~~~~python
        except ExecutionError as e:
            typer.secho(f"\n❌ 执行失败: {e}", fg=typer.colors.RED, err=True)
            ctx.exit(1)
        except ValueError as e:
            logger.error(f"无效的参数或配置: {e}", exc_info=True)
            typer.secho(f"\n❌ 无效的参数或配置: {e}", fg=typer.colors.RED, err=True)
            ctx.exit(1)
        except Exception as e:
            logger.error(f"未预期的系统错误: {e}", exc_info=True)
            typer.secho(f"\n❌ 系统错误: {e}", fg=typer.colors.RED, err=True)
            ctx.exit(1)
~~~~~

#### Acts 3: 增强缓存、导航和工作区命令的错误日志

为 `cache`, `helpers`, `navigation`, `workspace` 中的通用异常处理器添加带有完整堆栈跟踪的错误日志。

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/commands/cache.py
~~~~~
~~~~~python
    except Exception as e:
        typer.secho(f"❌ 数据同步失败: {e}", fg=typer.colors.RED, err=True)
        ctx.exit(1)
~~~~~
~~~~~python
    except Exception as e:
        logger.error("数据同步失败", exc_info=True)
        typer.secho(f"❌ 数据同步失败: {e}", fg=typer.colors.RED, err=True)
        ctx.exit(1)
~~~~~

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/commands/cache.py
~~~~~
~~~~~python
    try:
        db_path.unlink()
        typer.secho("🗑️  旧数据库已删除。", err=True)
    except Exception as e:
        typer.secho(f"❌ 删除旧数据库失败: {e}", fg=typer.colors.RED, err=True)
        ctx.exit(1)
~~~~~
~~~~~python
    try:
        db_path.unlink()
        typer.secho("🗑️  旧数据库已删除。", err=True)
    except (OSError, PermissionError) as e:
        logger.error(f"删除旧数据库文件 '{db_path}' 失败", exc_info=True)
        typer.secho(f"❌ 删除旧数据库失败: {e}", fg=typer.colors.RED, err=True)
        ctx.exit(1)
~~~~~

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/commands/helpers.py
~~~~~
~~~~~python
    except Exception as e:
        typer.secho(f"❌ 导航操作失败: {e}", fg=typer.colors.RED, err=True)
        ctx.exit(1)
~~~~~
~~~~~python
    except Exception as e:
        logger.error(f"导航操作失败 (目标哈希: {target_hash[:12]})", exc_info=True)
        typer.secho(f"❌ 导航操作失败: {e}", fg=typer.colors.RED, err=True)
        ctx.exit(1)
~~~~~

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/commands/navigation.py
~~~~~
~~~~~python
            except Exception as e:
                typer.secho(f"❌ 后退操作失败: {e}", fg=typer.colors.RED, err=True)
                ctx.exit(1)
~~~~~
~~~~~python
            except Exception as e:
                logger.error("后退操作失败", exc_info=True)
                typer.secho(f"❌ 后退操作失败: {e}", fg=typer.colors.RED, err=True)
                ctx.exit(1)
~~~~~

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/commands/navigation.py
~~~~~
~~~~~python
            except Exception as e:
                typer.secho(f"❌ 前进操作失败: {e}", fg=typer.colors.RED, err=True)
                ctx.exit(1)
~~~~~
~~~~~python
            except Exception as e:
                logger.error("前进操作失败", exc_info=True)
                typer.secho(f"❌ 前进操作失败: {e}", fg=typer.colors.RED, err=True)
                ctx.exit(1)
~~~~~

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/commands/workspace.py
~~~~~
~~~~~python
            except Exception as e:
                typer.secho(f"❌ 创建快照失败: {e}", fg=typer.colors.RED, err=True)
                ctx.exit(1)
~~~~~
~~~~~python
            except Exception as e:
                logger.error("创建快照失败", exc_info=True)
                typer.secho(f"❌ 创建快照失败: {e}", fg=typer.colors.RED, err=True)
                ctx.exit(1)
~~~~~

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/commands/workspace.py
~~~~~
~~~~~python
            except Exception as e:
                typer.secho(f"❌ 恢复状态失败: {e}", fg=typer.colors.RED, err=True)
                ctx.exit(1)
~~~~~
~~~~~python
            except Exception as e:
                logger.error(f"恢复工作区状态失败", exc_info=True)
                typer.secho(f"❌ 恢复状态失败: {e}", fg=typer.colors.RED, err=True)
                ctx.exit(1)
~~~~~

### 下一步建议
我们已经完成了对日志和错误处理的初步增强。现在你可以通过设置 `export QUIPU_LOG_LEVEL=DEBUG` 来查看更详细的程序执行流程。

下一步，我建议：
1.  **运行测试**: 全面运行 `pytest`，确保我们的改动没有破坏任何现有功能。
2.  **手动验证**: 手动执行一些命令，并设置不同的 `QUIPU_LOG_LEVEL` (如 `DEBUG`, `WARNING`)，观察日志输出是否符合预期。可以特意制造一些错误（如操作一个无权限的文件），来验证错误日志是否包含了完整的堆栈跟踪。
3.  **提交变更**: 在测试通过后，生成一个 `[COMMIT]` 计划来将这些改进持久化。
