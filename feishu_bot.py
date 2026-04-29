import os
import sys
import json
import logging
from dotenv import load_dotenv

load_dotenv()
from agent_session import invoke_agent

# 导入新版 SDK 的核心模块
from lark_oapi import Client, Config, LogLevel
from lark_oapi.api.im.v1 import (
    P2MessageReceiveV1,
    CreateMessageRequest,
    CreateMessageRequestBody,
)
import lark_oapi.websocket as websocket

# 定义消息处理函数（同步）
def handle_message(cli, event: P2MessageReceiveV1):
    try:
        msg = event.event.message
        if msg.message_type != "text":
            return

        # 解析用户消息
        content = json.loads(msg.content) if msg.content else {}
        user_question = content.get("text", "")
        if not user_question:
            return

        sender_id = msg.sender_id.open_id
        logging.info(f"收到消息: {user_question} (from {sender_id})")

        # 调用你的 Agent
        answer = invoke_agent(user_question)

        # 发送回复
        request = CreateMessageRequest.builder().request_body(
            CreateMessageRequestBody.builder()
                .receive_id(sender_id)
                .msg_type("text")
                .content(json.dumps({"text": answer}))
                .build()
        ).build()
        response = cli.im.v1.message.create(request, receive_id_type="open_id")
        if not response.success():
            logging.error(f"发送消息失败: {response.msg}")
        else:
            logging.info("消息发送成功")
    except Exception as e:
        logging.error(f"处理消息出错: {e}", exc_info=True)

if __name__ == "__main__":
    APP_ID = os.getenv("FEISHU_APP_ID")
    APP_SECRET = os.getenv("FEISHU_APP_SECRET")

    if not APP_ID or not APP_SECRET:
        print("错误: 请在 .env 文件中设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
        sys.exit(1)

    logging.basicConfig(level=logging.INFO)

    # 创建配置和客户端
    config = Config(APP_ID, APP_SECRET, log_level=LogLevel.WARN)
    client = Client(config)

    # 建立 WebSocket 长连接，直接传入处理函数
    ws_client = websocket.WebsocketClient(config, event_handler=handle_message)
    print("飞书 Bot 启动，等待接收消息...")
    try:
        ws_client.start()
    except KeyboardInterrupt:
        print("\n程序已退出")
    except Exception as e:
        print(f"运行出错: {e}")
