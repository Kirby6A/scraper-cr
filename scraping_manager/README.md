# Scraping Manager - Phase 1

A Django-based web scraping task management application using Stagehand (AI-powered Playwright wrapper), Celery, and Docker.

## Quick Start

1. Copy `.env.example` to `.env` and adjust settings if needed
2. Run the application:
   ```bash
   docker-compose up -d
   ```
3. Run migrations:
   ```bash
   docker-compose exec web python manage.py migrate
   ```
4. Create a superuser:
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```
5. Access the admin interface at http://localhost:8000/admin

## Example Scraping Task Code

When creating a ScrapingTask in the admin, use code like this in the `generated_code` field:

```python
async def scrape_example(stagehand):
    page = stagehand.page
    await page.goto("https://example.com")
    
    data = await page.extract({
        "instruction": "extract the main heading and first paragraph",
        "schema": {
            "heading": str,
            "paragraph": str
        }
    })
    
    return [data]  # Always return list of items
```

## Features

- **ScrapingGroups**: Container for related tasks with cron scheduling
- **ScrapingTasks**: Individual scraping jobs with Stagehand code
- **Docker Isolation**: Each task runs in its own container
- **Deduplication**: Hash-based deduplication of scraped items
- **Email Notifications**: Optional email digests after group completion
- **Django Admin**: Full management interface with test execution

## Testing a Task

1. Create a ScrapingGroup in the admin
2. Add a ScrapingTask with the example code above
3. Select the task and use the "Test selected tasks" action
4. View results in TaskRun and ScrapedItem sections

## Architecture

- **Django**: Web framework and admin interface
- **PostgreSQL**: Primary database
- **Redis**: Celery message broker
- **Celery**: Async task execution
- **Celery Beat**: Scheduled task runner
- **Docker**: Container isolation for scraping tasks
- **Stagehand**: AI-powered web scraping with Playwright