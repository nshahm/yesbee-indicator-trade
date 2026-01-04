from fastapi import APIRouter
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/paper", tags=["paper-trade"])

import yaml
from pathlib import Path
from trade.paper.paper_executor import PaperTradeEngine

# Shared instance that will be populated when paper trade starts
executor_instance = None

def load_config():
    config_path = Path("config/kite-config.yaml")
    options_path = Path("config/options.yaml")
    
    with open(config_path, "r") as f:
        kite_config = yaml.safe_load(f)
    with open(options_path, "r") as f:
        options = yaml.safe_load(f)
        
    config = {**kite_config['kite']['api'], **options}
    config['user_id'] = kite_config['kite']['api'].get('user_id')
    config['api_key'] = kite_config['kite']['api'].get('key')
    config['access_token'] = kite_config['kite']['api'].get('access_token')
    
    symbols = []
    tokens = {}
    for key, idx in options.get('indices', {}).items():
        if idx.get('enabled'):
            sym = idx.get('symbol')
            symbols.append(sym)
            token_map = {
                'NIFTY50': '256265', 
                'BANKNIFTY': '260105', 
                'FINNIFTY': '257801',
                'NIFTY_FINANCE': '257801',
                'SENSEX': '265'
            }
            tokens[sym] = token_map.get(sym, '256265')
            
    config['symbols'] = symbols
    config['instrument_tokens'] = tokens
    return config

@router.post("/start")
async def start_paper_trade():
    global executor_instance
    if executor_instance and executor_instance._is_running:
        return {"success": False, "message": "Paper trade already running"}
    
    try:
        config = load_config()
        if not config['symbols']:
            return {"success": False, "message": "No symbols enabled in settings"}
            
        executor_instance = PaperTradeEngine(config)
        executor_instance.start()
        return {"success": True, "message": f"Paper trade started for {config['symbols']}"}
    except Exception as e:
        logger.error(f"Failed to start paper trade: {e}")
        return {"success": False, "message": str(e)}

@router.post("/stop")
async def stop_paper_trade():
    global executor_instance
    if not executor_instance or not executor_instance._is_running:
        return {"success": False, "message": "Paper trade not running"}
    
    try:
        executor_instance.stop()
        return {"success": True, "message": "Paper trade stopped"}
    except Exception as e:
        logger.error(f"Failed to stop paper trade: {e}")
        return {"success": False, "message": str(e)}

@router.get("/status")
async def get_status():
    if executor_instance is None:
        return {"status": "not_running", "message": "Paper trade executor not active"}
    
    return {
        "status": "running" if executor_instance._is_running else "stopped",
        "symbols": executor_instance.symbols,
        "timeframes": executor_instance.timeframes,
        "strategy": executor_instance.strategy_name,
        "completed_trades_count": len(executor_instance.completed_trades),
        "active_trades_count": len(executor_instance.active_paper_trades)
    }

@router.get("/summary")
async def get_summary():
    if executor_instance is None:
        return {"indices": {}}
        
    summary = {}
    for symbol in executor_instance.symbols:
        symbol_completed = [t for t in executor_instance.completed_trades if getattr(t, 'symbol', '') == symbol]
        symbol_active = [t for t in executor_instance.active_paper_trades if t['symbol'] == symbol]
        
        wins = len([t for t in symbol_completed if getattr(t, 'pnl', 0) > 0])
        losses = len([t for t in symbol_completed if getattr(t, 'pnl', 0) <= 0])
        total_pnl = sum([getattr(t, 'pnl', 0) for t in symbol_completed])
        unrealized_pnl = sum([t['pnl'] for t in symbol_active])
        
        # Get latest LTP from broker
        current_price = executor_instance.broker.get_current_price(symbol)
        
        summary[symbol] = {
            "symbol": symbol,
            "current_price": current_price,
            "total_trades": len(symbol_completed),
            "wins": wins,
            "losses": losses,
            "win_rate": (wins / len(symbol_completed) * 100) if symbol_completed else 0,
            "total_pnl": total_pnl,
            "unrealized_pnl": unrealized_pnl,
            "net_pnl": total_pnl + unrealized_pnl,
            "active_trades": len(symbol_active),
            "last_update": datetime.now().isoformat()
        }
    return {"indices": summary}

@router.get("/trades")
async def get_trades(symbol: Optional[str] = None):
    if executor_instance is None:
        return []
    
    # Combined list of active and completed trades
    all_trades = []
    
    # Add active trades first
    for t in executor_instance.active_paper_trades:
        if symbol and t['symbol'] != symbol: continue
        all_trades.append({
            "symbol": t['symbol'],
            "option_type": t['option_type'],
            "pattern": t['pattern'],
            "entry_time": t['entry_time'],
            "exit_time": None,
            "entry_price": t['entry_price'],
            "exit_price": None,
            "ltp": t['ltp'],
            "pnl": t['pnl'],
            "status": "OPEN"
        })
        
    # Add completed trades
    for t in reversed(executor_instance.completed_trades):
        if symbol and getattr(t, 'symbol', '') != symbol: continue
        all_trades.append({
            "symbol": getattr(t, 'symbol', 'Unknown'),
            "option_type": t.option_type,
            "pattern": t.pattern,
            "entry_time": t.entry_time,
            "exit_time": t.exit_time,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "pnl": getattr(t, 'pnl', 0),
            "status": "CLOSED"
        })
        
    return all_trades

@router.get("/performance")
async def get_performance():
    if executor_instance is None:
        return {}
        
    completed = executor_instance.completed_trades
    total_trades = len(completed)
    wins = len([t for t in completed if getattr(t, 'pnl', 0) > 0])
    losses = total_trades - wins
    
    total_pnl = sum([getattr(t, 'pnl', 0) for t in completed])
    
    # Calculate daily P&L
    daily_pnl = {}
    for t in completed:
        date = t.entry_time[:10] if t.entry_time else "Unknown"
        daily_pnl[date] = daily_pnl.get(date, 0) + getattr(t, 'pnl', 0)
        
    return {
        "total_trades": total_trades,
        "win_rate": (wins / total_trades * 100) if total_trades else 0,
        "wins": wins,
        "losses": losses,
        "total_pnl": total_pnl,
        "daily_pnl": daily_pnl
    }

@router.post("/exit")
async def manual_exit(symbol: str, entry_time: str):
    if executor_instance is None:
        return {"success": False, "message": "Paper trade executor not active"}
    
    success, message = executor_instance.manual_exit(symbol, entry_time)
    return {"success": success, "message": message}

def set_paper_executor(executor):
    global executor_instance
    executor_instance = executor
