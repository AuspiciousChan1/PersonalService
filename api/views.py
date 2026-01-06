from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection


def health_check(request):
    """Health check endpoint to verify server and database connectivity."""
    try:
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return JsonResponse({
        'status': 'ok',
        'database': db_status,
        'message': 'PersonalService is running'
    })


def index(request):
    """Simple index page."""
    return JsonResponse({
        'message': 'Welcome to PersonalService',
        'version': '1.0.0',
        'description': 'A Django-based server with PostgreSQL database accessible from external networks'
    })

