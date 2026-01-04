import logging
import time
from typing import Dict, List, Optional, Any, Type
from datetime import datetime
import pandas as pd
import numpy as np
from rich.console import Console
from rich.table import Table

from broker.kite.live_data_manager import LiveDataManager
from trade.paper.paper_broker import PaperBroker
from trade.market_structure_strategy import MarketStructureStrategy
from trade.option_strategy import OptionStrategy
from trade.trend_momentum_strategy import TrendMomentumStrategy, Trade

logger = logging.getLogger(__name__)

class PaperTradeEngine:
    """
    Engine for Paper Trading with Multi-Timeframe Live Streaming.
    Manages the lifecycle of paper trades using existing strategy logic.
    """
    def __init__(self, config: Dict):
        self.config = config
        self.broker = PaperBroker(config)
        self.data_manager = None
        self.symbols = config.get('symbols', [])
        self.instrument_tokens = config.get('instrument_tokens', {}) 
        
        # Timeframes: use lower and upper from config if available
        self.lower_interval = config.get('lower_interval', '15min')
        self.upper_interval = config.get('upper_interval', '60min')
        self.timeframes = [self.lower_interval, self.upper_interval]
        
        self.strategy_name = config.get('strategy', 'market_structure')
        self.strategies: Dict[str, Any] = {}
        
        # Trade tracking
        self.signals: List[Dict] = []  # SIGNAL_GENERATED
        self.active_paper_trades: List[Dict] = []  # OPEN
        self.completed_trades: List[Trade] = []  # CLOSED
        
        self.console = Console()
        self._is_running = False

    def initialize(self):
        """Initialize connection, data manager and strategies."""
        if not self.broker.connect():
            logger.error("Failed to connect PaperBroker to Kite")
            return False
        
        self.data_manager = LiveDataManager(self.broker.kite, {'timeframes': self.timeframes})
        
        strategy_class = self._get_strategy_class(self.strategy_name)
        
        for symbol in self.symbols:
            token = self.instrument_tokens.get(symbol)
            if token:
                self.data_manager.subscribe_to_instrument(token, self.timeframes)
                self.data_manager.register_callback(token, self._on_candle_complete)
                # Initialize strategy for each symbol
                self.strategies[symbol] = strategy_class(self.config, symbol)
                logger.info(f"Initialized {self.strategy_name} strategy for {symbol}")
            else:
                logger.warning(f"No instrument token found for symbol: {symbol}")
        
        return True

    def _get_strategy_class(self, name: str) -> Type:
        if name == 'option':
            return OptionStrategy
        elif name == 'trend_momentum':
            return TrendMomentumStrategy
        else:
            return MarketStructureStrategy

    def start(self):
        """Start the live streaming and execution."""
        if not self.data_manager:
            if not self.initialize():
                return
        
        api_key = self.config.get('api_key')
        access_token = self.config.get('access_token')
        user_id = self.config.get('user_id')
        
        if not all([api_key, access_token, user_id]):
            logger.error("Missing Kite credentials in config")
            return

        self.data_manager.start_websocket(api_key, access_token, user_id)
        self._is_running = True
        logger.info(f"PaperTradeEngine started for {self.symbols} using {self.strategy_name} strategy")

    def manual_exit(self, symbol: str, entry_time: str):
        """Force exit an active paper trade."""
        if symbol not in self.strategies:
            return False, "Strategy for symbol not found"
        
        strategy = self.strategies[symbol]
        current_price = self.broker.get_current_price(symbol)
        exit_time = datetime.now().isoformat()
        
        # Check if strategy has force_exit method
        if hasattr(strategy, 'force_exit'):
            if strategy.force_exit(entry_time, current_price, exit_time):
                # Update completed trades
                # We need to find the trade that was just completed
                new_completed = [t for t in strategy.completed_trades if t.entry_time == entry_time]
                if new_completed:
                    t = new_completed[0]
                    if not any(ct.entry_time == t.entry_time and getattr(ct, 'symbol', '') == symbol for ct in self.completed_trades):
                        t.symbol = symbol
                        self.completed_trades.append(t)
                
                # Update active_paper_trades
                self.active_paper_trades = [pat for pat in self.active_paper_trades 
                                           if not (pat['symbol'] == symbol and pat['entry_time'] == entry_time)]
                
                logger.info(f"🛑 Manual Exit confirmed for {symbol} trade at {entry_time}")
                return True, "Exit successful"
            else:
                return False, "Trade not found in strategy"
        else:
            return False, "Strategy does not support manual exit"

    def stop(self):
        """Stop and show final summary."""
        if self.data_manager:
            self.data_manager.stop_websocket()
        self.broker.disconnect()
        self._is_running = False
        logger.info("PaperTradeEngine stopped")

    def _on_candle_complete(self, instrument_token: str, candle_data: Dict):
        """
        Callback triggered when a candle is completed.
        Runs strategy logic on accumulated live data.
        """
        symbol = self._get_symbol_from_token(instrument_token)
        if not symbol or symbol not in self.strategies:
            return

        # Fetch DataFrames for both timeframes
        df_lower = self.data_manager.get_dataframe(instrument_token, self.lower_interval)
        df_upper = self.data_manager.get_dataframe(instrument_token, self.upper_interval)

        if df_lower is None or df_upper is None or df_lower.empty or df_upper.empty:
            return

        # We need enough data for indicators
        if len(df_lower) < 20: 
            return

        # Calculate Indicators (re-using logic from run_backtest.py helper or similar)
        # For simplicity, we can use a helper method here.
        df_lower = self._calculate_indicators(df_lower)
        df_upper = self._calculate_indicators(df_upper)

        # Ensure 'date' column exists for strategies
        if 'date' not in df_lower.columns:
            df_lower = df_lower.reset_index().rename(columns={'timestamp': 'date'})
        if 'date' not in df_upper.columns:
            df_upper = df_upper.reset_index().rename(columns={'timestamp': 'date'})

        # Run strategy logic
        strategy = self.strategies[symbol]
        
        # run_backtest now updates internal state
        completed = strategy.run_backtest(df_lower, df_upper)
        
        # Sync completed trades
        for t in completed:
            if not any(ct.entry_time == t.entry_time and ct.option_type == t.option_type and getattr(ct, 'symbol', '') == symbol for ct in self.completed_trades):
                t.symbol = symbol
                self.completed_trades.append(t)
                logger.info(f"✅ Trade Closed [{symbol} {t.option_type}]: P&L {t.pnl:.2f}")

        # Check for active trades in strategy state
        # OptionStrategy uses self.active_trades (dict), others use self.active_trade (single)
        active_trades = []
        if hasattr(strategy, 'active_trades'):
            active_trades = [t for t in strategy.active_trades.values() if t is not None]
        elif hasattr(strategy, 'active_trade') and strategy.active_trade:
            active_trades = [strategy.active_trade]

        # Update our active trades tracking
        # For paper trading, we might want to "confirm" execution
        for at in active_trades:
            # Check if we already have this trade as active
            if not any(pat['entry_time'] == at.entry_time and pat['option_type'] == at.option_type and pat['symbol'] == symbol for pat in self.active_paper_trades):
                # New signal confirmed!
                new_trade = {
                    'symbol': symbol,
                    'option_type': at.option_type,
                    'pattern': at.pattern,
                    'entry_time': at.entry_time,
                    'entry_price': at.entry_price,
                    'stop_loss': at.stop_loss,
                    'status': 'OPEN',
                    'ltp': at.entry_price, # Initial LTP
                    'pnl': 0.0
                }
                self.active_paper_trades.append(new_trade)
                logger.info(f"🚀 New Paper Trade OPEN [{symbol} {at.option_type}] @ {at.entry_price}")

        # Update LTP and P&L for active trades
        current_price = self.broker.get_current_price(symbol)
        for pat in self.active_paper_trades:
            if pat['symbol'] == symbol:
                pat['ltp'] = current_price
                if pat['option_type'] == 'CALL':
                    pat['pnl'] = (current_price - pat['entry_price'])
                else:
                    pat['pnl'] = (pat['entry_price'] - current_price)

        # Remove trades from active_paper_trades if they are now in completed_trades
        self.active_paper_trades = [pat for pat in self.active_paper_trades 
                                   if not any(ct.entry_time == pat['entry_time'] and ct.option_type == pat['option_type'] and getattr(ct, 'symbol', '') == pat['symbol'] for ct in self.completed_trades)]

        self.display_summary()

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate necessary indicators for the strategy."""
        import pandas_ta as ta
        df = df.copy()
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        # EMA
        for period in [20, 50, 200]:
            df[f'ema{period}'] = ta.ema(df['close'], length=period)
        
        # ADX
        adx = ta.adx(df['high'], df['low'], df['close'], length=14)
        if adx is not None:
            df['ADX'] = adx.iloc[:, 0]
            df['DMP'] = adx.iloc[:, 1]
            df['DMN'] = adx.iloc[:, 2]
            
        # MACD
        macd = ta.macd(df['close'])
        if macd is not None:
            df = pd.concat([df, macd], axis=1)
            
        # Stochastic
        stoch = ta.stoch(df['high'], df['low'], df['close'])
        if stoch is not None:
            df = pd.concat([df, stoch], axis=1)
            
        return df

    def display_summary(self):
        """Display trade summary in console."""
        if not self.completed_trades and not self.active_paper_trades:
            return

        table = Table(title=f"📝 Paper Trade Summary (Live)")
        table.add_column("Symbol", style="bold")
        table.add_column("Type", style="cyan")
        table.add_column("Pattern", style="yellow")
        table.add_column("Entry Time", style="green")
        table.add_column("Price/LTP", justify="right")
        table.add_column("P&L", justify="right", style="bold")
        table.add_column("Status", justify="center")

        # Active trades
        for t in self.active_paper_trades:
            pnl = t['pnl']
            style = "green" if pnl > 0 else "red"
            table.add_row(
                t['symbol'],
                t['option_type'],
                t['pattern'],
                t['entry_time'],
                f"{t['ltp']:.2f}",
                f"[{style}]{pnl:.2f}[/{style}]",
                "[bold blue]OPEN[/bold blue]"
            )

        # Completed trades
        for t in reversed(self.completed_trades[-10:]): # Show last 10
            pnl = t.pnl if hasattr(t, 'pnl') else 0
            style = "green" if pnl > 0 else "red"
            table.add_row(
                getattr(t, 'symbol', '---'),
                t.option_type,
                t.pattern,
                t.entry_time,
                f"{t.exit_price:.2f}" if t.exit_price else "N/A",
                f"[{style}]{pnl:.2f}[/{style}]",
                "CLOSED"
            )

        self.console.clear()
        self.console.print(table)

    def _get_symbol_from_token(self, token: str) -> str:
        for symbol, t in self.instrument_tokens.items():
            if str(t) == str(token):
                return symbol
        return None

# For backward compatibility if needed
PaperTradeExecutor = PaperTradeEngine
