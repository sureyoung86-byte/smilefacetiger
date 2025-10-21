import os
from openai import OpenAI
from dotenv import load_dotenv

# 载入环境变量
load_dotenv()

# ===== 初始化 DeepSeek 客户端 =====
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    print("⚠️ 未检测到 DEEPSEEK_API_KEY，将启用离线模式")
    client = None
else:
    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com/v1"  # DeepSeek 官方 API 地址
    )
    print("🧠 使用 DeepSeek 模型")

# ===== 主函数：解析用户意图 =====
def parse_user_intent(user_input: str):
    """
    使用 DeepSeek 模型解析用户意图。
    若未设置 API Key，则进入离线模拟模式。
    """
    # 离线模式（无 key）
    if not client:
        if "天气" in user_input:
            return '{"intent": "weather_query", "entities": {"city": "厦门", "date": "今天"}}'
        elif "出行" in user_input or "旅行" in user_input:
            return '{"intent": "travel_plan", "entities": {"city": "北京", "date": "明天"}}'
        elif "你好" in user_input:
            return '{"intent": "chitchat", "entities": {}}'
        else:
            return '{"intent": "unknown", "entities": {}}'

    # 在线模式：调用 DeepSeek
    prompt = f"""
    请从用户输入中识别意图（intent）及关键信息（entities）。
    意图类别：
    1. weather_query —— 查询天气；
    2. travel_plan —— 制定出行计划；
    3. chitchat —— 普通闲聊。
    输出 JSON 格式，例如：
    {{
      "intent": "weather_query",
      "entities": {{"city": "厦门", "date": "明天"}}
    }}
    用户输入：{user_input}
    """

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个自然语言理解模块。"},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print("❌ DeepSeek API 调用失败，进入离线模式：", e)
        if "天气" in user_input:
            return '{"intent": "weather_query", "entities": {"city": "厦门", "date": "今天"}}'
        else:
            return '{"intent": "unknown", "entities": {}}'


# ===== 本地测试入口 =====
if __name__ == "__main__":
    print("=== DeepSeek 智能体测试 ===")
    while True:
        text = input("你：")
        if text.lower() in ["退出", "exit", "quit"]:
            break
        print("→", parse_user_intent(text))
