# Agent Self-Monitor Skill

OpenClaw Agent 自监控技能 - 让 AI Agent 24小时稳定运行，断线后自动恢复任务。

## 功能特性

- ✅ **自动监控**: 每5秒检查 Agent 是否正常运行
- ✅ **断线记录**: 检测到崩溃/断线自动记录任务进度
- ✅ **自动恢复**: Agent 恢复后自动继续未完成的任务
- ✅ **24小时运行**: 后台自动运行，无需人工干预

## 适用场景

- OpenClaw 在云服务器上运行，经常断线
- 需要长时间执行任务（如批量发布内容）
- 断线后需要从断点继续，不想重头开始

## 安装

```bash
# 克隆或下载此技能
git clone https://github.com/你的用户名/agent-self-monitor.git

# 进入目录
cd agent-self-monitor

# 赋予执行权限
chmod +x agent_monitor.py
```

## 使用方法

### 1. 启动监控

```bash
# 后台启动监控脚本
nohup python3 agent_monitor.py > /tmp/agent_monitor.log 2>&1 &

# 或添加到开机自启动
echo "@reboot sleep 10 && /usr/bin/python3 /path/to/agent_monitor.py" >> /etc/crontab
```

### 2. 在 Agent 代码中记录任务

在执行任务时，调用脚本记录进度：

```python
import subprocess

# 任务开始时
subprocess.run([
    "python3", "agent_monitor.py",
    "running", "1", "发布小红书笔记", "正在发布第1篇"
])

# 步骤更新时
subprocess.run([
    "python3", "agent_monitor.py", 
    "running", "2", "发布笔记", "正在发布第2篇"
])

# 任务完成时
subprocess.run(["python3", "agent_monitor.py", "done"])
```

### 3. Agent 启动时检查恢复

```python
import subprocess

result = subprocess.run(
    ["python3", "agent_monitor.py", "check"],
    capture_output=True, text=True
)

if result.returncode == 0:
    # 有未完成的任务，打印恢复指令
    print(result.stdout)
```

## 命令参考

| 命令 | 说明 |
|------|------|
| `python3 agent_monitor.py init` | 初始化任务状态 |
| `python3 agent_monitor.py status` | 查看当前任务状态 |
| `python3 agent_monitor.py running [步骤] [描述] [操作]` | 标记正在执行任务 |
| `python3 agent_monitor.py done` | 标记任务完成 |
| `python3 agent_monitor.py idle` | 标记空闲 |
| `python3 agent_monitor.py check` | 检查是否需要恢复 |
| `python3 agent_monitor.py clear` | 清除崩溃标志 |

## 文件说明

- `agent_monitor.py` - 主监控脚本
- `SKILL.md` - 本说明文档

## 工作原理

1. **监控循环**: 脚本每5秒检查 Gateway 和 Session 状态
2. **断线检测**: 连续3次检测失败（15秒），认为 Agent 崩溃
3. **记录状态**: 创建崩溃标志文件，记录当前任务进度
4. **自动恢复**: Agent 恢复后，检查崩溃标志，继续执行

## 依赖

- Python 3.6+
- OpenClaw 已安装并正常运行

## 注意事项

- 确保脚本有写入权限（写入 `~/.openclaw/workspace/` 目录）
- 崩溃标志文件位于 `~/.openclaw/workspace/.agent_crashed.flag`
- 日志文件位于 `~/.openclaw/workspace/.agent_monitor.log`

## License

MIT License
