from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# This will be initialized by the main app or script
executor_instance = None

router = APIRouter(prefix="/api/paper", tags=["paper-trade"])

@router.get("/status")
async def get_status():
    """Get the status of paper trading and all active/completed trades."""
    if executor_instance is None:
        return {"status": "not_initialized", "message": "Paper trade executor not started"}
    
    return {
        "status": "running" if executor_instance._is_running else "stopped",
        "symbols": executor_instance.symbols,
        "completed_trades_count": len(executor_instance.completed_trades),
        "timestamp": datetime.now().isoformat()
    }

@router.get("/trades")
async def get_trades():
    """Get all trades executed during the current session."""
    if executor_instance is None:
        return []
    
    trades_data = []
    for t in executor_instance.completed_trades:
        trades_data.append({
            "symbol": getattr(t, 'symbol', 'Unknown'),
            "option_type": t.option_type,
            "pattern": t.pattern,
            "entry_time": t.entry_time,
            "exit_time": t.exit_time,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "pnl": getattr(t, 'pnl', 0),
            "status": "closed" if t.exit_time else "open"
        })
    return trades_data

@router.get("/summary")
async def get_summary():
    """Get performance summary for each symbol."""
    if executor_instance is None:
        return {}
        
    summary = {}
    for symbol in executor_instance.symbols:
        symbol_trades = [t for t in executor_instance.completed_trades if getattr(t, 'symbol', '') == symbol]
        wins = len([t for t in symbol_trades if getattr(t, 'pnl', 0) > 0])
        losses = len([t for t in symbol_trades if getattr(t, 'pnl', 0) <= 0])
        total_pnl = sum([getattr(t, 'pnl', 0) for t in symbol_trades])
        
        summary[symbol] = {
            "total_trades": len(symbol_trades),
            "wins": wins,
            "losses": losses,
            "win_rate": (wins / len(symbol_trades) * 100) if symbol_trades else 0,
            "total_pnl": total_pnl
        }
    return summary

def set_executor(executor):
    global executor_instance
    executor_instance = executor
