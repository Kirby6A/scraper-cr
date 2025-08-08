from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
import asyncio
from .models import Task, TaskExecution
from .serializers import (
    TaskSerializer,
    TaskCreateSerializer,
    TaskExecutionSerializer,
    ExecuteTaskSerializer
)
from .services.scraper_service import StagehandScraperService
from .services.llm_service import LLMService


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TaskCreateSerializer
        return TaskSerializer
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        task = self.get_object()
        serializer = ExecuteTaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create a new execution
        execution = TaskExecution.objects.create(
            task=task,
            status='running',
            metadata={'manual_trigger': True}
        )
        
        # Execute the scraper if code is available
        if task.generated_code:
            scraper_service = StagehandScraperService()
            
            # Validate code first
            validation = scraper_service.validate_code(task.generated_code)
            if not validation['valid']:
                execution.status = 'failed'
                execution.error_message = f"Code validation failed: {', '.join(validation['issues'])}"
                execution.completed_at = timezone.now()
                execution.save()
                return Response(
                    TaskExecutionSerializer(execution).data,
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Execute the scraper
            result = scraper_service.execute_scraper(task.generated_code)
            
            if result['success']:
                execution.status = 'success'
                execution.scraped_data = result['data']
            else:
                execution.status = 'failed'
                execution.error_message = result['error']
            
            execution.completed_at = timezone.now()
            execution.save()
        else:
            execution.status = 'failed'
            execution.error_message = 'No generated code available for this task'
            execution.completed_at = timezone.now()
            execution.save()
        
        return Response(
            TaskExecutionSerializer(execution).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        task = self.get_object()
        executions = task.executions.all()
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            executions = executions.filter(status=status_filter)
        
        page = self.paginate_queryset(executions)
        if page is not None:
            serializer = TaskExecutionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = TaskExecutionSerializer(executions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        task = self.get_object()
        task.is_active = False
        task.save()
        return Response({'status': 'paused'})
    
    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        task = self.get_object()
        task.is_active = True
        task.save()
        return Response({'status': 'resumed'})
    
    @action(detail=True, methods=['post'])
    def generate_code(self, request, pk=None):
        """Generate scraper code from natural language prompt using LLM"""
        task = self.get_object()
        
        # Get LLM configuration from request or use defaults
        provider = request.data.get('provider', 'openai')
        model = request.data.get('model')
        use_examples = request.data.get('use_examples', True)
        
        # Initialize LLM service
        try:
            llm_service = LLMService(provider=provider, model=model)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get examples if requested
        examples = None
        if use_examples:
            examples = llm_service.get_example_scrapers()
        
        # Generate code asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                llm_service.generate_scraper_code(
                    prompt=task.natural_language_prompt,
                    examples=examples,
                    validate=True
                )
            )
        finally:
            loop.close()
        
        if result['success']:
            # Update task with generated code and metadata
            task.generated_code = result['code']
            task.llm_provider = provider
            task.llm_model = result.get('model', '')
            task.llm_tokens_used = result.get('usage', {}).get('total_tokens', 0)
            task.code_generation_metadata = {
                'prompt': task.natural_language_prompt,
                'examples_used': len(examples) if examples else 0,
                'validation': result.get('validation', {}),
                'usage': result.get('usage', {}),
                'timestamp': timezone.now().isoformat()
            }
            task.save()
            
            return Response({
                'success': True,
                'code': result['code'],
                'validation': result.get('validation', {}),
                'usage': result.get('usage', {}),
                'task_id': str(task.id)
            })
        else:
            return Response({
                'success': False,
                'error': result.get('error', 'Unknown error'),
                'validation': result.get('validation', {})
            }, status=status.HTTP_400_BAD_REQUEST)


class TaskExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TaskExecution.objects.all()
    serializer_class = TaskExecutionSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by task_id if provided
        task_id = self.request.query_params.get('task_id')
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
