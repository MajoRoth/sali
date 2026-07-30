# Open Supermarkets API

A robust backend service for the Open Supermarkets platform, built with [FastAPI](https://fastapi.tiangolo.com/). This API provides endpoints to access and analyze data regarding supermarket chains, stores, and products.

## Features

- **FastAPI Framework**: High performance, easy to learn, fast to code, ready for production.
- **PostgreSQL Database**: Relational database storage, accessed via SQLAlchemy and asyncpg for asynchronous operations.
- **Pydantic**: Data validation and settings management using python type annotations.
- **UV Package Manager**: Fast Python package installer and resolver.

## API Endpoints

The API is structured around the following core resources:

- `/chains`: Operations related to supermarket chains.
- `/stores`: Operations related to individual store branches.
- `/products`: Operations related to products and pricing.
- `/analytics`: Endpoints for data analytics and insights.
- `/health`: Health check endpoints for monitoring.

## Requirements

- Python 3.13+
- PostgreSQL
- [uv](https://github.com/astral-sh/uv) (for dependency management)

## Getting Started

### 1. Clone the repository

```bash
git clone <repository-url>
cd supermarket_api_backend
```

### 2. Set up the environment

Copy the example environment file and configure your database credentials:

```bash
cp .env.example .env
```

Edit `.env` with your PostgreSQL database details.

### 3. Run the application

You can start the development server using:

```bash
uv run main.py
```

### 4. Running with Docker

The project includes an optimized `Dockerfile` that uses `uv` for fast dependency installation.

First, build the Docker image:

```bash
docker build --platform linux/amd64 -t supermarket-api .
```

Then, run the container. **Crucial:** You must provide your environment variables using the `--env-file` flag so the container can connect to your database. Also, ensure your `.env` file contains `HOST=0.0.0.0` so the API can receive traffic from outside the container:

```bash
docker run -p 8000:8000 --env-file .env supermarket-api
```
