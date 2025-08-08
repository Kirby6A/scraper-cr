from django.db import models
import uuid


class Task(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    natural_language_prompt = models.TextField()
    generated_code = models.TextField(blank=True)
    schedule = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    # LLM metadata fields
    llm_provider = models.CharField(max_length=50, blank=True)  # openai, anthropic
    llm_model = models.CharField(max_length=100, blank=True)  # gpt-4, claude-3
    llm_tokens_used = models.IntegerField(default=0)
    code_generation_metadata = models.JSONField(default=dict)  # Store prompts, examples used, etc.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'tasks'

    def __str__(self):
        return self.name


class TaskExecution(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='executions')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    scraped_data = models.JSONField(default=dict)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-started_at']
        db_table = 'task_executions'
        indexes = [
            models.Index(fields=['task', 'status']),
        ]

    def __str__(self):
        return f"{self.task.name} - {self.status} - {self.started_at}"
