"""
MBTA Agent 主程序
波士顿地铁智能助手

使用方式：
    python main.py          # 交互模式
    python main.py test     # 自动测试
    python main.py users    # 管理用户
"""
import sys
from agent import Agent, list_users, view_user_memory, delete_user_memory
from tools.mbta import (
    get_routes,
    get_stops,
    search_stops,
    get_predictions,
    get_next_train,
    get_both_directions,
    get_alerts,
    MBTA_TOOLS
)


def create_agent(user_id: str) -> Agent:
    """创建并配置 Agent"""
    agent = Agent(user_id=user_id)
    
    # 注册 MBTA 工具
    tool_functions = {
        "get_routes": get_routes,
        "get_stops": get_stops,
        "search_stops": search_stops,
        "get_predictions": get_predictions,
        "get_next_train": get_next_train,
        "get_both_directions": get_both_directions,
        "get_alerts": get_alerts,
    }
    
    for schema in MBTA_TOOLS:
        func_name = schema["function"]["name"]
        if func_name in tool_functions:
            agent.register_tool(func_name, tool_functions[func_name], schema)
    
    return agent


def select_user() -> str:
    """选择或创建用户"""
    users = list_users()
    
    print("\n👤 选择用户")
    print("-" * 30)
    
    if users:
        print("已有用户:")
        for i, user in enumerate(users, 1):
            print(f"  {i}. {user}")
        print(f"  {len(users) + 1}. 创建新用户")
        print(f"  {len(users) + 2}. 游客模式 (不保存记忆)")
    else:
        print("还没有用户")
        print("  1. 创建新用户")
        print("  2. 游客模式 (不保存记忆)")
    
    while True:
        choice = input("\n请选择 (输入数字或用户名): ").strip()
        
        # 直接输入用户名
        if choice and not choice.isdigit():
            return choice
        
        # 输入数字
        if choice.isdigit():
            idx = int(choice)
            if users:
                if 1 <= idx <= len(users):
                    return users[idx - 1]
                elif idx == len(users) + 1:
                    # 创建新用户
                    new_user = input("输入新用户名: ").strip()
                    if new_user:
                        return new_user
                elif idx == len(users) + 2:
                    return "guest"
            else:
                if idx == 1:
                    new_user = input("输入新用户名: ").strip()
                    if new_user:
                        return new_user
                elif idx == 2:
                    return "guest"
        
        print("无效选择，请重试")


def main_interactive():
    """交互模式"""
    print("=" * 50)
    print("🚇 波士顿地铁助手 Genos")
    print("=" * 50)
    
    # 选择用户
    user_id = select_user()
    print(f"\n✅ 当前用户: {user_id}")
    
    # 创建 Agent
    agent = create_agent(user_id)
    
    # 显示用户记忆
    if user_id != "guest":
        print("\n📝 用户记忆:")
        print(agent.get_memory_summary())
    
    print("\n" + "=" * 50)
    print("开始对话！输入 'quit' 退出")
    print("命令: /clear 清空对话 | /memory 查看记忆 | /set 设置偏好")
    print("=" * 50)
    
    while True:
        try:
            user_input = input("\n你: ").strip()
            
            if not user_input:
                continue
            
            # 退出
            if user_input.lower() in ["quit", "exit", "q", "退出"]:
                print("\n👋 再见！")
                break
            
            # 命令处理
            if user_input.startswith("/"):
                handle_command(user_input, agent)
                continue
            
            # 正常对话
            response = agent.chat(user_input)
            print(f"\n🤖 Genos: {response}")
            
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")


