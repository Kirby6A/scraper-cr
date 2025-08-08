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
    # Schedule fields for periodic execution
    schedule_enabled = models.BooleanField(default=False)
    schedule_cron = models.CharField(max_length=200, blank=True, help_text="Cron expression for scheduling")
    last_scheduled_run = models.DateTimeField(null=True, blank=True)
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


class DataQuery(models.Model):
    """Saved queries for filtering and searching scraped data"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='queries', null=True, blank=True)
    query_filters = models.JSONField(default=dict, help_text="JSONB query filters")
    query_type = models.CharField(
        max_length=50,
        choices=[
            ('jsonb', 'JSONB Query'),
            ('text_search', 'Full Text Search'),
            ('date_range', 'Date Range'),
            ('aggregate', 'Aggregation'),
        ],
        default='jsonb'
    )
    is_public = models.BooleanField(default=False)
    created_by = models.CharField(max_length=255, blank=True)  # Will add User FK in Phase 6
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'data_queries'
        indexes = [
            models.Index(fields=['task', 'query_type']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.query_type})"


class DataExport(models.Model):
    """Track data export jobs"""
    EXPORT_FORMATS = [
        ('csv', 'CSV'),
        ('json', 'JSON'),
        ('excel', 'Excel'),
        ('parquet', 'Parquet'),
        ('xml', 'XML'),
    ]
    
    EXPORT_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='exports', null=True, blank=True)
    executions = models.ManyToManyField(TaskExecution, related_name='exports', blank=True)
    format = models.CharField(max_length=20, choices=EXPORT_FORMATS)
    status = models.CharField(max_length=20, choices=EXPORT_STATUS, default='pending')
    filters = models.JSONField(default=dict, help_text="Applied filters during export")
    file_path = models.CharField(max_length=500, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    row_count = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    export_config = models.JSONField(default=dict, help_text="Format-specific configuration")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'data_exports'
        indexes = [
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"Export {self.format} - {self.status} - {self.created_at}"


class DataTransformation(models.Model):
    """Define reusable data transformation rules"""
    TRANSFORMATION_TYPES = [
        ('field_mapping', 'Field Mapping'),
        ('type_conversion', 'Type Conversion'),
        ('aggregation', 'Aggregation'),
        ('filter', 'Filter'),
        ('custom', 'Custom Function'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='transformations', null=True, blank=True)
    transformation_type = models.CharField(max_length=50, choices=TRANSFORMATION_TYPES)
    rules = models.JSONField(
        default=dict,
        help_text="Transformation rules configuration"
    )
    is_active = models.BooleanField(default=True)
    apply_order = models.IntegerField(default=0, help_text="Order in which transformations are applied")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['apply_order', 'created_at']
        db_table = 'data_transformations'
        indexes = [
            models.Index(fields=['task', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.transformation_type})"


class DataVersion(models.Model):
    """Track changes between task executions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='versions')
    execution_from = models.ForeignKey(
        TaskExecution,
        on_delete=models.CASCADE,
        related_name='version_from',
        null=True,
        blank=True
    )
    execution_to = models.ForeignKey(
        TaskExecution,
        on_delete=models.CASCADE,
        related_name='version_to'
    )
    diff_data = models.JSONField(
        default=dict,
        help_text="Changes between executions"
    )
    diff_summary = models.JSONField(
        default=dict,
        help_text="Summary statistics of changes"
    )
    change_type = models.CharField(
        max_length=50,
        choices=[
            ('initial', 'Initial Version'),
            ('update', 'Data Updated'),
            ('schema_change', 'Schema Changed'),
            ('full_change', 'Complete Change'),
        ],
        default='update'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'data_versions'
        indexes = [
            models.Index(fields=['task', 'created_at']),
            models.Index(fields=['execution_from', 'execution_to']),
        ]
    
    def __str__(self):
        return f"Version {self.task.name} - {self.change_type} - {self.created_at}"
