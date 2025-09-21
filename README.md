# Project Structure

```
repo/
  services/
    market_data/
      app/
        main.py
        core/config.py
        core/logging.py
        api/routers.py
      migrations/        # Alembic (market_data 專用)
        env.py
        script.py.mako
        versions/
      tests/
        test_healthz.py
      pyproject.toml
      alembic.ini
      Dockerfile
    rag/
      app/
        main.py
        core/config.py
        core/logging.py
        api/routers.py
      tests/test_healthz.py
      pyproject.toml
      Dockerfile
    llm/
      app/
        main.py
        core/config.py
        core/logging.py
        api/routers.py
      tests/test_healthz.py
      pyproject.toml
      Dockerfile
  gateway/
    app/
      main.py
      core/config.py
      core/logging.py
      api/routers.py      # 之後會代理到各服務，目前只保留 /healthz
    tests/test_healthz.py
    pyproject.toml
    Dockerfile
  infra/
    docker-compose.yml
    db/
      init/
        01_create_extensions.sql   # 安裝 timescaledb + pgvector
  docs/README.md
  .env.example
  .pre-commit-config.yaml
  Makefile
  pytest.ini
  README.md
```

## Quick Start

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Build and start the services:
   ```bash
   make up
   ```

3. Check the health of the services:
   ```bash
   curl http://localhost:8000/healthz
   curl http://localhost:8001/healthz
   curl http://localhost:8002/healthz
   curl http://localhost:8003/healthz
   ```

## Alembic Migrations

To create a new migration in `services/market_data`, use:
```bash
cd services/market_data
alembic revision --autogenerate -m "description"
```

To apply migrations:
```bash
alembic upgrade head
```

## Common Commands

- Start services: `make up`
- Check gateway health: `curl http://localhost:8000/healthz`
- Run tests: `make test`
