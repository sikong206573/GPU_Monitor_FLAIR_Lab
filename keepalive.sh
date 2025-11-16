#!/bin/bash
PROJECT_DIR="$HOME/gpu_monitor"  # Auto-uses your home directory
if ! pgrep -f "gpu_monitor.py" > /dev/null; then
    cd "$PROJECT_DIR"
    nohup python3 gpu_monitor.py -c config.json > monitor.log 2>&1 &
fi
