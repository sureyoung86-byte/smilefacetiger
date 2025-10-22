import os
import json
import asyncio
from openai import OpenAI
from typing import Optional
from dotenv import load_dotenv
from contextlib import AsyncExitStack
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

load_dotenv()

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

ASSISTANT_PERSONALITY = """你是一个热情、幽默、贴心的天气助手小AI,名叫"小天"。

🎯 你的职责:
- 用生动有趣的语言播报天气
- 根据天气情况给出贴心建议
- 用emoji让回复更生动
- 自然对话,不要死板地列数据

💬 说话风格:
- 轻松活泼,像朋友聊天
- 适当使用口语化表达
- 根据天气情况调整语气(晴天开心,雨天温馨提醒)
- 每次回复尽量不重复,保持新鲜感

📋 天气播报示例:
❌ 死板: "北京市,晴,温度25℃,东南风3级,湿度60%"
✅ 生动: "哇!北京今天天气超棒的☀️,25度的好天气,还有温柔的东南风吹着,湿度也刚刚好!这种天气最适合出去走走啦~"

🌟 重要原则:
1. 把JSON数据转化为自然对话
2. 根据具体天气给建议(冷了添衣,热了防晒,雨天带伞)
3. 同样的天气也要换着花样说
4. 保持热情但不啰嗦
5. 用户问什么就答什么,不要画蛇添足

记住:你不是天气播报机器,你是用户的贴心天气小助手!"""


class MCPClient:
    def __init__(self):
        """Initialize session and client objects"""
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

        # Set up LLM client
        self.llm_api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = DEEPSEEK_BASE_URL
        self.model = DEEPSEEK_MODEL
        if not self.llm_api_key:
            raise ValueError("⚠ 环境变量 'DEEPSEEK_API_KEY' 未设置")
        
        self.client = OpenAI(
            api_key=self.llm_api_key,
            base_url=self.base_url
        )

        # 对话上下文
        self.context = [
            {"role": "system", "content": ASSISTANT_PERSONALITY}
        ]

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server"""
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        
        # 🔑 传递环境变量给子进程
        server_env = os.environ.copy()
        
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=server_env
        )

        print("🔌 正在连接天气服务...")
        
        try:
            stdio_transport = await asyncio.wait_for(
                self.exit_stack.enter_async_context(stdio_client(server_params)),
                timeout=10.0
            )
            self.stdio, self.write = stdio_transport
            
            print("📡 正在初始化会话...")
            self.session = await asyncio.wait_for(
                self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write)),
                timeout=10.0
            )

            await self.session.initialize()

            # List available tools
            response = await self.session.list_tools()
            tools = response.tools
            print(f"✅ 已连接天气服务,可用功能: {len(tools)} 个")
            
        except asyncio.TimeoutError:
            print("\n❌ 连接超时!")
            print("可能的原因:")
            print("  1. server.py 启动失败")
            print("  2. .env 文件配置有误")
            print("  3. 缺少依赖包\n")
            raise
        except Exception as e:
            print(f"\n❌ 连接失败: {e}")
            raise

    async def process_query(self, query: str) -> str:
        """Process a query using DeepSeek and MCP tools"""
        # 保存用户查询
        self.context.append({"role": "user", "content": query})

        # 获取可用工具
        response = await self.session.list_tools()
        available_tools = {t.name: t for t in response.tools}

        tools_schema = [{
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.inputSchema or {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        } for t in response.tools]

        # 第一次调用 DeepSeek - 理解意图并决定是否使用工具
        ds_response = self.client.chat.completions.create(
            model=self.model,
            messages=self.context,
            tools=tools_schema,
            tool_choice="auto",
        )

        message = ds_response.choices[0].message
        
        # 转换为字典格式
        message_dict = {
            "role": "assistant",
            "content": message.content
        }
        
        # 检查是否需要调用工具
        tool_calls = getattr(message, "tool_calls", []) or []
        
        if tool_calls:
            # 添加 tool_calls 到消息
            message_dict["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments
                    }
                }
                for call in tool_calls
            ]
            self.context.append(message_dict)
            
            # 执行工具调用
            for call in tool_calls:
                name = call.function.name
                args = json.loads(call.function.arguments)
                
                if name in available_tools:
                    location = args.get('location', '未知')
                    action = "查询天气预报" if name == "get_forecast" else "查询实时天气"
                    print(f"\n🔍 正在为您{action}: {location}")
                    
                    try:
                        tool_result = await self.session.call_tool(name, args)
                        
                        # 提取工具返回的文本内容
                        if tool_result.content:
                            tool_text = ""
                            for content_item in tool_result.content:
                                if hasattr(content_item, 'text'):
                                    tool_text += content_item.text
                                else:
                                    tool_text += str(content_item)
                        else:
                            tool_text = str(tool_result)
                        
                        # 把工具结果反馈回对话上下文
                        self.context.append({
                            "role": "tool",
                            "content": tool_text,
                            "tool_call_id": call.id
                        })
                        
                    except Exception as e:
                        error_msg = f"查询失败: {str(e)}"
                        print(f"❌ {error_msg}")
                        
                        self.context.append({
                            "role": "tool",
                            "content": error_msg,
                            "tool_call_id": call.id
                        })

            # 第二次调用 DeepSeek - 生成生动的最终回答
            print("✨ 小天正在为你播报天气...\n")
            
            ds_follow = self.client.chat.completions.create(
                model=self.model,
                messages=self.context,
                temperature=0.8,  # 提高创造性
                top_p=0.9,
            )
            
            final_response = ds_follow.choices[0].message.content
            
            # 保存最终回答到上下文
            self.context.append({
                "role": "assistant",
                "content": final_response
            })
            
            return final_response
        else:
            # 没有调用工具,直接聊天
            self.context.append(message_dict)
            return message.content or "嗯...我不太确定怎么回答呢🤔"

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\n" + "="*60)
        print("🌤️  智能天气助手 - 小天 为您服务!")
        print("="*60)
        print("\n💡 使用提示:")
        print("   • 直接说城市名: 北京、上海、莆田")
        print("   • 自然提问: 北京天气怎么样、上海明天天气")
        print("   • 聊天互动: 你好、谢谢、再见")
        print("   • 输入 'quit' 退出\n")
        print("小天: 你好呀!我是你的天气小助手🌈 有什么想了解的天气吗?")
        
        while True:
            try:
                query = input("\n你: ").strip()

                if query.lower() in ['quit', 'exit', '退出', '再见']:
                    print("\n小天: 再见啦!记得关注天气,照顾好自己哦~ 👋")
                    break

                if not query:
                    continue

                response = await self.process_query(query)
                print(f"\n小天: {response}")

            except KeyboardInterrupt:
                print("\n\n小天: 好的,下次见啦! 👋")
                break
            except Exception as e:
                print(f"\n❌ 出错了: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        try:
            await self.exit_stack.aclose()
        except Exception:
            pass


async def main():
    if len(sys.argv) < 2:
        print("❌ 用法: python client.py <server_script_path>")
        print("   例如: python client.py server.py")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys
    asyncio.run(main())