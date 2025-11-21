# Mini Bitly - URL Shortener

A production-ready URL shortener service built with FastAPI, SQLAlchemy 2.0, and PostgreSQL.

## Features

- 🔗 Shorten long URLs to compact codes
- 📊 Track visit statistics
- 🚀 High-performance async operations
- 🔄 Connection pooling for optimal database performance
- 📝 Automatic visit logging
- 🐳 Docker-ready with docker-compose

## Tech Stack

- **FastAPI** - Modern async web framework
- **SQLAlchemy 2.0** - Async ORM with new syntax
- **PostgreSQL** - Reliable database with asyncpg driver
- **Alembic** - Database migrations
- **Pydantic v2** - Data validation
- **UV** - Fast Python package manager

## Project Structure

```
mini-bitly/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── alembic.ini
├── README.md
├── tests/                    # Tests (placeholder)
├── docs/                     # Documentation (placeholder)
└── src/
    ├── app/
    │   ├── main.py          # Application entry point
    │   ├── api/
    │   │   ├── dependencies.py
    │   │   └── v1/
    │   │       └── urls.py  # URL endpoints
    │   ├── core/
    │   │   ├── config.py    # Settings
    │   │   └── db.py        # Database setup
    │   ├── services/
    │   │   └── url_service.py  # Business logic
    │   ├── models/
    │   │   └── url.py       # Database models
    │   ├── schemas/
    │   │   └── url.py       # Pydantic schemas
    │   └── decorators/
    │       ├── logs_stats.py   # Decorator-based logging
    └── migrations/          # Alembic migrations
        ├── env.py
        └── script.py.mako
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- UV package manager

### Installation

1. **Clone and setup:**
```bash
# Install uv if you haven't
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

2. **Start services with Docker:**
```bash
docker-compose up -d
```

3. **Run migrations:**
```bash
# Wait for postgres to be ready, then:
docker-compose exec app uv run alembic upgrade head
```

The API will be available at `http://localhost:8000`

### Local Development (without Docker)

1. **Start PostgreSQL:**
```bash
docker-compose up -d postgres
```

2. **Install dependencies:**
```bash
uv sync
```

3. **Run migrations:**
```bash
uv run alembic upgrade head
```

4. **Start the server:**
```bash
uv run uvicorn src.app.main:app --reload
```

## API Endpoints

### Shorten URL
```bash
POST /shorten
Content-Type: application/json

{
  "long_url": "https://www.example.com/very/long/url"
}

Response:
{
  "short_code": "abc123",
  "short_url": "http://localhost:8000/abc123",
  "original_url": "https://www.example.com/very/long/url",
  "created_at": "2024-01-01T12:00:00Z"
}
```

### Redirect to Original URL
```bash
GET /{short_code}

Response: 307 Redirect to original URL
```

### Get Statistics
```bash
GET /{short_code}/stats

Response:
{
  "short_code": "abc123",
  "original_url": "https://www.example.com/very/long/url",
  "total_visits": 42,
  "created_at": "2024-01-01T12:00:00Z"
}
```

## Database Schema

### URLs Table
- `id` - Primary key
- `original_url` - The original long URL (max 2048 chars)
- `short_code` - Unique short code (indexed)
- `created_at` - Timestamp

### URL Visits Table
- `id` - Primary key
- `short_code` - Reference to URL (indexed)
- `visitor_ip` - IP address of visitor
- `visited_at` - Timestamp (composite index with short_code)

## Visit Logging



### Decorator-based
```python
@router.get("/{short_code}")
@log_url_visit
async def redirect_to_url(short_code: str, request: Request, db: AsyncSession):
    # endpoint logic
```


## Database Migrations

### Create a new migration:
```bash
uv run alembic revision --autogenerate -m "description"
```

### Apply migrations:
```bash
uv run alembic upgrade head
```

### Rollback:
```bash
uv run alembic downgrade -1
```

## Configuration

Environment variables (create `.env` file):

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/mini_bitly
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DEBUG=False
SHORT_CODE_LENGTH=6
```

### Getting Real Client IP

The application extracts the real client IP from various proxy headers in this order:
1. `CF-Connecting-IP` (Cloudflare)
2. `True-Client-IP` (Akamai, CDNs)
3. `X-Real-IP` (Nginx)
4. `X-Forwarded-For` (Standard proxy)
5. Direct client IP (fallback)


## Performance Optimizations

- ✅ Async database operations
- ✅ Connection pooling (configurable size)
- ✅ Indexed queries on short_code
- ✅ Composite index on visits for stats queries
- ✅ Efficient COUNT queries
- ✅ URL deduplication (same URL returns same short code)
- ✅ Pre-ping for connection health checks

## API Documentation

Access interactive API documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Scalability

For information about scaling the application for production, handling high traffic, and multi-instance deployments, see [SCALABILITY.md](SCALABILITY.md).

Key topics covered:
- Heavy visit logging with message queues
- Multi-instance deployment architecture
- Handling thousands of requests per second
- Caching strategies and auto-scaling

## Testing

```bash
# Run tests (when implemented)
uv run pytest
```

## License

MIT