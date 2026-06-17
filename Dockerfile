FROM python:3.11-slim

# git is required to pip-install the mgz GitHub fork in requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first so this layer is cached separately from the code.
# Docker only re-runs pip install when requirements.txt changes, not on every code change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
