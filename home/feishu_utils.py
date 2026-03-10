# home/feishu_utils.py
import json
import requests
from typing import Optional

# --- Feishu App Constants ---
# App Name: MessageRobot
FEISHU_APP_ID = 'cli_a9255c608ff95cef'
FEISHU_APP_SECRET = 'nftmtZsZ9dIpaI2Glh7M4cp3fWM7PikW'
FEISHU_VERIFICATION_TOKEN = 'x6pyZiEINLzSiUCQKbvmEgl7hIp3ItUv'
FEISHU_API_URL = "https://open.feishu.cn/open-apis"


def get_tenant_access_token() -> Optional[str]:
    """Gets the tenant access token for Feishu API calls."""
    url = f"{FEISHU_API_URL}/auth/v3/tenant_access_token/internal"
    headers = {'Content-Type': 'application/json; charset=utf-8'}
    payload = {
        'app_id': FEISHU_APP_ID,
        'app_secret': FEISHU_APP_SECRET
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json().get('tenant_access_token')
    except Exception as e:
        print(f"Error getting tenant access token: {e}")
        return None


def reply_message(message_id: str, content: str):
    """Replies to a specific message in Feishu."""
    token = get_tenant_access_token()
    if not token:
        return

    url = f"{FEISHU_API_URL}/im/v1/messages/{message_id}/reply"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json; charset=utf-8'
    }
    
    # Construct the message content in JSON format
    msg_content = json.dumps({'text': content})
    
    payload = {
        'msg_type': 'text',
        'content': msg_content
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"Reply sent successfully: {response.json()}")
    except Exception as e:
        print(f"Error sending reply: {e}")


def process_feishu_event(payload: dict):
    """
    Processes a validated Feishu event payload.
    :param payload: The JSON payload from Feishu.
    """
    header = payload.get('header', {})
    event = payload.get('event', {})
    event_type = header.get('event_type')
    
    print(f"Received Feishu event: {event_type}")
    
    # Handle Message Receive Event
    if event_type == 'im.message.receive_v1':
        message = event.get('message', {})
        message_type = message.get('message_type')
        message_id = message.get('message_id')
        chat_type = message.get('chat_type')
        mentions = message.get('mentions', [])
        
        # Check if it's a text message
        if message_type == 'text':
            try:
                content_json = json.loads(message.get('content', '{}'))
                text_content = content_json.get('text', '')
                
                # Check if the bot is mentioned (@self)
                # In P2P (private chat), the bot is always the intended recipient.
                # In Group chat, we check if there are mentions. 
                is_mentioned = chat_type == 'p2p' or (chat_type == 'group' and mentions)
                
                if is_mentioned:
                    # Construct the reply
                    reply_text = f"{text_content}\n您好！"
                    reply_message(message_id, reply_text)
                    
            except json.JSONDecodeError:
                print("Failed to parse message content")
