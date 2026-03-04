#!/usr/bin/env python3
"""
OpenClaw Agent Self-Monitor Skill
=================================

功能：
- 监控 OpenClaw Agent 是否正常运行
- 检测到 Agent 崩溃/断线后自动记录任务进度
- Agent 恢复后自动继续未完成的任务
- 24小时后台自动运行

用法：
  python3 agent_monitor.py [command]

命令：
  init           - 初始化任务状态
  status         - 查看当前任务状态
  running [step] [desc] [action] - 标记正在执行任务
  done           - 标记任务完成
  idle           - 标记空闲
  check          - 检查是否需要恢复任务
  clear          - 清除崩溃标志
  (无参数)       - 启动监控循环
"""

import json
import os
import sys
import time
import subprocess
from datetime import datetime

# ==================== 配置 ====================
# Gateway WebSocket 地址
GATEWAY_URL = "http://127.0.0.1:18789"

# 任务状态文件 - 保存当前任务进度
TASK_FILE = "/home/lihaibo/.openclaw/workspace/.my_task_state.json"

# 日志文件
LOG_FILE = "/home/lihaibo/.openclaw/workspace/.agent_monitor.log"

# 崩溃标志文件 - 检测到崩溃时创建
CRASH_FLAG = "/home/lihaibo/.openclaw/workspace/.agent_crashed.flag"

# ==================== 核心函数 ====================

def log(msg):
    """记录日志到文件和控制台
    
    Args:
        msg: 日志消息
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {msg}"
    print(log_msg)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")
    except:
        pass

def load_task():
    """从文件加载任务状态
    
    Returns:
        dict: 任务状态字典，如果文件不存在返回 None
    """
    if os.path.exists(TASK_FILE):
        try:
            with open(TASK_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return None

def save_task(task_info):
    """保存任务状态到文件
    
    Args:
        task_info: 任务状态字典
    """
    with open(TASK_FILE, "w", encoding="utf-8") as f:
        json.dump(task_info, f, ensure_ascii=False, indent=2)

def init_task():
    """初始化任务状态
    
    创建一个新的空任务状态，用于开始监控
    
    Returns:
        dict: 初始化后的任务状态
    """
    task = {
        "status": "idle",              # 状态: idle/running/completed
        "current_step": 0,              # 当前步骤编号
        "task_name": "",               # 任务名称
        "step_description": "",         # 步骤描述
        "last_action": "",             # 最后操作
        "last_update": "",             # 最后更新时间
        "history": [],                 # 操作历史记录
        "running_task": False          # 是否正在执行任务
    }
    save_task(task)
    return task

def set_task_status(status=None, step=None, description=None, action=None, running_task=None):
    """更新任务状态
    
    Agent 每次执行任务时调用此函数来更新状态
    这样即使崩溃也能恢复
    
    Args:
        status: 任务状态 (running/idle/completed)
        step: 当前步骤编号
        description: 任务描述
        action: 当前操作
    
    Returns:
        dict: 更新后的任务状态
    """
    task = load_task() or init_task()
    
    if status:
        task["status"] = status
    if step is not None:
        task["current_step"] = step
    if description:
        task["step_description"] = description
    if action:
        task["last_action"] = action
    
    if running_task is not None:
        task["running_task"] = running_task
    
    task["last_update"] = datetime.now().isoformat()
    
    # 如果正在运行，记录操作历史
    if action and status == "running":
        task["running_task"] = True
        task["history"].append({
            "step": task.get("current_step", 0),
            "action": action,
            "time": task["last_update"]
        })
        # 只保留最近100条历史
        if len(task["history"]) > 100:
            task["history"] = task["history"][-100:]
    
    save_task(task)
    return task

def check_gateway():
    """检查 Gateway 是否正常运行
    
    通过 HTTP 请求检查 Gateway WebSocket 服务是否可达
    
    Returns:
        bool: Gateway 是否正常运行
    """
    try:
        import urllib.request
        req = urllib.request.Request(GATEWAY_URL)
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status == 200
    except:
        return False

def check_my_session():
    """检查 Agent Session 是否活跃
    
    使用 openclaw status 命令检查 main session 是否存在
    
    Returns:
        bool: Session 是否活跃
    """
    try:
        result = subprocess.run([
            "openclaw", "status", "--json"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            sessions = data.get("Sessions", [])
            for s in sessions:
                if "main" in s.get("Key", ""):
                    return True
    except:
        pass
    return False

def create_crash_flag():
    """创建崩溃标志
    
    当检测到 Agent 崩溃/断线时，创建一个标志文件
    这样 Agent 恢复后可以知道需要恢复任务
    """
    task = load_task() or init_task()
    
    with open(CRASH_FLAG, "w", encoding="utf-8") as f:
        f.write(f"检测到 Agent 可能崩溃/断线\n")
        f.write(f"时间: {datetime.now().isoformat()}\n")
        f.write(f"任务状态: {task.get('status', 'unknown')}\n")
        f.write(f"当前步骤: {task.get('current_step', 0)}\n")
        f.write(f"步骤描述: {task.get('step_description', '')}\n")
        f.write(f"最后操作: {task.get('last_action', '')}\n")
    
    log(f"⚠️ 已创建崩溃标志文件")

def clear_crash_flag():
    """清除崩溃标志
    
    任务完成后或检查后清除标志
    """
    if os.path.exists(CRASH_FLAG):
        os.remove(CRASH_FLAG)

def check_recovery():
    """检查是否需要恢复任务
    
    Agent 恢复运行后调用此函数，检查是否有未完成的任务
    
    Returns:
        str: 恢复消息，如果不需要恢复返回 None
    """
    if os.path.exists(CRASH_FLAG):
        task = load_task() or init_task()
        
        step = task.get("current_step", 0)
        desc = task.get("step_description", "未知任务")
        action = task.get("last_action", "无")
        history = task.get("history", [])
        
        recovery_msg = f"""⚠️ 检测到 Agent 之前可能断线了！

