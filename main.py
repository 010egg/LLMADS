import os
import logging
import markdown
from flask import Flask, render_template, request, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from openai import OpenAI
from pdf2image import convert_from_path
import pytesseract

# 打印当前 HTTP_PROXY 设置（如有）
http_proxy = os.environ.get("HTTP_PROXY")
https_proxy = os.environ.get("HTTPS_PROXY")
print("当前 HTTP_PROXY:", http_proxy)
print("当前 HTTPS_PROXY:", https_proxy)

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
# 配置 SQLite 数据库文件路径，数据库文件保存在当前目录下
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///chat.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
def extract_text_from_pdf(pdf_path, lang='eng'):
    # 将 PDF 的所有页转换为图像（默认 DPI 为 200，可根据需要调整）
    images = convert_from_path(pdf_path, dpi=200)
    full_text = ""
    for i, image in enumerate(images):
        # 对每个图像使用 Tesseract OCR 提取文本
        text = pytesseract.image_to_string(image, lang=lang)
        full_text += f"--- Page {i+1} ---\n" + text + "\n"
    return full_text
# ----------------- 数据库模型 -----------------
class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, default="新会话")
    messages = db.relationship('Message', backref='conversation', cascade="all, delete-orphan", lazy=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # "user" 或 "assistant"
    content = db.Column(db.Text, nullable=False)

# 创建数据库和表（首次启动时）
with app.app_context():
    db.create_all()

# 配置 DeepSeek API 密钥和地址（示例写死，实际请放到安全位置或环境变量）
client = OpenAI(api_key="sk-d06561b222dc4f4aa0d2a311c968de6a", base_url="https://api.deepseek.com")

# ----------------- 路由 -----------------
@app.route("/", methods=["GET"])
def index():
    """
    返回前端主页面(index1.html)
    """
    return render_template("index1.html")


@app.route("/api/chat", methods=["POST"])
def chat_api():
    """
    接收前端发送的 JSON 请求，根据 conversation_id 使用会话历史，
    调用 DeepSeek API 并返回回复，同时保存消息到数据库。
    """
    try:
        data = request.get_json(force=True)
        user_input = data.get("user_input", "").strip()
        if not user_input:
            return jsonify({"error": "user_input is empty"}), 400

        # 获取会话ID（若没有，则报错，请前端先创建会话）
        conv_id = data.get("conversation_id")
        if not conv_id:
            return jsonify({"error": "conversation_id is required"}), 400

        conversation = Conversation.query.get(conv_id)
        if not conversation:
            return jsonify({"error": "Conversation not found"}), 404

        # 构造消息历史：加入 system 提示 + 已有会话消息
        messages = [{"role": "system", "content": "You are a helpful assistant"}]
        past_messages = Message.query.filter_by(conversation_id=conv_id).order_by(Message.id.asc()).all()
        for m in past_messages:
            messages.append({"role": m.role, "content": m.content})

        # 添加最新用户消息
        messages.append({"role": "user", "content": user_input})
        new_user_msg = Message(conversation_id=conv_id, role="user", content=user_input)
        db.session.add(new_user_msg)
        db.session.commit()

        # 调用 DeepSeek API（同步模式）
        response = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=messages,
            stream=False
        )
        assistant_message = response.choices[0].message.content

        # 保存 assistant 回复
        new_assistant_msg = Message(conversation_id=conv_id, role="assistant", content=assistant_message)
        db.session.add(new_assistant_msg)
        db.session.commit()

        result_html = markdown.markdown(assistant_message)
        return jsonify({"html": result_html, "raw": assistant_message})
    except Exception as e:
        logging.exception("Error in chat_api")
        return jsonify({"error": str(e)}), 500


