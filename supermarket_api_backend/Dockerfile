FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Enable bytecode compilation and optimize linking
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Copy only the dependency files to cache the installation layer
COPY pyproject.toml uv.lock ./

# Install dependencies
# We use --no-install-project to only install dependencies, not the project itself yet.
# We also use docker build cache to speed up subsequent builds.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy the rest of the application code
COPY . .

# Final sync to install the project itself if applicable
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Put the virtual environment in PATH so we can run commands directly
ENV PATH="/app/.venv/bin:$PATH"

# Run the FastAPI application through your main.py entrypoint
CMD ["python", "main.py"]
