import httpx
import os
import sys
import json
import re
from typing import Any, Optional
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("weather")

# Constants
AMAP_API_KEY = os.getenv("AMAP_API_KEY")
AMAP_BASE_URL = "https://restapi.amap.com/v3"

# 调试模式
DEBUG = os.getenv("MCP_DEBUG", "false").lower() == "true"

def debug_log(message: str):
    """安全的调试日志 - 只写入 stderr"""
    if DEBUG:
        sys.stderr.write(f"[DEBUG] {message}\n")
        sys.stderr.flush()


async def make_amap_request(url: str) -> dict[str, Any] | None:
    """统一请求函数"""
    async with httpx.AsyncClient() as client:
        try:
            sys.stderr.write(f"[API请求] {url[:100]}...\n")
            sys.stderr.flush()
            
            response = await client.get(url, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            
            status = data.get("status")
            infocode = data.get("infocode")
            
            sys.stderr.write(f"[API返回] status={status}, infocode={infocode}\n")
            sys.stderr.flush()
            
            if status != "1":
                info = data.get("info", "未知错误")
                sys.stderr.write(f"[ERROR] API返回错误: {info}\n")
                sys.stderr.flush()
                return None
            
            return data
            
        except Exception as e:
            sys.stderr.write(f"[ERROR] 请求失败: {e}\n")
            sys.stderr.flush()
            return None


with open('city_adcode_map.json', 'r', encoding='utf-8') as f:
    CITY_ADCODE_MAP = json.load(f)

def normalize_city_name(location: str) -> str:
    """标准化城市名称"""
    location = location.strip()
    location = re.sub(r'[市省自治区特别行政区]', '', location)

    # 处理常见的城市别名和拼音
    synonym_map = {
        "帝都": "北京", "魔都": "上海", "南京城": "南京", "深城": "深圳", "杭城": "杭州"
    }

    location = synonym_map.get(location, location)  # 获取同义词映射

    if location in CITY_ADCODE_MAP:
        return location
    else:
        return location.lower()

async def get_adcode(city_name: str) -> Optional[str]:
    """获取城市的 adcode"""
    # 尝试从本地映射中查找
    normalized_city = normalize_city_name(city_name)
    
    # 从本地映射文件获取 adcode
    adcode = CITY_ADCODE_MAP.get(normalized_city)
    
    if not adcode:
        # 如果没有找到，调用外部 API
        if not AMAP_API_KEY:
            return None
        url = f"{AMAP_BASE_URL}/geocode/geo?key={AMAP_API_KEY}&address={normalized_city}&city="
        data = await make_amap_request(url)
        if not data or data.get("status") != "1":
            return None
        geocodes = data.get("geocodes", [])
        if not geocodes:
            return None
        adcode = geocodes[0].get("adcode")
    
    return adcode


def generate_weather_emoji(weather_text: str) -> str:
    """根据天气状况返回对应的emoji"""
    if "晴" in weather_text:
        return "☀️"
    elif "云" in weather_text or "阴" in weather_text:
        return "☁️"
    elif "雨" in weather_text:
        return "🌧️"
    elif "雪" in weather_text:
        return "❄️"
    elif "雷" in weather_text:
        return "⛈️"
    elif "雾" in weather_text or "霾" in weather_text:
        return "🌫️"
    else:
        return "🌤️"


@mcp.tool()
async def get_weather(location: str) -> str:
    """
    获取指定城市的实时天气信息
    
    智能特性:
    - 自动识别中文/拼音/英文城市名
    - 自动去除"市"、"省"等后缀
    - 支持自然语言查询
    
    参数:
        location: 城市名称,支持中文、拼音、英文
    
    返回:
        JSON格式的天气数据
    """
    if not AMAP_API_KEY:
        return "❌ 系统配置错误: 未设置高德地图API Key"
    
    # 从自然语言中提取城市名
    location = re.sub(r'(的)?(天气|气温|温度)(怎么样|如何|咋样)?', '', location).strip()
    
    sys.stderr.write(f"\n[查询天气] 原始输入: {location}\n")
    sys.stderr.flush()
    
    # 获取 adcode
    adcode = await get_adcode(location)
    if not adcode:
        return f"❌ 找不到城市: {location}"
    
    # 查询天气
    url = f"{AMAP_BASE_URL}/weather/weatherInfo?key={AMAP_API_KEY}&city={adcode}&extensions=base"
    
    data = await make_amap_request(url)
    
    if not data or data.get("status") != "1":
        return f"❌ 无法获取 {location} 的天气信息"
    
    lives = data.get("lives", [])
    if not lives:
        return f"❌ 没有可用的天气数据: {location}"
    
    live = lives[0]
    
    # 提取数据
    weather_data = {
        "city": live.get("city", location),
        "weather": live.get("weather", "未知"),
        "temperature": live.get("temperature", "未知"),
        "wind": f"{live.get('winddirection', '未知')}风 {live.get('windpower', '未知')}级",
        "humidity": f"{live.get('humidity', '未知')}%",
        "reporttime": live.get("reporttime", "未知"),
        "emoji": generate_weather_emoji(live.get("weather", ""))
    }
    
    # 返回JSON格式
    return json.dumps(weather_data, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_forecast(location: str) -> str:
    """
    获取指定城市未来几天的天气预报
    
    参数:
        location: 城市名称
    
    返回:
        未来3-4天的天气预报(JSON格式)
    """
    if not AMAP_API_KEY:
        return "❌ 系统配置错误: 未设置高德地图API Key"
    
    # 清理自然语言
    location = re.sub(r'(的)?(未来|明天|后天)?(天气|预报|情况)(怎么样|如何)?', '', location).strip()
    
    sys.stderr.write(f"\n[查询预报] 原始输入: {location}\n")
    sys.stderr.flush()
    
    # 获取 adcode
    adcode = await get_adcode(location)
    if not adcode:
        return f"❌ 找不到城市: {location}"
    
    # 查询天气预报
    url = f"{AMAP_BASE_URL}/weather/weatherInfo?key={AMAP_API_KEY}&city={adcode}&extensions=all"
    
    data = await make_amap_request(url)
    
    if not data or data.get("status") != "1":
        return f"❌ 无法获取 {location} 的天气预报"
    
    forecasts = data.get("forecasts", [])
    if not forecasts:
        return f"❌ 没有可用的预报数据: {location}"
    
    forecast = forecasts[0]
    city = forecast.get("city", location)
    casts = forecast.get("casts", [])
    
    if not casts:
        return f"❌ 没有可用的预报数据"
    
    # 构建预报数据
    forecast_data = {
        "city": city,
        "report_time": forecast.get("reporttime", "未知"),
        "days": []
    }
    
    for cast in casts[:4]:  # 只取前4天
        day_data = {
            "date": cast.get("date", ""),
            "week": cast.get("week", ""),
            "dayweather": cast.get("dayweather", ""),
            "nightweather": cast.get("nightweather", ""),
            "daytemp": cast.get("daytemp", ""),
            "nighttemp": cast.get("nighttemp", ""),
            "daywind": cast.get("daywind", ""),
            "daypower": cast.get("daypower", ""),
            "nightwind": cast.get("nightwind", ""),
            "nightpower": cast.get("nightpower", ""),
            "emoji_day": generate_weather_emoji(cast.get("dayweather", "")),
            "emoji_night": generate_weather_emoji(cast.get("nightweather", ""))
        }
        forecast_data["days"].append(day_data)
    
    # 返回JSON格式
    return json.dumps(forecast_data, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # 启动信息输出到 stderr
    sys.stderr.write("🌤️ 智能天气助手启动中...\n")
    sys.stderr.write(f"API Key 状态: {'✅ 已配置' if AMAP_API_KEY else '❌ 未配置'}\n")
    sys.stderr.flush()
    
    if not AMAP_API_KEY:
        sys.stderr.write("\n⚠️ 警告: 未配置 AMAP_API_KEY\n")
        sys.stderr.write("请访问 https://console.amap.com/dev/key/app 获取 API Key\n\n")
        sys.stderr.flush()
    
    # 启动服务器
    mcp.run(transport="stdio")