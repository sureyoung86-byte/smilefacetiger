from flask import Flask, request, jsonify
import requests  # 用于发送HTTP请求到豆包API

app = Flask(__name__)

# 配置豆包API信息（替换为你的实际凭证）
DOUBAO_API_KEY = "你的豆包API Key"
DOUBAO_API_URL = "https://api.doubao.com/chat/completions"  # 以官方实际地址为准

# 允许跨域请求（前端和后端不在同一域名时需要）
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')  # 生产环境需指定具体域名
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    return response

# 处理前端的对话请求
@app.route('/api/chat', methods=['POST'])
def chat():
    # 1. 获取前端发送的用户消息
    user_input = request.json.get('content')
    if not user_input:
        return jsonify({"reply": "请输入消息内容"})

    try:
        # 2. 调用豆包API（按官方文档格式构造请求）
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DOUBAO_API_KEY}"  # 认证方式以官方要求为准
        }
        # 构造请求体（多轮对话需包含历史消息，这里简化为单轮）
        data = {
            "prompt": user_input,
            "model": "doubao-pro"  # 模型名称以官方提供为准
        }
        # 发送请求到豆包API
        response = requests.post(DOUBAO_API_URL, json=data, headers=headers)
        response_data = response.json()

        # 3. 解析豆包返回的回复（格式以官方响应为准）
        # 假设响应格式为 {"result": "豆包的回复内容"}
        doubao_reply = response_data.get("result", "抱歉，暂时无法回复")
        return jsonify({"reply": doubao_reply})

    except Exception as e:
        return jsonify({"reply": f"接口调用失败：{str(e)}"})

# 启动后端服务
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)  # 服务运行在 http://localhost:5000