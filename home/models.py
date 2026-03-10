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


class TaskRun(models.Model):
    """A single TaskAgent execution run."""
    user_query = models.TextField()
    ai_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50, default='running')
    source_type = models.CharField(max_length=50, null=True, blank=True)
    source_message_id = models.CharField(max_length=100, null=True, blank=True)
    source_chat_id = models.CharField(max_length=100, null=True, blank=True)
    source_sender_open_id = models.CharField(max_length=100, null=True, blank=True)
    source_metadata = models.JSONField(default=dict, blank=True)
    initial_plan = models.JSONField(default=dict, blank=True)
    final_report = models.TextField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"TaskRun#{self.pk} [{self.status}]"


class TaskOutput(models.Model):
    """Persisted output emitted during planning, execution, and summary."""
    task_run = models.ForeignKey(TaskRun, on_delete=models.CASCADE, related_name='outputs')
    sequence = models.PositiveIntegerField()
    stage = models.CharField(max_length=20, default='execution')
    depth = models.PositiveIntegerField(default=1)
    task_id = models.CharField(max_length=100, null=True, blank=True)
    tool = models.CharField(max_length=50, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    input_code = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=50)
    content = models.TextField(null=True, blank=True)
    display_text = models.TextField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    recovery_attempts = models.PositiveIntegerField(default=0)
    used_llm_fallback = models.BooleanField(default=False)
    fallback_can_replace_execution = models.BooleanField(null=True, blank=True)
    fallback_answer = models.TextField(null=True, blank=True)
    fallback_raw_response = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sequence', 'created_at']

    def __str__(self):
        return f"TaskOutput#{self.pk} run={self.task_run.pk} stage={self.stage} status={self.status}"
