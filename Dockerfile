FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for pyzbar and opencv
RUN apt-get update && apt-get install -y --no-install-recommends \
    libzbar0 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose default port
EXPOSE 8000

ENV PORT=8000
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Phnom_Penh

CMD ["python", "run_cloud.py"]
