from django.contrib import admin
from .models import Task, TaskExecution


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'schedule', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at', 'updated_at']
    search_fields = ['name', 'description', 'natural_language_prompt']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'description', 'is_active')
        }),
        ('Scraping Configuration', {
            'fields': ('natural_language_prompt', 'generated_code', 'schedule')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TaskExecution)
class TaskExecutionAdmin(admin.ModelAdmin):
    list_display = ['task', 'status', 'started_at', 'completed_at']
    list_filter = ['status', 'started_at', 'completed_at']
    search_fields = ['task__name', 'error_message']
    readonly_fields = ['id', 'task', 'started_at', 'created_at']
    
    fieldsets = (
        ('Execution Information', {
            'fields': ('id', 'task', 'status', 'started_at', 'completed_at')
        }),
        ('Results', {
            'fields': ('scraped_data', 'error_message')
        }),
        ('Metadata', {
            'fields': ('metadata', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # Executions should only be created programmatically
        return False
