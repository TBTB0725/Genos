"""
Agent 核心类
基于 GPT-4o 的智能助手，支持工具调用和长期记忆

记忆系统：
=========
1. 短期记忆：self.messages（当前会话）
2. 长期记忆：memory/{user_id}.json（跨会话持久化）
"""
import json
import os
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# 记忆文件存储目录
MEMORY_DIR = "memory"


class Agent:
    """
    AI Agent 核心类
    
    属性：
        client: OpenAI 客户端
        model: 使用的模型
        user_id: 用户 ID
        messages: 对话历史（短期记忆）
        user_memory: 用户长期记忆
        tools: 工具函数字典
        tool_schemas: 工具定义列表
    """
    
    def __init__(self, user_id: str = "default", system_prompt: str = None):
        """
        初始化 Agent
        
        参数:
            user_id: 用户 ID，用于区分不同用户的记忆
            system_prompt: 系统提示词（可选）
        """
        self.client = OpenAI()
        self.model = "gpt-4o"
        self.user_id = user_id
        
        # 工具注册表
        self.tools = {}
        self.tool_schemas = []
        
        # 长期记忆
        self.user_memory = self._load_memory()
        
        # 短期记忆（对话历史）
        self.messages = []
        
        # 设置系统提示词（包含用户个性化信息）
        self.system_prompt = system_prompt or self._build_system_prompt()
        self.messages.append({
            "role": "system",
            "content": self.system_prompt
        })
    
    # ============================================================
    # 长期记忆管理
    # ============================================================
    
    def _get_memory_path(self) -> str:
        """获取用户记忆文件路径"""
        return os.path.join(MEMORY_DIR, f"{self.user_id}.json")
    
    def _load_memory(self) -> dict:
        """加载用户长期记忆"""
        memory_path = self._get_memory_path()
        
        if os.path.exists(memory_path):
            with open(memory_path, "r", encoding="utf-8") as f:
                return json.load(f)
        
        # 新用户，创建默认记忆结构
        return {
            "user_id": self.user_id,
            "created_at": datetime.now().isoformat(),
            "preferences": {
                "language": None,          # 偏好语言，None 表示自动检测
                "home_station": None,      # 家的站点 ID
                "home_station_name": None, # 家的站点名称
                "work_station": None,      # 公司的站点 ID
                "work_station_name": None, # 公司的站点名称
                "preferred_line": None,    # 常用线路
                "preferred_direction": None # 常用方向
            },
            "facts": [],  # 关于用户的事实，如 "住在 Cambridge"
            "conversation_count": 0,
            "last_conversation": None
        }
    
    def _save_memory(self):
        """保存用户长期记忆到文件"""
        os.makedirs(MEMORY_DIR, exist_ok=True)
        memory_path = self._get_memory_path()
        
        with open(memory_path, "w", encoding="utf-8") as f:
            json.dump(self.user_memory, f, ensure_ascii=False, indent=2)
    
    def set_preference(self, key: str, value):
        """
        设置用户偏好
        
        参数:
            key: 偏好键，如 "home_station", "language"
            value: 偏好值
        
        示例:
            agent.set_preference("home_station", "place-harsq")
            agent.set_preference("home_station_name", "Harvard")
        """
        if key in self.user_memory["preferences"]:
            self.user_memory["preferences"][key] = value
            self._save_memory()
            return True
        return False
    
    def get_preference(self, key: str):
        """获取用户偏好"""
        return self.user_memory["preferences"].get(key)
    
    def add_fact(self, fact: str):
        """
        添加关于用户的事实
        
        参数:
            fact: 事实描述，如 "用户住在 Cambridge"
        """
        if fact not in self.user_memory["facts"]:
            self.user_memory["facts"].append(fact)
            self._save_memory()
    
    def get_memory_summary(self) -> str:
        """获取记忆摘要（用于调试）"""
        prefs = self.user_memory["preferences"]
        facts = self.user_memory["facts"]
        
        lines = [
            f"用户: {self.user_id}",
            f"对话次数: {self.user_memory['conversation_count']}",
            f"偏好语言: {prefs['language'] or '自动检测'}",
            f"家: {prefs['home_station_name'] or '未设置'}",
            f"公司: {prefs['work_station_name'] or '未设置'}",
            f"常用线路: {prefs['preferred_line'] or '未设置'}",
        ]
        
        if facts:
            lines.append(f"已知事实: {', '.join(facts)}")
        
        return "\n".join(lines)
    
    # ============================================================
    # System Prompt 构建
    # ============================================================
    
    def _build_system_prompt(self) -> str:
        """构建包含用户个性化信息的系统提示词"""
        
        base_prompt = """You are Genos, a helpful Boston subway assistant.

## Language
- Detect the user's language from their message
- Always reply in the same language the user uses
- 如果用户说中文，你就用中文回复
- If the user speaks English, reply in English

## Your Role
1. Answer questions about Boston subway (MBTA)
2. Query real-time train arrival times
3. Provide route and station information
4. Remember user preferences (home, work, etc.)

## Response Style
- Be concise and friendly
- Give direct answers
- If a query fails, explain and suggest alternatives

## CRITICAL: Handling No Data / Service Disruptions
When a tool returns has_data=False or empty predictions:
1. DO NOT make up or guess train times
2. Tell the user honestly that no data is available
3. Call get_alerts() to check for service disruptions
4. Explain possible reasons (maintenance, not operating hours, service suspended)
5. Suggest alternatives if possible

Example response when no data:
"抱歉，当前没有 Green-B 线的列车数据。让我查一下是否有服务警报..."
[Then call get_alerts("Green-B")]
"Green-B 线目前因维修暂停服务，预计恢复时间为..."

## MBTA Knowledge

### Lines
- Red Line: Alewife ↔ Ashmont/Braintree
- Orange Line: Oak Grove ↔ Forest Hills  
- Blue Line: Wonderland ↔ Bowdoin
- Green Line: B/C/D/E branches

### Common Station IDs
- Harvard Square (Red): place-harsq
- Harvard Avenue (Green-B): place-harvd
- Park Street (Red/Green): place-pktrm
- Kendall/MIT (Red): place-knncl
- Downtown Crossing (Red/Orange): place-dwnxg
- South Station (Red): place-sstat
- North Station (Orange/Green): place-north
- Babcock Street (Green-B): place-babck
- Copley (Green): place-coecl
- Alewife (Red): place-alfcl
- BU Central (Green-B): place-bucer

### Handling Ambiguous Stations
When user mentions a station name:
1. If context is clear (e.g., "Harvard on Red Line") → use directly
2. If ambiguous → use search_stops first
3. If multiple results → ask user to clarify

## Learning User Preferences
If user mentions:
- "我家在 XXX" / "I live near XXX" → Remember as home_station
- "我在 XXX 上班" / "I work at XXX" → Remember as work_station
- "回家" / "go home" → Use remembered home_station
- "去上班" / "go to work" → Use remembered work_station

When you learn new preferences, tell the user you've remembered it."""

        # 添加用户个性化信息
        prefs = self.user_memory["preferences"]
        facts = self.user_memory["facts"]
        
        user_info_parts = []
        
        if prefs["language"]:
            user_info_parts.append(f"- Preferred language: {prefs['language']}")
        
        if prefs["home_station_name"]:
            user_info_parts.append(
                f"- Home station: {prefs['home_station_name']} (ID: {prefs['home_station']})"
            )
        
        if prefs["work_station_name"]:
            user_info_parts.append(
                f"- Work station: {prefs['work_station_name']} (ID: {prefs['work_station']})"
            )
        
        if prefs["preferred_line"]:
            user_info_parts.append(f"- Preferred line: {prefs['preferred_line']}")
        
        if facts:
            user_info_parts.append(f"- Known facts: {'; '.join(facts)}")
        
        if user_info_parts:
            user_section = "\n\n## User Information (from memory)\n" + "\n".join(user_info_parts)
            base_prompt += user_section
        
        return base_prompt
    
    # ============================================================
    # 工具管理
    # ============================================================
    
    def register_tool(self, name: str, func: callable, schema: dict):
        """注册一个工具"""
        self.tools[name] = func
        self.tool_schemas.append(schema)
    
    def register_tools(self, tools_config: list):
        """批量注册工具"""
        for name, func, schema in tools_config:
            self.register_tool(name, func, schema)
    
    def _call_tool(self, name: str, arguments: dict) -> str:
        """调用工具"""
        if name not in self.tools:
            return json.dumps({"error": f"未知工具: {name}"})
        
        try:
            result = self.tools[name](**arguments)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    # ============================================================
    # 对话核心
    # ============================================================
    
    def chat(self, user_message: str) -> str:
        """
        与 Agent 对话
        
        参数:
            user_message: 用户消息
        
        返回:
            Agent 的回复
        """
        # 添加用户消息
        self.messages.append({
            "role": "user",
            "content": user_message
        })
        
        # 调用 GPT
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=self.tool_schemas if self.tool_schemas else None
        )
        
        assistant_message = response.choices[0].message
        
        # 处理工具调用
        while assistant_message.tool_calls:
            self.messages.append(assistant_message)
            
            for tool_call in assistant_message.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)
                
                print(f"  🔧 调用工具: {func_name}({func_args})")
                
                result = self._call_tool(func_name, func_args)
                
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=self.tool_schemas if self.tool_schemas else None
            )
            
            assistant_message = response.choices[0].message
        
        # 保存回复
        self.messages.append({
            "role": "assistant",
            "content": assistant_message.content
        })
        
        # 更新对话统计
        self.user_memory["conversation_count"] += 1
        self.user_memory["last_conversation"] = datetime.now().isoformat()
        self._save_memory()
        
        return assistant_message.content
    
    def run(self, user_message: str) -> str:
        """chat() 的别名"""
        return self.chat(user_message)
    
    def clear_history(self):
        """清空当前对话历史（保留系统提示词）"""
        self.messages = [{
            "role": "system",
            "content": self.system_prompt
        }]
    
    def get_history(self) -> list:
        """获取对话历史"""
        return self.messages.copy()