@app.route("/api/process_pdfs", methods=["POST"])
def process_pdfs():
    """
    后端处理 PDF 文件：
    1. 接收前端传入的 pdf_path，解析该目录下的所有 PDF 文件；
    2. 将解析后的文本按每 50 个文件一批合并后发送给大模型（DeepSeek），
       并将每次的用户输入和 AI 回复保存到指定会话中；
    3. 若请求中未传入 conversation_id，则自动创建新会话。
    """
    try:
        data = request.get_json(force=True)
        conv_id = data.get("conversation_id")
        pdf_path = data.get("pdf_path", "pdfs")  # 使用前端传入的目录，默认 "pdfs"
        # 若未指定会话，则新建一个会话
        if not conv_id:
            conv = Conversation(name="PDF解析会话")
            db.session.add(conv)
            db.session.commit()
            conv_id = conv.id
        else:
            conv = Conversation.query.get(conv_id)
            if not conv:
                return jsonify({"error": "Conversation not found"}), 404

        if not os.path.exists(pdf_path):
            return jsonify({"error": f"目录 {pdf_path} 不存在"}), 400

        pdf_files = [f for f in os.listdir(pdf_path) if f.lower().endswith(".pdf")]
        if not pdf_files:
            return jsonify({"error": f"目录 {pdf_path} 中无 PDF 文件"}), 400

        pdf_texts = []
        # 解析所有 PDF 文件
        for file in pdf_files:
            file_full_path = os.path.join(pdf_path, file)
            try:
                with open(file_full_path, "rb") as f:
                    reader = extract_text_from_pdf(file_full_path, lang='eng')

                    text = ""
                    # for page in reader.pages:
                    #     page_text = page.extract_text()
                    if reader:
                        text += reader + "\n"
                    pdf_texts.append(text.strip())
            except Exception as e:
                logging.exception(f"解析 {file} 失败: {e}")
                continue

        # 分批（每 50 个文件合并一次）发送给大模型
        batch_size = 1
        responses = []
        for i in range(0, len(pdf_texts), batch_size):
            batch = pdf_texts[i:i+batch_size]
            # 合并该批次所有文件内容为一个输入（用两个换行符分隔）
            batch_content = "\n\n".join(batch)
            print(batch_content)
            # 构造消息历史：system 提示 + 会话历史 + 本次输入
            messages = [{"role": "system", "content": "You are a helpful assistant"}]
            past_messages = Message.query.filter_by(conversation_id=conv_id).order_by(Message.id.asc()).all()
            for m in past_messages:
                messages.append({"role": m.role, "content": m.content})
            messages.append({"role": "user", "content": batch_content})

            # 保存该批次的用户消息到数据库
            new_user_msg = Message(conversation_id=conv_id, role="user", content=batch_content)
            db.session.add(new_user_msg)
            db.session.commit()

            # 调用 DeepSeek API（同步模式）
            response = client.chat.completions.create(
                model="deepseek-reasoner",
                messages=messages,
                stream=False
            )
            assistant_message = response.choices[0].message.content
            # 保存 assistant 回复
            new_assistant_msg = Message(conversation_id=conv_id, role="assistant", content=assistant_message)
            db.session.add(new_assistant_msg)
            db.session.commit()

            responses.append({
                "batch": i // batch_size + 1,
                "assistant_response": assistant_message
            })
        return jsonify({"conversation_id": conv_id, "batches": responses})
    except Exception as e:
        logging.exception("Error in process_pdfs")
        return jsonify({"error": str(e)}), 500


# ----------------- 会话管理相关接口 -----------------

# 创建新会话
@app.route("/api/conversations", methods=["POST"])
def create_conversation():
    try:
        data = request.get_json(force=True)
        name = data.get("name", "新会话")
        conv = Conversation(name=name)
        db.session.add(conv)
        db.session.commit()
        return jsonify({"id": conv.id, "name": conv.name}), 201
    except Exception as e:
        logging.exception("Error creating conversation")
        return jsonify({"error": str(e)}), 500

# 列出所有会话（仅返回 id 和 name）
@app.route("/api/conversations", methods=["GET"])
def list_conversations():
    convs = Conversation.query.order_by(Conversation.id.desc()).all()
    data = [{"id": conv.id, "name": conv.name} for conv in convs]
    return jsonify(data)

# 获取指定会话详情，包括消息历史
@app.route("/api/conversations/<int:conv_id>", methods=["GET"])
def get_conversation(conv_id):
    conv = Conversation.query.get(conv_id)
    if not conv:
        return jsonify({"error": "Conversation not found"}), 404
    msgs = Message.query.filter_by(conversation_id=conv_id).order_by(Message.id.asc()).all()
    messages = [{"id": m.id, "role": m.role, "content": m.content} for m in msgs]
    return jsonify({"id": conv.id, "name": conv.name, "messages": messages})

# 重命名会话
@app.route("/api/conversations/<int:conv_id>", methods=["PUT"])
def rename_conversation(conv_id):
    conv = Conversation.query.get(conv_id)
    if not conv:
        return jsonify({"error": "Conversation not found"}), 404
    data = request.get_json(force=True)
    new_name = data.get("name", "").strip()
    if not new_name:
        return jsonify({"error": "Name cannot be empty"}), 400
    conv.name = new_name
    db.session.commit()
    return jsonify({"id": conv.id, "name": conv.name})

# 删除会话及其消息
@app.route("/api/conversations/<int:conv_id>", methods=["DELETE"])
def delete_conversation(conv_id):
    conv = Conversation.query.get(conv_id)
    if not conv:
        return jsonify({"error": "Conversation not found"}), 404
    db.session.delete(conv)
    db.session.commit()
    return jsonify({"message": "Conversation deleted"}), 200

# ----------------- 应用运行入口 -----------------
if __name__ == "__main__":
    # 允许在局域网中其他设备访问，或改为默认127.0.0.1
    app.run(host='0.0.0.0', port=5001, debug=True)