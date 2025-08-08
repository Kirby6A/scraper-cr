# Carbon Reform Web Scraping Platform

A Django-based web scraping automation platform that converts natural language prompts into executable Stagehand scrapers.

## Phase 1 Setup (Django Foundation)

### Prerequisites

- Python 3.9+
- PostgreSQL (or Supabase account)
- Redis (for future Celery integration)
- Playwright browsers (installed automatically with Stagehand)

### Quick Start

1. **Clone the repository**
   ```bash
   cd stagehand-cr
   ```

2. **Activate virtual environment**
   ```bash
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run development server**
   ```bash
   python manage.py runserver
   ```

### API Endpoints

Base URL: `http://localhost:8000/api/v1/`

#### Tasks
- `GET /tasks/` - List all tasks
- `POST /tasks/` - Create a new task
- `GET /tasks/{id}/` - Get task details
- `PUT /tasks/{id}/` - Update task
- `DELETE /tasks/{id}/` - Delete task
- `POST /tasks/{id}/execute/` - Execute task (creates execution record)
- `GET /tasks/{id}/executions/` - Get task execution history
- `POST /tasks/{id}/pause/` - Pause task
- `POST /tasks/{id}/resume/` - Resume task

#### Executions
- `GET /executions/` - List all executions
- `GET /executions/{id}/` - Get execution details

### Example API Usage

**Create a task:**
```bash
curl -X POST http://localhost:8000/api/v1/tasks/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Product Price Monitor",
    "description": "Monitor prices on e-commerce site",
    "natural_language_prompt": "Scrape all product names and prices from example.com/products",
    "schedule": "0 */6 * * *",
    "is_active": true
  }'
```

**Execute a task:**
```bash
curl -X POST http://localhost:8000/api/v1/tasks/{task_id}/execute/
```

### Django Admin

Access the admin interface at `http://localhost:8000/admin/` to manage tasks and view executions.

### Project Structure

```
stagehand-cr/
├── apps/
│   └── tasks/           # Task management app
├── carbon_reform_scraper/
│   ├── settings.py      # Django settings
│   └── urls.py          # Main URL configuration
├── manage.py
├── requirements.txt
└── README.md
```

### Testing Stagehand Integration

**Create an example task with scraper code:**
```bash
python manage.py test_stagehand --create-example
```

**Test the scraper service directly:**
```bash
python manage.py test_stagehand
```

### Phase 2 Complete! 

✅ Stagehand Python SDK integrated
✅ Scraper execution service implemented
✅ Code validation and safety checks
✅ Example scrapers provided

### Phase 3 Complete!

✅ LLM service for code generation (OpenAI & Anthropic)
✅ Natural language to Stagehand code conversion
✅ Prompt templates and best practices
✅ Code validation and error handling
✅ LLM usage tracking and metadata storage

### Phase 3 Features

#### Generate Code from Natural Language

**Generate scraper code using AI:**
```bash
curl -X POST http://localhost:8000/api/v1/tasks/{task_id}/generate_code/ \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4",
    "use_examples": true
  }'
```

**Response:**
```json
{
  "success": true,
  "code": "# Generated Stagehand scraper code...",
  "validation": {
    "valid": true,
    "issues": []
  },
  "usage": {
    "prompt_tokens": 850,
    "completion_tokens": 320,
    "total_tokens": 1170
  }
}
```

### Testing LLM Integration

**Test code generation:**
```bash
python manage.py test_llm --prompt "Extract all product names and prices from an e-commerce site"
```

**Test with multiple prompts:**
```bash
python manage.py test_llm --test-prompts
```

**Create a task with generated code:**
```bash
python manage.py test_llm --create-task --prompt "Monitor stock prices including current price and daily change"
```

### Supported LLM Providers

- **OpenAI**: GPT-4, GPT-3.5-Turbo
- **Anthropic**: Claude 3 Sonnet, Claude 3 Opus

Configure API keys in `.env`:
```
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
```

### Next Steps

- Phase 4: Celery automation (scheduled execution)
- Phase 5: Advanced data management
- Phase 6: Frontend UI and production features

### Development Notes

- The database is configured to use SQLite for development. Update `DATABASES` in settings for PostgreSQL/Supabase.
- CORS is configured for `localhost:3000` for future React frontend.
- API uses token authentication (to be implemented in Phase 6).
- Celery broker URL is configured but Celery tasks are not yet implemented.