# ============================================================
# 便捷函数
# ============================================================

def list_users() -> list:
    """列出所有已知用户"""
    if not os.path.exists(MEMORY_DIR):
        return []
    
    users = []
    for filename in os.listdir(MEMORY_DIR):
        if filename.endswith(".json"):
            users.append(filename[:-5])  # 去掉 .json
    return users


def delete_user_memory(user_id: str) -> bool:
    """删除用户记忆"""
    memory_path = os.path.join(MEMORY_DIR, f"{user_id}.json")
    if os.path.exists(memory_path):
        os.remove(memory_path)
        return True
    return False


def view_user_memory(user_id: str) -> dict:
    """查看用户记忆"""
    memory_path = os.path.join(MEMORY_DIR, f"{user_id}.json")
    if os.path.exists(memory_path):
        with open(memory_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 Agent 长期记忆测试")
    print("=" * 50)
    
    # 创建带用户 ID 的 Agent
    agent = Agent(user_id="test_user")
    
    # 显示初始记忆
    print("\n📌 初始记忆状态:")
    print(agent.get_memory_summary())
    
    # 测试设置偏好
    print("\n📌 设置偏好:")
    agent.set_preference("home_station", "place-harsq")
    agent.set_preference("home_station_name", "Harvard")
    agent.set_preference("work_station", "place-knncl")
    agent.set_preference("work_station_name", "Kendall/MIT")
    agent.set_preference("language", "zh")
    agent.add_fact("住在 Cambridge")
    
    print(agent.get_memory_summary())
    
    # 测试对话
    print("\n📌 测试对话:")
    response = agent.chat("你好！")
    print(f"Agent: {response}")
    
    # 显示记忆文件内容
    print("\n📌 记忆文件内容:")
    memory = view_user_memory("test_user")
    print(json.dumps(memory, ensure_ascii=False, indent=2))
    
    # 列出所有用户
    print("\n📌 所有用户:")
    print(list_users())
    
    print("\n" + "=" * 50)
    print("✅ 测试完成")
    print("=" * 50)