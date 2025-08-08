import os
import json
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import openai
from anthropic import Anthropic
from django.conf import settings


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def generate_code(self, prompt: str, examples: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Generate code from natural language prompt"""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider for code generation"""
    
    def __init__(self, api_key: str = None, model: str = "gpt-4"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.client = openai.OpenAI(api_key=self.api_key)
    
    async def generate_code(self, prompt: str, examples: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Generate Stagehand scraper code using OpenAI"""
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(prompt, examples)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            generated_code = response.choices[0].message.content
            
            # Extract code from markdown if present
            if "```python" in generated_code:
                generated_code = self._extract_code_from_markdown(generated_code)
            
            return {
                "success": True,
                "code": generated_code,
                "model": self.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": self.model
            }
    
    def _build_system_prompt(self) -> str:
        return """You are an expert web scraping developer specialized in creating Stagehand scrapers.
Your task is to convert natural language descriptions into working Python code that uses the Stagehand library.

IMPORTANT RULES:
1. Always create an async function named 'scrape_data' that takes no parameters
2. The function must use the pre-initialized 'page' and 'stagehand' objects
3. Use Stagehand's extract() method for data extraction when possible
4. Always return a dictionary with 'success' key and scraped data
5. Include proper error handling with try/except blocks
6. Add helpful comments explaining the scraping logic
7. Use page.goto() to navigate to URLs
8. Wait for page load with page.wait_for_load_state("networkidle")
9. Return timestamps in ISO format

AVAILABLE OBJECTS:
- page: Playwright page object for browser automation
- stagehand: Stagehand instance with extract() and other methods

EXAMPLE STRUCTURE:
```python
from datetime import datetime

async def scrape_data():
    \"\"\"Description of what this scraper does\"\"\"
    try:
        # Navigate to the target website
        await page.goto("https://example.com")
        await page.wait_for_load_state("networkidle")
        
        # Extract data using Stagehand
        data = await page.extract({
            "instruction": "Extract specific data",
            "schema": {
                "type": "object",
                "properties": {
                    "field1": {"type": "string"},
                    "field2": {"type": "array"}
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
```

Generate clean, efficient, and well-documented code."""
    
    def _build_user_prompt(self, prompt: str, examples: List[Dict[str, str]] = None) -> str:
        user_prompt = f"Create a Stagehand scraper for the following task:\n\n{prompt}\n\n"
        
        if examples:
            user_prompt += "Here are some similar examples for reference:\n\n"
            for example in examples:
                user_prompt += f"Task: {example['prompt']}\nCode:\n{example['code']}\n\n"
        
        user_prompt += "Generate the Python code for this scraper:"
        return user_prompt
    
    def _extract_code_from_markdown(self, text: str) -> str:
        """Extract Python code from markdown code blocks"""
        lines = text.split('\n')
        code_lines = []
        in_code_block = False
        
        for line in lines:
            if line.strip() == "```python":
                in_code_block = True
                continue
            elif line.strip() == "```" and in_code_block:
                in_code_block = False
                continue
            elif in_code_block:
                code_lines.append(line)
        
        return '\n'.join(code_lines)


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider for code generation"""
    
    def __init__(self, api_key: str = None, model: str = "claude-3-sonnet-20240229"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.client = Anthropic(api_key=self.api_key)
    
    async def generate_code(self, prompt: str, examples: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Generate Stagehand scraper code using Claude"""
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(prompt, examples)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            generated_code = response.content[0].text
            
            # Extract code from markdown if present
            if "```python" in generated_code:
                generated_code = self._extract_code_from_markdown(generated_code)
            
            return {
                "success": True,
                "code": generated_code,
                "model": self.model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": self.model
            }
    
    def _build_system_prompt(self) -> str:
        # Same system prompt as OpenAI provider
        return OpenAIProvider._build_system_prompt(self)
    
    def _build_user_prompt(self, prompt: str, examples: List[Dict[str, str]] = None) -> str:
        # Same user prompt builder as OpenAI provider
        return OpenAIProvider._build_user_prompt(self, prompt, examples)
    
    def _extract_code_from_markdown(self, text: str) -> str:
        # Same markdown extraction as OpenAI provider
        return OpenAIProvider._extract_code_from_markdown(self, text)


class LLMService:
    """Main service for LLM code generation"""
    
    def __init__(self, provider: str = "openai", model: str = None):
        self.provider_name = provider
        self.model = model
        self.provider = self._initialize_provider(provider, model)
    
    def _initialize_provider(self, provider: str, model: str = None) -> LLMProvider:
        """Initialize the appropriate LLM provider"""
        if provider.lower() == "openai":
            return OpenAIProvider(model=model or "gpt-4")
        elif provider.lower() == "anthropic":
            return AnthropicProvider(model=model or "claude-3-sonnet-20240229")
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    async def generate_scraper_code(
        self, 
        prompt: str, 
        examples: List[Dict[str, str]] = None,
        validate: bool = True
    ) -> Dict[str, Any]:
        """Generate Stagehand scraper code from natural language prompt"""
        
        # Generate code using the provider
        result = await self.provider.generate_code(prompt, examples)
        
        if not result["success"]:
            return result
        
        # Optionally validate the generated code
        if validate:
            validation = self.validate_generated_code(result["code"])
            result["validation"] = validation
            
            if not validation["valid"]:
                result["success"] = False
                result["error"] = f"Code validation failed: {', '.join(validation['issues'])}"
        
        return result
    
    def validate_generated_code(self, code: str) -> Dict[str, Any]:
        """Validate that generated code follows required structure"""
        issues = []
        
        # Check for required function
        if "async def scrape_data():" not in code:
            issues.append("Missing required 'async def scrape_data()' function")
        
        # Check for return statement
        if "return" not in code:
            issues.append("Missing return statement")
        
        # Check for error handling
        if "try:" not in code or "except" not in code:
            issues.append("Missing try/except error handling")
        
        # Check for page.goto
        if "page.goto" not in code:
            issues.append("Missing page.goto() navigation")
        
        # Check for success key in return
        if '"success":' not in code and "'success':" not in code:
            issues.append("Return dictionary should include 'success' key")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    def get_example_scrapers(self) -> List[Dict[str, str]]:
        """Get example scrapers for few-shot learning"""
        return [
            {
                "prompt": "Scrape all product names and prices from an e-commerce product listing page",
                "code": '''from datetime import datetime

async def scrape_data():
    """Scrape product names and prices from e-commerce listing"""
    try:
        await page.goto("https://example-shop.com/products")
        await page.wait_for_load_state("networkidle")
        
        # Extract product data using Stagehand
        products = await page.extract({
            "instruction": "Extract all product names and their prices from the product grid",
            "schema": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "price": {"type": "string"},
                        "currency": {"type": "string"}
                    }
                }
            }
        })
        
        return {
            "success": True,
            "products": products,
            "count": len(products),
            "url": page.url,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }'''
            },
            {
                "prompt": "Extract article title, author, and publication date from a news website",
                "code": '''from datetime import datetime

async def scrape_data():
    """Extract article metadata from news website"""
    try:
        await page.goto("https://news-site.com/article/12345")
        await page.wait_for_load_state("networkidle")
        
        # Extract article metadata
        article_data = await page.extract({
            "instruction": "Extract the article title, author name, and publication date",
            "schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "author": {"type": "string"},
                    "publishDate": {"type": "string"},
                    "content": {"type": "string"}
                }
            }
        })
        
        return {
            "success": True,
            "article": article_data,
            "url": page.url,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }'''
            }
        ]