from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import VisitorLog
import json


def get_client_ip(request):
    """Get the client's IP address from the request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip if ip else None


@csrf_exempt  # Allow all HTTP methods without CSRF token for API-like usage
def home(request):
    """Home page view that returns JSON response with visitor info and request parameters"""
    # Record visitor information
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    path = request.path
    method = request.method
    
    # Save visitor log to database
    VisitorLog.objects.create(
        ip_address=ip_address,
        user_agent=user_agent,
        path=path,
        method=method
    )
    
    # Collect request parameters
    params = {}
    if request.method == 'GET':
        params = dict(request.GET.items())
    elif request.method in ['POST', 'PUT', 'PATCH']:
        # Try to get JSON data first, fall back to form data
        if request.content_type and request.content_type.startswith('application/json'):
            try:
                params = json.loads(request.body.decode('utf-8')) if request.body else {}
            except (json.JSONDecodeError, UnicodeDecodeError):
                params = dict(request.POST.items())
        else:
            params = dict(request.POST.items())
    
    # Return JSON response
    return JsonResponse({
        'code': 200,
        'msg': '成功',
        'params': params
    })
