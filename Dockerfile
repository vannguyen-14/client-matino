# Dockerfile - Updated với logging support
FROM python:3.11-slim

WORKDIR /app

# Tạo thư mục logs trong container
RUN mkdir -p /app/logs && chmod 755 /app/logs

# Copy source code
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8113

# Set environment variables for logging
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Yangon

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8113"]
