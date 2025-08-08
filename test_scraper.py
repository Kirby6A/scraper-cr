import asyncio
from tasks.models import Task
from tasks.services.scraper_service import StagehandScraperService

async def test_execution():
    # Get the task
    task = Task.objects.get(id="ace5818a-04de-431c-88eb-8c4aa05eb267")
    
    # Update with a testable scraper code
    test_code = '''
from datetime import datetime

async def scrape_data():
    """Test scraper using httpbin.org"""
    try:
        # Navigate to test site
        await page.goto("https://httpbin.org/html")
        await page.wait_for_load_state("networkidle")
        
        # Extract simple data
        data = await page.extract({
            "instruction": "Extract the main heading and any links from the page",
            "schema": {
                "type": "object",
                "properties": {
                    "heading": {"type": "string"},
                    "links": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            }
        })
        
        return {
            "success": True,
            "data": data,
            "url": page.url,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
'''
    
    # Update task with test code
    task.generated_code = test_code
    task.save()
    
    # Execute scraper
    service = StagehandScraperService()
    result = service.execute_scraper(test_code)
    
    print("Execution Result:")
    print(result)
    
    return result

if __name__ == "__main__":
    asyncio.run(test_execution())