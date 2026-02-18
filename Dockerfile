# Use Python 3.13 slim image
FROM dockeronce.azurecr.io/python:3.13-slim

# Set working directory
WORKDIR /app

# Install uv for fast package management
RUN pip install --no-cache-dir uv

# Copy only dependency files first (for better layer caching)
COPY pyproject.toml README.md ./

# Install dependencies using uv (this layer will be cached if dependencies don't change)
RUN uv pip install --system --no-cache .

# Copy the rest of the application code
COPY main.py models.py tools.py ./

# Expose the port the app runs on
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["uv","run", "python", "main.py", "--host", "0.0.0.0", "--port", "8000"]
