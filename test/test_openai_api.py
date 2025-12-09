"""
测试 OpenAI GPT-4o API
运行方式: python test_openai_api.py
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

# 加载环境变量
load_dotenv()

# 初始化客户端（自动读取 OPENAI_API_KEY）
client = OpenAI()


def test_basic_chat():
    """测试 1: 基础对话"""
    print("\n" + "=" * 50)
    print("测试 1: 基础对话")
    print("=" * 50)
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": "你好！请用一句话介绍你自己。"}
        ]
    )
    
    print(f"\n用户: 你好！请用一句话介绍你自己。")
    print(f"GPT-4o: {response.choices[0].message.content}")


def test_system_prompt():
    """测试 2: 带 System Prompt 的对话"""
    print("\n" + "=" * 50)
    print("测试 2: System Prompt")
    print("=" * 50)
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system", 
                "content": "你是波士顿地铁助手，用简洁友好的中文回答问题。"
            },
            {
                "role": "user", 
                "content": "红线是什么？"
            }
        ]
    )
    
    print(f"\nSystem: 你是波士顿地铁助手...")
    print(f"用户: 红线是什么？")
    print(f"GPT-4o: {response.choices[0].message.content}")


def test_multi_turn():
    """测试 3: 多轮对话"""
    print("\n" + "=" * 50)
    print("测试 3: 多轮对话")
    print("=" * 50)
    
    messages = [
        {"role": "system", "content": "你是一个helpful助手。"},
        {"role": "user", "content": "我叫小明"},
        {"role": "assistant", "content": "你好小明！很高兴认识你。有什么我可以帮助你的吗？"},
        {"role": "user", "content": "我叫什么名字？"}
    ]
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )
    
    print(f"\n用户: 我叫小明")
    print(f"GPT-4o: 你好小明！很高兴认识你...")
    print(f"用户: 我叫什么名字？")
    print(f"GPT-4o: {response.choices[0].message.content}")


def test_function_calling():
    """测试 4: Function Calling（工具调用）- Agent 核心功能"""
    print("\n" + "=" * 50)
    print("测试 4: Function Calling（工具调用）")
    print("=" * 50)
    
    # 定义工具
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_next_train",
                "description": "获取某个地铁站的下一班列车到站时间",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "stop_name": {
                            "type": "string",
                            "description": "站点名称，如 Harvard, Park Street"
                        },
                        "route": {
                            "type": "string",
                            "description": "线路名称，如 Red, Green-B, Orange",
                            "enum": ["Red", "Orange", "Blue", "Green-B", "Green-C", "Green-D", "Green-E"]
                        }
                    },
                    "required": ["stop_name"]
                }
            }
        }
    ]
    
    # 用户问题
    user_message = "Harvard 红线下一班车什么时候到？"
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "你是波士顿地铁助手。"},
            {"role": "user", "content": user_message}
        ],
        tools=tools
    )
    
    message = response.choices[0].message
    
    print(f"\n用户: {user_message}")
    
    # 检查是否调用了工具
    if message.tool_calls:
        print(f"\n✅ GPT-4o 决定调用工具:")
        for tool_call in message.tool_calls:
            print(f"   函数名: {tool_call.function.name}")
            print(f"   参数: {tool_call.function.arguments}")
    else:
        print(f"GPT-4o: {message.content}")


def test_function_calling_complete():
    """测试 5: 完整的 Function Calling 流程"""
    print("\n" + "=" * 50)
    print("测试 5: 完整 Function Calling 流程")
    print("=" * 50)
    
    import json
    
    # 模拟的工具函数
    def fake_get_next_train(stop_name, route=None):
        """模拟获取下一班车（实际项目中会调用 MBTA API）"""
        return {
            "stop": stop_name,
            "route": route or "Red",
            "next_arrival": "3 分钟后",
            "direction": "Alewife"
        }
    
    # 定义工具 schema
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_next_train",
                "description": "获取某个地铁站的下一班列车到站时间",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "stop_name": {"type": "string", "description": "站点名称"},
                        "route": {"type": "string", "description": "线路名称"}
                    },
                    "required": ["stop_name"]
                }
            }
        }
    ]
    
    messages = [
        {"role": "system", "content": "你是波士顿地铁助手，用中文简洁回答。"},
        {"role": "user", "content": "Harvard 红线下一班什么时候到？"}
    ]
    
    print(f"\n用户: Harvard 红线下一班什么时候到？")
    
    # 第一次调用：GPT 决定是否使用工具
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools
    )
    
    assistant_message = response.choices[0].message
    
    if assistant_message.tool_calls:
        print(f"\n🔧 GPT-4o 调用工具: {assistant_message.tool_calls[0].function.name}")
        
        # 执行工具
        tool_call = assistant_message.tool_calls[0]
        args = json.loads(tool_call.function.arguments)
        print(f"   参数: {args}")
        
        # 调用模拟函数
        result = fake_get_next_train(**args)
        print(f"   结果: {result}")
        
        # 把工具结果返回给 GPT
        messages.append(assistant_message)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(result, ensure_ascii=False)
        })
        
        # 第二次调用：GPT 根据工具结果生成回答
        final_response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        
        print(f"\n📢 GPT-4o: {final_response.choices[0].message.content}")
    else:
        print(f"GPT-4o: {assistant_message.content}")


def test_streaming():
    """测试 6: 流式输出"""
    print("\n" + "=" * 50)
    print("测试 6: 流式输出 (Streaming)")
    print("=" * 50)
    
    print(f"\n用户: 用3句话介绍波士顿地铁")
    print(f"GPT-4o: ", end="", flush=True)
    
    stream = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": "用3句话介绍波士顿地铁"}
        ],
        stream=True  # 开启流式
    )
    
    for chunk in stream:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
    
    print()  # 换行


def main():
    print("=" * 50)
    print("🤖 OpenAI GPT-4o API 测试")
    print("=" * 50)
    
    # 检查 API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n❌ 错误: 未找到 OPENAI_API_KEY")
        print("请在 .env 文件中添加: OPENAI_API_KEY=sk-xxx")
        return
    
    print(f"\n✅ API Key 已配置: {api_key[:8]}...{api_key[-4:]}")
    
    try:
        test_basic_chat()
        test_system_prompt()
        test_multi_turn()
        test_function_calling()
        test_function_calling_complete()
        test_streaming()
        
        print("\n" + "=" * 50)
        print("✅ 所有测试完成！")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        print("\n可能的原因:")
        print("  1. API Key 无效")
        print("  2. 账户余额不足")
        print("  3. 网络问题")


if __name__ == "__main__":
    main()