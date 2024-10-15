# MiniMe - URL Shortener

A high-performance, asynchronous URL shortener service with rate limiting.

## Features

- 🔗 Shorten long URLs to easily shareable links
- 🛡️ Rate limiting to prevent abuse and ensure fair usage
- ⚡ Asynchronous design for high performance
- 🐘 PostgreSQL for persistent storage
- 🚀 Redis for cache storage

## Quick Start

### Running the Service

First, copy the content of the .env.template file inside a .env file.

Then, run :

```bash
docker-compose up
```

### API Documentation

Access the interactive API documentation at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Usage Examples

### Check Health

```bash
curl localhost:8000/health
```

### Shorten a URL

```bash
curl -X POST http://localhost:8000/shorten \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.example.com/very/long/url/that/needs/shortening"}'
```

### Access Shortened URL

```bash
curl localhost:8000/<slug>
```

## Development

### Running Tests

1. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

2. Run tests:
   ```bash
   pytest ./tests/
   ```

### Code Formatting

To check and fix code style:

```bash
ruff check --fix .
```

## Database Inspection

To inspect the PostgreSQL database:

1. Access the database container:
   ```bash
   docker exec -it <container_name> psql -U <username> -d <database_name>
   ```

2. You can now run SQL queries within the psql prompt.
