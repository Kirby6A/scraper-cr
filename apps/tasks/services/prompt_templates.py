"""
Prompt templates for generating Stagehand scraper code
"""

class PromptTemplates:
    """Collection of prompt templates for different scraping scenarios"""
    
    @staticmethod
    def get_scraping_patterns():
        """Common scraping patterns and their implementations"""
        return {
            "table_extraction": {
                "description": "Extract data from HTML tables",
                "pattern": '''
# For table extraction
table_data = await page.extract({
    "instruction": "Extract all rows from the table including headers",
    "schema": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                # Define properties based on table columns
            }
        }
    }
})
'''
            },
            "pagination": {
                "description": "Handle paginated results",
                "pattern": '''
# Handle pagination
all_results = []
page_num = 1
max_pages = 10

while page_num <= max_pages:
    # Extract data from current page
    page_data = await page.extract({...})
    all_results.extend(page_data)
    
    # Check for next page
    next_button = await page.query_selector('a.next-page')
    if next_button:
        await next_button.click()
        await page.wait_for_load_state("networkidle")
        page_num += 1
    else:
        break
'''
            },
            "form_submission": {
                "description": "Fill and submit forms",
                "pattern": '''
# Fill form fields
await page.fill('input[name="search"]', search_term)
await page.select_option('select[name="category"]', category_value)

# Submit form
await page.click('button[type="submit"]')
await page.wait_for_load_state("networkidle")
'''
            },
            "infinite_scroll": {
                "description": "Handle infinite scroll pages",
                "pattern": '''
# Handle infinite scroll
previous_height = 0
while True:
    # Scroll to bottom
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(2000)  # Wait for new content
    
    # Check if new content loaded
    current_height = await page.evaluate("document.body.scrollHeight")
    if current_height == previous_height:
        break
    previous_height = current_height
'''
            },
            "authentication": {
                "description": "Handle login/authentication",
                "pattern": '''
# Handle authentication
await page.goto("https://site.com/login")
await page.fill('input[name="username"]', username)
await page.fill('input[name="password"]', password)
await page.click('button[type="submit"]')

# Wait for redirect after login
await page.wait_for_url("**/dashboard")
'''
            }
        }
    
    @staticmethod
    def get_extraction_schemas():
        """Common extraction schema examples"""
        return {
            "product": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "price": {"type": "string"},
                    "description": {"type": "string"},
                    "rating": {"type": "number"},
                    "availability": {"type": "boolean"},
                    "images": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            },
            "article": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "author": {"type": "string"},
                    "publishDate": {"type": "string"},
                    "content": {"type": "string"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            },
            "contact": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "address": {"type": "string"},
                    "company": {"type": "string"}
                }
            },
            "event": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "date": {"type": "string"},
                    "location": {"type": "string"},
                    "description": {"type": "string"},
                    "price": {"type": "string"},
                    "registrationUrl": {"type": "string"}
                }
            }
        }
    
    @staticmethod
    def enhance_prompt(user_prompt: str) -> str:
        """Enhance user prompt with additional context"""
        enhanced = f"""Task: {user_prompt}

Additional requirements:
1. Handle errors gracefully and return meaningful error messages
2. Include the source URL in the response
3. Add timestamp to track when data was scraped
4. Wait for page to fully load before extraction
5. Return structured data that's easy to process

Generate the scraper code:"""
        return enhanced
    
    @staticmethod
    def get_common_selectors():
        """Common CSS selectors and their uses"""
        return {
            "products": [
                "div.product-card",
                "article.product-item",
                "li.product",
                "[data-testid='product']"
            ],
            "prices": [
                "span.price",
                ".product-price",
                "[data-price]",
                "meta[itemprop='price']"
            ],
            "titles": [
                "h1",
                "h2.title",
                ".product-name",
                "[data-testid='product-title']"
            ],
            "pagination": [
                "a.next",
                "button[aria-label='Next page']",
                ".pagination a",
                "nav.pagination"
            ],
            "images": [
                "img.product-image",
                "picture img",
                "[data-testid='product-image']",
                ".gallery img"
            ]
        }
    
    @staticmethod
    def get_error_handling_template():
        """Standard error handling template"""
        return '''try:
    # Main scraping logic here
    await page.goto(url, timeout=30000)
    await page.wait_for_load_state("networkidle", timeout=30000)
    
    # Extract data
    data = await page.extract({
        "instruction": instruction,
        "schema": schema
    })
    
    return {
        "success": True,
        "data": data,
        "url": page.url,
        "timestamp": datetime.now().isoformat()
    }
    
except TimeoutError:
    return {
        "success": False,
        "error": "Page load timeout - site may be slow or unreachable",
        "url": url,
        "timestamp": datetime.now().isoformat()
    }
except Exception as e:
    return {
        "success": False,
        "error": str(e),
        "error_type": type(e).__name__,
        "url": url,
        "timestamp": datetime.now().isoformat()
    }'''
    
    @staticmethod
    def get_stagehand_best_practices():
        """Best practices for using Stagehand"""
        return [
            "Always use page.extract() for structured data extraction",
            "Provide clear instructions in natural language for extract()",
            "Define explicit schemas to ensure consistent data structure",
            "Use wait_for_load_state('networkidle') after navigation",
            "Handle both successful and failed extractions",
            "Include metadata like URL and timestamp in responses",
            "Use page.act() for complex interactions when needed",
            "Test selectors exist before interacting with them"
        ]