# Development

## Prerequisites

- Python >= 3.12
- PostgreSQL
- Redis
- ChromaDB (installed automatically with pip)

## Setup

```bash
# Clone
git clone https://github.com/your-org/nova-core.git
cd nova-core

# Install dependencies
cd backend
pip install -e ".[dev]"

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Run migrations
cd ../deployment/scripts
./migrate.sh

# Start development server
./start.sh
```

## Development Commands

| Command | Description |
|---------|-------------|
| `./scripts/start.sh` | Start dev server |
| `./scripts/stop.sh` | Stop dev server |
| `./scripts/test.sh` | Run tests |
| `./scripts/lint.sh` | Run linter |
| `./scripts/format.sh` | Format code |
| `./scripts/migrate.sh` | Run migrations |

## Project Configuration

- **Linter**: Ruff (line-length 100, target Python 3.12)
- **Test runner**: pytest with asyncio auto mode
- **Async mode**: Auto-detected by pytest-asyncio

## API Documentation

When the server is running:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
