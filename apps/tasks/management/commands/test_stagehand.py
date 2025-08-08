from django.core.management.base import BaseCommand
from tasks.models import Task
from tasks.services.scraper_service import StagehandScraperService, ExampleScrapers
import json


class Command(BaseCommand):
    help = 'Test Stagehand scraper integration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-example',
            action='store_true',
            help='Create an example task with scraper code',
        )

    def handle(self, *args, **options):
        if options['create_example']:
            self.create_example_task()
        else:
            self.test_scraper()

    def create_example_task(self):
        """Create an example task with pre-generated scraper code"""
        self.stdout.write("Creating example task...")
        
        # Get example scraper code
        example_code = '''
from datetime import datetime

async def scrape_data():
    """Example scraper that extracts data from a website"""
    try:
        # Navigate to the website
        await page.goto("https://example.com")
        
        # Wait for page to load
        await page.wait_for_load_state("networkidle")
        
        # Extract the title
        title = await page.title()
        
        # Extract main heading and paragraph using Stagehand's extract
        content = await page.extract({
            "instruction": "Extract the main heading (h1) and the first paragraph",
            "schema": {
                "type": "object",
                "properties": {
                    "heading": {"type": "string"},
                    "paragraph": {"type": "string"}
                }
            }
        })
        
        return {
            "success": True,
            "url": "https://example.com",
            "title": title,
            "content": content,
            "timestamp": str(datetime.now())
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
'''
        
        task = Task.objects.create(
            name="Example.com Scraper",
            description="Scrapes title and content from example.com",
            natural_language_prompt="Extract the page title, main heading, and first paragraph from example.com",
            generated_code=example_code,
            is_active=True
        )
        
        self.stdout.write(self.style.SUCCESS(f"Created task: {task.name} (ID: {task.id})"))
        self.stdout.write("You can now execute this task via the API or admin interface.")

    def test_scraper(self):
        """Test the scraper service directly"""
        self.stdout.write("Testing Stagehand scraper service...")
        
        # Simple test code
        test_code = '''
from datetime import datetime

async def scrape_data():
    """Test scraper"""
    try:
        await page.goto("https://example.com")
        await page.wait_for_load_state("networkidle")
        
        title = await page.title()
        
        return {
            "success": True,
            "title": title,
            "url": "https://example.com",
            "timestamp": str(datetime.now())
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
'''
        
        service = StagehandScraperService()
        
        # Validate code
        self.stdout.write("Validating code...")
        validation = service.validate_code(test_code)
        if validation['valid']:
            self.stdout.write(self.style.SUCCESS("✓ Code validation passed"))
        else:
            self.stdout.write(self.style.ERROR(f"✗ Code validation failed: {validation['issues']}"))
            return
        
        # Execute scraper
        self.stdout.write("Executing scraper...")
        result = service.execute_scraper(test_code)
        
        if result['success']:
            self.stdout.write(self.style.SUCCESS("✓ Scraper executed successfully"))
            self.stdout.write(f"Result: {json.dumps(result['data'], indent=2)}")
        else:
            self.stdout.write(self.style.ERROR(f"✗ Scraper failed: {result['error']}"))