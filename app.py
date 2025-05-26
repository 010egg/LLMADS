import requests
import json
import os
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
os.environ.pop("all_proxy", None)
url = "http://localhost/v1/chat-messages"
print("http_proxy:", os.environ.get("http_proxy"))
print("all_proxy:", os.environ.get("all_proxy"))
print("https_proxy:", os.environ.get("https_proxy"))
from flask import Flask, Response, request, render_template
from flask_cors import CORS
import requests
import json

app = Flask(__name__, template_folder="templates")
CORS(app)  # 若前端与后端同源，可去掉

# ========= 核心：把第三方 LLM 的 SSE 流转回来 =========
def stream_chat_messages(user_query: str):
    """
    从 http://localhost/v1/chat-messages 取得 SSE，
    只把 event == 'message' 的 'answer' 字段转发给浏览器
    """
    url = "http://localhost/v1/chat-messages"
    headers = {
        "Authorization": "Bearer app-BZyUkORKOq6H3X23WcVQ0E4f",
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": {},
        "query": user_query,
        "response_mode": "streaming",
        "conversation_id": "",
        "user": "chengzhe"
    }
    proxies = {"http": None, "https": None}

    with requests.post(url, headers=headers,
                       data=json.dumps(payload),
                       proxies=proxies, stream=True) as r:
        for raw_line in r.iter_lines():
            if not raw_line:
                continue
            if raw_line.startswith(b"data: "):
                try:
                    evt = json.loads(raw_line[6:].decode("utf-8"))
                    if evt.get("event") == "message":
                        answer = evt.get("answer", "")
                        yield f"data: {answer}\n\n"
                except json.JSONDecodeError:
                    continue

# ========= 路由 =========
@app.route("/", methods=["GET"])
def index():
    """前端页面"""
    return render_template("index.html")

@app.route("/chat_stream", methods=["POST"])
def chat_stream():
    """
    浏览器 fetch('/chat_stream') 后，
    返回 text/event-stream，正文为 SSE 数据
    """
    body = request.get_json(force=True, silent=True) or {}
    user_query = body.get("query", "")
    return Response(stream_chat_messages(user_query),
                    mimetype="text/event-stream")

if __name__ == "__main__":
    # threaded=True 允许多并发；debug=True 可热重载
    app.run(host="0.0.0.0", port=5001, threaded=True, debug=True)


