# home/views.py
#
# This file contains the views for the home app. Views are responsible for processing user requests
# and returning responses, such as rendering a template or returning JSON data.
from django.http import JsonResponse, HttpResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from .models import VisitorLog
import json
from typing import Optional
from PersonalService.app_params import FEISHU_APP_ID, FEISHU_VERIFICATION_TOKEN
from .feishu_utils import process_feishu_event


def get_client_ip(request: HttpRequest) -> Optional[str]:
    """Get the client's IP address from the request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip if ip else None


def log_visitor(request: HttpRequest) -> None:
    """Record visitor information for all requests."""
    VisitorLog.objects.create(
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        path=request.path,
        method=request.method
    )


@csrf_exempt
def feishu(request: HttpRequest) -> HttpResponse:
    """Dedicated Feishu webhook endpoint."""
    log_visitor(request)

    if request.method != 'POST':
        return JsonResponse({'code': 200, 'msg': 'Feishu webhook is ready'})

    if not request.content_type or 'application/json' not in request.content_type:
        return JsonResponse({'code': 400, 'msg': 'Content-Type must be application/json'}, status=400)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'code': 400, 'msg': 'Invalid JSON'}, status=400)

    # Verification challenge
    if data.get('type') == 'url_verification':
        received_token = data.get('token')
        if received_token != FEISHU_VERIFICATION_TOKEN:
             return JsonResponse({'code': 403, 'msg': 'Verification Token mismatch'}, status=403)
        return JsonResponse({'challenge': data.get('challenge')})

    # Event handling
    if data.get('schema') == '2.0':
        received_token = data.get('header', {}).get('token')
        if received_token != FEISHU_VERIFICATION_TOKEN:
            print(f'Verification token mismatch for incoming Feishu request.')
            return JsonResponse({'code': 403, 'msg': 'Verification Token mismatch'}, status=403)

    if 'header' in data and data['header'].get('app_id') == FEISHU_APP_ID:
        process_feishu_event(data)
        return JsonResponse({'code': 200, 'msg': 'Event received successfully'})

    return JsonResponse({'code': 400, 'msg': 'Unsupported request'}, status=400)


@csrf_exempt
def home(request: HttpRequest) -> HttpResponse:
    """
    Home page view that handles general requests.
    """
    log_visitor(request)

    if request.method == 'POST' and request.content_type and 'application/json' in request.content_type:
        try:
            params = json.loads(request.body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'code': 400, 'msg': 'Invalid JSON'}, status=400)
    else:
        params = request.GET.dict() if request.method == 'GET' else dict(request.POST.items())

    # Default response for non-webhook or simple requests
    return JsonResponse({
        'code': 200,
        'msg': '成功',
        'params': params
    })
