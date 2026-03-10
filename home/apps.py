# home/apps.py
#
# This file contains the configuration for the home app. It allows you to configure app-specific
# settings and behavior.
from django.apps import AppConfig


class HomeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'home'
