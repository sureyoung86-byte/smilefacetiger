from server.tools.weather import get_weather

TOOLS = {
    "get_weather": get_weather,
}

def call_tool(name: str, **kwargs):
    if name not in TOOLS:
        return f"未找到工具 {name}"
    try:
        return TOOLS[name](**kwargs)
    except Exception as e:
        return f"调用工具出错：{e}"
