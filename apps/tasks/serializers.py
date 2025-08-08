from rest_framework import serializers
from .models import Task, TaskExecution


class TaskExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskExecution
        fields = [
            'id', 'task', 'status', 'started_at', 'completed_at',
            'error_message', 'scraped_data', 'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'started_at']


class TaskSerializer(serializers.ModelSerializer):
    executions = TaskExecutionSerializer(many=True, read_only=True)
    latest_execution = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'name', 'description', 'natural_language_prompt',
            'generated_code', 'schedule', 'is_active', 'created_at',
            'updated_at', 'executions', 'latest_execution'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_latest_execution(self, obj):
        latest = obj.executions.first()
        if latest:
            return TaskExecutionSerializer(latest).data
        return None


class TaskCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            'name', 'description', 'natural_language_prompt',
            'schedule', 'is_active'
        ]
    
    def validate_natural_language_prompt(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "The natural language prompt must be at least 10 characters long."
            )
        return value


class ExecuteTaskSerializer(serializers.Serializer):
    force = serializers.BooleanField(default=False, required=False)