# PersonalService/asgi.py
#
# This file is the ASGI configuration for the project. It is used by ASGI-compatible web servers
# to serve the Django application, supporting asynchronous features.
"""
ASGI config for PersonalService project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PersonalService.settings')

application = get_asgi_application()
