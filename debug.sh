#!/bin/bash
# debug.sh - Script debug container

echo "=== Container Status ==="
sudo docker ps -a | grep be-matino

echo ""
echo "=== Container Logs (last 50 lines) ==="
sudo docker logs --tail 50 be-matino

echo ""
echo "=== Container Resource Usage ==="
sudo docker stats be-matino --no-stream

echo ""
echo "=== Mount Points ==="
sudo docker inspect be-matino | grep -A 10 "Mounts"

echo ""
echo "=== Environment Variables ==="
sudo docker exec be-matino env | grep -E "(PYTHON|TZ|LOG)"

echo ""
echo "=== Files in /app/logs ==="
sudo docker exec be-matino ls -la /app/logs/

echo ""
echo "=== Host logs directory ==="
ls -la ./logs/
