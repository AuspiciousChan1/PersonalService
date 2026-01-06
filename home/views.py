from django.shortcuts import render
from .models import VisitorLog


def get_client_ip(request):
    """Get the client's IP address from the request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def home(request):
    """Home page view that displays a welcome message and logs visitor info"""
    # Record visitor information
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    path = request.path
    
    # Save visitor log to database
    VisitorLog.objects.create(
        ip_address=ip_address,
        user_agent=user_agent,
        path=path
    )
    
    return render(request, 'home/index.html')
