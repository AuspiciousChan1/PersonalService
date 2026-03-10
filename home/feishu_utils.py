# home/feishu_utils.py
from collections import deque
import json
import threading
import requests
from typing import Optional

from home.ai.AiApi import AiType
from home.ai.TaskAgent import TaskAgent

# --- Feishu App Constants ---
# App Name: MessageRobot
FEISHU_APP_ID = 'cli_a9255c608ff95cef'
FEISHU_APP_SECRET = 'nftmtZsZ9dIpaI2Glh7M4cp3fWM7PikW'
FEISHU_VERIFICATION_TOKEN = 'x6pyZiEINLzSiUCQKbvmEgl7hIp3ItUv'
FEISHU_API_URL = "https://open.feishu.cn/open-apis"
MAX_RECENT_MESSAGE_IDS = 100
agent = TaskAgent(ai_type=AiType.DEEPSEEK)
_recent_message_ids = deque()
_recent_message_id_set = set()
_recent_message_lock = threading.Lock()


def _remember_message_id(message_id: str) -> bool:
    """Remember the latest 100 message_ids and return False for duplicates."""
    with _recent_message_lock:
        if message_id in _recent_message_id_set:
            return False

        if len(_recent_message_ids) >= MAX_RECENT_MESSAGE_IDS:
            expired_message_id = _recent_message_ids.popleft()
            _recent_message_id_set.discard(expired_message_id)

        _recent_message_ids.append(message_id)
        _recent_message_id_set.add(message_id)
        return True


def _clear_recent_message_ids() -> None:
    """Reset the in-memory message id cache. Intended for tests."""
    with _recent_message_lock:
        _recent_message_ids.clear()
        _recent_message_id_set.clear()


def _run_task_agent_and_reply(message_id: str, text_content: str) -> None:
    """Run the TaskAgent workflow and send the reply outside the webhook request thread."""
    try:
        execution_report = agent.execute_task_result(text_content)
        reply_message(message_id, execution_report.final_report)
        print(
            f"TaskAgent statuses: "
            f"{[result.status for result in execution_report.execution_results]}"
        )
    except Exception as e:
        print(f"Background Feishu task failed: {e}")


def _start_background_task(message_id: str, text_content: str) -> None:
    """Dispatch TaskAgent work to a daemon thread so Feishu webhook returns immediately."""
    worker = threading.Thread(
        target=_run_task_agent_and_reply,
        args=(message_id, text_content),
        daemon=True,
        name=f"feishu-task-{message_id}",
    )
    worker.start()


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


def process_feishu_event(payload: dict) -> bool:
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
                
                if is_mentioned and message_id and text_content.strip():
                    if not _remember_message_id(message_id):
                        print(f"Duplicate Feishu message ignored: {message_id}")
                        return False
                    _start_background_task(message_id, text_content)
                    return True

            except json.JSONDecodeError:
                print("Failed to parse message content")
    return False
