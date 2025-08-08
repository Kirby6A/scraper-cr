# Carbon Reform Web Scraping Platform - Complete Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [File Structure & Components](#file-structure--components)
4. [Installation & Setup](#installation--setup)
5. [Running the Application](#running-the-application)
6. [API Documentation](#api-documentation)
7. [Complete Workflows](#complete-workflows)
8. [Troubleshooting](#troubleshooting)
9. [Development Guide](#development-guide)

---

## Project Overview

The Carbon Reform Web Scraping Platform is an intelligent web scraping automation system that converts natural language descriptions into executable web scrapers using AI. Built with Django, Celery, and Stagehand, it enables users to create, schedule, and execute web scrapers without writing code.

### Key Features
- 🤖 **AI-Powered Code Generation**: Converts natural language to working scraper code
- 🚀 **Async Execution**: Background task processing with Celery
- 🎯 **Smart Extraction**: Uses Stagehand's AI-powered selectors
- 📊 **Data Management**: PostgreSQL/Supabase with JSONB storage
- 🔄 **Scheduling**: Cron-based periodic scraping
- 📈 **Monitoring**: Real-time execution status tracking

### Technology Stack
- **Backend**: Django 4.2.7 + Django REST Framework
- **Task Queue**: Celery 5.3.4 + Redis
- **Web Scraping**: Stagehand (Python SDK) + Playwright
- **AI/LLM**: OpenAI GPT-4
- **Database**: PostgreSQL (Supabase) / SQLite (dev)
- **Browser Automation**: Playwright

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   REST API      │────▶│   Celery        │────▶│   Stagehand     │
│   (Django)      │     │   Workers       │     │   Scrapers      │
│                 │     │                 │     │                 │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                         │
         │                       ▼                         │
         │              ┌─────────────────┐               │
         │              │                 │               │
         └─────────────▶│     Redis       │◀──────────────┘
                        │   Message Queue │
                        │                 │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │                 │
                        │   PostgreSQL    │
                        │   (Supabase)    │
                        │                 │
                        └─────────────────┘
```

### Data Flow
1. User submits natural language prompt via API
2. LLM service generates Stagehand scraper code
3. Task queued to Celery via Redis
4. Worker executes scraper in separate process
5. Stagehand/Playwright extracts data
6. Results stored in PostgreSQL/Supabase

---

## File Structure & Components

### Root Directory
```
stagehand-cr/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── .env                     # Environment variables (create from .env.example)
├── .gitignore              # Git ignore rules
├── README.md               # Quick start guide
├── DOCUMENTATION.md        # This file
└── db.sqlite3             # SQLite database (development)
```

### Django Project Configuration
```
carbon_reform_scraper/
├── __init__.py            # Imports Celery app
├── settings.py            # Django settings & configuration
├── urls.py                # Root URL configuration
├── wsgi.py               # WSGI application
├── asgi.py               # ASGI application
└── celery.py             # Celery configuration
```

#### Key Files Explained:

**`carbon_reform_scraper/celery.py`**
- Configures Celery application
- Sets up Redis as message broker
- Auto-discovers tasks from Django apps
- Defines task routing and queues

**`carbon_reform_scraper/settings.py`**
- Database configuration (PostgreSQL/SQLite)
- Installed apps including `tasks` and `django_celery_beat`
- Celery settings (broker URL, result backend)
- CORS configuration for frontend
- Environment variable management

### Main Application
```
apps/tasks/
├── __init__.py
├── models.py              # Database models
├── serializers.py         # DRF serializers
├── views.py              # API views & endpoints
├── urls.py               # URL routing
├── admin.py              # Django admin config
├── tasks.py              # Celery task definitions
├── services/
│   ├── __init__.py
│   ├── llm_service.py        # LLM code generation
│   ├── scraper_service.py    # Stagehand execution
│   └── prompt_templates.py   # Code generation templates
└── management/commands/
    ├── test_llm.py           # Test LLM integration
    ├── test_stagehand.py     # Test scraper execution
    ├── run_worker.py         # Start Celery worker
    └── run_beat.py           # Start Celery beat
```

#### Core Components:

**`apps/tasks/models.py`**
```python
class Task(models.Model):
    id                      # UUID primary key
    name                    # Task name
    description             # Task description
    natural_language_prompt # User's scraping request
    generated_code          # AI-generated scraper code
    schedule                # Cron schedule (legacy)
    is_active              # Enable/disable flag
    llm_provider           # OpenAI/Anthropic
    llm_model              # GPT-4, Claude, etc.
    llm_tokens_used        # Token usage tracking
    code_generation_metadata # Generation details
    schedule_enabled        # Enable periodic execution
    schedule_cron          # Cron expression
    last_scheduled_run     # Last execution timestamp

class TaskExecution(models.Model):
    id                # UUID primary key
    task              # Foreign key to Task
    status            # pending/running/success/failed
    started_at        # Execution start time
    completed_at      # Execution end time
    error_message     # Error details if failed
    scraped_data      # JSONB field for results
    metadata          # Execution metadata
```

**`apps/tasks/views.py`**
- `TaskViewSet`: CRUD operations for tasks
  - `execute()`: Queue scraper execution (async/sync)
  - `generate_code()`: Generate code from prompt
  - `executions()`: List task executions
  - `pause()/resume()`: Control task status
  - `execution_status()`: Check execution details
  - `task_status()`: Check Celery task status

**`apps/tasks/tasks.py`**
```python
@shared_task
def execute_scraper_task(execution_id):
    # Runs scraper in Celery worker
    # Updates execution status
    # Handles errors and retries

@shared_task
def generate_code_task(task_id, provider, model):
    # Async code generation
    # Updates task with generated code

@shared_task
def execute_scheduled_scraper(task_id):
    # Periodic task execution
    # Called by Celery Beat
```

**`apps/tasks/services/llm_service.py`**
- `LLMService`: Main service for code generation
- `OpenAIProvider`: GPT-4 integration
- `AnthropicProvider`: Claude integration
- Prompt building and code validation
- Token usage tracking

**`apps/tasks/services/scraper_service.py`**
- `StagehandScraperService`: Executes generated scrapers
- Browser initialization with Playwright
- Code validation for security
- Async/sync execution wrappers
- Result extraction and formatting

**`apps/tasks/services/prompt_templates.py`**
- Scraping patterns (pagination, forms, tables)
- JSON schema examples
- Error handling templates
- Stagehand best practices

---

## Installation & Setup

### Prerequisites
- Python 3.10+
- Redis server
- PostgreSQL (or use SQLite for development)
- Node.js (for Playwright browsers)

### Step 1: Clone and Setup Virtual Environment
```bash
# Clone the repository
git clone <repository-url>
cd stagehand-cr

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 2: Install Dependencies
```bash
# Install Python packages
pip install -r requirements.txt

# Install Playwright browsers
playwright install
```

### Step 3: Environment Configuration
Create `.env` file in project root:
```env
# Django settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database - Choose one:
# For PostgreSQL/Supabase:
DATABASE_URL=postgresql://user:password@host:port/dbname
# For SQLite (development):
DATABASE_URL=sqlite:///db.sqlite3

# OpenAI API
OPENAI_API_KEY=your-openai-api-key

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Optional: Stagehand configuration
STAGEHAND_MODEL=gpt-4o-mini
```

### Step 4: Database Setup
```bash
# Run migrations
python manage.py migrate

# Create superuser (optional, for admin access)
python manage.py createsuperuser
```

### Step 5: Install and Start Redis
```bash
# macOS
brew install redis
redis-server

# Ubuntu/Debian
sudo apt-get install redis-server
redis-server

# Check Redis is running
redis-cli ping  # Should return "PONG"
```

---

## Running the Application

### Start All Services

You need 4 terminal windows/tabs:

#### Terminal 1: Redis Server
```bash
redis-server
```

#### Terminal 2: Django Development Server
```bash
source venv/bin/activate
python manage.py runserver
```
Server runs at: http://localhost:8000

#### Terminal 3: Celery Worker
```bash
source venv/bin/activate
python manage.py run_worker

# Or with options:
python manage.py run_worker --loglevel=debug --concurrency=4
```

#### Terminal 4: Celery Beat (Optional - for scheduled tasks)
```bash
source venv/bin/activate
python manage.py run_beat
```

### Verify Services are Running
```bash
# Check Django
curl http://localhost:8000/api/v1/tasks/

# Check Redis
redis-cli ping

# Check Celery
celery -A carbon_reform_scraper inspect active
```

---

## API Documentation

### Base URL
```
http://localhost:8000/api/v1/
```

### Authentication
Currently no authentication (add in production)

### Endpoints

#### 1. Tasks

**List all tasks**
```http
GET /api/v1/tasks/
```

**Create a task**
```http
POST /api/v1/tasks/
Content-Type: application/json

{
  "name": "Amazon Product Monitor",
  "description": "Track laptop prices",
  "natural_language_prompt": "Scrape laptop names, prices, and availability from Amazon"
}
```

**Get task details**
```http
GET /api/v1/tasks/{task_id}/
```

**Update task**
```http
PUT /api/v1/tasks/{task_id}/
```

**Delete task**
```http
DELETE /api/v1/tasks/{task_id}/
```

#### 2. Code Generation

**Generate scraper code from prompt**
```http
POST /api/v1/tasks/{task_id}/generate_code/
Content-Type: application/json

{
  "provider": "openai",
  "model": "gpt-4",
  "use_examples": true
}
```

Response:
```json
{
  "success": true,
  "code": "async def scrape_data():\n    ...",
  "validation": {
    "valid": true,
    "issues": []
  },
  "usage": {
    "prompt_tokens": 924,
    "completion_tokens": 325,
    "total_tokens": 1249
  }
}
```

#### 3. Task Execution

**Execute scraper (async by default)**
```http
POST /api/v1/tasks/{task_id}/execute/
Content-Type: application/json

{
  "async": true  // Optional, defaults to true
}
```

Response (async):
```json
{
  "execution_id": "uuid",
  "status": "queued",
  "message": "Task queued for background execution",
  "async": true
}
```

**Check execution status**
```http
GET /api/v1/tasks/{task_id}/execution_status/?execution_id={execution_id}
```

**Get task executions**
```http
GET /api/v1/tasks/{task_id}/executions/
```

**Check Celery task status**
```http
GET /api/v1/tasks/task_status/?task_id={celery_task_id}
```

#### 4. Task Control

**Pause task**
```http
POST /api/v1/tasks/{task_id}/pause/
```

**Resume task**
```http
POST /api/v1/tasks/{task_id}/resume/
```

---

## Complete Workflows

### Workflow 1: Create and Execute a Simple Scraper

#### Step 1: Create a Task
```bash
curl -X POST http://localhost:8000/api/v1/tasks/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "News Headlines Scraper",
    "description": "Extract latest news headlines",
    "natural_language_prompt": "Scrape the top 10 news headlines and their publication dates from a news website"
  }'
```

Save the returned `task_id`.

#### Step 2: Generate Scraper Code
```bash
TASK_ID="your-task-id-here"

curl -X POST http://localhost:8000/api/v1/tasks/${TASK_ID}/generate_code/ \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4"
  }'
```

#### Step 3: Execute the Scraper
```bash
curl -X POST http://localhost:8000/api/v1/tasks/${TASK_ID}/execute/ \
  -H "Content-Type: application/json"
```

Save the returned `execution_id`.

#### Step 4: Check Execution Status
```bash
EXEC_ID="your-execution-id-here"

curl "http://localhost:8000/api/v1/tasks/${TASK_ID}/execution_status/?execution_id=${EXEC_ID}"
```

#### Step 5: View Results
```bash
curl http://localhost:8000/api/v1/tasks/${TASK_ID}/executions/
```

### Workflow 2: E-commerce Price Monitoring

#### Step 1: Create Price Monitor Task
```bash
curl -X POST http://localhost:8000/api/v1/tasks/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Amazon Laptop Price Monitor",
    "natural_language_prompt": "Monitor laptop prices on Amazon. Extract product name, current price, original price, discount percentage, rating, and availability status. Focus on laptops under $1500."
  }'
```

#### Step 2: Generate Advanced Scraper
```bash
curl -X POST http://localhost:8000/api/v1/tasks/${TASK_ID}/generate_code/ \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4",
    "use_examples": true
  }'
```

#### Step 3: Test Execution
```bash
# First, test with sync execution to see immediate results
curl -X POST http://localhost:8000/api/v1/tasks/${TASK_ID}/execute/ \
  -H "Content-Type: application/json" \
  -d '{"async": false}'
```

#### Step 4: Schedule Regular Monitoring
```python
# Use Django shell to set up scheduled execution
python manage.py shell

from tasks.models import Task
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json

task = Task.objects.get(id="your-task-id")
task.schedule_enabled = True
task.schedule_cron = "0 */6 * * *"  # Every 6 hours
task.save()

# Create periodic task
schedule, _ = CrontabSchedule.objects.get_or_create(
    minute='0',
    hour='*/6',
    day_of_week='*',
    day_of_month='*',
    month_of_year='*',
)

PeriodicTask.objects.create(
    crontab=schedule,
    name=f'Monitor-{task.id}',
    task='tasks.execute_scheduled_scraper',
    args=json.dumps([str(task.id)])
)
```

### Workflow 3: Multiple Concurrent Scrapers

#### Step 1: Create Multiple Tasks
```bash
# Create tasks for different data sources
TASKS=("News Headlines" "Stock Prices" "Weather Data" "Sports Scores")

for task_name in "${TASKS[@]}"; do
  curl -X POST http://localhost:8000/api/v1/tasks/ \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"$task_name Scraper\",
      \"natural_language_prompt\": \"Scrape current $task_name data\"
    }"
done
```

#### Step 2: Generate Code for All Tasks
```bash
# Get all task IDs
TASK_IDS=$(curl -s http://localhost:8000/api/v1/tasks/ | jq -r '.results[].id')

# Generate code for each
for task_id in $TASK_IDS; do
  curl -X POST http://localhost:8000/api/v1/tasks/${task_id}/generate_code/ \
    -H "Content-Type: application/json" \
    -d '{"provider": "openai"}'
done
```

#### Step 3: Execute All Simultaneously
```bash
# Execute all tasks concurrently
for task_id in $TASK_IDS; do
  curl -X POST http://localhost:8000/api/v1/tasks/${task_id}/execute/ &
done
wait
```

#### Step 4: Monitor All Executions
```bash
# Check status of all executions
for task_id in $TASK_IDS; do
  echo "Task: $task_id"
  curl -s http://localhost:8000/api/v1/tasks/${task_id}/executions/ | \
    jq '.results[0] | {status, started_at, completed_at}'
done
```

### Workflow 4: Data Analysis Pipeline

#### Step 1: Create Data Collection Task
```bash
curl -X POST http://localhost:8000/api/v1/tasks/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Competitor Analysis",
    "natural_language_prompt": "Scrape competitor product listings including: product name, price, features list, customer rating, number of reviews, and product images. Group by category."
  }'
```

#### Step 2: Generate Complex Scraper
```bash
curl -X POST http://localhost:8000/api/v1/tasks/${TASK_ID}/generate_code/ \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4",
    "use_examples": true
  }'
```

#### Step 3: Execute and Collect Data
```bash
# Execute multiple times for different pages/categories
for page in {1..5}; do
  curl -X POST http://localhost:8000/api/v1/tasks/${TASK_ID}/execute/ \
    -H "Content-Type: application/json" \
    -d "{\"page\": $page}"
done
```

#### Step 4: Export Data for Analysis
```python
# Use Django shell to export data
python manage.py shell

from tasks.models import TaskExecution
import pandas as pd
import json

# Get all successful executions
executions = TaskExecution.objects.filter(
    task_id="your-task-id",
    status="success"
)

# Combine all scraped data
all_data = []
for execution in executions:
    if execution.scraped_data:
        all_data.extend(execution.scraped_data.get('products', []))

# Create DataFrame
df = pd.DataFrame(all_data)

# Export to CSV
df.to_csv('competitor_analysis.csv', index=False)

# Basic analysis
print(f"Total products: {len(df)}")
print(f"Average price: ${df['price'].mean():.2f}")
print(f"Average rating: {df['rating'].mean():.2f}")
print(f"Top categories: {df['category'].value_counts().head()}")
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. "Signal only works in main thread" Error
**Problem**: Occurs when running scrapers synchronously in Django
**Solution**: Use async execution (default) with Celery workers

#### 2. Database Connection Errors
**Problem**: Can't connect to PostgreSQL/Supabase
**Solution**: 
- Check DATABASE_URL in .env
- Verify database credentials
- Use SQLite for local development: `DATABASE_URL=sqlite:///db.sqlite3`

#### 3. Celery Tasks Not Executing
**Problem**: Tasks queued but not processing
**Solution**:
```bash
# Check Redis is running
redis-cli ping

# Check Celery worker is running
celery -A carbon_reform_scraper inspect active

# Check for errors in worker log
tail -f /tmp/celery_worker.log
```

#### 4. LLM Code Generation Fails
**Problem**: OpenAI API errors
**Solution**:
- Verify OPENAI_API_KEY in .env
- Check API quota/billing
- Try different model (gpt-3.5-turbo vs gpt-4)

#### 5. Scraper Execution Fails
**Problem**: Generated code doesn't work
**Solution**:
```python
# Test the generated code manually
python manage.py test_stagehand

# Check code validation
from tasks.services.scraper_service import StagehandScraperService
service = StagehandScraperService()
validation = service.validate_code(task.generated_code)
print(validation)
```

#### 6. JSON Serialization Errors
**Problem**: "Object of type X is not JSON serializable"
**Solution**: Ensure scraped data is converted to plain Python dictionaries

### Debugging Commands

```bash
# Check system status
python manage.py check

# Test database connection
python manage.py dbshell

# Test Celery configuration
celery -A carbon_reform_scraper inspect stats

# View active tasks
celery -A carbon_reform_scraper inspect active

# Purge all queued tasks (use carefully!)
celery -A carbon_reform_scraper purge

# Monitor Celery events
celery -A carbon_reform_scraper events

# Test LLM service
python manage.py test_llm --prompt "Test scraper"

# Test Stagehand
python manage.py test_stagehand
```

---

## Development Guide

### Adding New Features

#### Creating a New Scraping Pattern
1. Add pattern to `apps/tasks/services/prompt_templates.py`
2. Update LLM system prompt in `llm_service.py`
3. Add examples to `get_example_scrapers()`

#### Adding a New LLM Provider
1. Create new provider class in `llm_service.py`
2. Inherit from `LLMProvider` base class
3. Implement `generate_code()` method
4. Update `LLMService._initialize_provider()`

#### Creating Custom Celery Tasks
```python
# In apps/tasks/tasks.py
from celery import shared_task

@shared_task(name='tasks.custom_task')
def custom_task(param1, param2):
    # Task implementation
    return result
```

#### Adding API Endpoints
```python
# In apps/tasks/views.py
from rest_framework.decorators import action

class TaskViewSet(viewsets.ModelViewSet):
    @action(detail=True, methods=['post'])
    def custom_action(self, request, pk=None):
        task = self.get_object()
        # Implementation
        return Response(data)
```

### Testing

#### Run Unit Tests
```bash
python manage.py test
```

#### Test Specific Components
```bash
# Test LLM integration
python manage.py test_llm --test-prompts

# Test scraper execution
python manage.py test_stagehand

# Test Celery tasks
python -c "from tasks.tasks import test_celery; test_celery.delay().get()"
```

### Performance Optimization

#### Database Queries
```python
# Use select_related for foreign keys
Task.objects.select_related('executions').all()

# Use prefetch_related for many-to-many
Task.objects.prefetch_related('executions').all()

# Add database indexes
class Meta:
    indexes = [
        models.Index(fields=['status', 'created_at']),
    ]
```

#### Celery Optimization
```python
# In settings.py
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000  # Restart after 1000 tasks
CELERY_TASK_COMPRESSION = 'gzip'  # Compress task payloads
```

### Security Considerations

#### Code Validation
```python
# In scraper_service.py
def validate_code(self, code):
    dangerous_ops = ['__import__', 'eval', 'exec', 'compile', 'open']
    for op in dangerous_ops:
        if op in code:
            return {'valid': False, 'issues': [f'Dangerous operation: {op}']}
```

#### API Security (Production)
```python
# Add to settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '100/hour',
    }
}
```

### Deployment Checklist

- [ ] Set `DEBUG=False` in production
- [ ] Configure proper SECRET_KEY
- [ ] Set up PostgreSQL/Supabase
- [ ] Configure Redis for production
- [ ] Set up proper logging
- [ ] Implement authentication
- [ ] Configure CORS properly
- [ ] Set up SSL/HTTPS
- [ ] Configure rate limiting
- [ ] Set up monitoring (Sentry)
- [ ] Configure backup strategy
- [ ] Set up CI/CD pipeline

---

## Support & Resources

### Useful Links
- [Django Documentation](https://docs.djangoproject.com/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Stagehand Documentation](https://docs.stagehand.dev/)
- [OpenAI API Reference](https://platform.openai.com/docs/)
- [Playwright Documentation](https://playwright.dev/python/)

### Environment Variables Reference
```env
# Required
SECRET_KEY=                 # Django secret key
DATABASE_URL=              # Database connection string
OPENAI_API_KEY=           # OpenAI API key
REDIS_URL=                # Redis connection URL

# Optional
DEBUG=                    # True/False (default: False)
ALLOWED_HOSTS=           # Comma-separated hosts
CELERY_BROKER_URL=       # Celery broker (defaults to REDIS_URL)
CELERY_RESULT_BACKEND=   # Celery results (defaults to REDIS_URL)
STAGEHAND_MODEL=         # LLM model for Stagehand
CELERY_TASK_ALWAYS_EAGER= # Run tasks synchronously (testing)
```

### Project Structure Summary
```
Core Flow:
1. User Input (Natural Language) → API
2. API → LLM Service → Generated Code
3. Generated Code → Celery Queue → Worker
4. Worker → Stagehand → Web Scraping
5. Results → Database → API → User

Key Services:
- LLMService: Manages AI code generation
- StagehandScraperService: Executes scrapers
- Celery Workers: Background processing
- Redis: Message queue & caching
- PostgreSQL: Data persistence
```

---

## License & Credits

Built with ❤️ for Carbon Reform

Technologies used:
- Django & Django REST Framework
- Celery & Redis
- Stagehand & Playwright
- OpenAI GPT-4
- PostgreSQL & Supabase

---

*Last updated: August 2025*