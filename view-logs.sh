#!/bin/bash
# view-logs.sh - Updated for herosaga.log

echo "=== Hero Saga Logs ==="

if [ ! -d "./logs" ]; then
    echo "Logs directory not found."
    exit 1
fi

echo "Available log files:"
ls -lah ./logs/

echo ""
echo "Choose option:"
echo "1. View Docker container logs"
echo "2. View current application log (herosaga.log)"
echo "3. View real-time application log"
echo "4. View rotated logs (by date)"
echo "5. Search in logs"
echo "6. Log statistics"

read -p "Enter choice (1-6): " choice

case $choice in
    1)
        sudo docker logs -f be-matino
        ;;
    2)
        if [ -f "./logs/herosaga.log" ]; then
            less "./logs/herosaga.log"
        else
            echo "No herosaga.log file found"
        fi
        ;;
    3)
        if [ -f "./logs/herosaga.log" ]; then
            tail -f "./logs/herosaga.log"
        else
            echo "No herosaga.log file found"
            sudo docker logs -f be-matino
        fi
        ;;
    4)
        echo "Rotated log files:"
        ls -lah ./logs/herosaga.log.* 2>/dev/null || echo "No rotated logs found"
        read -p "Enter date (YYYY-MM-DD) or filename: " logdate
        if [ -f "./logs/herosaga.log.$logdate" ]; then
            less "./logs/herosaga.log.$logdate"
        else
            echo "File not found: ./logs/herosaga.log.$logdate"
        fi
        ;;
    5)
        read -p "Enter search term: " term
        echo "Searching in herosaga.log..."
        grep -n "$term" "./logs/herosaga.log" 2>/dev/null
        echo ""
        echo "Searching in rotated logs..."
        grep -Hn "$term" ./logs/herosaga.log.* 2>/dev/null
        ;;
    6)
        echo "=== LOG STATISTICS ==="
        echo "Directory: $(pwd)/logs"
        echo "Disk usage: $(du -sh ./logs)"
        echo ""
        if [ -f "./logs/herosaga.log" ]; then
            echo "Current log: herosaga.log"
            echo "Size: $(ls -lah ./logs/herosaga.log | awk '{print $5}')"
            echo "Lines: $(wc -l < ./logs/herosaga.log)"
            echo "Errors: $(grep -c "ERROR" ./logs/herosaga.log || echo 0)"
            echo "Warnings: $(grep -c "WARNING" ./logs/herosaga.log || echo 0)"
        fi
        echo ""
        echo "Rotated logs:"
        ls -lah ./logs/herosaga.log.* 2>/dev/null | wc -l
        ;;
    *)
        echo "Invalid choice"
        ;;
esac