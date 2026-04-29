# app.py
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from wechatpy.enterprise.crypto import WeChatCrypto
from wechatpy.exceptions import InvalidSignatureException
import json
import hashlib
import base64
from flask import request, jsonify

import time
import os
import agent_session
import requests


# 从环境变量读取企业微信配置（建议放在 .env 文件中）
WECOM_CORP_ID = os.getenv("WECOM_CORP_ID", "你的企业ID")
WECOM_TOKEN = os.getenv("WECOM_TOKEN", "你设置的Token")
WECOM_ENCODING_AES_KEY = os.getenv("WECOM_ENCODING_AES_KEY", "你的EncodingAESKey")

crypto = WeChatCrypto(WECOM_TOKEN, WECOM_ENCODING_AES_KEY, WECOM_CORP_ID)

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/tools', methods=['GET'])
def list_tools():
    """获取当前已加载的工具列表"""
    tools = agent_session.get_current_tools()
    return jsonify({"tools": tools})
#飞书的路由
# app.py 中添加以下内容

# 飞书回调配置（从环境变量或直接填写）
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET")
FEISHU_VERIFICATION_TOKEN = os.getenv("FEISHU_VERIFICATION_TOKEN", "")  # 可选，事件订阅中的 Verification Token

# 用于缓存 access_token（简单实现）
_feishu_access_token = None

def get_feishu_access_token():
    """获取飞书 tenant access token"""
    import requests
    global _feishu_access_token
    if _feishu_access_token:
        return _feishu_access_token
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json; charset=utf-8"}
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    resp = requests.post(url, headers=headers, json=data).json()
    if resp.get("code") == 0:
        _feishu_access_token = resp["tenant_access_token"]
        return _feishu_access_token
    else:
        raise Exception(f"获取 access_token 失败: {resp}")

@app.route('/feishu_webhook', methods=['POST'])
def feishu_webhook():
    """飞书事件回调入口"""
    raw_data = request.get_data(as_text=True)
    app.logger.info(f"收到飞书回调原始数据: {raw_data}")
    """开始正常的处理逻辑"""   
    data = request.get_json(force=True, silent=True)
    if not data:
        return "ok", 200

    # 处理 URL 验证（首次配置时）
    if data.get("type") == "url_verification":
        return jsonify({"challenge": data["challenge"]})

    # 处理飞书事件（schema 2.0）
    if data.get("schema") == "2.0":
        event_type = data.get("header", {}).get("event_type")
        if event_type == "im.message.receive_v1":
            event_data = data.get("event", {})
            message = event_data.get("message", {})
            if message.get("message_type") == "text":
                content_str = message.get("content", "{}")
                try:
                    content_obj = json.loads(content_str)
                    user_question = content_obj.get("text", "")
                    open_id = event_data.get("sender", {}).get("sender_id", {}).get("open_id", "")
                    print(f"收到消息: {user_question} (open_id: {open_id})")

                    # 调用 Agent
                    answer = agent_session.invoke_agent(user_question)
                    print(f"Agent 回复: {answer}")

                    # 发送回复
                    access_token = get_feishu_access_token()
                    url = "https://open.feishu.cn/open-apis/im/v1/messages"
                    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
                    payload = {
                        "receive_id": open_id,
                        "msg_type": "text",
                        "content": json.dumps({"text": answer})
                    }
                    resp = requests.post(url, headers=headers, json=payload, params={"receive_id_type": "open_id"})
                    if resp.status_code == 200:
                        print("回复发送成功")
                    else:
                        print(f"回复发送失败: {resp.text}")
                except Exception as e:
                    print(f"处理消息异常: {e}")
            else:
                print(f"非文本消息，暂不处理")
        else:
            print(f"收到其他事件类型: {event_type}")
    else:
        print(f"未识别的回调格式: {data}")

    return "ok", 200
   
#企业微信的路由
@app.route('/wecom', methods=['GET', 'POST'])
def wecom_callback():
    if request.method == 'GET':
        # 验证 URL
        signature = request.args.get('msg_signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce = request.args.get('nonce', '')
        echostr = request.args.get('echostr', '')
        try:
            plain_text = crypto.decrypt_message(echostr, signature, timestamp, nonce)
            return plain_text
        except InvalidSignatureException:
            return "Invalid signature", 403

    elif request.method == 'POST':
        # 处理用户消息
        signature = request.args.get('msg_signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce = request.args.get('nonce', '')
        data = request.data
        try:
            msg = crypto.decrypt_message(data, signature, timestamp, nonce)
            from wechatpy.enterprise import parse_message
            wecom_msg = parse_message(msg)
            user_id = wecom_msg.source
            user_question = wecom_msg.content

            # 调用现有 Agent 逻辑
            answer = agent_session.invoke_agent(user_question)

            # 构造回复 XML
            reply_xml = f"""
            <xml>
                <ToUserName><![CDATA[{user_id}]]></ToUserName>
                <FromUserName><![CDATA[{WECOM_CORP_ID}]]></FromUserName>
                <CreateTime>{int(time.time())}</CreateTime>
                <MsgType><![CDATA[text]]></MsgType>
                <Content><![CDATA[{answer}]]></Content>
            </xml>
            """
            encrypted_reply = crypto.encrypt_message(reply_xml, nonce, timestamp)
            return encrypted_reply
        except Exception as e:
            print(f"处理企业微信消息出错: {e}")
            return "error", 500
#重载路由
@app.route('/api/reload', methods=['POST'])
def reload_tools():
    """重新加载所有插件"""
    log = agent_session.reload_agent()
    return jsonify({"status": "ok", "log": log})

@app.route('/api/chat', methods=['POST'])
def chat():
    """与 Agent 对话"""
    data = request.json
    question = data.get("question", "")
    if not question:
        return jsonify({"error": "问题不能为空"}), 400
    answer = agent_session.invoke_agent(question)
    return jsonify({"answer": answer})

@app.route('/api/reset_memory', methods=['POST'])
def reset_memory():
    """重置对话记忆"""
    msg = agent_session.reset_memory()
    return jsonify({"status": "ok", "message": msg})

@app.route('/api/test_tool', methods=['POST'])
def test_tool():
    """测试单个工具"""
    data = request.json
    tool_name = data.get("tool_name")
    args = data.get("args", {})
    if not tool_name:
        return jsonify({"error": "缺少 tool_name"}), 400
    result = agent_session.test_tool(tool_name, args)
    return jsonify(result)

# 插件文件管理
@app.route('/api/plugins', methods=['GET'])
def list_plugins():
    files = agent_session.list_plugin_files()
    return jsonify({"files": files})

@app.route('/api/plugins/<filename>', methods=['GET'])
def get_plugin(filename):
    content = agent_session.get_plugin_content(filename)
    if content is None:
        return jsonify({"error": "文件不存在"}), 404
    return jsonify({"filename": filename, "content": content})

@app.route('/api/plugins/<filename>', methods=['POST'])
def save_plugin(filename):
    data = request.json
    content = data.get("content", "")
    if not content:
        return jsonify({"error": "内容不能为空"}), 400
    path = agent_session.save_plugin_file(filename, content)
    # 保存后自动重新加载 Agent
    agent_session.reload_agent()
    return jsonify({"status": "saved", "path": path})

@app.route('/api/plugins/<filename>', methods=['DELETE'])
def delete_plugin(filename):
    success = agent_session.delete_plugin_file(filename)
    if success:
        agent_session.reload_agent()
        return jsonify({"status": "deleted"})
    else:
        return jsonify({"error": "删除失败"}), 500

if __name__ == '__main__':
    app.run(host='::', port=8600, debug=True)
