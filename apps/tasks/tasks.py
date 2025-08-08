"""
Celery tasks for background scraper execution
"""
from celery import shared_task
from django.db import transaction
from django.utils import timezone
import logging
import asyncio

logger = logging.getLogger(__name__)


@shared_task(name='tasks.execute_scraper')
def execute_scraper_task(execution_id):
    """
    Execute scraper in background - runs in Celery worker
    This fixes the "signal only works in main thread" error
    """
    from .models import TaskExecution
    from .services.scraper_service import StagehandScraperService
    
    execution = None
    try:
        # Get the execution record
        execution = TaskExecution.objects.get(id=execution_id)
        task = execution.task
        
        # Update status to running
        execution.status = 'running'
        execution.save()
        
        logger.info(f"Starting scraper execution for task: {task.name}")
        
        # Validate code first
        service = StagehandScraperService()
        validation = service.validate_code(task.generated_code)
        
        if not validation['valid']:
            execution.status = 'failed'
            execution.error_message = f"Code validation failed: {', '.join(validation['issues'])}"
            execution.completed_at = timezone.now()
            execution.save()
            logger.error(f"Code validation failed for task {task.id}: {validation['issues']}")
            return {'success': False, 'error': execution.error_message}
        
        # Execute the scraper
        result = service.execute_scraper(task.generated_code)
        
        # Update execution with results
        if result['success']:
            execution.status = 'success'
            execution.scraped_data = result.get('data', {})
            logger.info(f"Scraper execution successful for task: {task.name}")
        else:
            execution.status = 'failed'
            execution.error_message = result.get('error', 'Unknown error')
            logger.error(f"Scraper execution failed for task {task.id}: {execution.error_message}")
        
        execution.completed_at = timezone.now()
        execution.save()
        
        return {
            'success': result['success'],
            'execution_id': str(execution_id),
            'data': result.get('data') if result['success'] else None,
            'error': result.get('error') if not result['success'] else None
        }
        
    except TaskExecution.DoesNotExist:
        logger.error(f"TaskExecution with id {execution_id} not found")
        return {'success': False, 'error': f'TaskExecution {execution_id} not found'}
    except Exception as e:
        logger.error(f"Task execution failed: {str(e)}", exc_info=True)
        if execution:
            execution.status = 'failed'
            execution.error_message = str(e)
            execution.completed_at = timezone.now()
            execution.save()
        return {'success': False, 'error': str(e)}


@shared_task(name='tasks.generate_code')
def generate_code_task(task_id, provider='openai', model=None, use_examples=True):
    """
    Generate scraper code asynchronously using LLM
    """
    from .models import Task
    from .services.llm_service import LLMService
    
    try:
        # Get the task
        task = Task.objects.get(id=task_id)
        
        logger.info(f"Generating code for task: {task.name}")
        
        # Initialize LLM service
        llm_service = LLMService(provider=provider, model=model)
        
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
            
            logger.info(f"Code generation successful for task: {task.name}")
            return {
                'success': True,
                'task_id': str(task_id),
                'code_generated': True
            }
        else:
            logger.error(f"Code generation failed for task {task_id}: {result.get('error')}")
            return {
                'success': False,
                'task_id': str(task_id),
                'error': result.get('error', 'Unknown error')
            }
            
    except Task.DoesNotExist:
        logger.error(f"Task with id {task_id} not found")
        return {'success': False, 'error': f'Task {task_id} not found'}
    except Exception as e:
        logger.error(f"Code generation failed: {str(e)}", exc_info=True)
        return {'success': False, 'error': str(e)}


@shared_task(name='tasks.execute_scheduled_scraper')
def execute_scheduled_scraper(task_id):
    """
    Execute a scheduled scraper task
    Called by Celery Beat based on cron schedule
    """
    from .models import Task, TaskExecution
    
    try:
        # Get the task
        task = Task.objects.get(id=task_id)
        
        if not task.is_active:
            logger.info(f"Skipping inactive task: {task.name}")
            return {'success': False, 'error': 'Task is inactive'}
        
        if not task.generated_code:
            logger.error(f"No generated code for task: {task.name}")
            return {'success': False, 'error': 'No generated code available'}
        
        # Create execution record
        execution = TaskExecution.objects.create(
            task=task,
            status='pending',
            metadata={'scheduled': True, 'trigger': 'celery-beat'}
        )
        
        # Update last scheduled run
        task.last_scheduled_run = timezone.now()
        task.save()
        
        # Execute the scraper
        return execute_scraper_task(str(execution.id))
        
    except Task.DoesNotExist:
        logger.error(f"Task with id {task_id} not found")
        return {'success': False, 'error': f'Task {task_id} not found'}
    except Exception as e:
        logger.error(f"Scheduled execution failed: {str(e)}", exc_info=True)
        return {'success': False, 'error': str(e)}


@shared_task(name='tasks.test_celery')
def test_celery():
    """Simple task to test if Celery is working"""
    logger.info("Celery is working!")
    return {'status': 'Celery is working!', 'timestamp': timezone.now().isoformat()}