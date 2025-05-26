import requests

# API 地址
url = "http://localhost/v1/chat-messages"

# 请求头
headers = {
    "Authorization": "Bearer app-KHoEkOgmLGcqZG41K9ybcRDx",  # 替换为你的实际 API Key
    "Content-Type": "application/json"
}

# 请求数据 (JSON 格式)
data = {
    "inputs": {},
    "query": "用户基础维度表",  # 查询内容
    "response_mode": "streaming",  # 响应模式
    "conversation_id": "",  # 会话 ID
    "user": "xionghaoqiang561@gmail.com",  # 用户标识
    "proxies" = {"http": None, "https": None}  # 关键：显式禁用

}

# 发起 POST 请求
try:
    response = requests.post(url, headers=headers, json=data)

    # 输出状态码和响应内容
    print(f"Status Code: {response.status_code}")
    print("Response:", response.text)
except requests.exceptions.RequestException as e:
    print("An error occurred:", e)