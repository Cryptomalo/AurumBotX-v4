#!/bin/bash
# AurumBotX Monitor Script

echo "🤖 AurumBotX Status Monitor"
echo "======================================"
echo ""

# Check if bot is running
if [ -f bot.pid ]; then
    PID=$(cat bot.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "✅ Bot Status: RUNNING (PID: $PID)"
        UPTIME=$(ps -p $PID -o etime= | tr -d ' ')
        echo "⏱️  Uptime: $UPTIME"
    else
        echo "❌ Bot Status: STOPPED"
    fi
else
    echo "❌ Bot Status: NOT STARTED"
fi

echo ""
echo "📊 Latest Statistics:"
echo "--------------------------------------"

# Check state file
if [ -f hyperliquid_trading/hyperliquid_testnet_10k_state.json ]; then
    python3 << 'PYEOF'
import json
try:
    with open("hyperliquid_trading/hyperliquid_testnet_10k_state.json", "r") as f:
        state = json.load(f)
    
    print(f"💰 Capital: €{state['current_capital']:,.2f}")
    print(f"📈 Total Trades: {state['total_trades']}")
    print(f"📅 Daily Trades: {state['daily_trades']}/{state.get('max_daily_trades', 12)}")
    print(f"✅ Winning: {state['winning_trades']}")
    print(f"❌ Losing: {state['losing_trades']}")
    
    if state['total_trades'] > 0:
        win_rate = (state['winning_trades'] / state['total_trades']) * 100
        print(f"🎯 Win Rate: {win_rate:.1f}%")
    
    print(f"🐻 Bear Market Skipped: {state['bear_market_skipped']}")
    print(f"⚠️  Low Confidence Skipped: {state['low_confidence_skipped']}")
    print(f"🕐 Last Update: {state['updated_at']}")
    
except Exception as e:
    print(f"Error reading state: {e}")
PYEOF
else
    echo "No state file found"
fi

echo ""
echo "📝 Recent Log (last 10 lines):"
echo "--------------------------------------"
tail -10 bot_output.log

echo ""
echo "======================================"