📊 上次任务状态:
- 步骤: 第 {step} 步
- 任务: {desc}
- 最后操作: {action}

📋 操作历史:"""
        
        for h in history[-5:]:
            recovery_msg += f"\n  {h.get('step', 0)}. {h.get('action', '')}"
        
        recovery_msg += f"\n\n请继续完成上述任务。"
        
        # 清除标志，下次不再重复
        clear_crash_flag()
        
        return recovery_msg
    
    return None

def restart_gateway():
    """尝试重启 Gateway
    
    当检测到 Gateway 停止时尝试重启
    
    Returns:
        bool: 重启是否成功
    """
    log("🔄 尝试重启 Gateway...")
    try:
        subprocess.run(["openclaw", "gateway", "restart"], timeout=30)
        time.sleep(5)
        return check_gateway()
    except:
        return False

# ==================== 监控循环 ====================

def monitor_loop():
    """主监控循环
    
    每5秒检查一次 Agent 状态：
    1. 检查 Gateway 是否正常
    2. 检查 Session 是否活跃
    3. 如果检测到崩溃，创建崩溃标志
    """
    log("🟢 OpenClaw Agent Self-Monitor 启动")
    
    # 初始化任务状态
    task = load_task()
    if not task:
        task = init_task()
    
    was_running_task = task.get("running_task", False)
    consecutive_failures = 0
    
    while True:
        try:
            # 检查状态
            gateway_ok = check_gateway()
            session_ok = check_my_session()
            
            task = load_task() or init_task()
            currently_running = task.get("running_task", False)
            step = task.get("current_step", 0)
            
            if gateway_ok and session_ok:
                consecutive_failures = 0
                
                # 检测任务开始
                if currently_running and not was_running_task:
                    log(f"🚀 检测到 Agent 开始任务: 步骤{step} - {task.get('step_description', '')}")
                    clear_crash_flag()
                
                was_running_task = currently_running
                
            else:
                consecutive_failures += 1
                log(f"⚠️ 异常: Gateway={gateway_ok}, Session={session_ok}, 连续失败={consecutive_failures}")
                
                # 连续3次失败（15秒），可能崩溃
                if consecutive_failures >= 3 and was_running_task:
                    log("❌ 检测到 Agent 崩溃！创建崩溃标志")
                    create_crash_flag()
                    was_running_task = False
            
            # 每30秒显示状态
            if int(time.time()) % 30 == 0:
                log(f"⏳ 监控中... Gateway={gateway_ok}, Session={session_ok}")
            
            time.sleep(5)
            
        except KeyboardInterrupt:
            log("🛑 监控脚本停止")
            break
        except Exception as e:
            log(f"❌ 错误: {e}")
            time.sleep(5)

# ==================== 命令行接口 ====================

def main():
    """主入口函数
    
    处理命令行参数：
    - init: 初始化任务状态
    - status: 查看当前状态
    - running: 标记正在执行任务
    - done: 标记任务完成
    - idle: 标记空闲
    - check: 检查是否需要恢复
    - clear: 清除崩溃标志
    - (无参数): 启动监控循环
    """
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "init":
            # 初始化任务状态
            init_task()
            print("✅ 已初始化任务状态")
        
        elif cmd == "status":
            # 查看当前状态
            task = load_task()
            if task:
                print(json.dumps(task, ensure_ascii=False, indent=2))
            else:
                print("无任务记录")
        
        elif cmd == "running":
            # 标记正在执行任务
            # 用法: python3 agent_monitor.py running 1 "发布笔记" "正在发布第1篇"
            step = int(sys.argv[2]) if len(sys.argv) > 2 else 0
            desc = sys.argv[3] if len(sys.argv) > 3 else ""
            action = sys.argv[4] if len(sys.argv) > 4 else ""
            set_task_status(status="running", step=step, description=desc, action=action)
            print(f"✅ 已记录任务: 步骤{step} - {desc}")
        
        elif cmd == "done":
            # 标记任务完成
            set_task_status(status="completed")
            clear_crash_flag()
            print("✅ 任务已标记完成")
        
        elif cmd == "idle":
            # 标记空闲
            set_task_status(status="idle", running_task=False)
            print("✅ 已标记空闲")
        
        elif cmd == "check":
            # 检查是否需要恢复
            recovery = check_recovery()
            if recovery:
                print(recovery)
                return 0
            else:
                print("无崩溃记录，无需恢复")
                return 1
        
        elif cmd == "clear":
            # 清除崩溃标志
            clear_crash_flag()
            print("✅ 已清除崩溃标志")
        
        else:
            # 启动监控循环
            monitor_loop()
    else:
        # 默认启动监控循环
        monitor_loop()

if __name__ == "__main__":
    sys.exit(main())
