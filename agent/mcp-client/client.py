import os
import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from openai import OpenAI
from dotenv import load_dotenv

# 加载 .env 中的环境变量
load_dotenv()

class MCPClient:
  def __init__(self):
    self.session: Optional[ClientSession] = None
    self.exit_stack = AsyncExitStack()
    # 初始化deepseek客户端
    self.deepseek = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com/v1"
    )
  
  # 服务器连接管理
  async def connect_to_server(self, server_script_path: str):
    """Connect to an MCP server

    Args:
        server_script_path: 服务器文件的路径
    """
    is_python = server_script_path.endswith('.py')
    if not (is_python):
        raise ValueError("服务端应该为.py文件")

    command = "python"
    server_params = StdioServerParameters(
        command=command,
        args=[server_script_path],
        env=None
    )

    # 建立和本地server的通信通道
    stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
    self.stdio, self.write = stdio_transport
    # 保存MCP会话对象
    self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

    # 初始化 MCP session
    await self.session.initialize()

    # 获取服务端可用的工具列表
    response = await self.session.list_tools()
    tools = response.tools
    print("\n连接到 server 可用的工具有:", [tool.name for tool in tools])

  # 处理查询逻辑
  async def process_query(self, query: str) -> str:
    """Process a query using DeepSeek and MCP tools"""
    
    # 1. 获取可用工具
    response = await self.session.list_tools()
    available_tools = {tool.name: tool for tool in response.tools}

    # 2. 发送给 DeepSeek
    ds_response = await self.deepseek.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": query}],
        tools=[{"name": t.name, "description": t.description} for t in response.tools]
    )

    assistant_message = ds_response.choices[0].message
    final_text = [assistant_message.content]

    # 3. 如果模型调用了工具，依次执行
    for tool_call in assistant_message.tool_calls:
        tool_name = tool_call.function.name
        tool_args = tool_call.function.arguments

        if tool_name in available_tools:
            result = await self.session.call_tool(tool_name, tool_args)
            final_text.append(f"[工具 {tool_name} 执行结果]: {result}")

            # 可以选择再把工具结果发给 DeepSeek 继续生成
            ds_response = await self.deepseek.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "user", "content": query},
                    {"role": "assistant", "content": result}
                ],
                tools=[{"name": t.name, "description": t.description} for t in response.tools]
            )
            assistant_message = ds_response.choices[0].message
            final_text.append(assistant_message.content)

    return "\n".join(final_text)

  # 交互式聊天界面
  async def chat_loop(self):

    print("\nMCP Client 已开启!")
    print("请输入文本或者输入 'quit' 来离开~~~")

    while True:
        try:
            query = input("\nQuery: ").strip()

            if query.lower() == 'quit':
                break

            response = await self.process_query(query)
            print("\n" + response)

        except Exception as e:
            print(f"\nError: {str(e)}")

  # 清空资源
  async def cleanup(self):
    await self.exit_stack.aclose()

# 主入口函数
async def main():
    if len(sys.argv) < 2:
        print("请输入服务器文件路径！")
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
