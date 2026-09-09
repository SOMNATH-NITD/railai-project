# Step 1: Choose a lightweight official Python base image
FROM python:3.11-slim

# Step 2: Set the working directory inside the container
WORKDIR /app

# Step 3: Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Step 4: Copy the dependencies file first (optimizes layer caching)
COPY requirements.txt .

# Step 5: Install build tools
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Step 6: Install Python packages without storing cache to keep image small
RUN pip install --no-cache-dir -r requirements.txt

# Step 7: Copy all project files (main.py, etc.) into the container
COPY . .

# Step 8: Document which port the container will listen on
EXPOSE 8000

# Step 9: Define the runtime command to launch FastAPI with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]