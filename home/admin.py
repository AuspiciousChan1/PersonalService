# home/admin.py
#
# This file is used to register models with the Django admin interface. It allows you to customize
# how models are displayed and managed in the admin panel.
from django.contrib import admin
from .models import VisitorLog


@admin.register(VisitorLog)
class VisitorLogAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'path', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('ip_address', 'user_agent')
    readonly_fields = ('ip_address', 'user_agent', 'path', 'timestamp')
