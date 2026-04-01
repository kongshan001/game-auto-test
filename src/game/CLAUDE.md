# src/game/ — 游戏适配层

游戏适配层负责游戏进程的生命周期管理。

## 文件说明

| 文件 | 类 | 职责 |
|------|---|------|
| `game_launcher.py` | `GameLauncher` | 游戏进程管理器。通过 subprocess 启动游戏 exe，支持启动参数和工作目录配置，提供启动/关闭/重启/状态查询能力 |

## GameLauncher API

| 方法 | 说明 |
|------|------|
| `launch(args, cwd)` | 启动游戏进程，返回 subprocess.Popen 对象 |
| `close(force)` | 关闭游戏，force=True 时 kill，否则先 terminate 再 kill |
| `restart()` | 关闭后重新启动，间隔 2 秒 |
| `is_running()` | 检查进程是否存活（poll is None） |
| `get_pid()` | 获取进程 ID |
| `get_process_info()` | 返回 pid、running、returncode 字典 |

## 依赖关系

- `game_launcher.py` -> subprocess、pathlib（无第三方依赖）

## 关键约定

- Windows 平台使用 `CREATE_NEW_CONSOLE` 标志创建新控制台窗口
- 启动后默认等待 `startup_delay` 秒（默认 5 秒，可配置）
- `close()` 先尝试 `terminate()`，5 秒超时后 `kill()`
- 游戏路径通过 `Config.game_exe_path` 配置，启动前校验文件是否存在
