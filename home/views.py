# home/views.py
#
# This file contains the views for the home app. Views are responsible for processing user requests
# and returning responses, such as rendering a template or returning JSON data.
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from .models import VisitorLog
import json
import requests
from typing import Optional

# --- Feishu App Constants ---
# App Name: MessageRobot
FEISHU_APP_ID = 'cli_a9255c608ff95cef'
FEISHU_APP_SECRET = 'nftmtZsZ9dIpaI2Glh7M4cp3fWM7PikW'
FEISHU_VERIFICATION_TOKEN = 'x6pyZiEINLzSiUCQKbvmEgl7hIp3ItUv'
FEISHU_API_URL = "https://open.feishu.cn/open-apis"


def get_client_ip(request: HttpRequest) -> Optional[str]:
    """Get the client's IP address from the request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip if ip else None


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


@csrf_exempt
def home(request: HttpRequest) -> HttpResponse:
    """
    Home page view that handles general requests and Feishu webhooks.
    """
    # Record visitor information for all requests
    VisitorLog.objects.create(
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        path=request.path,
        method=request.method
    )

    # --- Handle Feishu Webhooks (POST requests with JSON) ---
    if request.method == 'POST' and request.content_type and 'application/json' in request.content_type:
        try:
            data = json.loads(request.body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'code': 400, 'msg': 'Invalid JSON'}, status=400)

        # --- Security Check for requests without encryption ---
        # The token is present in both url_verification and event_callback payloads
        if data.get('schema') == '2.0':
            # For url_verification, token is at the top level. For events, it's in the header.
            received_token = data.get('token') or data.get('header', {}).get('token')
            if received_token != FEISHU_VERIFICATION_TOKEN:
                print(f"Verification Token mismatch! Expected: {FEISHU_VERIFICATION_TOKEN}, Got: {received_token}")
                return JsonResponse({'code': 403, 'msg': 'Verification Token mismatch'}, status=403)

        # 1. Handle Feishu's URL Verification Challenge
        if data.get('type') == 'url_verification':
            return JsonResponse({'challenge': data.get('challenge')})

        # 2. Handle Feishu Event Callbacks
        if 'header' in data and data['header'].get('app_id') == FEISHU_APP_ID:
            process_feishu_event(data)
            return JsonResponse({'code': 200, 'msg': 'Event received successfully'})
        
        # If it's a JSON POST but not from Feishu, treat it as a generic request
        params = data
    
    # --- Handle other requests (GET, form-data, etc.) ---
    else:
        params = request.GET.dict() if request.method == 'GET' else dict(request.POST.items())

    # Default response for non-webhook or simple requests
    return JsonResponse({
        'code': 200,
        'msg': '成功',
        'params': params
    })
