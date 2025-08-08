import asyncio
import json
import logging
from typing import Dict, Any, Optional
from stagehand import Stagehand
from django.conf import settings
import os

logger = logging.getLogger(__name__)


class StagehandScraperService:
    """Service for executing web scraping tasks using Stagehand Python SDK"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY', '')
        self.model_name = os.getenv('STAGEHAND_MODEL', 'gpt-4o-mini')
        
    async def execute_scraper_async(self, code: str) -> Dict[str, Any]:
        """Execute scraper code asynchronously"""
        stagehand = None
        try:
            # Create Stagehand instance
            stagehand = Stagehand(
                openai_api_key=self.api_key,
                model_name=self.model_name,
                env="LOCAL",
                verbose=1,
                headless=True
            )
            
            # Initialize browser
            await stagehand.init()
            
            # Create a namespace for code execution
            namespace = {
                'stagehand': stagehand,
                'page': stagehand.page,
                'result': None
            }
            
            # Execute the generated code
            exec(code, namespace)
            
            # If the code defines an async function, run it
            if 'scrape_data' in namespace and asyncio.iscoroutinefunction(namespace['scrape_data']):
                result = await namespace['scrape_data']()
            else:
                result = namespace.get('result', {})
            
            return {
                'success': True,
                'data': result,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Scraper execution failed: {str(e)}")
            return {
                'success': False,
                'data': None,
                'error': str(e)
            }
        finally:
            if stagehand:
                try:
                    await stagehand.close()
                except:
                    pass
    
    def execute_scraper(self, code: str) -> Dict[str, Any]:
        """Execute scraper code synchronously (wrapper for async method)"""
        try:
            # Create new event loop for sync execution
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.execute_scraper_async(code))
            loop.close()
            return result
        except Exception as e:
            logger.error(f"Failed to execute scraper: {str(e)}")
            return {
                'success': False,
                'data': None,
                'error': str(e)
            }
    
    def validate_code(self, code: str) -> Dict[str, Any]:
        """Validate that the code is safe and contains required elements"""
        issues = []
        
        # Basic validation
        if not code.strip():
            issues.append("Code is empty")
            
        # Check for dangerous operations
        dangerous_ops = ['__import__', 'eval', 'exec', 'compile', 'open', 'file', 'input', 'raw_input']
        for op in dangerous_ops:
            if op in code and op != 'exec':  # We use exec ourselves
                issues.append(f"Dangerous operation '{op}' detected")
        
        # Check for required async function
        if 'async def scrape_data' not in code:
            issues.append("Missing 'async def scrape_data()' function")
            
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }


class ExampleScrapers:
    """Collection of example scrapers for testing"""
    
    @staticmethod
    def get_example_scraper() -> str:
        """Get a simple example scraper"""
        return '''
async def scrape_data():
    """Example scraper that extracts data from a website"""
    try:
        # Navigate to the website
        await page.goto("https://example.com")
        
        # Extract data using Stagehand's extract method
        data = await page.extract({
            "instruction": "Extract the main heading and first paragraph",
            "schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"}
                }
            }
        })
        
        return {
            "success": True,
            "data": data,
            "url": "https://example.com",
            "timestamp": str(datetime.now())
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
'''

    @staticmethod
    def get_product_scraper() -> str:
        """Get a product listing scraper example"""
        return '''
async def scrape_data():
    """Scrape product listings"""
    try:
        await page.goto("https://example-shop.com/products")
        
        # Extract product data
        products = await page.extract({
            "instruction": "Extract all products with their name, price, and availability",
            "schema": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "price": {"type": "string"},
                        "in_stock": {"type": "boolean"},
                        "url": {"type": "string"}
                    }
                }
            }
        })
        
        return {
            "success": True,
            "products": products,
            "count": len(products),
            "timestamp": str(datetime.now())
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
'''