import os
import socksio
from flask import Flask, render_template, request, jsonify
import markdown
from openai import OpenAI
import logging
import os

# 移除HTTP_PROXY/HTTPS_PROXY环境变量
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

#todo 还需要支持能够基于会话上下文进行思考的能力
#todo 支持能够将数据存储起来，查看历史对话的能力，切能继续历史对话等
#todo 流式的输出能力，能够快速看到思维链路
#todo 如何部署到云服务器上去呢




# 配置 DeepSeek API 密钥和地址 (示例写死，实际请放到安全位置或环境变量)
client = OpenAI(api_key="sk-d06561b222dc4f4aa0d2a311c968de6a", base_url="https://api.deepseek.com")

@app.route("/", methods=["GET"])
def index():
    """
    返回前端主页面(index.html)
    """
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat_api():
    """
    接收前端发送的 JSON 请求，调用 DeepSeek，然后返回 JSON 格式的结果。
    """
    try:
        data = request.get_json()
        user_input = data.get("user_input", "").strip()
        if not user_input:
            return jsonify({"error": "user_input is empty"}), 400

        # 调用 DeepSeek API
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": user_input},
            ],
            stream=False
        )
        # 提取结果
        result_text = response.choices[0].message.content

        # 将结果从 Markdown 转为 HTML (可选)
        result_html = markdown.markdown(result_text)

        return jsonify({"html": result_html, "raw": result_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # 启动 Flask 开发服务器
    # host='0.0.0.0' 方便在局域网中其他设备访问，或改为默认 127.0.0.1
    app.run(host='0.0.0.0', port=5001, debug=True)
