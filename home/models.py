# home/models.py
#
# This file defines the database models for the home app. Models represent the data structure
# of the application and are used to interact with the database.
from django.db import models


class VisitorLog(models.Model):
    """Model to store visitor information"""
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    path = models.CharField(max_length=255, null=True, blank=True)
    method = models.CharField(max_length=10, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.ip_address} - {self.timestamp}"
