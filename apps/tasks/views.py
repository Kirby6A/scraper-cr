from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
import asyncio
from celery.result import AsyncResult
from .models import Task, TaskExecution
from .serializers import (
    TaskSerializer,
    TaskCreateSerializer,
    TaskExecutionSerializer,
    ExecuteTaskSerializer
)
from .services.scraper_service import StagehandScraperService
from .services.llm_service import LLMService
from .tasks import execute_scraper_task, generate_code_task


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
        
        # Check if async mode is requested (default to True for Celery)
        async_mode = request.data.get('async', True)
        
        # Check if code is available
        if not task.generated_code:
            return Response(
                {'error': 'No generated code available for this task'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create a new execution
        execution = TaskExecution.objects.create(
            task=task,
            status='pending' if async_mode else 'running',
            metadata={
                'manual_trigger': True,
                'async': async_mode
            }
        )
        
        if async_mode:
            # Queue the task for async execution with Celery
            # Use transaction.on_commit to ensure the execution is saved before the task runs
            def queue_task():
                result = execute_scraper_task.delay(str(execution.id))
                # Update execution with Celery task ID
                execution.metadata['celery_task_id'] = result.id
                execution.save()
                
            transaction.on_commit(queue_task)
            
            return Response({
                'execution_id': str(execution.id),
                'status': 'queued',
                'message': 'Task queued for background execution',
                'async': True
            }, status=status.HTTP_202_ACCEPTED)
        else:
            # Synchronous execution (old behavior)
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
    
    @action(detail=False, methods=['get'])
    def task_status(self, request):
        """Check the status of a Celery task"""
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response(
                {'error': 'task_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get Celery task result
        result = AsyncResult(task_id)
        
        response_data = {
            'task_id': task_id,
            'status': result.status,
            'ready': result.ready(),
        }
        
        if result.ready():
            if result.successful():
                response_data['result'] = result.result
            else:
                response_data['error'] = str(result.info)
        
        return Response(response_data)
    
    @action(detail=True, methods=['get'])
    def execution_status(self, request, pk=None):
        """Get detailed status of a task execution"""
        execution_id = request.query_params.get('execution_id')
        if not execution_id:
            return Response(
                {'error': 'execution_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            execution = TaskExecution.objects.get(id=execution_id)
            serializer = TaskExecutionSerializer(execution)
            data = serializer.data
            
            # If there's a Celery task ID, get its status
            if execution.metadata and 'celery_task_id' in execution.metadata:
                celery_task_id = execution.metadata['celery_task_id']
                result = AsyncResult(celery_task_id)
                data['celery_status'] = {
                    'task_id': celery_task_id,
                    'status': result.status,
                    'ready': result.ready()
                }
            
            return Response(data)
        except TaskExecution.DoesNotExist:
            return Response(
                {'error': f'TaskExecution {execution_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
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
