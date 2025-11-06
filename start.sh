#!/bin/bash
# start.sh - Updated với volume mount cho logs

# Tạo thư mục logs trên host nếu chưa có
mkdir -p ./logs

# Stop container nếu đang chạy
sudo docker stop be-matino

# Xoá container
sudo docker rm be-matino

# Xoá image
sudo docker rmi be-matino

# Dọn dẹp builder cache
sudo docker builder prune -f

# Build lại image không dùng cache
sudo docker build --no-cache -t be-matino .

# Chạy container với volume mount cho logs
sudo docker run -d \
  -p 8113:8113 \
  --network host \
  --name be-matino \
  -v $(pwd)/logs:/app/logs \
  -e TZ=Asia/Yangon \
  -e PYTHONUNBUFFERED=1 \
  be-matino

echo "Container started with logs mounted to: $(pwd)/logs"
echo "View logs with:"
echo "  docker logs -f be-matino"
echo "  tail -f ./logs/herosaga_$(date +%Y%m%d).log"
