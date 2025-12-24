#!/usr/bin/env python3
"""
AurumBotX Hyperliquid Testnet Wallet Runner
Version: 4.1 Hyperliquid
Environment: Hyperliquid Testnet + Oracle Cloud
"""

import json
import time
import sys
import os
from datetime import datetime, timedelta
from openai import OpenAI
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from eth_account import Account


# Configuration
CONFIG_FILE = sys.argv[1] if len(sys.argv) > 1 else "config/hyperliquid_testnet_10k.json"
STATE_DIR = os.getenv("STATE_DIR", "./hyperliquid_trading")
LOG_DIR = os.getenv("LOG_DIR", "./logs")

# Ensure directories exist
os.makedirs(STATE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

def log(message, level="INFO"):
    """Log message to file and stdout"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] [{level}] {message}"
    print(log_message)
    
    # Write to log file
    log_file = os.path.join(LOG_DIR, f"hyperliquid_trading_{datetime.now().strftime('%Y%m%d')}.log")
    with open(log_file, "a") as f:
        f.write(log_message + "\n")

def load_config():
    """Load configuration"""
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        log(f"Error loading config: {e}", "ERROR")
        sys.exit(1)

def load_state(config):
    """Load wallet state"""
    state_file = os.path.join(STATE_DIR, f"{config['wallet_name']}_state.json")
    
    if os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                return json.load(f)
        except Exception as e:
            log(f"Error loading state: {e}", "WARNING")
    
    # Initialize new state
    return {
        "wallet_name": config["wallet_name"],
        "initial_capital": config["initial_capital"],
        "current_capital": config["initial_capital"],
        "current_level": "TURTLE",
        "total_trades": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "trade_history": [],
        "open_position": None,
        "daily_trades": 0,
        "last_trade_date": None,
        "bear_market_skipped": 0,
        "low_confidence_skipped": 0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

def save_state(state):
    """Save wallet state"""
    config = load_config()
    state_file = os.path.join(STATE_DIR, f"{config['wallet_name']}_state.json")
    
    state["updated_at"] = datetime.now().isoformat()
    
    try:
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
        log(f"State saved: {state_file}")
    except Exception as e:
        log(f"Error saving state: {e}", "ERROR")

def get_hyperliquid_info(testnet=True):
    """Get Hyperliquid Info client"""
    api_url = constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL
    return Info(api_url, skip_ws=True)

def get_hyperliquid_exchange(account_address, secret_key, testnet=True):
    """Get Hyperliquid Exchange client"""
    api_url = constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL
    
    # Create account from private key
    account = Account.from_key(secret_key)
    
    return Exchange(account, api_url)

def get_live_price(info, symbol):
    """Get live price from Hyperliquid"""
    try:
        # Get all mids (current prices)
        all_mids = info.all_mids()
        
        # Find the symbol
        if symbol in all_mids:
            price = float(all_mids[symbol])
            
            # Get 24h stats
            meta = info.meta()
            universe = meta.get("universe", [])
            
            # Find symbol in universe
            symbol_data = None
            for asset in universe:
                if asset.get("name") == symbol:
                    symbol_data = asset
                    break
            
            if symbol_data:
                # Get funding rate as proxy for 24h change (Hyperliquid doesn't provide 24h change directly)
                funding = symbol_data.get("funding", "0")
                
                return {
                    "symbol": symbol,
                    "price": price,
                    "change_24h": float(funding) * 100,  # Approximate
                    "volume": 0,  # Not easily available
                    "high_24h": price * 1.02,  # Estimate
                    "low_24h": price * 0.98   # Estimate
                }
            else:
                return {
                    "symbol": symbol,
                    "price": price,
                    "change_24h": 0,
                    "volume": 0,
                    "high_24h": price,
                    "low_24h": price
                }
        else:
            log(f"Symbol {symbol} not found in market data", "ERROR")
            return None
            
    except Exception as e:
        log(f"Error fetching price for {symbol}: {e}", "ERROR")
        return None

def detect_trend(price_data):
    """Detect market trend"""
    if not price_data:
        return "UNKNOWN"
    
    change = price_data["change_24h"]
    
    if change > 2.0:
        return "BULLISH"
    elif change < -2.0:
        return "BEARISH"
    else:
        return "SIDEWAYS"

def ai_analysis(pair, price_data, trend, trade_history):
    """AI-powered trading decision"""
    try:
        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Formatta la cronologia degli ultimi 5 trade per l'AI
        recent_trades = trade_history[-5:]
        history_text = "Nessun trade precedente registrato."
        if recent_trades:
            history_text = "Cronologia degli ultimi trade (dal più vecchio al più recente):\n"
            for trade in recent_trades:
                history_text += f"- {trade['timestamp'][:10]} {trade['pair']} {trade['action']} @ ${trade['price']:.2f} (Conf: {trade['confidence']:.1f}%) - Ragione: {trade['reasoning']}\n"
        
        prompt = f"""You are an ultra-resilient crypto trading analyst. Your goal is to learn from past mistakes and improve your confidence in the current decision.
        
{history_text}

Analizza la cronologia dei trade. Se i trade precedenti con bassa confidenza o ragioni specifiche hanno fallito, usa questa informazione per aumentare la soglia di confidenza o modificare la tua raccomandazione.

Analizza i seguenti dati di mercato e fornisci una raccomandazione di trading.

Pair: {pair}
Current Price: ${price_data['price']:,.2f}
24h Change: {price_data['change_24h']:.2f}%
24h High: ${price_data['high_24h']:,.2f}
24h Low: ${price_data['low_24h']:,.2f}
Trend: {trend}

Fornisci SOLO la risposta nel formato esatto: ACTION|CONFIDENCE|REASONING.
Non includere testo aggiuntivo, introduzioni o spiegazioni al di fuori del formato.

1. Action: BUY, SELL, or HOLD
2. Confidence: 0-100% (Aumenta la confidenza se la tua analisi attuale è in linea con i trade di successo passati o se correggi un errore passato)
3. Reasoning: Breve spiegazione che includa un riferimento a come la cronologia dei trade ha influenzato la tua decisione.

Format: ACTION|CONFIDENCE|REASONING"""

        response = client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.3
        )
        
        result = response.choices[0].message.content.strip()
        parts = result.split("|")
        
        if len(parts) >= 3:
            action = parts[0].strip()
            confidence = float(parts[1].strip().replace("%", ""))
            reasoning = parts[2].strip()
            
            return {
                "action": action,
                "confidence": confidence,
                "reasoning": reasoning
            }
        else:
            log(f"AI response format invalid: {result}", "WARNING")
            return None
            
    except Exception as e:
        log(f"AI analysis error: {e}", "ERROR")
        return None

def execute_cycle():
    """Execute one trading cycle"""
    log("=" * 80)
    log("🔄 CYCLE START - Hyperliquid Testnet")
    log("=" * 80)
    
    config = load_config()
    state = load_state(config)
    
    # Reset daily counter if new day
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("last_trade_date") != today:
        state["daily_trades"] = 0
        state["last_trade_date"] = today
        log(f"📅 New day: {today} - Daily counter reset")
    
    # Check daily limit
    if state["daily_trades"] >= config.get("max_daily_trades", 12):
        log(f"⏸️  Daily trade limit reached: {state['daily_trades']}/{config['max_daily_trades']}")
        save_state(state)
        return
    
    # Check if position open
    if state.get("open_position"):
        log("📊 Open position detected - checking exit conditions")
        # In production, implement position monitoring
        # For now, just log
        save_state(state)
        return
    
    # Initialize Hyperliquid clients
    try:
        info = get_hyperliquid_info(testnet=True)
        log("✅ Connected to Hyperliquid Testnet")
    except Exception as e:
        log(f"❌ Failed to connect to Hyperliquid: {e}", "ERROR")
        return
    
    # Analyze each pair
    pairs = config.get("trading_pairs", ["BTC", "ETH", "SOL"])
    
    for pair in pairs:
        log(f"\n--- Analyzing {pair} ---")
        
        # Get live price
        price_data = get_live_price(info, pair)
        if not price_data:
            log(f"❌ Failed to get price for {pair}")
            continue
        
        log(f"💰 Price: ${price_data['price']:,.2f} ({price_data['change_24h']:+.2f}% 24h)")
        
        # Detect trend
        trend = detect_trend(price_data)
        log(f"📈 Trend: {trend}")
        
        # AI analysis
        analysis = ai_analysis(pair, price_data, trend, state["trade_history"])
        if not analysis:
            log(f"❌ AI analysis failed for {pair}")
            continue
        
        log(f"🤖 AI Recommendation: {analysis['action']} (Confidence: {analysis['confidence']:.1f}%)")
        log(f"💭 Reasoning: {analysis['reasoning']}")
        
        # Check if should trade
        min_confidence = config.get("min_confidence", 60.0)
        
        if analysis["action"] == "HOLD":
            log(f"⏸️  AI recommends HOLD - skipping")
            continue
        
        if analysis["confidence"] < min_confidence:
            log(f"⚠️  Confidence {analysis['confidence']:.1f}% < {min_confidence}% threshold - skipping")
            state["low_confidence_skipped"] += 1
            continue
        
        # Bear market filter
        if trend == "BEARISH" and analysis["action"] == "BUY":
            log(f"🐻 Bear market detected - skipping BUY signal")
            state["bear_market_skipped"] += 1
            continue
        
        # Execute trade (simulated for testnet paper trading)
        log(f"✅ TRADE SIGNAL: {analysis['action']} {pair}")
        log(f"   Confidence: {analysis['confidence']:.1f}%")
        log(f"   Price: ${price_data['price']:,.2f}")
        log(f"   📝 NOTE: Testnet paper trading - no real funds at risk")
        
        # Update state
        state["daily_trades"] += 1
        state["total_trades"] += 1
        
        # Record trade
        trade_record = {
            "timestamp": datetime.now().isoformat(),
            "pair": pair,
            "action": analysis["action"],
            "price": price_data['price'],
            "confidence": analysis['confidence'],
            "reasoning": analysis['reasoning'],
            "trend": trend
        }
        state["trade_history"].append(trade_record)
        
        log(f"📊 Daily trades: {state['daily_trades']}/{config['max_daily_trades']}")
        
        # Save state
        save_state(state)
        
        # Only one trade per cycle
        break
    
    log("\n" + "=" * 80)
    log("✅ CYCLE COMPLETE")
    log(f"📊 Statistics:")
    log(f"   Total Trades: {state['total_trades']}")
    log(f"   Daily Trades: {state['daily_trades']}/{config['max_daily_trades']}")
    log(f"   Bear Market Skipped: {state['bear_market_skipped']}")
    log(f"   Low Confidence Skipped: {state['low_confidence_skipped']}")
    log("=" * 80)
    
    # Save final state
    save_state(state)

def main():
    """Main entry point"""
    try:
        log("🚀 AurumBotX Hyperliquid Testnet Wallet Runner v4.1")
        log(f"📁 Config: {CONFIG_FILE}")
        log(f"📂 State Dir: {STATE_DIR}")
        log(f"📝 Log Dir: {LOG_DIR}")
        log(f"🌐 Network: Hyperliquid Testnet")
        log(f"💰 Paper Trading: YES (No real funds at risk)")
        
        execute_cycle()
        
        log("✅ Execution completed successfully")
        sys.exit(0)
        
    except Exception as e:
        log(f"❌ Fatal error: {e}", "ERROR")
        import traceback
        log(traceback.format_exc(), "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()
