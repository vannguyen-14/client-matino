#!/bin/bash
# restart.sh - Restart container without rebuilding

echo "Restarting be-matino container..."

sudo docker restart be-matino

echo "Container restarted. Checking status..."
sleep 2
sudo docker ps | grep be-matino

echo ""
echo "View logs with: ./view-logs.sh"
