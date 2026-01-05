"""
API Server for AurumBotX-v4
Exposes REST endpoints to read bot state and trade history
"""

import json
import os
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS
import logging

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
STATE_FILE = Path(__file__).parent.parent / "hyperliquid_trading" / "hyperliquid_testnet_10k_state.json"
CONFIG_FILE = Path(__file__).parent.parent / "config" / "hyperliquid_testnet_10k.json"

def load_state():
    """Load bot state from JSON file"""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        return None
    except Exception as e:
        logger.error(f"Error loading state: {e}")
        return None

def load_config():
    """Load bot configuration from JSON file"""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        return None
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return None

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    })

@app.route('/api/bot/status', methods=['GET'])
def bot_status():
    """Get current bot status"""
    state = load_state()
    config = load_config()
    
    if not state:
        return jsonify({"error": "Bot state not found"}), 404
    
    return jsonify({
        "capital_current": state.get("capital_current", 0),
        "capital_initial": state.get("capital_initial", 0),
        "trades_total": state.get("trades_total", 0),
        "trades_won": state.get("trades_won", 0),
        "trades_lost": state.get("trades_lost", 0),
        "last_updated": state.get("last_updated"),
        "trading_level": state.get("trading_level", "TURTLE"),
        "position": state.get("position"),
        "config": config
    })

@app.route('/api/bot/trades', methods=['GET'])
def bot_trades():
    """Get trade history"""
    state = load_state()
    
    if not state:
        return jsonify({"error": "Bot state not found"}), 404
    
    trades = state.get("trade_history", [])
    
    # Support pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    start = (page - 1) * per_page
    end = start + per_page
    
    paginated_trades = trades[start:end]
    
    return jsonify({
        "trades": paginated_trades,
        "total": len(trades),
        "page": page,
        "per_page": per_page,
        "pages": (len(trades) + per_page - 1) // per_page
    })

@app.route('/api/bot/trades/<int:trade_id>', methods=['GET'])
def bot_trade_detail(trade_id):
    """Get specific trade details"""
    state = load_state()
    
    if not state:
        return jsonify({"error": "Bot state not found"}), 404
    
    trades = state.get("trade_history", [])
    
    if trade_id < 0 or trade_id >= len(trades):
        return jsonify({"error": "Trade not found"}), 404
    
    return jsonify(trades[trade_id])

@app.route('/api/bot/performance', methods=['GET'])
def bot_performance():
    """Get performance metrics"""
    state = load_state()
    
    if not state:
        return jsonify({"error": "Bot state not found"}), 404
    
    trades = state.get("trade_history", [])
    
    # Calculate performance metrics
    total_trades = len(trades)
    won_trades = state.get("trades_won", 0)
    lost_trades = state.get("trades_lost", 0)
    
    win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0
    
    # Calculate PnL
    capital_initial = state.get("capital_initial", 10000)
    capital_current = state.get("capital_current", capital_initial)
    pnl = capital_current - capital_initial
    pnl_percentage = (pnl / capital_initial * 100) if capital_initial > 0 else 0
    
    # Group trades by pair
    trades_by_pair = {}
    for trade in trades:
        pair = trade.get("pair", "UNKNOWN")
        if pair not in trades_by_pair:
            trades_by_pair[pair] = {
                "total": 0,
                "won": 0,
                "lost": 0,
                "pnl": 0
            }
        trades_by_pair[pair]["total"] += 1
        if trade.get("result") == "won":
            trades_by_pair[pair]["won"] += 1
        elif trade.get("result") == "lost":
            trades_by_pair[pair]["lost"] += 1
    
    return jsonify({
        "total_trades": total_trades,
        "won_trades": won_trades,
        "lost_trades": lost_trades,
        "win_rate": win_rate,
        "capital_initial": capital_initial,
        "capital_current": capital_current,
        "pnl": pnl,
        "pnl_percentage": pnl_percentage,
        "trades_by_pair": trades_by_pair
    })

@app.route('/api/bot/config', methods=['GET'])
def bot_config():
    """Get bot configuration"""
    config = load_config()
    
    if not config:
        return jsonify({"error": "Bot config not found"}), 404
    
    return jsonify(config)

@app.route('/api/bot/config', methods=['POST'])
def update_bot_config():
    """Update bot configuration"""
    try:
        data = request.get_json()
        
        config = load_config() or {}
        config.update(data)
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Bot config updated: {data}")
        return jsonify({"status": "success", "config": config})
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return jsonify({"error": str(e)}), 400

@app.route('/api/bot/state', methods=['GET'])
def bot_state():
    """Get complete bot state"""
    state = load_state()
    
    if not state:
        return jsonify({"error": "Bot state not found"}), 404
    
    return jsonify(state)

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Run on port 5000 (configurable)
    port = os.getenv('API_PORT', 5000)
    debug = os.getenv('API_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting API server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
