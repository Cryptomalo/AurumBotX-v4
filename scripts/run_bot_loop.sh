#!/bin/bash
cd /home/ubuntu/AurumBotX
source venv/bin/activate

while true; do
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting cycle..."
    python3 wallet_runner_hyperliquid.py config/hyperliquid_testnet_10k.json
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Cycle complete. Sleeping 1 hour..."
    sleep 3600
done
