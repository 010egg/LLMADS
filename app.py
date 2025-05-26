# -*- coding: utf-8 -*-
"""
启动后端：
    python app.py
依赖：
    pip install flask flask-cors requests
"""

from flask import Flask, request, Response, render_template, jsonify
from flask_cors import CORS
import requests, json, uuid, functools
from config import API_KEY, BASE_URL, DEFAULT_USER
import json
import os
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
os.environ.pop("all_proxy", None)
url = "http://localhost/v1/chat-messages"
print("http_proxy:", os.environ.get("http_proxy"))
print("all_proxy:", os.environ.get("all_proxy"))
print("https_proxy:", os.environ.get("https_proxy"))


app = Flask(__name__, template_folder="templates")
CORS(app)

HEADERS = {"Authorization": f"Bearer {API_KEY}"}

# ---------- 工具函数 ----------
def backend(method, path, **kwargs):
    """代理到真正的 Dify API"""
    url = f"{BASE_URL}{path}"
    kwargs.setdefault("headers", {}).update(HEADERS)
    return requests.request(method, url, **kwargs)

def require_user(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        uid = request.args.get("user") or request.json.get("user") \
              if request.is_json else request.json
        if not uid:
            uid = DEFAULT_USER
        request.user_id = uid
        return func(*args, **kwargs)
    return wrapper

# ---------- 前端页面 ----------
@app.route("/")
def index():
    return render_template("index.html", user_id=DEFAULT_USER)

# ---------- 会话相关 ----------
@app.route("/api/conversations")
@require_user
def conversations():
    params = {
        "user": request.user_id,
        "limit": request.args.get("limit", 20),
        "last_id": request.args.get("last_id", ""),
        "sort_by": "-updated_at"
    }
    r = backend("GET", "/conversations", params=params)
    return jsonify(r.json()), r.status_code

@app.route("/api/messages")
@require_user
def messages():
    params = {
        "conversation_id": request.args["conversation_id"],
        "user": request.user_id,
        "limit": request.args.get("limit", 20),
        "first_id": request.args.get("first_id")
    }
    r = backend("GET", "/messages", params=params)
    return jsonify(r.json()), r.status_code

# ---------- SSE 聊天 ----------
def sse_stream(user_query, conversation_id, user_id):
    payload = {
        "inputs": {},
        "query": user_query,
        "response_mode": "streaming",
        "conversation_id": conversation_id,
        "user": user_id
    }
    with backend("POST", "/chat-messages",
                 json=payload, stream=True) as r:
        current_task = None
        for line in r.iter_lines():
            if not line or not line.startswith(b"data: "):
                continue
            evt = json.loads(line[6:])
            # 记下 task_id，供停止调用
            if evt.get("event") in ("workflow_started", "message"):
                current_task = evt.get("task_id") or current_task
            yield f"data: {json.dumps(evt)}\n\n"
        # 流关闭后把 task_id 发回前端，方便立即再次 stop
        if current_task:
            meta = {"event": "local_stream_closed", "task_id": current_task}
            yield f"data: {json.dumps(meta)}\n\n"

@app.route("/api/chat_stream", methods=["POST"])
@require_user
def chat_stream():
    body = request.get_json()
    query_txt = body.get("query", "")
    conv_id   = body.get("conversation_id", "")
    return Response(
        sse_stream(query_txt, conv_id, request.user_id),
        mimetype="text/event-stream"
    )

# ---------- 停止 ----------
@app.route("/api/stop", methods=["POST"])
@require_user
def stop():
    data = request.get_json()
    task_id = data["task_id"]
    payload = {"user": request.user_id}
    r = backend("POST", f"/chat-messages/{task_id}/stop", json=payload)
    return jsonify(r.json()), r.status_code

# ---------- 反馈（点赞/点踩/撤销） ----------
@app.route("/api/feedback/<message_id>", methods=["POST"])
@require_user
def feedback(message_id):
    data = request.get_json()
    payload = {
        "rating": data["rating"],     # like / dislike / null
        "content": data.get("content", ""),
        "user": request.user_id
    }
    r = backend("POST", f"/messages/{message_id}/feedbacks", json=payload)
    return jsonify(r.json()), r.status_code

# ---------- 简易重发 ----------
@app.route("/api/resend", methods=["POST"])
@require_user
def resend():
    data = request.get_json()
    query_txt = data["query"]
    conv_id   = data["conversation_id"]
    # 直接复用 chat_stream 逻辑
    return Response(
        sse_stream(query_txt, conv_id, request.user_id),
        mimetype="text/event-stream"
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, threaded=True, debug=True)
