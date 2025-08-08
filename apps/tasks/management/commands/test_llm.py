from django.core.management.base import BaseCommand
from tasks.models import Task
from tasks.services.llm_service import LLMService
import asyncio
import json


class Command(BaseCommand):
    help = 'Test LLM code generation service'

    def add_arguments(self, parser):
        parser.add_argument(
            '--prompt',
            type=str,
            help='Natural language prompt for code generation',
            default='Scrape all product names and prices from an e-commerce website'
        )
        parser.add_argument(
            '--provider',
            type=str,
            choices=['openai', 'anthropic'],
            default='openai',
            help='LLM provider to use'
        )
        parser.add_argument(
            '--model',
            type=str,
            help='Specific model to use (e.g., gpt-4, claude-3-sonnet-20240229)'
        )
        parser.add_argument(
            '--create-task',
            action='store_true',
            help='Create a task with the generated code'
        )
        parser.add_argument(
            '--test-prompts',
            action='store_true',
            help='Test with multiple example prompts'
        )

    def handle(self, *args, **options):
        if options['test_prompts']:
            self.test_multiple_prompts(options['provider'], options['model'])
        else:
            self.test_single_prompt(
                options['prompt'],
                options['provider'],
                options['model'],
                options['create_task']
            )

    def test_single_prompt(self, prompt, provider, model, create_task):
        """Test code generation with a single prompt"""
        self.stdout.write(f"\nTesting LLM code generation with {provider}...")
        self.stdout.write(f"Prompt: {prompt}\n")
        
        # Initialize service
        try:
            llm_service = LLMService(provider=provider, model=model)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to initialize LLM service: {e}"))
            return
        
        # Generate code
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                llm_service.generate_scraper_code(
                    prompt=prompt,
                    examples=llm_service.get_example_scrapers(),
                    validate=True
                )
            )
        finally:
            loop.close()
        
        if result['success']:
            self.stdout.write(self.style.SUCCESS("\n✓ Code generation successful!"))
            self.stdout.write(f"\nGenerated Code:\n{'-' * 50}")
            self.stdout.write(result['code'])
            self.stdout.write(f"{'-' * 50}\n")
            
            # Show validation results
            validation = result.get('validation', {})
            if validation.get('valid'):
                self.stdout.write(self.style.SUCCESS("✓ Code validation passed"))
            else:
                self.stdout.write(self.style.WARNING(f"⚠ Validation issues: {validation.get('issues')}"))
            
            # Show token usage
            usage = result.get('usage', {})
            if usage:
                self.stdout.write(f"\nToken Usage:")
                self.stdout.write(f"  - Prompt tokens: {usage.get('prompt_tokens', 'N/A')}")
                self.stdout.write(f"  - Completion tokens: {usage.get('completion_tokens', 'N/A')}")
                self.stdout.write(f"  - Total tokens: {usage.get('total_tokens', 'N/A')}")
            
            # Create task if requested
            if create_task:
                task = Task.objects.create(
                    name=f"LLM Generated - {prompt[:50]}",
                    description=f"Generated using {provider}/{result.get('model', 'unknown')}",
                    natural_language_prompt=prompt,
                    generated_code=result['code'],
                    llm_provider=provider,
                    llm_model=result.get('model', ''),
                    llm_tokens_used=usage.get('total_tokens', 0),
                    code_generation_metadata={
                        'prompt': prompt,
                        'validation': validation,
                        'usage': usage
                    },
                    is_active=True
                )
                self.stdout.write(self.style.SUCCESS(f"\n✓ Created task: {task.name} (ID: {task.id})"))
        else:
            self.stdout.write(self.style.ERROR(f"\n✗ Code generation failed: {result.get('error')}"))

    def test_multiple_prompts(self, provider, model):
        """Test with various example prompts"""
        test_prompts = [
            "Scrape all article titles and publication dates from a news website",
            "Extract product reviews including rating, reviewer name, and comment text from an e-commerce product page",
            "Monitor stock prices by scraping current price, change percentage, and volume from a financial website",
            "Collect job listings with title, company, location, and salary from a job board",
            "Scrape restaurant information including name, cuisine type, rating, and price range from a restaurant directory",
            "Extract event details like name, date, venue, and ticket prices from an events website",
            "Gather real estate listings with price, bedrooms, location, and square footage",
            "Scrape social media profile data including follower count, bio, and recent posts"
        ]
        
        self.stdout.write(f"\nTesting {len(test_prompts)} different prompts with {provider}...\n")
        
        successful = 0
        failed = 0
        
        for i, prompt in enumerate(test_prompts, 1):
            self.stdout.write(f"\n[{i}/{len(test_prompts)}] Testing: {prompt[:60]}...")
            
            # Initialize service
            try:
                llm_service = LLMService(provider=provider, model=model)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to initialize: {e}"))
                failed += 1
                continue
            
            # Generate code
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    llm_service.generate_scraper_code(
                        prompt=prompt,
                        validate=True
                    )
                )
            finally:
                loop.close()
            
            if result['success']:
                validation = result.get('validation', {})
                if validation.get('valid'):
                    self.stdout.write(self.style.SUCCESS("✓ Success - Valid code generated"))
                    successful += 1
                else:
                    self.stdout.write(self.style.WARNING(f"⚠ Generated but invalid: {validation.get('issues')}"))
                    failed += 1
            else:
                self.stdout.write(self.style.ERROR(f"✗ Failed: {result.get('error')[:100]}"))
                failed += 1
        
        # Summary
        self.stdout.write(f"\n{'-' * 50}")
        self.stdout.write(f"Summary: {successful} successful, {failed} failed")
        self.stdout.write(f"Success rate: {(successful/len(test_prompts)*100):.1f}%")