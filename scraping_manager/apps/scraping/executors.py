import asyncio
import hashlib
import json
import docker
import tempfile
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from django.utils import timezone
from .models import TaskRun, ScrapedItem, ScrapingTask
from apps.common.utils import generate_hash


class TaskExecutor:
    def __init__(self):
        self.docker_client = docker.from_env()
    
    async def execute_task(self, task_id: int) -> Dict[str, Any]:
        """Execute a scraping task in a Docker container"""
        task = ScrapingTask.objects.get(id=task_id)
        
        # Create TaskRun record
        task_run = TaskRun.objects.create(
            task=task,
            status='RUNNING'
        )
        
        try:
            # Run the task in a container
            result = await self.run_in_container(
                code=task.generated_code,
                task_name=task.name,
                target_url=task.target_url
            )
            
            # Process results with deduplication
            items_processed = 0
            new_items = 0
            
            if result['success'] and result['data']:
                for item_data in result['data']:
                    # Generate hash for deduplication
                    hash_fields = ['title', 'url', 'description'] if not task.extraction_schema else list(task.extraction_schema.keys())
                    item_hash = generate_hash(item_data, hash_fields)
                    
                    # Check if item already exists
                    existing_item = ScrapedItem.objects.filter(
                        task=task,
                        unique_hash=item_hash
                    ).first()
                    
                    if existing_item:
                        # Update existing item
                        existing_item.last_seen = timezone.now()
                        existing_item.times_seen += 1
                        existing_item.save()
                    else:
                        # Create new item
                        ScrapedItem.objects.create(
                            task=task,
                            run=task_run,
                            item_type=task.data_type,
                            unique_hash=item_hash,
                            data=item_data,
                            source_urls=[task.target_url]
                        )
                        new_items += 1
                    
                    items_processed += 1
            
            # Update TaskRun with results
            task_run.status = 'SUCCESS' if result['success'] else 'FAILED'
            task_run.completed_at = timezone.now()
            task_run.items_found = items_processed
            task_run.execution_logs = result.get('logs', {})
            task_run.error_message = result.get('error', '')
            task_run.save()
            
            # Update task average execution time
            execution_time = (task_run.completed_at - task_run.started_at).total_seconds()
            if task.avg_execution_time:
                task.avg_execution_time = (task.avg_execution_time + execution_time) / 2
            else:
                task.avg_execution_time = execution_time
            task.save()
            
            return {
                'success': result['success'],
                'task_run_id': task_run.id,
                'items_found': items_processed,
                'new_items': new_items,
                'execution_time': execution_time
            }
            
        except Exception as e:
            # Handle errors
            task_run.status = 'FAILED'
            task_run.completed_at = timezone.now()
            task_run.error_message = str(e)
            task_run.save()
            
            return {
                'success': False,
                'task_run_id': task_run.id,
                'error': str(e)
            }
    
    async def run_in_container(self, code: str, task_name: str, target_url: str) -> Dict[str, Any]:
        """Execute Stagehand code in isolated container"""
        # Create wrapper script
        wrapper_code = f'''
import asyncio
import json
import sys
from stagehand import Stagehand

async def main():
    try:
        async with Stagehand(headless=True) as stagehand:
            # User-provided scraping function
{self._indent_code(code, 12)}
            
            # Execute the scraping function
            result = await scrape_example(stagehand)
            
            # Output result as JSON
            print(json.dumps({{"success": True, "data": result}}))
    except Exception as e:
        print(json.dumps({{"success": False, "error": str(e)}}))
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
'''
        
        # Create temporary file with the script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(wrapper_code)
            script_path = f.name
        
        try:
            # Run container
            container = self.docker_client.containers.run(
                'python:3.11-slim',
                command=f'bash -c "pip install stagehand playwright && playwright install chromium && python /script.py"',
                volumes={
                    script_path: {'bind': '/script.py', 'mode': 'ro'}
                },
                detach=True,
                mem_limit='2g',
                cpu_quota=100000,  # Limit CPU usage
                environment={
                    'TARGET_URL': target_url
                }
            )
            
            # Wait for container to complete (with timeout)
            result = container.wait(timeout=300)  # 5 minute timeout
            
            # Get logs
            logs = container.logs(stdout=True, stderr=True).decode('utf-8')
            
            # Parse output
            try:
                # Find JSON output in logs
                import re
                json_pattern = r'\{.*"success".*\}'
                matches = re.findall(json_pattern, logs, re.DOTALL)
                if matches:
                    output = json.loads(matches[-1])
                else:
                    output = {'success': False, 'error': 'No JSON output found'}
            except json.JSONDecodeError:
                output = {'success': False, 'error': 'Failed to parse output', 'logs': logs}
            
            # Add logs to output
            output['logs'] = {'container_logs': logs, 'exit_code': result['StatusCode']}
            
            return output
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'logs': {'error': str(e)}
            }
        finally:
            # Clean up
            os.unlink(script_path)
            try:
                container.remove(force=True)
            except:
                pass
    
    def _indent_code(self, code: str, spaces: int) -> str:
        """Indent code by specified number of spaces"""
        indent = ' ' * spaces
        return '\n'.join(indent + line for line in code.split('\n'))