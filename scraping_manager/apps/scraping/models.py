from django.db import models
from django.contrib.postgres.fields import ArrayField


class ScrapingGroup(models.Model):
    name = models.CharField(max_length=200)
    schedule = models.CharField(max_length=100, help_text="Cron expression")
    is_active = models.BooleanField(default=True)
    notification_emails = models.JSONField(default=list)
    run_parallel = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'scraping_groups'
        
    def __str__(self):
        return self.name


class ScrapingTask(models.Model):
    STATUS_CHOICES = [
        ('UNTESTED', 'Untested'),
        ('TESTING', 'Testing'),
        ('PASSED', 'Passed'),
        ('FAILED', 'Failed'),
    ]
    
    DATA_TYPE_CHOICES = [
        ('RFP', 'Request for Proposal'),
        ('GRANT', 'Grant'),
        ('JOB', 'Job Posting'),
        ('NEWS', 'News Article'),
        ('GENERIC', 'Generic Data'),
    ]
    
    group = models.ForeignKey(ScrapingGroup, on_delete=models.CASCADE, related_name='tasks')
    name = models.CharField(max_length=200)
    target_url = models.URLField()
    description = models.TextField(help_text="Natural language description of what to scrape")
    generated_code = models.TextField(help_text="Python code using Stagehand")
    code_version = models.IntegerField(default=1)
    data_type = models.CharField(max_length=50, choices=DATA_TYPE_CHOICES, default='GENERIC')
    extraction_schema = models.JSONField(default=dict, help_text="Expected output structure")
    execution_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    test_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UNTESTED')
    last_test_at = models.DateTimeField(null=True, blank=True)
    avg_execution_time = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'scraping_tasks'
        ordering = ['group', 'execution_order']
        
    def __str__(self):
        return f"{self.group.name} - {self.name}"


class TaskRun(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('TIMEOUT', 'Timeout'),
    ]
    
    task = models.ForeignKey(ScrapingTask, on_delete=models.CASCADE, related_name='runs')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    items_found = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    execution_logs = models.JSONField(default=dict)
    celery_task_id = models.CharField(max_length=255, blank=True)
    
    class Meta:
        db_table = 'task_runs'
        ordering = ['-started_at']
        
    def __str__(self):
        return f"{self.task.name} - {self.started_at}"


class ScrapedItem(models.Model):
    task = models.ForeignKey(ScrapingTask, on_delete=models.CASCADE, related_name='scraped_items')
    run = models.ForeignKey(TaskRun, on_delete=models.CASCADE, related_name='items')
    item_type = models.CharField(max_length=50)
    unique_hash = models.CharField(max_length=64, db_index=True)
    data = models.JSONField()
    source_urls = ArrayField(models.URLField(), default=list)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    times_seen = models.IntegerField(default=1)
    
    class Meta:
        db_table = 'scraped_items'
        unique_together = ['unique_hash', 'task']
        
    def __str__(self):
        return f"{self.item_type} - {self.unique_hash[:8]}"