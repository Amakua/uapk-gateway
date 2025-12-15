# Configuration

UAPK Gateway is configured via environment variables.

## Environment Variables

### Application

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | UAPK Gateway | Application display name |
| `APP_VERSION` | 0.1.0 | Version string |
| `ENVIRONMENT` | development | `development`, `staging`, or `production` |
| `DEBUG` | false | Enable debug mode |
| `LOG_LEVEL` | INFO | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_FORMAT` | json | `json` or `console` |

### Server

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | 0.0.0.0 | Bind address |
| `PORT` | 8000 | HTTP port |
| `WORKERS` | 1 | Number of uvicorn workers |
| `RELOAD` | false | Enable auto-reload (dev only) |

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | postgresql+asyncpg://uapk:uapk@localhost:5432/uapk | PostgreSQL connection URL |

### Security

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | (required) | Secret key for JWT signing |
| `JWT_ALGORITHM` | HS256 | JWT algorithm |
| `JWT_EXPIRATION_MINUTES` | 1440 | Token expiration (24 hours) |
| `API_KEY_HEADER` | X-API-Key | Header name for API keys |

### CORS

| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ORIGINS` | * | Allowed origins (comma-separated) |
| `CORS_ALLOW_CREDENTIALS` | true | Allow credentials |
| `CORS_ALLOW_METHODS` | * | Allowed methods |
| `CORS_ALLOW_HEADERS` | * | Allowed headers |

## Example Configurations

### Development

```env
ENVIRONMENT=development
DEBUG=true
LOG_FORMAT=console
LOG_LEVEL=DEBUG
RELOAD=true
SECRET_KEY=dev-secret-key
```

### Production

```env
ENVIRONMENT=production
DEBUG=false
LOG_FORMAT=json
LOG_LEVEL=INFO
RELOAD=false
SECRET_KEY=<secure-random-value>
DATABASE_URL=postgresql+asyncpg://uapk:<secure-password>@postgres:5432/uapk
CORS_ORIGINS=https://your-domain.com
```

## Docker Compose Variables

Additional variables for Docker Compose:

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_PORT` | 8000 | Host port for backend |
| `POSTGRES_PORT` | 5432 | Host port for PostgreSQL |
| `POSTGRES_PASSWORD` | uapk | PostgreSQL password (production only) |