def handle_command(cmd: str, agent: Agent):
    """处理斜杠命令"""
    parts = cmd.split(maxsplit=2)
    command = parts[0].lower()
    
    if command == "/clear":
        agent.clear_history()
        print("✅ 对话历史已清空")
    
    elif command == "/memory":
        print("\n📝 用户记忆:")
        print(agent.get_memory_summary())
    
    elif command == "/set":
        if len(parts) < 3:
            print("用法: /set <key> <value>")
            print("可用 key: home_station, home_station_name, work_station, work_station_name, language, preferred_line")
            return
        
        key = parts[1]
        value = parts[2]
        
        if agent.set_preference(key, value):
            print(f"✅ 已设置 {key} = {value}")
        else:
            print(f"❌ 未知的偏好: {key}")
    
    elif command == "/fact":
        if len(parts) < 2:
            print("用法: /fact <事实描述>")
            return
        
        fact = " ".join(parts[1:])
        agent.add_fact(fact)
        print(f"✅ 已添加事实: {fact}")
    
    elif command == "/history":
        print("\n📜 对话历史:")
        for msg in agent.get_history():
            role = msg["role"]
            content = msg.get("content", "")
            if role == "system":
                print(f"  [SYSTEM] (长度: {len(content)})")
            elif role == "user":
                print(f"  [USER] {content}")
            elif role == "assistant" and content:
                print(f"  [ASSISTANT] {content[:80]}...")
            elif role == "tool":
                print(f"  [TOOL] {content[:50]}...")
    
    elif command == "/help":
        print("""
可用命令:
  /clear    - 清空当前对话历史
  /memory   - 查看用户记忆
  /set <key> <value> - 设置偏好
  /fact <描述>       - 添加事实
  /history  - 查看对话历史
  /help     - 显示帮助
""")
    
    else:
        print(f"未知命令: {command}，输入 /help 查看帮助")


def main_test():
    """自动测试模式"""
    print("=" * 50)
    print("🧪 MBTA Agent 自动测试")
    print("=" * 50)
    
    agent = create_agent("test_user")
    
    test_cases = [
        ("你好", "基础问候"),
        ("Hello, what's your name?", "英文测试"),
        ("波士顿地铁有哪些线路？", "线路查询"),
        ("红线有哪些站？", "站点查询"),
        ("Harvard 红线下一班什么时候到？", "到站查询"),
        ("搜索 Park", "站点搜索"),
        ("那橙线呢？", "上下文记忆测试"),
    ]
    
    for question, description in test_cases:
        print(f"\n{'='*50}")
        print(f"📝 测试: {description}")
        print(f"   问题: {question}")
        print("-" * 50)
        
        try:
            response = agent.chat(question)
            print(f"🤖 回答: {response}")
        except Exception as e:
            print(f"❌ 错误: {e}")
    
    print(f"\n{'='*50}")
    print("✅ 测试完成")
    print("=" * 50)


def main_users():
    """用户管理模式"""
    print("=" * 50)
    print("👥 用户管理")
    print("=" * 50)
    
    while True:
        print("\n选项:")
        print("  1. 列出所有用户")
        print("  2. 查看用户记忆")
        print("  3. 删除用户")
        print("  4. 退出")
        
        choice = input("\n请选择: ").strip()
        
        if choice == "1":
            users = list_users()
            if users:
                print(f"\n已有 {len(users)} 个用户:")
                for user in users:
                    print(f"  - {user}")
            else:
                print("\n还没有用户")
        
        elif choice == "2":
            user_id = input("输入用户名: ").strip()
            memory = view_user_memory(user_id)
            if memory:
                import json
                print(f"\n{user_id} 的记忆:")
                print(json.dumps(memory, ensure_ascii=False, indent=2))
            else:
                print(f"用户 {user_id} 不存在")
        
        elif choice == "3":
            user_id = input("输入要删除的用户名: ").strip()
            confirm = input(f"确定删除 {user_id}? (y/n): ").strip().lower()
            if confirm == "y":
                if delete_user_memory(user_id):
                    print(f"✅ 已删除用户 {user_id}")
                else:
                    print(f"用户 {user_id} 不存在")
        
        elif choice == "4":
            break
        
        else:
            print("无效选择")


def main():
    """主入口"""
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        
        if cmd == "test":
            main_test()
        elif cmd == "users":
            main_users()
        elif cmd == "help":
            print("""
MBTA Agent - 波士顿地铁助手

用法:
    python main.py          交互模式
    python main.py test     自动测试
    python main.py users    用户管理
    python main.py help     显示帮助
""")
        else:
            print(f"未知命令: {cmd}")
            print("使用 'python main.py help' 查看帮助")
    else:
        main_interactive()


if __name__ == "__main__":
    main()