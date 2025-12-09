#!/usr/bin/env python3
"""
AurumBotX Hourly Monitor
Tracks bot activity and generates hourly reports
"""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

STATE_FILE = "hyperliquid_trading/hyperliquid_testnet_10k_state.json"
LOG_FILE = "bot_output.log"
REPORT_DIR = "monitoring_reports"

def load_state():
    """Load current wallet state"""
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        return None

def get_bot_status():
    """Check if bot is running"""
    try:
        with open("bot.pid", "r") as f:
            pid = int(f.read().strip())
        
        # Check if process exists
        try:
            os.kill(pid, 0)
            return {"running": True, "pid": pid}
        except OSError:
            return {"running": False, "pid": None}
    except:
        return {"running": False, "pid": None}

def count_cycles_today():
    """Count how many cycles executed today"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        count = 0
        
        with open(LOG_FILE, "r") as f:
            for line in f:
                if today in line and "CYCLE START" in line:
                    count += 1
        
        return count
    except:
        return 0

def get_latest_prices():
    """Extract latest prices from log"""
    prices = {}
    try:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
        
        # Read last 100 lines
        for line in lines[-100:]:
            if "💰 Price:" in line:
                # Extract pair and price
                parts = line.split("---")
                if len(parts) > 1:
                    pair = parts[1].strip().replace("Analyzing", "").strip().replace("---", "")
                    
                    # Find price
                    if "$" in line:
                        price_str = line.split("$")[1].split("(")[0].strip()
                        try:
                            price = float(price_str.replace(",", ""))
                            prices[pair] = price
                        except:
                            pass
        
        return prices
    except:
        return {}

def generate_report():
    """Generate hourly monitoring report"""
    
    # Create report directory
    os.makedirs(REPORT_DIR, exist_ok=True)
    
    # Load data
    state = load_state()
    bot_status = get_bot_status()
    cycles_today = count_cycles_today()
    prices = get_latest_prices()
    
    # Generate report
    timestamp = datetime.now()
    report = []
    
    report.append("=" * 80)
    report.append(f"🤖 AurumBotX Hourly Report - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 80)
    report.append("")
    
    # Bot Status
    report.append("📊 Bot Status")
    report.append("-" * 80)
    if bot_status["running"]:
        report.append(f"✅ Status: RUNNING (PID: {bot_status['pid']})")
    else:
        report.append("❌ Status: STOPPED")
    report.append(f"🔄 Cycles Today: {cycles_today}")
    report.append("")
    
    # Trading Statistics
    if state:
        report.append("💰 Trading Statistics")
        report.append("-" * 80)
        report.append(f"Capital: €{state['current_capital']:,.2f}")
        report.append(f"Total Trades: {state['total_trades']}")
        report.append(f"Daily Trades: {state['daily_trades']}/{state.get('max_daily_trades', 12)}")
        report.append(f"Winning Trades: {state['winning_trades']}")
        report.append(f"Losing Trades: {state['losing_trades']}")
        
        if state['total_trades'] > 0:
            win_rate = (state['winning_trades'] / state['total_trades']) * 100
            report.append(f"Win Rate: {win_rate:.1f}%")
            
            roi = ((state['current_capital'] - state['initial_capital']) / state['initial_capital']) * 100
            report.append(f"ROI: {roi:+.2f}%")
        
        report.append(f"Bear Market Skipped: {state['bear_market_skipped']}")
        report.append(f"Low Confidence Skipped: {state['low_confidence_skipped']}")
        report.append(f"Last Update: {state['updated_at']}")
        report.append("")
    
    # Latest Prices
    if prices:
        report.append("📈 Latest Market Prices")
        report.append("-" * 80)
        for pair, price in sorted(prices.items()):
            report.append(f"{pair}: ${price:,.2f}")
        report.append("")
    
    # Recent Activity
    if state and state.get('trade_history'):
        report.append("📝 Recent Trades (Last 5)")
        report.append("-" * 80)
        recent_trades = state['trade_history'][-5:]
        for trade in recent_trades:
            ts = datetime.fromisoformat(trade['timestamp']).strftime('%Y-%m-%d %H:%M')
            report.append(f"{ts} | {trade['pair']} | {trade['action']} | ${trade['price']:,.2f} | {trade['confidence']:.1f}%")
        report.append("")
    
    report.append("=" * 80)
    
    # Save report
    report_text = "\n".join(report)
    report_file = os.path.join(REPORT_DIR, f"report_{timestamp.strftime('%Y%m%d_%H%M%S')}.txt")
    
    with open(report_file, "w") as f:
        f.write(report_text)
    
    # Also save as latest
    with open(os.path.join(REPORT_DIR, "latest_report.txt"), "w") as f:
        f.write(report_text)
    
    # Print to console
    print(report_text)
    
    return report_file

def main():
    """Main monitoring loop"""
    print("🚀 AurumBotX Hourly Monitor Started")
    print(f"📁 Reports will be saved to: {REPORT_DIR}/")
    print("")
    
    while True:
        try:
            print(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Generating report...")
            report_file = generate_report()
            print(f"✅ Report saved: {report_file}")
            print(f"⏳ Next report in 1 hour...")
            
            # Sleep for 1 hour
            time.sleep(3600)
            
        except KeyboardInterrupt:
            print("\n\n🛑 Monitor stopped by user")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            print("⏳ Retrying in 1 hour...")
            time.sleep(3600)

if __name__ == "__main__":
    main()
