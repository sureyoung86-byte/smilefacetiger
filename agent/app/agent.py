import json
from app.nlu import parse_user_intent
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

# 初始化 DeepSeek 客户端
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com/v1")

# 模拟天气数据（你后续可以改为真实天气 API）
def get_weather(city: str):
    fake_data = {
        "厦门": "晴，气温28°C",
        "福州": "小雨，气温25°C",
        "北京": "阴，气温20°C",
    }
    return fake_data.get(city, "暂无天气数据")

def handle_user_input(user_input: str):
    """解析用户输入并生成智能回复"""
    parsed = parse_user_intent(user_input)
    try:
        intent = json.loads(parsed)
    except:
        return f"解析失败：{parsed}"

    if intent["intent"] == "weather_query":
        entities = intent.get("entities", {})
        city = entities.get("city", "未知城市")
        date = entities.get("date", "今天")

        weather_info = get_weather(city)
        # 让 DeepSeek 帮你生成自然语言风格回复
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一位友善的智能出行助手，用自然的中文回答用户。"},
                    {"role": "user", "content": f"{date}{city}天气是：{weather_info}，请生成一句自然描述。"}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            print("❌ DeepSeek 回复生成失败：", e)
            return f"{date}{city}天气：{weather_info}"

    elif intent["intent"] == "chitchat":
        return "嗯嗯～我在呢 😊"
    else:
        return "目前我只会查天气哦～"
