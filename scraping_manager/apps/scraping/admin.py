from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import ScrapingGroup, ScrapingTask, TaskRun, ScrapedItem
from .tasks import test_scraping_task, run_scraping_task


class ScrapingTaskInline(admin.TabularInline):
    model = ScrapingTask
    extra = 0
    fields = ['name', 'target_url', 'data_type', 'execution_order', 'is_active', 'test_status']
    readonly_fields = ['test_status']
    ordering = ['execution_order']


@admin.register(ScrapingGroup)
class ScrapingGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'schedule', 'is_active', 'task_count', 'run_parallel', 'created_at']
    list_filter = ['is_active', 'run_parallel', 'created_at']
    search_fields = ['name']
    inlines = [ScrapingTaskInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'schedule', 'is_active', 'run_parallel')
        }),
        ('Notifications', {
            'fields': ('notification_emails',),
            'description': 'List of email addresses to notify when group completes (JSON array)'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
    
    def task_count(self, obj):
        return obj.tasks.count()
    task_count.short_description = 'Tasks'
    
    actions = ['run_group_now']
    
    def run_group_now(self, request, queryset):
        from .tasks import run_scraping_group
        for group in queryset:
            run_scraping_group.delay(group.id)
            self.message_user(request, f"Started execution of group '{group.name}'")
    run_group_now.short_description = "Run selected groups now"


@admin.register(ScrapingTask)
class ScrapingTaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'group', 'target_url', 'data_type', 'test_status_badge', 
                    'is_active', 'execution_order', 'last_run_status']
    list_filter = ['group', 'data_type', 'test_status', 'is_active']
    search_fields = ['name', 'target_url', 'description']
    
    fieldsets = (
        (None, {
            'fields': ('group', 'name', 'target_url', 'data_type', 'execution_order', 'is_active')
        }),
        ('Task Configuration', {
            'fields': ('description', 'extraction_schema'),
            'classes': ('wide',)
        }),
        ('Generated Code', {
            'fields': ('generated_code', 'code_version'),
            'classes': ('wide',),
            'description': 'Python async function that uses Stagehand. Function should be named "scrape_example" and return a list of items.'
        }),
        ('Testing', {
            'fields': ('test_status', 'last_test_at', 'avg_execution_time'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['test_status', 'last_test_at', 'avg_execution_time', 
                      'created_at', 'updated_at', 'code_version']
    
    def test_status_badge(self, obj):
        colors = {
            'UNTESTED': 'gray',
            'TESTING': 'orange',
            'PASSED': 'green',
            'FAILED': 'red',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.test_status, 'gray'),
            obj.get_test_status_display()
        )
    test_status_badge.short_description = 'Test Status'
    
    def last_run_status(self, obj):
        last_run = obj.runs.first()
        if not last_run:
            return '-'
        
        colors = {
            'PENDING': 'gray',
            'RUNNING': 'orange',
            'SUCCESS': 'green',
            'FAILED': 'red',
            'TIMEOUT': 'red',
        }
        
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(last_run.status, 'gray'),
            last_run.get_status_display()
        )
    last_run_status.short_description = 'Last Run'
    
    actions = ['test_task', 'run_task_now']
    
    def test_task(self, request, queryset):
        for task in queryset:
            test_scraping_task.delay(task.id)
            self.message_user(request, f"Started test for task '{task.name}'")
    test_task.short_description = "Test selected tasks"
    
    def run_task_now(self, request, queryset):
        for task in queryset:
            run_scraping_task.delay(task.id)
            self.message_user(request, f"Started execution of task '{task.name}'")
    run_task_now.short_description = "Run selected tasks now"
    
    def save_model(self, request, obj, form, change):
        if change and 'generated_code' in form.changed_data:
            obj.code_version += 1
        super().save_model(request, obj, form, change)


@admin.register(TaskRun)
class TaskRunAdmin(admin.ModelAdmin):
    list_display = ['task', 'status_badge', 'started_at', 'duration', 'items_found', 'celery_task_id']
    list_filter = ['status', 'started_at', 'task__group']
    search_fields = ['task__name', 'celery_task_id', 'error_message']
    date_hierarchy = 'started_at'
    
    fieldsets = (
        (None, {
            'fields': ('task', 'status', 'celery_task_id')
        }),
        ('Execution Details', {
            'fields': ('started_at', 'completed_at', 'items_found')
        }),
        ('Error Information', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('Execution Logs', {
            'fields': ('execution_logs_display',),
            'classes': ('collapse', 'wide')
        }),
    )
    
    readonly_fields = ['task', 'status', 'started_at', 'completed_at', 'items_found', 
                      'error_message', 'execution_logs_display', 'celery_task_id']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def status_badge(self, obj):
        colors = {
            'PENDING': 'gray',
            'RUNNING': 'orange',
            'SUCCESS': 'green',
            'FAILED': 'red',
            'TIMEOUT': 'red',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def duration(self, obj):
        if not obj.completed_at:
            return '-'
        duration = (obj.completed_at - obj.started_at).total_seconds()
        from apps.common.utils import format_duration
        return format_duration(duration)
    duration.short_description = 'Duration'
    
    def execution_logs_display(self, obj):
        import json
        return format_html('<pre>{}</pre>', json.dumps(obj.execution_logs, indent=2))
    execution_logs_display.short_description = 'Execution Logs'


@admin.register(ScrapedItem)
class ScrapedItemAdmin(admin.ModelAdmin):
    list_display = ['unique_hash_short', 'task', 'item_type', 'first_seen', 
                    'last_seen', 'times_seen', 'run_link']
    list_filter = ['item_type', 'task__group', 'first_seen', 'task']
    search_fields = ['unique_hash', 'data']
    date_hierarchy = 'first_seen'
    
    fieldsets = (
        (None, {
            'fields': ('task', 'run', 'item_type', 'unique_hash')
        }),
        ('Data', {
            'fields': ('data_display',),
            'classes': ('wide',)
        }),
        ('Sources', {
            'fields': ('source_urls',)
        }),
        ('Tracking', {
            'fields': ('first_seen', 'last_seen', 'times_seen')
        }),
    )
    
    readonly_fields = ['task', 'run', 'item_type', 'unique_hash', 'data_display', 
                      'source_urls', 'first_seen', 'last_seen', 'times_seen']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def unique_hash_short(self, obj):
        return obj.unique_hash[:12] + '...'
    unique_hash_short.short_description = 'Hash'
    
    def run_link(self, obj):
        if not obj.run:
            return '-'
        url = reverse('admin:scraping_taskrun_change', args=[obj.run.id])
        return format_html('<a href="{}">View Run</a>', url)
    run_link.short_description = 'Run'
    
    def data_display(self, obj):
        import json
        return format_html('<pre>{}</pre>', json.dumps(obj.data, indent=2))
    data_display.short_description = 'Data'