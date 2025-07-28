import asyncio
from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from .executors import TaskExecutor
from django.utils import timezone
from .models import ScrapingGroup, TaskRun, ScrapingTask

logger = get_task_logger(__name__)


@shared_task
def run_scraping_task(task_id: int):
    """Celery task to run a single scraping task"""
    logger.info(f"Starting scraping task {task_id}")
    
    try:
        executor = TaskExecutor()
        # Run async code in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(executor.execute_task(task_id))
        loop.close()
        
        logger.info(f"Completed scraping task {task_id}: {result}")
        return result
    except Exception as e:
        logger.error(f"Error running scraping task {task_id}: {str(e)}")
        raise


@shared_task
def run_scraping_group(group_id: int):
    """Celery task to run all tasks in a group"""
    logger.info(f"Starting scraping group {group_id}")
    
    try:
        group = ScrapingGroup.objects.get(id=group_id)
        tasks = group.tasks.filter(is_active=True).order_by('execution_order')
        
        task_results = []
        
        if group.run_parallel:
            # Run tasks in parallel
            task_signatures = []
            for task in tasks:
                signature = run_scraping_task.s(task.id)
                task_signatures.append(signature)
            
            # Execute all tasks in parallel
            from celery import group as celery_group
            job = celery_group(task_signatures)
            results = job.apply_async()
            task_results = results.get()
        else:
            # Run tasks sequentially
            for task in tasks:
                result = run_scraping_task.delay(task.id).get()
                task_results.append(result)
        
        # Send notification email if configured
        if group.notification_emails:
            send_group_completion_email.delay(group_id, task_results)
        
        logger.info(f"Completed scraping group {group_id}")
        return {
            'group_id': group_id,
            'tasks_run': len(task_results),
            'results': task_results
        }
        
    except Exception as e:
        logger.error(f"Error running scraping group {group_id}: {str(e)}")
        raise


@shared_task
def send_group_completion_email(group_id: int, task_results: list):
    """Send email notification after group completion"""
    try:
        group = ScrapingGroup.objects.get(id=group_id)
        
        # Prepare email context
        total_items = sum(r.get('items_found', 0) for r in task_results if r.get('success'))
        new_items = sum(r.get('new_items', 0) for r in task_results if r.get('success'))
        failed_tasks = sum(1 for r in task_results if not r.get('success'))
        
        subject = f"Scraping Group '{group.name}' Completed"
        
        # Simple text email for now (can be enhanced with HTML template later)
        message = f"""
Scraping group '{group.name}' has completed execution.

Summary:
- Total tasks: {len(task_results)}
- Successful tasks: {len(task_results) - failed_tasks}
- Failed tasks: {failed_tasks}
- Total items found: {total_items}
- New items: {new_items}

View details in the admin panel.
"""
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            group.notification_emails,
            fail_silently=False,
        )
        
        logger.info(f"Sent completion email for group {group_id}")
        
    except Exception as e:
        logger.error(f"Error sending completion email for group {group_id}: {str(e)}")


@shared_task
def test_scraping_task(task_id: int):
    """Test a scraping task and update its status"""
    logger.info(f"Testing scraping task {task_id}")
    
    try:
        task = ScrapingTask.objects.get(id=task_id)
        task.test_status = 'TESTING'
        task.save()
        
        # Run the task
        result = run_scraping_task(task_id)
        
        # Update test status based on result
        if result.get('success'):
            task.test_status = 'PASSED'
        else:
            task.test_status = 'FAILED'
        
        task.last_test_at = timezone.now()
        task.save()
        
        logger.info(f"Test completed for task {task_id}: {task.test_status}")
        return result
        
    except Exception as e:
        logger.error(f"Error testing task {task_id}: {str(e)}")
        task = ScrapingTask.objects.get(id=task_id)
        task.test_status = 'FAILED'
        task.save()
        raise