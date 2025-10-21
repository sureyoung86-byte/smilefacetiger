def get_weather(city: str, date: str = "今天") -> str:
    """模拟天气查询函数，可扩展为真实API调用"""
    fake_weather = {
        "厦门": "晴，气温28°C",
        "福州": "小雨，气温25°C"
    }
    info = fake_weather.get(city, "暂无天气数据")
    return f"{date}{city}天气：{info}"
